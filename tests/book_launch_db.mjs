// Isolated PostgreSQL/WASM; no bank, live DB or TTS. Single-connection contract QA.
import {PGlite} from '../.qa/heygen-db/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const db=new PGlite();
const sql=p=>readFile(new URL('../'+p,import.meta.url),'utf8');
const one=async(q,args=[])=>(await db.query(q,args)).rows[0];
const key=n=>n.toString(16).padStart(32,'0');
const mac='SNDDDDDDDDDDDD',secret='d'.repeat(64),mac2='SNEEEEEEEEEEEE',secret2='e'.repeat(64);
const body=n=>({title:'Sách combo QA '+n,voice:'3414fd7fdaa64e619fb8b021534ce368',language:'vi',revision:'pro-cloud-heygen-v1',openingPage:0,
 segments:[{id:key(100+n),index:0,page:0,text:'Nội dung cuốn sách '+n+'. '+'Chữ Việt nguyên vẹn. '.repeat(20)}]});
const quote=(device=mac,hash=secret,k=key(1))=>one('select wsn_launch_quote($1,$2,$3,$4::jsonb) as o',[device,hash,k,JSON.stringify({bin:'970423',account:'0000000000',name:'QA',holder:'QA ONLY'})]).then(r=>r.o);
const status=(device=mac,hash=secret)=>one('select wsn_launch_status($1,$2) as s',[device,hash]).then(r=>r.s);
const redeem=(n,k=key(1000+n),device=mac,hash=secret)=>one("select wsn_book_create($1,$2,$3::jsonb,'bundle_book',$4) as o",[device,hash,JSON.stringify(body(n)),k]).then(r=>r.o);
const confirm=(o,tx,at,amount=50000,account='0000000000')=>one('select wsn_book_confirm($1,$2,$3,$4,$5,$6::timestamptz) as r',[o.payment_code,tx,account,'0000000000',amount,at]);
try {
 await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;create schema storage;
 create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);`);
 for(const file of ['20261020074917_wsn_device_commerce','20261021140853_book_orders','20261022083604_book_trial_10x4000','20261022090045_launch_combo_five_books'])
  await db.exec(await sql('supabase/migrations/'+file+'.sql'));
 assert.equal((await one("select wsn_launch_active('2026-11-01T16:59:59.999Z') as active")).active,true);
 assert.equal((await one("select wsn_launch_active('2026-11-01T17:00:00Z') as active")).active,false);
 const q=await quote();assert.equal(q.kind,'bundle');assert.equal(q.amount_vnd,50000);
 assert.equal((await quote(mac,secret,key(2))).id,q.id);
 await assert.rejects(()=>quote(mac,'f'.repeat(64)),/Device key mismatch/);
 assert.equal((await status()).bundle,null);
 await assert.rejects(()=>redeem(1),/chưa có combo/);
 const at=(await one('select now() as at')).at;
 await assert.rejects(()=>confirm(q,'launch-qa-1',at,49999),/does not match/);
 await assert.rejects(()=>confirm(q,'launch-qa-1',at,50000,'1111111111'),/Invalid receipt/);
 await assert.rejects(()=>db.query('select wsn_book_confirm($1,$2,$3,$3,50000,$4::timestamptz)',[q.payment_code,'launch-wrong-quote-bank','1111111111',at]),/bank does not match quote/);
 assert.equal((await confirm(q,'launch-qa-1',at)).r.status,'paid');
 assert.equal((await confirm(q,'launch-qa-1',at)).r.status,'duplicate');
 assert.equal((await status()).bundle.remaining,5);
 await assert.rejects(()=>quote(mac,secret,key(3)),/chỉ mua một combo/);
 const first=await redeem(1);assert.equal(first.amount_vnd,0);assert.equal(first.state,'queued');assert.ok(first.paid_at&&first.funding_bundle_id);
 assert.equal((await redeem(1)).id,first.id);assert.equal((await redeem(1,key(888))).id,first.id);
 assert.equal((await status()).bundle.remaining,4);
 await assert.rejects(()=>redeem(2,key(1001)),/Request conflict/);
 // All five books may enter the queue before the campaign deadline.
 for(let n=2;n<=5;n++)await redeem(n);
 assert.equal((await status()).bundle.remaining,0);
 await assert.rejects(()=>redeem(6),/đủ 5 cuốn/);
 await assert.rejects(()=>db.query('update wsn_book_orders set funding_bundle_id=null where id=$1',[first.id]),/immutable/);
 const regular=(await one("select wsn_book_create($1,$2,$3::jsonb,'book',$4) as o",[mac,secret,JSON.stringify(body(7)),key(2007)])).o;
 assert.equal(regular.amount_vnd,10000);assert.equal(regular.pricing_version,'book-v1');
 assert.equal((await one('select wsn_book_claim($1::uuid) as o',[first.id])).o,null);
 const q2=await quote(mac2,secret2);
 await assert.rejects(()=>confirm(q2,'launch-qa-1',at),/Receipt conflict|already used/);
 await assert.rejects(()=>db.query("select wsn_accept_payment('launch-qa-1','0000000000',$1,189000,$2::timestamptz)",[mac,at]),/already used for a book/);
 await confirm(q2,'launch-qa-2',at);
 await assert.rejects(()=>status(mac2,secret),/Device key mismatch/);
 // Simulate a server-side closed campaign without changing any customer clock.
 await db.exec('create or replace function wsn_launch_active(p_at timestamptz default now()) returns boolean language sql immutable security invoker set search_path=pg_catalog as $$select false;$$;');
 await assert.rejects(()=>redeem(1,key(3001),mac2,secret2),/hết hạn/);
 assert.equal((await redeem(1)).id,first.id); // existing job still retrievable after expiry
 await assert.rejects(()=>quote('SNFFFFFFFFFFFF','f'.repeat(64),key(4)),/kết thúc/);
 const guards=await one(`select has_function_privilege('anon','wsn_launch_quote(text,text,text,jsonb)','execute') as anon,
 has_function_privilege('authenticated','wsn_launch_status(text,text)','execute') as client,
 has_function_privilege('service_role','wsn_launch_quote(text,text,text,jsonb)','execute') as server,
 (select bool_and(relrowsecurity) from pg_class where oid in ('wsn_launch_bundles'::regclass,'wsn_launch_redemptions'::regclass)) as rls;`);
 assert.deepEqual(guards,{anon:false,client:false,server:true,rls:true});
 await db.exec(await sql('tests/book-commerce.sql'));
 const report={passed:true,engine:'PGlite 0.5.11, one connection',priceVND:50000,booksPerMac:5,
 exactReceiptRequired:true,receiptReplayIdempotent:true,oneComboPerMac:true,bookRetryDoesNotConsume:true,
 sixthBookBlocked:true,allFiveMayQueueBeforeDeadline:true,serverDeadlineEnforced:true,oldJobsRemainAfterDeadline:true,
 crossLedgerReplayBlocked:true,regularPricingUnchanged:true,rlsAndGrantsClosed:true,
 heygenNotClaimedByModal:true,liveDatabaseModified:false,parallelContentionTested:false};
 await writeFile(new URL('../.qa/launch-db-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
} finally {await db.close();}
