// Isolated PostgreSQL/WASM: never connects to Supabase or a provider.
import {PGlite} from '../.qa/heygen-db/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const db=new PGlite();
const sql=p=>readFile(new URL('../'+p,import.meta.url),'utf8');
const key=n=>n.toString(16).padStart(32,'0');
function payload(count,units){
 const chars=Array.from(('Việt 😀. ').repeat(Math.ceil(count/8)+1)).slice(0,count);const segments=[];
 for(let at=0;at<chars.length;at+=1000)segments.push({id:key(at+1),index:segments.length,page:0,text:chars.slice(at,at+1000).join('')});
 return {title:'Chương thử độc lập',voice:'voice-003',language:'vi',revision:'pro-cloud-modal-v1',openingPage:0,segments,...(units===undefined?{}:{trialUnits:units})};
}
const device='SNCCCCCCCCCCCC',secret='c'.repeat(64);
async function trial(p,k,d=device,group=false){const rpc=group?'wsn_book_create_group':'wsn_book_create';return (await db.query(`select public.${rpc}($1,$2,$3::jsonb,'trial',$4) as o`,[d,secret,JSON.stringify(p),key(k)])).rows[0].o;}
const used=async d=>(await db.query('select trials_used from wsn_book_devices where device_code=$1',[d])).rows[0]?.trials_used||0;
try{
 await db.exec('create role anon;create role authenticated;create role service_role bypassrls;create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);');
 for(const p of ['supabase/migrations/20261020074917_wsn_device_commerce.sql','supabase/migrations/20261021140853_book_orders.sql'])await db.exec(await sql(p));
 const oldPayload=payload(21000);const old=await trial(oldPayload,1);assert.equal(old.character_count,500);
 for(const p of ['supabase/migrations/20261022083604_book_trial_10x4000.sql','supabase/migrations/20261022090045_launch_combo_five_books.sql','commerce/manual/trial-10x5000.sql'])await db.exec(await sql(p));
 const single=await trial(oldPayload,2);assert.equal(single.character_count,5000);assert.equal(await used(device),2);
 await db.exec(await sql('commerce/manual/trial-group-up-to-four.sql'));
 assert.equal(await used(device),2);
 const restored=await trial(oldPayload,1);assert.equal(restored.id,old.id);assert.equal(restored.character_count,500);assert.deepEqual(restored.payload,old.payload);assert.equal(restored.content_hash,old.content_hash);assert.equal(restored.trial_units,1);
 const group=await trial(payload(20000,4),3,device,true);assert.equal(group.trial_units,4);assert.equal(group.character_count,20000);assert.equal(await used(device),6);
 const retry=await trial(payload(20000,4),3,device,true);assert.equal(retry.id,group.id);assert.equal(await used(device),6);
 const second=await trial(payload(10001,3),4,device,true);assert.equal(second.trial_units,3);assert.equal(await used(device),9);
 const ordersBefore=(await db.query('select count(*)::int as n from wsn_book_orders')).rows[0].n;
 await assert.rejects(()=>trial(payload(5001,2),5,device,true),/Trial limit reached/);
 assert.equal(await used(device),9);assert.equal((await db.query('select count(*)::int as n from wsn_book_orders')).rows[0].n,ordersBefore);
 await trial(payload(5000),6);assert.equal(await used(device),10);
 await assert.rejects(()=>trial(payload(1),7),/Trial limit reached/);
 await assert.rejects(()=>trial(payload(20000,3),3,device,true),/Request conflict/);
 await assert.rejects(()=>db.query('update wsn_book_orders set trial_units=3 where id=$1',[group.id]),/immutable/);
 for(const invalid of [0,5,2.5,true,'4',null])await assert.rejects(()=>trial(payload(100,invalid),8,device,true),/Invalid/);
 let n=0;
 for(const [count,expected] of [[1,1],[5000,1],[5001,2],[10000,2],[10001,3],[15000,3],[15001,4],[20000,4],[21000,4]]){
  const d='SN'+(++n).toString(16).toUpperCase().padStart(12,'0');
  // Request up to four; the server only charges the actual text used.
  const order=await trial(payload(count,4),100+n,d,true);
  assert.equal(order.character_count,Math.min(count,20000));assert.equal(order.trial_units,expected);assert.equal(await used(d),expected);
 }
 const guards=(await db.query(`select has_function_privilege('anon','public.wsn_book_create_group(text,text,jsonb,text,text)','execute') as anon_execute,has_function_privilege('authenticated','public.wsn_book_create_group(text,text,jsonb,text,text)','execute') as auth_execute,has_function_privilege('service_role','public.wsn_book_create_group(text,text,jsonb,text,text)','execute') as service_execute`)).rows[0];
 assert.deepEqual(guards,{anon_execute:false,auth_execute:false,service_execute:true});
 await db.exec((await sql('tests/book-commerce.sql')).replace('integer<>4000','integer<>5000').replace('10x4000','10x5000'));
 // Upgrade from ten to five WITHOUT rewriting consumed counters or old snapshots.
 await db.exec(await sql('commerce/manual/trial-five-unit-policy.sql'));
 assert.equal(await used(device),10);
 assert.equal((await trial(payload(20000,4),3,device,true)).id,group.id);
 assert.equal(await used(device),10);
 await assert.rejects(()=>trial(payload(1),999),/Trial limit reached/);
 const fresh='SNDDDDDDDDDDDD';
 const singleFive=await trial(payload(5000),1000,fresh);assert.equal(await used(fresh),1);
 const fullFive=(await db.query("select public.wsn_book_create_trial_v2($1,$2,$3::jsonb,'trial',$4) as o",[fresh,secret,JSON.stringify(payload(20000,4)),key(1001)])).rows[0].o;
 assert.equal(fullFive.trial_units,4);assert.equal(await used(fresh),5);
 await assert.rejects(()=>trial(payload(1),1002,fresh),/Trial limit reached/);
 assert.equal((await trial(payload(5000),1000,fresh)).id,singleFive.id);assert.equal(await used(fresh),5);
 const upgraded='SNEEEEEEEEEEEE';await trial(payload(5000),1010,upgraded);await trial(payload(5000),1011,upgraded);
 await assert.rejects(()=>trial(payload(20000,4),1012,upgraded,true),/Trial limit reached/);assert.equal(await used(upgraded),2);
 await trial(payload(15000,3),1013,upgraded,true);assert.equal(await used(upgraded),5);
 const v2guards=(await db.query("select has_function_privilege('anon','public.wsn_book_create_trial_v2(text,text,jsonb,text,text)','execute') as a,has_function_privilege('authenticated','public.wsn_book_create_trial_v2(text,text,jsonb,text,text)','execute') as b,has_function_privilege('service_role','public.wsn_book_create_trial_v2(text,text,jsonb,text,text)','execute') as c")).rows[0];assert.deepEqual(v2guards,{a:false,b:false,c:true});
 const report={passed:true,engine:'PGlite one connection',fiveUnitLimit:true,legacyTenUsedCounterPreserved:true,onePlusFourExactlyFive:true,usedTrialsPreserved:true,legacyPayloadAndHashPreserved:true,groupCostsByUnicodeCharacters:true,fourUnitAndTwentyThousandCap:true,atomicInsufficientQuota:true,retryDoesNotDebitAgain:true,unitCostImmutable:true,paidPricingReceiptAndClaimsPreserved:true,serviceRoleOnly:true,liveDatabaseModified:false,concurrencyTested:false};
 await writeFile(new URL('../.qa/grouped-trials-db-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{await db.close();}
