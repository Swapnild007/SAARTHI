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
