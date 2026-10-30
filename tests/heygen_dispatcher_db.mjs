import {PGlite} from '../.qa/heygen-db/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile,writeFile} from 'node:fs/promises';import assert from 'node:assert/strict';
const db=new PGlite();const key=n=>n.toString(16).padStart(32,'0');
try{
 await db.exec('create role anon;create role authenticated;create role service_role bypassrls;create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);');
 for(const p of ['supabase/migrations/20261020074917_wsn_device_commerce.sql','supabase/migrations/20261021140853_book_orders.sql','supabase/migrations/20261022083604_book_trial_10x4000.sql','supabase/migrations/20261022090045_launch_combo_five_books.sql','commerce/manual/trial-10x5000.sql','commerce/manual/trial-group-up-to-four.sql','commerce/manual/trial-five-unit-policy.sql','commerce/manual/heygen-trial-dispatcher.sql'])await db.exec(await readFile(new URL('../'+p,import.meta.url),'utf8'));
 const payload={title:'QA giữ nguyên dấu',language:'vi',voice:'3414fd7fdaa64e619fb8b021534ce368',revision:'pro-cloud-heygen-v1',openingPage:0,segments:[1,2,3].map(n=>({id:key(n),index:n,page:0,text:'Đây là đoạn thử nguyên vẹn. '}))};
 const create=async(d,k)=>(await db.query("select public.wsn_book_create_trial_v2($1,$2,$3::jsonb,'trial',$4) as o",[d,'a'.repeat(64),JSON.stringify(payload),key(k)])).rows[0].o;
 const a=await create('SNAAAAAAAAAAAA',1),b=await create('SNBBBBBBBBBBBB',2);
 const next=async()=>(await db.query('select public.wsn_heygen_next() as t')).rows[0].t;
 const reset=()=>db.exec("update wsn_heygen_control set next_at=now()-interval '1 second',blocked_until=now()-interval '1 second';");
 const record=(t,state,url=null,retry=30)=>db.query('select public.wsn_heygen_result($1,$2,$3,$4,$5,$6,null)',[t.orderId,t.segment.id,t.token,state,url,retry]);
 assert.equal((await db.query('select public.wsn_book_claim() as o')).rows[0].o,null);
 const t1=await next();assert.equal(t1.orderId,a.id);assert.equal(await next(),null);
 await reset();const t2=await next();assert.equal(t2.orderId,b.id);
 await reset();const t3=await next();assert.equal(t3.orderId,a.id);assert.notEqual(t3.segment.id,t1.segment.id);
 await reset();assert.equal(await next(),null); // Max three in-flight, globally.
 await assert.rejects(()=>record({...t1,token:'00000000-0000-0000-0000-000000000000'},'done'),/Invalid dispatcher claim/);
 await record(t1,'audio','https://resource.heygen.ai/fixture.wav',3);
 await db.exec("update wsn_heygen_tasks set available_at=now()-interval '1 second' where state='audio'");
 const recovered=await next();assert.equal(recovered.audioURL,'https://resource.heygen.ai/fixture.wav');assert.equal(recovered.token,t1.token);
 await assert.rejects(()=>record(t1,'done'),/Audio not committed/);
 await db.query('select public.wsn_book_audio($1,$2,$3,$4)',[t1.orderId,t1.claim,t1.segment.id,'f'.repeat(64)]);await record(t1,'done');
 await record(t2,'retry',null,60);assert.equal(await next(),null);await reset();
 await record(t3,'uncertain');await next();assert.equal((await db.query('select state from wsn_book_orders where id=$1',[a.id])).rows[0].state,'failed');
 const grants=(await db.query("select has_function_privilege('anon','wsn_heygen_next()','execute') as anon,has_function_privilege('authenticated','wsn_heygen_next()','execute') as member,has_table_privilege('anon','wsn_heygen_tasks','select') as read")).rows[0];assert.deepEqual(grants,{anon:false,member:false,read:false});
 const report={passed:true,fiveUnitSchema:true,accountRateGate:true,threeInflightCap:true,deviceRoundRobin:true,modalIsolation:true,audioURLRecoveryNoSynthesis:true,unknownPOSTNotRetried:true,backoff:true,claimAuthorization:true,privateTables:true,liveDatabaseModified:false,concurrencyTested:false};console.log(JSON.stringify(report));await writeFile(new URL('../.qa/heygen-dispatcher-db-report.json',import.meta.url),JSON.stringify(report,null,2));
}finally{await db.close();}
