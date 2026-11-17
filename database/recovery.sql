-- Apply separately to each deployment database. Set the singleton scope row
-- to the environment of that database before starting SAARTHI.
create table if not exists public.saarthi_scope (
  singleton boolean primary key default true check (singleton),
  environment text not null check (environment in ('local','preview','staging','production'))
);

create table if not exists public.saarthi_threads (
  owner text not null,
  id text not null,
  title text not null,
  updated_at timestamptz not null default now(),
  primary key (owner,id)
);

create table if not exists public.saarthi_turns (
  owner text not null,
  conversation_id text not null,
  turn_id uuid not null,
  seq bigint generated always as identity,
  fingerprint text not null,
  message text not null,
  state text not null default 'pending' check (state in ('pending','completed','failed','cancelled')),
  result jsonb,
  created_at timestamptz not null default now(),
  primary key (owner,turn_id),
  foreign key (owner,conversation_id) references public.saarthi_threads(owner,id) on delete cascade
);

create table if not exists public.saarthi_daily_usage (
  owner text not null,
  day date not null,
  count integer not null,
  primary key (owner,day)
);

create index if not exists saarthi_turn_history on public.saarthi_turns(owner,conversation_id,seq);
create index if not exists saarthi_thread_history on public.saarthi_threads(owner,updated_at desc,id);

alter table public.saarthi_scope enable row level security;
alter table public.saarthi_threads enable row level security;
alter table public.saarthi_turns enable row level security;
alter table public.saarthi_daily_usage enable row level security;
revoke all on public.saarthi_scope, public.saarthi_threads, public.saarthi_turns,
  public.saarthi_daily_usage from public, anon, authenticated;
grant select on public.saarthi_scope to service_role;
grant select,insert,update,delete on public.saarthi_threads, public.saarthi_turns,
  public.saarthi_daily_usage to service_role;

create or replace function public.saarthi_begin_turn(
  p_owner text, p_conversation text, p_turn uuid, p_message text,
  p_fingerprint text, p_daily_limit integer
) returns jsonb language plpgsql set search_path = pg_catalog, public as $$
declare
  previous public.saarthi_turns%rowtype;
  used integer;
begin
  -- Serialize reservations for this owner across API instances.
  perform pg_advisory_xact_lock(hashtextextended(p_owner, 0));
  select * into previous from public.saarthi_turns where owner=p_owner and turn_id=p_turn;
  if found then
    if previous.fingerprint <> p_fingerprint or previous.conversation_id <> p_conversation then
      return jsonb_build_object('decision','conflict');
    end if;
    if previous.state='pending' and previous.created_at < now()-interval '60 seconds' then
      update public.saarthi_turns
        set state='failed', result='{"ok":false,"execution":"interrupted","reply":"This turn was interrupted. Start a new turn to run it again.","verification":{"verified":false}}'::jsonb
        where owner=p_owner and turn_id=p_turn and state='pending';
      select * into previous from public.saarthi_turns where owner=p_owner and turn_id=p_turn;
    end if;
    return jsonb_build_object('decision',previous.state,'result',previous.result);
  end if;
  if exists(select 1 from public.saarthi_turns
            where owner=p_owner and conversation_id=p_conversation and state='pending'
              and created_at >= now()-interval '60 seconds') then
    return jsonb_build_object('decision','busy');
  end if;
  insert into public.saarthi_daily_usage as usage(owner,day,count)
    values(p_owner,(now() at time zone 'UTC')::date,1)
    on conflict(owner,day) do update set count=usage.count+1 where usage.count<p_daily_limit
    returning count into used;
  if used is null then return jsonb_build_object('decision','quota'); end if;
  insert into public.saarthi_threads(owner,id,title)
    values(p_owner,p_conversation,left(p_message,120))
    on conflict(owner,id) do update set updated_at=now();
  insert into public.saarthi_turns(owner,conversation_id,turn_id,fingerprint,message)
    values(p_owner,p_conversation,p_turn,p_fingerprint,p_message);
  return jsonb_build_object('decision','started');
end
$$;

revoke all on function public.saarthi_begin_turn(text,text,uuid,text,text,integer)
  from public, anon, authenticated;
grant execute on function public.saarthi_begin_turn(text,text,uuid,text,text,integer)
  to service_role;

-- Spend admission is separate from the transcript so deletion cannot reset quotas.
create table if not exists public.saarthi_spend (
  owner text not null,
  turn_id uuid not null,
  day date not null,
  reserved_micro_usd bigint not null check (reserved_micro_usd > 0),
  reported_micro_usd bigint check (reported_micro_usd >= 0),
  primary key (owner,turn_id)
);
create index if not exists saarthi_spend_window on public.saarthi_spend(owner,day);
alter table public.saarthi_spend enable row level security;
revoke all on public.saarthi_spend from public, anon, authenticated;
grant select,insert,update on public.saarthi_spend to service_role;

create or replace function public.saarthi_admit_turn(
  p_owner text, p_conversation text, p_turn uuid, p_message text,
  p_fingerprint text, p_daily_limit integer, p_reserve bigint, p_day_cap bigint, p_month_cap bigint
) returns jsonb language plpgsql set search_path = pg_catalog, public as $$
declare
  current_day date := (now() at time zone 'UTC')::date;
  daily_used numeric;
  monthly_used numeric;
  admission jsonb;
begin
  perform pg_advisory_xact_lock(hashtextextended(p_owner, 0));
  -- Existing turns must replay even when the budget has subsequently filled.
  if exists(select 1 from public.saarthi_turns where owner=p_owner and turn_id=p_turn) then
    return public.saarthi_begin_turn(p_owner,p_conversation,p_turn,p_message,p_fingerprint,p_daily_limit);
  end if;
  if exists(select 1 from public.saarthi_spend where owner=p_owner and turn_id=p_turn) then
    return jsonb_build_object('decision','conflict');
  end if;
  if p_reserve is null or p_day_cap is null or p_month_cap is null
     or not (0 < p_reserve and p_reserve <= p_day_cap and p_day_cap <= p_month_cap) then
    return jsonb_build_object('decision','budget');
  end if;
  select coalesce(sum(greatest(reserved_micro_usd,reported_micro_usd)) filter(where day=current_day),0),
         coalesce(sum(greatest(reserved_micro_usd,reported_micro_usd)),0)
    into daily_used, monthly_used from public.saarthi_spend
    where owner=p_owner and day>=date_trunc('month',current_day::timestamp)::date and day<=current_day;
  if daily_used+p_reserve>p_day_cap or monthly_used+p_reserve>p_month_cap then
    return jsonb_build_object('decision','budget');
  end if;
  admission := public.saarthi_begin_turn(p_owner,p_conversation,p_turn,p_message,p_fingerprint,p_daily_limit);
  if admission->>'decision'='started' then
    insert into public.saarthi_spend(owner,turn_id,day,reserved_micro_usd)
      values(p_owner,p_turn,current_day,p_reserve);
  end if;
  return admission;
end
$$;
revoke all on function public.saarthi_admit_turn(text,text,uuid,text,text,integer,bigint,bigint,bigint)
  from public, anon, authenticated;
grant execute on function public.saarthi_admit_turn(text,text,uuid,text,text,integer,bigint,bigint,bigint)
  to service_role;

create table if not exists public.saarthi_login_rate (
  owner text primary key,
  minute timestamptz not null,
  attempts integer not null
);
alter table public.saarthi_login_rate enable row level security;
revoke all on public.saarthi_login_rate from public, anon, authenticated;
grant select,insert,update on public.saarthi_login_rate to service_role;

create or replace function public.saarthi_claim_login(p_owner text)
returns boolean language plpgsql set search_path = pg_catalog, public as $$
declare
  window_start timestamptz := date_trunc('minute',now());
  claimed integer;
begin
  insert into public.saarthi_login_rate as rate(owner,minute,attempts)
    values(p_owner,window_start,1)
    on conflict(owner) do update set minute=excluded.minute,
      attempts=case when rate.minute=excluded.minute then rate.attempts+1 else 1 end
    where rate.minute<>excluded.minute or rate.attempts<10
    returning attempts into claimed;
  return claimed is not null;
end
$$;
revoke all on function public.saarthi_claim_login(text) from public, anon, authenticated;
grant execute on function public.saarthi_claim_login(text) to service_role;

-- Database-backed owner onboarding. Only a deployment management authorization
-- can issue a grant. A password change consumes it and invalidates other grants.
create table if not exists public.saarthi_owner_credentials (
  owner text primary key,
  password_hash text not null,
  updated_at timestamptz not null default now()
);
create table if not exists public.saarthi_owner_grants (
  token_hash text primary key,
  owner text not null,
  prior_hash text not null,
  expires_at timestamptz not null default now()+interval '10 minutes'
);
alter table public.saarthi_owner_credentials enable row level security;
alter table public.saarthi_owner_grants enable row level security;
revoke all on public.saarthi_owner_credentials,public.saarthi_owner_grants from public,anon,authenticated;
grant select,insert,update on public.saarthi_owner_credentials to service_role;
grant select,insert,delete on public.saarthi_owner_grants to service_role;

create or replace function public.saarthi_issue_owner_grant(
  p_owner text,p_token_hash text,p_intent text,p_legacy_hash text
) returns boolean language plpgsql set search_path=pg_catalog,public as $$
declare prior text;
begin
  perform pg_advisory_xact_lock(hashtextextended(p_owner,0));
  select password_hash into prior from public.saarthi_owner_credentials where owner=p_owner;
  prior := coalesce(prior,p_legacy_hash,'');
  if p_intent not in ('setup','recover') or (p_intent='setup' and prior<>'') then return false; end if;
  delete from public.saarthi_owner_grants where owner=p_owner;
  insert into public.saarthi_owner_grants(token_hash,owner,prior_hash) values(p_token_hash,p_owner,prior);
  return true;
end
$$;

create or replace function public.saarthi_complete_owner_setup(
  p_owner text,p_token_hash text,p_password_hash text,p_legacy_hash text
) returns boolean language plpgsql set search_path=pg_catalog,public as $$
declare prior text; authorized public.saarthi_owner_grants%rowtype;
begin
  perform pg_advisory_xact_lock(hashtextextended(p_owner,0));
  select * into authorized from public.saarthi_owner_grants
    where owner=p_owner and token_hash=p_token_hash and expires_at>now();
  if not found then return false; end if;
  select password_hash into prior from public.saarthi_owner_credentials where owner=p_owner;
  if coalesce(prior,p_legacy_hash,'')<>authorized.prior_hash then return false; end if;
  if p_password_hash !~ '^scrypt-v1\$[a-f0-9]{32}\$[a-f0-9]{64}$' then return false; end if;
  insert into public.saarthi_owner_credentials(owner,password_hash) values(p_owner,p_password_hash)
    on conflict(owner) do update set password_hash=excluded.password_hash,updated_at=now();
  delete from public.saarthi_owner_grants where owner=p_owner;
  return true;
end
$$;
revoke all on function public.saarthi_issue_owner_grant(text,text,text,text),
  public.saarthi_complete_owner_setup(text,text,text,text) from public,anon,authenticated;
grant execute on function public.saarthi_issue_owner_grant(text,text,text,text),
  public.saarthi_complete_owner_setup(text,text,text,text) to service_role;
