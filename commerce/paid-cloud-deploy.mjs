// Owner operations for the Mac per-book service. Never package with the app.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
const ref='zpjphixcttehkkgxlmsn',base=`https://${ref}.supabase.co`,token=process.env.SUPABASE_ACCESS_TOKEN;
if(process.env.SUPABASE_URL!==base||!token)throw Error('Wrong project or missing deployment credential');
const dir='.qa/paid-cloud';mkdirSync(dir,{recursive:true,mode:0o700});
const migration='supabase/migrations/20261023170720_heygen_paid_book_dispatch.sql';
async function api(path,{method='GET',body}={}){const headers={authorization:'Bearer '+token};if(body&&!(body instanceof FormData))headers['content-type']='application/json';const response=await fetch(`https://api.supabase.com/v1/projects/${ref}${path}`,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(60000)});if(!response.ok)throw Error('Management HTTP '+response.status);const raw=await response.text();return raw?JSON.parse(raw):null;}
const query=(sql,read_only=false)=>api('/database/query',{method:'POST',body:{query:sql,read_only}});
const command=process.argv[2];
if(command==='schema'){
 const existing=await query("select exists(select 1 from information_schema.columns where table_schema='public' and table_name='wsn_book_orders' and column_name='receiving_bank') as applied",true);
 if(existing[0].applied)throw Error('Migration already present; inspect before applying again');
 const before=await query("select p.proname,pg_get_functiondef(p.oid) as definition from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'wsn_%'",true);
 writeFileSync(dir+'/schema-before.private.json',JSON.stringify(before),{mode:0o600});
 await query(readFileSync(migration,'utf8'));console.log(JSON.stringify({schemaApplied:true,ordersRewritten:false,paidActivated:false}));
}else if(command==='deploy'){
 const withoutImports=p=>readFileSync(p,'utf8').replace(/^import .*;\s*$/gm,'');
 for(const slug of ['wsn-books','wsn-heygen-worker','wsn-sepay-webhook']){
  let source;
  if(slug==='wsn-sepay-webhook')source="// @ts-nocheck\nimport {timingSafeEqual} from 'node:crypto';import {Buffer} from 'node:buffer';\n"+withoutImports('package qr pay/src/sepay.js')+'\n'+withoutImports('supabase/functions/_shared/wsn.ts')+'\n'+withoutImports(`supabase/functions/${slug}/index.ts`);
  else source='type Env=(name:string)=>string|undefined;type Fetch=typeof fetch;\n'+withoutImports('supabase/functions/_shared/books.ts')+'\n'+(slug==='wsn-heygen-worker'?withoutImports('supabase/functions/_shared/heygen-worker.ts')+'\n':'')+withoutImports(`supabase/functions/${slug}/index.ts`);
  writeFileSync(dir+'/'+slug+'.ts',source);
  const form=new FormData();form.set('metadata',JSON.stringify({entrypoint_path:'index.ts',name:slug,verify_jwt:false}));form.append('file',new Blob([source],{type:'application/typescript'}),'index.ts');
  const result=await api('/functions/deploy?slug='+slug,{method:'POST',body:form});console.log(JSON.stringify({slug:result.slug,status:result.status,version:result.version}));
 }
}else if(command==='schedule'){
 const schedule=`with proof as (select floor(extract(epoch from now()))::bigint::text||'.'||replace(gen_random_uuid()::text,'-','') as message) select net.http_post(url:='${base}/functions/v1/wsn-heygen-worker',headers:=jsonb_build_object('Content-Type','application/json','x-wsn-worker-proof',message||'.'||encode(extensions.hmac(message,(select decrypted_secret from vault.decrypted_secrets where name='wsn_heygen_worker_token' limit 1),'sha256'),'hex')),body:='{}'::jsonb,timeout_milliseconds:=120000) from proof where exists(select 1 from public.wsn_book_orders b where b.payload->>'revision'='pro-cloud-heygen-v1' and b.state in ('queued','processing') and (b.kind='trial' or (b.kind='book' and public.wsn_heygen_is_funded(b.id))));`;
 const jobs=await query("select jobid,command from cron.job where jobname='wsn-heygen-trial-dispatch'",true);if(jobs.length!==1)throw Error('Expected the existing single dispatcher job');
 writeFileSync(dir+'/cron-before.private.json',JSON.stringify(jobs),{mode:0o600});
 await query(`select cron.alter_job(${Number(jobs[0].jobid)},command:=$schedule$${schedule}$schedule$);`);console.log(JSON.stringify({existingScheduleUpdated:true,periodSeconds:3,paidRequiresReceipt:true}));
}else if(command==='activate'||command==='verify-activation'){
 if(!process.argv.includes('--commercial-rights-confirmed'))throw Error('Explicit owner commercial rights confirmation required');
 const db=JSON.parse(readFileSync(dir+'/db-report.json','utf8')),pre=JSON.parse(readFileSync(dir+'/preflight.json','utf8')),hook=JSON.parse(readFileSync(dir+'/webhook-verified.json','utf8'));
 if(!db.passed||!pre.bankLinkedActive||!hook.verified||!hook.retry||!hook.apiKey||!hook.receivingAccountMatches)throw Error('Complete DB, bank and webhook verification first');
 if(process.env.HEYGEN_MODEL!=='heygen-voice-1-turbo-free')throw Error('No paid provider fallback was authorized');
 const live=JSON.parse(readFileSync(dir+'/live-readonly-report.json','utf8'));if(!live.passed)throw Error('Complete read-only deployment verification first');
 const holder=process.env.WSN_BANK_HOLDER||process.env.VOICE_BANK_NAME;
 if(!holder||!/^\d{6,32}$/.test(process.env.VOICE_BANK_ACCOUNT||''))throw Error('Missing receiving bank');
 const values={WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED:'true',WSN_HEYGEN_PAID_ENABLED:'true',WSN_PAYMENTS_READY:'true',WSN_BOOKS_ENABLED:'true',WSN_BANK_BIN:'970423',WSN_BANK_NAME:'TPBank',WSN_BANK_HOLDER:holder,WSN_BANK_ACCOUNT:process.env.VOICE_BANK_ACCOUNT};
 let secrets=await api('/secrets');
 const matches=()=>Object.entries(values).every(([name,value])=>secrets.some(s=>s.name===name&&s.value===createHash('sha256').update(value).digest('hex')));
 if(!matches()){if(command==='verify-activation')throw Error('Paid configuration is not fully active');await api('/secrets',{method:'POST',body:Object.entries(values).map(([name,value])=>({name,value}))});secrets=await api('/secrets');}
 for(const [name,value] of Object.entries(values))if(!secrets.some(s=>s.name===name&&s.value===createHash('sha256').update(value).digest('hex')))throw Error('Activation verification failed');
 const report={at:new Date().toISOString(),paidEnabled:true,rightsConfirmedByOwner:true,bankVerified:true,comboActivationChanged:false,providerModel:'heygen-voice-1-turbo-free',receiptRequired:true};writeFileSync(dir+'/activation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}else if(command==='pause-sales'){
 await api('/secrets',{method:'POST',body:[{name:'WSN_BOOKS_ENABLED',value:'false'}]});console.log(JSON.stringify({newQuotesPaused:true,existingPaidJobsPreserved:true}));
}else throw Error('Use schema, deploy, schedule, activate, verify-activation or pause-sales');
