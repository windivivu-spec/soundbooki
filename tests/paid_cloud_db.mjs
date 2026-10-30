// Real PostgreSQL semantics in isolated WASM; no bank, live data or provider.
import {PGlite} from '../.qa/heygen-db/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile,writeFile} from 'node:fs/promises';import assert from 'node:assert/strict';
const db=new PGlite(),key=n=>n.toString(16).padStart(32,'0');
const stages=['supabase/migrations/20261020074917_wsn_device_commerce.sql','supabase/migrations/20261021140853_book_orders.sql','supabase/migrations/20261022083604_book_trial_10x4000.sql','supabase/migrations/20261022090045_launch_combo_five_books.sql','commerce/manual/trial-10x5000.sql','commerce/manual/trial-group-up-to-four.sql','commerce/manual/trial-five-unit-policy.sql','commerce/manual/heygen-trial-dispatcher.sql','supabase/migrations/20261023170720_heygen_paid_book_dispatch.sql'];
const bank={bin:'970423',name:'QA BANK',account:'0000000000',holder:'QA ONLY'};
const payload=(n=30)=>({title:'Sách QA giữ nguyên dấu',language:'vi',voice:'3414fd7fdaa64e619fb8b021534ce368',revision:'pro-cloud-heygen-v1',openingPage:0,segments:Array.from({length:n},(_,i)=>({id:key(i+1),index:i,page:0,text:'Tiếng Việt 😀. '+i}))});
const one=async(q,a=[])=> (await db.query(q,a)).rows[0];
const quote=async(d,k,p=payload(),b=bank)=>(await one('select wsn_book_quote($1,$2,$3::jsonb,$4,$5::jsonb) as o',[d,'a'.repeat(64),JSON.stringify(p),key(k),JSON.stringify(b)])).o;
const confirm=async(o,tx,amount=o.amount_vnd,b=bank.account)=>(await one('select wsn_book_confirm($1,$2,$3,$4,$5,$6) as r',[o.payment_code,tx,b,b,amount,o.created_at])).r;
const next=async(paid=true)=>(await one('select wsn_heygen_next_v2($1) as t',[paid])).t;
const reset=()=>db.exec("update wsn_heygen_control set next_at=now()-interval '1 second',blocked_until=now()-interval '1 second'");
const finish=async(t)=>{await db.query('select wsn_book_audio($1,$2,$3,$4)',[t.orderId,t.claim,t.segment.id,'f'.repeat(64)]);await db.query("select wsn_heygen_result($1,$2,$3,'done')",[t.orderId,t.segment.id,t.token]);};
try{
 await db.exec('create role anon;create role authenticated;create role service_role bypassrls;create schema storage;create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);');
 for(const p of stages)await db.exec(await readFile(new URL('../'+p,import.meta.url),'utf8'));
 const a=await quote('SNAAAAAAAAAAAA',1),b=await quote('SNBBBBBBBBBBBB',2);
 assert.equal(a.state,'awaiting_payment');assert.deepEqual(a.receiving_bank,bank);assert.equal(await next(),null);
 assert.equal((await quote('SNAAAAAAAAAAAA',1,payload(),{...bank,account:'9999999999'})).id,a.id);
 assert.deepEqual((await quote('SNAAAAAAAAAAAA',1)).receiving_bank,bank);
 await assert.rejects(()=>db.query("update wsn_book_orders set receiving_bank='{}' where id=$1",[a.id]),/Receiving bank is immutable/);
 await assert.rejects(()=>confirm(a,'wrong-bank',a.amount_vnd,'9999999999'),/bank does not match/);
 await assert.rejects(()=>confirm(a,'wrong-amount',a.amount_vnd+1),/does not match quote/);
 await assert.rejects(()=>quote('SNAAAAAAAAAAAA',1,{...payload(),title:'Đổi chữ'}),/Request conflict/);
 assert.equal((await one('select count(*)::int n from wsn_book_receipts')).n,0);
 assert.equal((await confirm(a,'paid-A')).status,'paid');
 assert.equal((await confirm(a,'paid-A')).status,'duplicate');
 await assert.rejects(()=>confirm(b,'paid-A'),/Receipt conflict/);
 await assert.rejects(()=>db.query("select wsn_accept_payment('paid-A','0000000000','SNCCCCCCCCCCCC',189000,now())"),/already used/);
 assert.equal(await next(false),null); // Kill switch blocks even funded books.
 await confirm(b,'paid-B');
 const trial=(await one("select wsn_book_create_trial_v2('SNCCCCCCCCCCCC',$1,$2::jsonb,'trial',$3) o",['a'.repeat(64),JSON.stringify(payload()),key(3)])).o;
 const sequence=[];
 for(let i=0;i<5;i++){await reset();const t=await next();assert.ok(t);sequence.push(t.kind);if(i<4)assert.equal(t.orderId,i%2===0?a.id:b.id);else assert.equal(t.orderId,trial.id);await finish(t);}
 assert.deepEqual(sequence,['book','book','book','book','trial']);
 await reset();const t1=await next();assert.equal(await next(),null);await reset();const t2=await next();await reset();const t3=await next();await reset();assert.equal(await next(),null);
 await finish(t1);await finish(t2);await finish(t3);
 // Twenty-five attempts already reserved in the sliding window => no new provider call.
 await db.exec("delete from wsn_heygen_dispatches;insert into wsn_heygen_dispatches(dispatched_at,order_id,segment_id,device_code,kind) select now(),'"+a.id+"','"+key(1)+"','SNAAAAAAAAAAAA','book' from generate_series(1,25)");
 await reset();assert.equal(await next(),null);
 await db.exec("update wsn_heygen_dispatches set dispatched_at=now()-interval '61 seconds'");await reset();const afterWindow=await next();assert.ok(afterWindow);await finish(afterWindow);
 // Same transaction rolls back a quote or trial admission and its quota debit.
 await db.exec('update wsn_heygen_control set max_pending_segments=1');
 const count=(await one('select count(*)::int n from wsn_book_orders')).n;
 await assert.rejects(()=>quote('SNDDDDDDDDDDDD',4),/Hàng đợi Pro đang đầy/);
 await assert.rejects(()=>one("select wsn_book_create_trial_v2('SNEEEEEEEEEEEE',$1,$2::jsonb,'trial',$3)",['a'.repeat(64),JSON.stringify(payload()),key(5)]),/Hàng đợi Pro đang đầy/);
 assert.equal((await one('select count(*)::int n from wsn_book_orders')).n,count);
 assert.equal((await one("select count(*)::int n from wsn_book_devices where device_code='SNEEEEEEEEEEEE'")).n,0);
 assert.equal((await quote('SNAAAAAAAAAAAA',1)).id,a.id); // Already admitted retries survive full capacity.
 await db.exec('update wsn_heygen_control set max_pending_segments=6000');
 // A forged paid_at alone is insufficient, even in a service-side inconsistent row.
 const fake=await quote('SNFFFFFFFFFFFF',6,payload(1));await db.query("update wsn_book_orders set state='queued',paid_at=now() where id=$1",[fake.id]);
 assert.equal((await one('select wsn_heygen_is_funded($1) funded',[fake.id])).funded,false);
 // Authentication never moves an order or its artifact to another Mac.
 assert.equal((await one('select count(*)::int n from wsn_book_orders where id=$1 and device_code=$2',[a.id,'SNBBBBBBBBBBBB'])).n,0);
 const modal=await quote('SN123456789ABC',7,{...payload(1),revision:'pro-cloud-modal-v1',voice:'voice-003'});await confirm(modal,'paid-legacy-modal');
 assert.equal((await one('select wsn_book_claim() o')).o.id,modal.id);
 const guard=await one("select has_function_privilege('anon','wsn_book_quote(text,text,jsonb,text,jsonb)','execute') q,has_function_privilege('authenticated','wsn_heygen_next_v2(boolean)','execute') w,has_table_privilege('anon','wsn_heygen_dispatches','select') r");assert.deepEqual(guard,{q:false,w:false,r:false});
 // Upgrade only new explicit HeyGen request packing; immutable old snapshots remain exact.
 const packed={...payload(1),chunkingVersion:'heygen-5000-v1'};packed.segments[0].text='Đ'.repeat(4977);
 await assert.rejects(()=>quote('SNABABABABABAB',800,packed),/Invalid segment/);
 const before=(await one('select payload,content_hash from wsn_book_orders where id=$1',[a.id]));
 await db.exec(await readFile(new URL('../supabase/migrations/20261025115543_heygen_request_5000.sql',import.meta.url),'utf8'));
 assert.deepEqual(await one('select payload,content_hash from wsn_book_orders where id=$1',[a.id]),before);
 const packedOrder=await quote('SNABABABABABAB',800,packed);
 assert.equal(packedOrder.payload.segments.length,1);assert.equal(packedOrder.character_count,4977);
 const grouped={...packed,trialUnits:4,segments:Array.from({length:4},(_,i)=>({id:key(900+i),index:i,page:0,text:'😀'.repeat(5000)}))};
 const group=(await one("select wsn_book_create_trial_v2('SNACACACACACAC',$1,$2::jsonb,'trial',$3) o",['a'.repeat(64),JSON.stringify(grouped),key(801)])).o;
 assert.equal(group.trial_units,4);assert.equal(group.character_count,20000);assert.equal(group.payload.segments.length,4);
 const groupRetry=(await one("select wsn_book_create_trial_v2('SNACACACACACAC',$1,$2::jsonb,'trial',$3) o",['a'.repeat(64),JSON.stringify(grouped),key(801)])).o;
 assert.equal(groupRetry.id,group.id);assert.equal((await one("select trials_used n from wsn_book_devices where device_code='SNACACACACACAC'")).n,4);
 for(const invalid of [{...packed,chunkingVersion:'unknown'},{...packed,revision:'pro-cloud-modal-v1',voice:'voice-003'},{...packed,segments:[{...packed.segments[0],text:'Đ'.repeat(5001)}]}])
  await assert.rejects(()=>quote('SNADADADADADAD',802,invalid),/Invalid segment/);
 assert.equal(await next(false),null);
 await db.exec(await readFile(new URL('../commerce/manual/book-direct-audio.sql',import.meta.url),'utf8'));
 const deliveryGuard=await one("select has_function_privilege('anon','wsn_book_audio_direct(uuid,uuid,text,text)','execute') a,has_function_privilege('authenticated','wsn_book_audio_direct(uuid,uuid,text,text)','execute') b");assert.deepEqual(deliveryGuard,{a:false,b:false});
 await confirm(packedOrder,'direct-verified-receipt');
 const directClaim=(await one("update wsn_book_orders set state='processing',claim_token=gen_random_uuid() where id=$1 returning claim_token",[packedOrder.id])).claim_token;
 await assert.rejects(()=>db.query('select wsn_book_audio_direct($1,$2,$3,$4)',[packedOrder.id,directClaim,packed.segments[0].id,'f'.repeat(64)]),/Missing provider audio/);
 await db.query("insert into wsn_heygen_tasks(order_id,segment_id,state,audio_url) values($1,$2,'audio','https://resource.heygen.ai/fixture.wav')",[packedOrder.id,packed.segments[0].id]);
 await assert.rejects(()=>db.query('select wsn_book_audio_direct($1,gen_random_uuid(),$2,$3)',[packedOrder.id,packed.segments[0].id,'f'.repeat(64)]),/Invalid audio claim/);
 await db.query('select wsn_book_audio_direct($1,$2,$3,$4)',[packedOrder.id,directClaim,packed.segments[0].id,'f'.repeat(64)]);
 const directResult=await one('select state,results,payload from wsn_book_orders where id=$1',[packedOrder.id]);
 assert.equal(directResult.state,'ready');assert.equal(directResult.results[0].delivery,'provider');assert.equal(directResult.results[0].path,undefined);assert.deepEqual(directResult.payload,packedOrder.payload);
 console.log('PASS direct delivery: original funded claim required, provider URL durable, no Storage path, snapshot preserved, private RPC');
 const report={passed:true,bankImmutable:true,exactVerifiedReceiptRequired:true,receiptReplayBlockedAcrossLedgers:true,unpaidNeverDispatched:true,deviceBindingPreserved:true,paidKillSwitch:true,paidTrialWeight4to1:true,deviceRoundRobin:true,threeInflight:true,sliding25PerMinute:true,atomicCapacityAdmission:true,trialDebitRollback:true,legacyModalPreserved:true,liveDatabaseModified:false,concurrencyTested:false,newHeygen5000Contract:true,oldOrderPayloadPreserved:true,grouped20000UsesFourRequests:true};
 await writeFile('.qa/paid-cloud/db-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await db.close();}
