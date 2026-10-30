// Explicit owner operations, pinned to Sách Nói's existing shared project.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {randomBytes} from 'node:crypto';
const ref='zpjphixcttehkkgxlmsn',token=process.env.SUPABASE_ACCESS_TOKEN;
if(!token||process.env.SUPABASE_URL!==`https://${ref}.supabase.co`)throw Error('Wrong deployment target');
const command=process.argv[2];mkdirSync('.qa/cloud-deploy',{recursive:true,mode:0o700});
async function api(path,{method='GET',body}={}){const headers={authorization:'Bearer '+token};if(body&&!(body instanceof FormData))headers['content-type']='application/json';const r=await fetch(`https://api.supabase.com/v1/projects/${ref}${path}`,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(120000)});if(!r.ok)throw Error('Management '+r.status+': '+(await r.text()).replaceAll(token,'[redacted]').slice(0,600));const raw=await r.text();return raw?JSON.parse(raw):null;}
async function query(query,read_only=false){return api('/database/query',{method:'POST',body:{query,read_only}});}
const stages=['supabase/migrations/20261022083604_book_trial_10x4000.sql','supabase/migrations/20261022090045_launch_combo_five_books.sql','commerce/manual/trial-10x5000.sql','commerce/manual/trial-group-up-to-four.sql','commerce/manual/trial-five-unit-policy.sql','commerce/manual/heygen-trial-dispatcher.sql'];
if(command==='schema'){
 const backup=await query(`select 'devices' as kind,coalesce(jsonb_agg(d),'[]') as rows from public.wsn_book_devices d union all select 'orders',coalesce(jsonb_agg(d),'[]') from public.wsn_book_orders d union all select 'receipts',coalesce(jsonb_agg(d),'[]') from public.wsn_book_receipts d union all select 'legacy_payments',coalesce(jsonb_agg(d),'[]') from public.wsn_payments d union all select 'licenses',coalesce(jsonb_agg(d),'[]') from public.wsn_licenses d`,true);
 writeFileSync('.qa/cloud-deploy/before.private.json',JSON.stringify(backup),{mode:0o600});
 const existing=await query("select to_regclass('public.wsn_heygen_tasks')::text as worker,to_regclass('public.wsn_launch_bundles')::text as bundles,exists(select 1 from information_schema.columns where table_schema='public' and table_name='wsn_book_orders' and column_name='trial_units') as grouped",true);
 if(existing[0].worker||existing[0].bundles||existing[0].grouped)throw Error('Partial/previous deployment: review before applying');
 const ddl='begin;\n'+stages.map(p=>readFileSync(p,'utf8').replace(/^begin;$/gm,'').replace(/^commit;$/gm,'')).join('\n')+"\nnotify pgrst, 'reload schema';\ncommit;";
 writeFileSync('.qa/cloud-deploy/applied.sql',ddl,{mode:0o600});await query(ddl);console.log('Applied quota5, immutable grouped trials and private trial dispatcher; preserved old rows.');
}else if(command==='deploy'||command==='deploy-books'){
 // Repair the existing gateway without redeploying or activating the dispatcher.
 for(const slug of command==='deploy-books'?['wsn-books']:['wsn-books','wsn-heygen-worker']){
  const withoutImports=p=>readFileSync(p,'utf8').replace(/^import .*;\s*$/gm,'');
  const source="type Env=(name:string)=>string|undefined;type Fetch=typeof fetch;\n"+withoutImports('supabase/functions/_shared/books.ts')+'\n'+(slug==='wsn-heygen-worker'?withoutImports('supabase/functions/_shared/heygen-worker.ts')+'\n':'')+withoutImports(`supabase/functions/${slug}/index.ts`);
  const form=new FormData();form.set('metadata',JSON.stringify({entrypoint_path:'index.ts',name:slug,verify_jwt:false}));form.append('file',new Blob([source],{type:'application/typescript'}),'index.ts');
  const r=await api('/functions/deploy?slug='+slug,{method:'POST',body:form});console.log(JSON.stringify({slug:r.slug,status:r.status,version:r.version}));
 }
}else if(command==='secrets'){
 const paidSchema=await query("select to_regprocedure('public.wsn_heygen_next_v2(boolean)') is not null as present",true);if(paidSchema[0].present)throw Error('Paid service is installed: use paid-cloud-deploy.mjs; trial setup must not reset its activation flags');
 const code=process.env.WSN_TEST_DEVICE;if(!/^SN[A-F0-9]{12}$/.test(code||''))throw Error('Supply the explicit owner test device code');
 if(!process.env.HEYGEN_API_KEY||process.env.HEYGEN_MODEL!=='heygen-voice-1-turbo-free')throw Error('Only configured free HeyGen model is allowed for this trial deployment');
 let worker;try{worker=readFileSync('.qa/cloud-deploy/worker-token.private','utf8');}catch{worker=randomBytes(32).toString('hex');writeFileSync('.qa/cloud-deploy/worker-token.private',worker,{mode:0o600});}
 await api('/secrets',{method:'POST',body:Object.entries({WSN_HEYGEN_API_KEY:process.env.HEYGEN_API_KEY,WSN_HEYGEN_WORKER_TOKEN:worker,WSN_BOOKS_TRIALS_ENABLED:'true',WSN_BOOKS_TEST_DEVICES:code,WSN_BOOKS_ENABLED:'false',WSN_LAUNCH_COMBO_ENABLED:'false'}).map(([name,value])=>({name,value}))});
 // Vault holds the random worker key. pg_net sees only a short-lived HMAC proof, never a reusable secret.
 await query(`do $vault$ declare existing uuid;begin select id into existing from vault.secrets where name='wsn_heygen_worker_token';if found then perform vault.update_secret(existing,'${worker}','wsn_heygen_worker_token','Sách Nói owner trial dispatcher');else perform vault.create_secret('${worker}','wsn_heygen_worker_token','Sách Nói owner trial dispatcher');end if;end;$vault$;`);
 const schedule=`with proof as (select floor(extract(epoch from now()))::bigint::text||'.'||replace(gen_random_uuid()::text,'-','') as message) select net.http_post(url:='https://${ref}.supabase.co/functions/v1/wsn-heygen-worker',headers:=jsonb_build_object('Content-Type','application/json','x-wsn-worker-proof',message||'.'||encode(extensions.hmac(message,(select decrypted_secret from vault.decrypted_secrets where name='wsn_heygen_worker_token' limit 1),'sha256'),'hex')),body:='{}'::jsonb,timeout_milliseconds:=120000) from proof where exists(select 1 from public.wsn_book_orders where kind='trial' and payload->>'revision'='pro-cloud-heygen-v1' and state in ('queued','processing'));`;
 const r=await query(`select cron.schedule('wsn-heygen-trial-dispatch','3 seconds',$schedule$${schedule}$schedule$) as job;`);console.log(JSON.stringify({trialEnabled:true,testDevice:code,paidEnabled:false,workerSchedule:r}));
}else if(command==='verify'){
 const result=await query(`select (select count(*) from wsn_payments) as legacy_receipts,(select count(*) from wsn_licenses) as legacy_licenses,(select count(*) from wsn_book_orders) as orders,(select coalesce(sum(trials_used),0) from wsn_book_devices) as used,(select public from storage.buckets where id='wsn-book-audio') as audio_public,(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname in ('wsn_book_devices','wsn_book_orders','wsn_book_receipts','wsn_heygen_control','wsn_heygen_tasks') and c.relrowsecurity) as protected_tables;`,true);console.log(JSON.stringify(result));
}else throw Error('Use schema, deploy, deploy-books, secrets or verify');
