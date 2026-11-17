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
