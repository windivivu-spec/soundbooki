// Narrow repair for new Mac Pro request packing. Never creates an order/task.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
const ref='zpjphixcttehkkgxlmsn',token=process.env.SUPABASE_ACCESS_TOKEN;
if(process.env.SUPABASE_URL!==`https://${ref}.supabase.co`||!token)throw Error('Wrong project or missing credential');
const dir='.qa/pro-batching';mkdirSync(dir,{recursive:true,mode:0o700});
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
async function query(sql,readOnly=true){
 const r=await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`,{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json'},body:JSON.stringify({query:sql,read_only:readOnly}),signal:AbortSignal.timeout(30000)});
 if(!r.ok)throw Error('Database HTTP '+r.status);
 return r.json();
}
const state=()=>query(`select pg_get_functiondef('wsn_book_create(text,text,jsonb,text,text)'::regprocedure) definition,
 (select jsonb_agg(jsonb_build_array(id,content_hash,payload,device_code,request_key,receiving_bank,character_count,amount_vnd,trial_units) order by id) from wsn_book_orders) orders,
 (select jsonb_agg(jsonb_build_array(device_code,trials_used,secret_hash) order by device_code) from wsn_book_devices) devices,
 (select jsonb_agg(to_jsonb(r) order by bank_account,transaction_id) from wsn_book_receipts r) receipts,
 (select count(*) from wsn_payments) legacy_receipts,(select count(*) from wsn_licenses) licenses,
 (select jsonb_agg(jsonb_build_array(proname,pg_get_functiondef(oid)) order by proname) from pg_proc where pronamespace='public'::regnamespace and proname in ('wsn_heygen_next_v2','wsn_book_quote','wsn_book_confirm','wsn_book_create_trial_v2')) guards,
 has_function_privilege('anon','wsn_book_create(text,text,jsonb,text,text)','execute') anon_create,
 has_function_privilege('authenticated','wsn_book_create(text,text,jsonb,text,text)','execute') member_create,
 has_function_privilege('service_role','wsn_book_create(text,text,jsonb,text,text)','execute') service_create`);
const command=process.argv[2]||'inspect';
if(command==='deploy-worker'){
 const log=readFileSync(dir+'/gateway-tests.log','utf8');
 if(!/0 failed/.test(log))throw Error('Complete worker/gateway tests first');
 const withoutImports=p=>readFileSync(p,'utf8').replace(/^import .*;\s*$/gm,'');
 const source='type Env=(name:string)=>string|undefined;type Fetch=typeof fetch;\n'+withoutImports('supabase/functions/_shared/books.ts')+'\n'+withoutImports('supabase/functions/_shared/heygen-worker.ts')+'\n'+withoutImports('supabase/functions/wsn-heygen-worker/index.ts');
 writeFileSync(dir+'/wsn-heygen-worker.ts',source);
 const form=new FormData();form.set('metadata',JSON.stringify({entrypoint_path:'index.ts',name:'wsn-heygen-worker',verify_jwt:false}));form.append('file',new Blob([source],{type:'application/typescript'}),'index.ts');
 const response=await fetch(`https://api.supabase.com/v1/projects/${ref}/functions/deploy?slug=wsn-heygen-worker`,{method:'POST',headers:{authorization:'Bearer '+token},body:form,signal:AbortSignal.timeout(60000)});
 if(!response.ok)throw Error('Worker deploy HTTP '+response.status);
 const deployed=await response.json();console.log(JSON.stringify({slug:deployed.slug,status:deployed.status,version:deployed.version,providerRequests:0}));process.exit(0);
}
const [before]=await state();
if(before.anon_create||before.member_create||!before.service_create)throw Error('Unexpected RPC grants');
if(command==='apply'){
 const db=JSON.parse(readFileSync('.qa/paid-cloud/db-report.json','utf8'));
 if(!db.passed||!db.newHeygen5000Contract||!db.oldOrderPayloadPreserved)throw Error('Complete isolated database verification first');
 if(!before.definition.includes("length(s->>'text') not between 1 and 2000")&&!before.definition.includes('heygen-5000-v1'))throw Error('Unexpected live creation contract');
 writeFileSync(dir+'/create-before.private.json',JSON.stringify({definition:before.definition}),{mode:0o600});
 await query(readFileSync('supabase/migrations/20261025115543_heygen_request_5000.sql','utf8'),false);
}
const [after]=command==='apply'?await state():[before];
const unchanged=['orders','devices','receipts','legacy_receipts','licenses','guards'].every(k=>digest(before[k])===digest(after[k]));
const report={at:new Date().toISOString(),command,acceptsPacked5000:after.definition.includes('heygen-5000-v1')&&after.definition.includes('then 5000 else 2000'),unchangedOrdersQuotaPaymentsAndDispatcher:unchanged,privateRPC:!after.anon_create&&!after.member_create&&after.service_create,providerRequests:0,orderCount:after.orders?.length||0};
writeFileSync(dir+'/live-contract.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
if(!unchanged||(command!=='inspect'&&!report.acceptsPacked5000))process.exitCode=1;
