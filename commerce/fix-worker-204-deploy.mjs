// Repair void RPC 204 handling in the existing dispatcher only. No job submissions.
import {readFileSync,writeFileSync} from 'node:fs';import {createHash} from 'node:crypto';
const ref='zpjphixcttehkkgxlmsn',token=process.env.SUPABASE_ACCESS_TOKEN;
if(process.env.SUPABASE_URL!==`https://${ref}.supabase.co`||!token)throw Error('Wrong project');
if(!/44 passed \| 0 failed/.test(readFileSync('.qa/latency-20261029/gateway-tests.log','utf8')))throw Error('Required regression tests missing');
async function api(path,{method='GET',body}={}){const r=await fetch(`https://api.supabase.com/v1/projects/${ref}${path}`,{method,headers:{authorization:'Bearer '+token,...(body&&!(body instanceof FormData)?{'content-type':'application/json'}:{})},body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error('Management HTTP '+r.status);const raw=await r.text();return raw?JSON.parse(raw):null;}
const query=query=>api('/database/query',{method:'POST',body:{query,read_only:true}});
const state=()=>query(`select (select md5(coalesce(jsonb_agg(to_jsonb(o) order by id)::text,'')) from wsn_book_orders o) orders,(select md5(coalesce(jsonb_agg(to_jsonb(d) order by device_code)::text,'')) from wsn_book_devices d) devices,(select count(*) from wsn_book_receipts) receipts,(select count(*) from wsn_book_orders where state in ('queued','processing')) active,(select md5(pg_get_functiondef('wsn_heygen_next_v2(boolean)'::regprocedure))) limiter,(select count(*) from cron.job where jobname='wsn-heygen-trial-dispatch' and active) schedules`);
const [before]=await state();if(before.active!==0)throw Error('A cloud order is active; wait before updating worker');
const strip=p=>readFileSync(p,'utf8').replace(/^import .*;\s*$/gm,'');
const source='type Env=(name:string)=>string|undefined;type Fetch=typeof fetch;\n'+strip('supabase/functions/_shared/books.ts')+'\n'+strip('supabase/functions/_shared/heygen-worker.ts')+'\n'+strip('supabase/functions/wsn-heygen-worker/index.ts');
if(!source.includes('r.status===204?null:r.json()'))throw Error('Fix missing');
writeFileSync('.qa/latency-20261029/wsn-heygen-worker.ts',source);
const form=new FormData();form.set('metadata',JSON.stringify({entrypoint_path:'index.ts',name:'wsn-heygen-worker',verify_jwt:false}));form.append('file',new Blob([source],{type:'application/typescript'}),'index.ts');
const deployed=await api('/functions/deploy?slug=wsn-heygen-worker',{method:'POST',body:form});
const [after]=await state();for(const k of Object.keys(before))if(before[k]!==after[k])throw Error('State changed: '+k);
const health=await fetch(`https://${ref}.supabase.co/functions/v1/wsn-heygen-worker`,{signal:AbortSignal.timeout(15000)});if(health.status!==405)throw Error('Worker health failed');
const result={at:new Date().toISOString(),slug:deployed.slug,status:deployed.status,version:deployed.version,sourceSHA256:createHash('sha256').update(source).digest('hex'),ordersAndQuotasPreserved:true,limiterPreserved:true,providerRequests:0};writeFileSync('.qa/latency-20261029/deployed.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
