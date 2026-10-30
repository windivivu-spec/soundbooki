// Isolated, in-memory PostgreSQL/WASM. No environment, bank or live Supabase.
// QA-only dependency: npm install --prefix .qa/heygen-db --save-exact @electric-sql/pglite@0.5.11
import {PGlite} from '../.qa/heygen-db/node_modules/@electric-sql/pglite/dist/index.js';
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const db=new PGlite();
const sql=path=>readFile(new URL('../'+path,import.meta.url),'utf8');
try {
 await db.exec(`create role anon; create role authenticated; create role service_role bypassrls;
  create schema storage;
  create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);`);
 await db.exec(await sql('supabase/migrations/20261020074917_wsn_device_commerce.sql'));
 await db.exec(await sql('supabase/migrations/20261021140853_book_orders.sql'));
 const device='SNCCCCCCCCCCCC',secret='c'.repeat(64);
 const payload={title:'Local QA migration',voice:'voice-003',language:'vi',revision:'pro-cloud-modal-v1',openingPage:0,
  segments:Array.from({length:8},(_,i)=>({id:(i+1).toString(16).padStart(32,'0'),index:i,page:0,text:'Tiếng Việt. '.repeat(100)}))};
 const makeTrial=key=>db.query('select public.wsn_book_create($1,$2,$3::jsonb,\'trial\',$4) as o',[device,secret,JSON.stringify(payload),key]);
 let oldOrder;
 for(let i=0;i<3;i++){
  oldOrder=(await makeTrial(i.toString(16).padStart(32,'0'))).rows[0].o;
  assert.equal(oldOrder.character_count,500);
 }
 await db.exec(`select public.wsn_accept_payment('qa-preserve-legacy','0000000000','SNCCCCCCCCCCCC',189000,now());`);
 const before=(await db.query('select (select count(*) from wsn_payments)::int as payments,(select count(*) from wsn_licenses)::int as licenses')).rows[0];
 await db.exec(await sql('supabase/migrations/20261022083604_book_trial_10x4000.sql'));
 await db.exec(await sql('supabase/migrations/20261022090045_launch_combo_five_books.sql'));
 await db.exec(await sql('commerce/manual/trial-10x5000.sql'));
 assert.equal((await db.query('select trials_used from wsn_book_devices where device_code=$1',[device])).rows[0].trials_used,3);
 // A retried historical sample retains its original immutable 500-character snapshot.
 assert.equal((await makeTrial('2'.padStart(32,'0'))).rows[0].o.id,oldOrder.id);
 assert.equal((await makeTrial('2'.padStart(32,'0'))).rows[0].o.character_count,500);
 for(let i=3;i<10;i++){
  const order=(await makeTrial(i.toString(16).padStart(32,'0'))).rows[0].o;
  assert.equal(order.character_count,5000);
  assert.equal(order.amount_vnd,0);
 }
 await assert.rejects(()=>makeTrial('a'.padStart(32,'0')),/Trial limit reached/);
 assert.equal((await db.query('select trials_used from wsn_book_devices where device_code=$1',[device])).rows[0].trials_used,10);
 const after=(await db.query('select (select count(*) from wsn_payments)::int as payments,(select count(*) from wsn_licenses)::int as licenses')).rows[0];
 assert.deepEqual(after,before);
 const guards=(await db.query(`select
  has_function_privilege('anon','public.wsn_book_create(text,text,jsonb,text,text)','execute') as anon_execute,
  has_function_privilege('authenticated','public.wsn_book_create(text,text,jsonb,text,text)','execute') as auth_execute,
  has_function_privilege('service_role','public.wsn_book_create(text,text,jsonb,text,text)','execute') as service_execute,
  (select bool_and(relrowsecurity) from pg_class where oid in ('wsn_book_devices'::regclass,'wsn_book_orders'::regclass,'wsn_book_receipts'::regclass)) as rls;`)).rows[0];
 assert.deepEqual(guards,{anon_execute:false,auth_execute:false,service_execute:true,rls:true});
 await db.exec((await sql('tests/book-commerce.sql')).replace('integer<>4000','integer<>5000').replace('10x4000','10x5000'));
 const report={passed:true,engine:'PGlite 0.5.11 (PostgreSQL WASM, one connection)',
  preservedUsedTrials:true,historicalTrialUnchanged:true,seventhAdditionalTrialAccepted:true,
  eleventhTrialRejected:true,newTrialCharacters:5000,legacyReceiptsAndLicensesPreserved:true,
  snapshotPricingReceiptAndClaimsRegression:true,roleGrantsAndRLSPreserved:true,
  liveDatabaseModified:false,concurrencyTested:false};
 await writeFile(new URL('../.qa/profile-db-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
} finally {await db.close();}
