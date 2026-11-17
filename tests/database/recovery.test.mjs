import assert from 'node:assert/strict';
import {readFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {test} from 'node:test';
import {PGlite} from '@electric-sql/pglite';

const schema=await readFile(new URL('../../database/recovery.sql',import.meta.url),'utf8');

test('SQL migration preserves owned turns across reopen and enforces replay and quotas',async()=>{
  const directory=await mkdtemp(join(tmpdir(),'saarthi-store-'));
  let db=new PGlite(directory);
  const start=(owner,thread,turn,message,fingerprint,limit=30)=>db.query(
    'select public.saarthi_begin_turn($1,$2,$3,$4,$5,$6) as outcome',
    [owner,thread,turn,message,fingerprint,limit],
  ).then(result=>result.rows[0].outcome);

  try{
    await db.exec('create role anon; create role authenticated; create role service_role bypassrls');
    await db.exec(schema);
    await db.exec(schema);
    await db.exec("insert into saarthi_scope(environment) values('staging'); set role service_role");
    assert.equal((await db.query('select environment from saarthi_scope')).rows[0].environment,'staging');
    const ids=[];
    for(let i=0;i<20;i++){
      const id=randomUUID();
      ids.push(id);
      assert.equal((await start('owner-a','thread',id,'prompt '+i,'fingerprint-'+i)).decision,'started');
      assert.equal((await start('owner-a','thread',id,'prompt '+i,'fingerprint-'+i)).decision,'pending');
      assert.equal((await start('owner-a','thread',randomUUID(),'parallel','parallel')).decision,'busy');
      const commit=await db.query(
        "update saarthi_turns set state='completed',result=$1 where owner=$2 and turn_id=$3 and state='pending'",
        [{ok:true,reply:'response '+i},'owner-a',id],
      );
      assert.equal(commit.affectedRows,1);
      const duplicate=await db.query("update saarthi_turns set state='failed' where owner=$1 and turn_id=$2 and state='pending'",['owner-a',id]);
      assert.equal(duplicate.affectedRows,0);
    }
    assert.equal((await start('owner-a','thread',ids[0],'different','different')).decision,'conflict');
    assert.deepEqual((await start('owner-a','thread',ids[0],'prompt 0','fingerprint-0')).result,{ok:true,reply:'response 0'});
    assert.equal((await start('owner-a','thread',randomUUID(),'extra','extra',20)).decision,'quota');
    assert.equal((await start('owner-b','thread',ids[0],'separate owner','separate owner')).decision,'started');
    await db.query("update saarthi_turns set created_at=now()-interval '90 seconds' where owner='owner-b'");
    assert.equal((await start('owner-b','thread',ids[0],'separate owner','separate owner')).result.execution,'interrupted');
    await db.close();
    db=new PGlite(directory);
    await db.exec('set role service_role');
    const persisted=await db.query("select message,result from saarthi_turns where owner='owner-a' and conversation_id='thread' order by seq");
    assert.equal(persisted.rows.length,20);
    assert.equal(persisted.rows[0].message,'prompt 0');
    assert.equal(persisted.rows[19].result.reply,'response 19');
    await db.exec("delete from saarthi_threads where owner='owner-b' and id='thread'");
    assert.equal((await db.query("select count(*) from saarthi_turns where owner='owner-b'")).rows[0].count,0);
    assert.equal((await db.query("select count(*) from saarthi_turns where owner='owner-a'")).rows[0].count,20);
    await db.exec('set role authenticated');
    await assert.rejects(db.query('select * from saarthi_turns'),/permission denied/);
  }finally{
    await db.close();
    await rm(directory,{recursive:true,force:true});
  }
});

test('spending reservations survive replay and deletion and distinguish daily from monthly limits',async()=>{
  const db=new PGlite();
  try{
    await db.exec('create role anon; create role authenticated; create role service_role bypassrls');
    await db.exec(schema);
    await db.exec('set role service_role');
    const owner='cost-owner';
    const turn=randomUUID();
    const admit=(id,day=10,month=15)=>db.query(
      'select saarthi_admit_turn($1,$2,$3,$4,$5,30,5,$6,$7) as result',
      [owner,id,id,'message','fingerprint',day,month],
    ).then(res=>res.rows[0].result.decision);
    assert.equal(await admit(turn),'started');
    assert.equal(await admit(turn),'pending');
    await db.query('update saarthi_spend set reported_micro_usd=7 where turn_id=$1',[turn]);
    assert.equal(await admit(randomUUID()),'budget');
    await db.query('delete from saarthi_threads where owner=$1 and id=$2',[owner,turn]);
    assert.equal(await admit(turn),'conflict');
    const later=randomUUID();
    assert.equal(await admit(later,15,15),'started');
    // Backdate both reservations to exercise the same month's ceiling independently of today's.
    await db.exec("update saarthi_spend set day=date_trunc('month',(now() at time zone 'UTC')::date)::date");
    assert.equal(await admit(randomUUID(),15,15),'budget');
    assert.equal(await admit(randomUUID(),15,20),'started');
    const claim=()=>db.query('select saarthi_claim_login($1) as allowed',[owner]).then(r=>r.rows[0].allowed);
    await db.exec('begin');
    for(let i=0;i<10;i++)assert.equal(await claim(),true);
    assert.equal(await claim(),false);
    await db.exec('commit');
    await db.exec('set role authenticated');
    await assert.rejects(claim(),/permission denied/);
  }finally{
    await db.close();
  }
});

test('owner grants expire, are consumed once and close first setup',async()=>{
  const db=new PGlite();
  const owner='onboarding-owner';
  const first='scrypt-v1$'+'a'.repeat(32)+'$'+'b'.repeat(64);
  const second='scrypt-v1$'+'c'.repeat(32)+'$'+'d'.repeat(64);
  const issue=(digest,intent='setup')=>db.query(
    "select saarthi_issue_owner_grant($1,$2,$3,'') as ok",[owner,digest,intent],
  ).then(r=>r.rows[0].ok);
  const finish=(digest,password)=>db.query(
    "select saarthi_complete_owner_setup($1,$2,$3,'') as ok",[owner,digest,password],
  ).then(r=>r.rows[0].ok);
  try{
    await db.exec('create role anon; create role authenticated; create role service_role bypassrls');
    await db.exec(schema);
    await db.exec(schema);
    await db.exec('set role service_role');
    assert.equal(await finish('no-grant',first),false);
    assert.equal(await issue('one-time'),true);
    assert.equal(await finish('wrong',first),false);
    assert.equal(await finish('one-time','malformed'),false);
    assert.equal(await finish('one-time',first),true);
    assert.equal(await finish('one-time',second),false);
    assert.equal(await issue('new-setup'),false);
    assert.equal(await issue('recovery','recover'),true);
    assert.equal(await finish('recovery',second),true);
    assert.equal((await db.query('select password_hash from saarthi_owner_credentials where owner=$1',[owner])).rows[0].password_hash,second);
    assert.equal(await issue('expired','recover'),true);
    await db.exec("reset role; update saarthi_owner_grants set expires_at=now()-interval '1 second'; set role service_role");
    assert.equal(await finish('expired',first),false);
    await db.exec('set role authenticated');
    await assert.rejects(issue('unauthorized'),/permission denied/);
    await assert.rejects(db.query('select * from saarthi_owner_credentials'),/permission denied/);
  }finally{await db.close();}
});
