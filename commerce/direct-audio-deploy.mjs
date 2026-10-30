// Owner requested direct provider delivery and a test build. No synthesis or payment actions.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const ref='zpjphixcttehkkgxlmsn',token=process.env.SUPABASE_ACCESS_TOKEN;
if(process.env.SUPABASE_URL!==`https://${ref}.supabase.co`||!token)throw Error('Wrong target');
async function api(path,{method='GET',body}={}){const r=await fetch(`https://api.supabase.com/v1/projects/${ref}${path}`,{method,headers:{authorization:'Bearer '+token,...(body&&!(body instanceof FormData)?{'content-type':'application/json'}:{})},body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error('Management HTTP '+r.status);const raw=await r.text();return raw?JSON.parse(raw):null;}
const query=(query,read_only=true)=>api('/database/query',{method:'POST',body:{query,read_only}});
const state=()=>query(`select (select md5(coalesce(jsonb_agg(to_jsonb(o) order by id)::text,'')) from wsn_book_orders o) orders,(select md5(coalesce(jsonb_agg(to_jsonb(d) order by device_code)::text,'')) from wsn_book_devices d) devices,(select count(*) from wsn_book_receipts) receipts,(select count(*) from wsn_payments) legacy_payments,(select count(*) from wsn_licenses) licenses,(select count(*) from wsn_book_orders where state in ('queued','processing')) active,(select md5(pg_get_functiondef('wsn_heygen_next_v2(boolean)'::regprocedure))) limiter,(select count(*) from cron.job where jobname='wsn-heygen-trial-dispatch' and active) schedules`);
if(process.argv[2]!=='apply')throw Error('Use apply');
const [before]=await state();if(before.active!==0)throw Error('Active generation: wait before upgrading');
writeFileSync('.qa/direct-audio/before.private.json',JSON.stringify(before),{mode:0o600});
// Add a private wrapper; old RPC and rows stay unchanged.
await query(readFileSync('commerce/manual/book-direct-audio.sql','utf8'),false);
for(const slug of ['wsn-books','wsn-heygen-worker']){
 const strip=p=>readFileSync(p,'utf8').replace(/^import .*;\s*$/gm,'');
 const source='type Env=(name:string)=>string|undefined;type Fetch=typeof fetch;\n'+strip('supabase/functions/_shared/books.ts')+'\n'+(slug==='wsn-heygen-worker'?strip('supabase/functions/_shared/heygen-worker.ts')+'\n':'')+strip(`supabase/functions/${slug}/index.ts`);
 writeFileSync('.qa/direct-audio/'+slug+'.ts',source);
 const form=new FormData();form.set('metadata',JSON.stringify({entrypoint_path:'index.ts',name:slug,verify_jwt:false}));form.append('file',new Blob([source],{type:'application/typescript'}),'index.ts');
 const deployed=await api('/functions/deploy?slug='+slug,{method:'POST',body:form});console.log(JSON.stringify({slug:deployed.slug,status:deployed.status,version:deployed.version,sourceSHA256:createHash('sha256').update(source).digest('hex')}));
}
const [after]=await state();for(const k of Object.keys(before))if(before[k]!==after[k])throw Error('State changed: '+k);
const [grants]=await query("select has_function_privilege('anon','wsn_book_audio_direct(uuid,uuid,text,text)','execute') a,has_function_privilege('authenticated','wsn_book_audio_direct(uuid,uuid,text,text)','execute') b,has_function_privilege('service_role','wsn_book_audio_direct(uuid,uuid,text,text)','execute') s");
if(grants.a||grants.b||!grants.s)throw Error('Wrong RPC grants');
for(const slug of ['wsn-books','wsn-heygen-worker']){const r=await fetch(`https://${ref}.supabase.co/functions/v1/${slug}`,{signal:AbortSignal.timeout(20000)});if(r.status!==405)throw Error('Runtime health failed');}
const report={at:new Date().toISOString(),passed:true,oldOrdersAndQuotasPreserved:true,limiterPreserved:true,privateRPC:true,providerRequests:0};
writeFileSync('.qa/direct-audio/deployed.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
