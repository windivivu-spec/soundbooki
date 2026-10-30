import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
const ref='zpjphixcttehkkgxlmsn',token=process.env.SUPABASE_ACCESS_TOKEN;
if(process.env.SUPABASE_URL!==`https://${ref}.supabase.co`||!token)throw Error('Select the configured Sách Nói database and management token.');
async function query(query,read_only=false){const r=await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`,{method:'POST',headers:{authorization:'Bearer '+token,'content-type':'application/json'},body:JSON.stringify({query,read_only}),signal:AbortSignal.timeout(45000)});if(!r.ok)throw Error('Database HTTP '+r.status+': '+(await r.text()).replaceAll(token,'[redacted]').slice(0,800));return r.json();}
const command=process.argv[2]||'verify';
if(command==='apply'){
 const pre=await query("select to_regclass('public.wsn_book_orders')::text as book_orders,(select count(*) from public.wsn_payments) as legacy_receipts,(select count(*) from public.wsn_licenses) as legacy_licenses",true);
 if(pre[0].book_orders)throw Error('Book ledger already exists. Use verify.');
 mkdirSync('.qa/book-commerce',{recursive:true});writeFileSync('.qa/book-commerce/before.json',JSON.stringify(pre,null,2));
 await query(readFileSync(new URL('../supabase/migrations/20261021140853_book_orders.sql',import.meta.url),'utf8'));console.log('Applied additive per-book ledger. Legacy receipts and licenses retained.');
}else if(command==='sync-create'){
 const source=readFileSync(new URL('../supabase/migrations/20261021140853_book_orders.sql',import.meta.url),'utf8');
 const begin=source.indexOf('create function public.wsn_book_create');const end=source.indexOf('create function public.wsn_book_confirm',begin);
 await query(source.slice(begin,end).replace('create function','create or replace function'));console.log('Updated only the book creation contract; existing snapshots retained.');
}else if(command==='test'){
 const result=await query(readFileSync(new URL('../tests/book-commerce.sql',import.meta.url),'utf8'));console.log(JSON.stringify(result));
}else if(command==='verify'){
 const tables=await query("select c.relname,c.relrowsecurity,has_table_privilege('anon',c.oid,'SELECT') as anon_read,has_table_privilege('authenticated',c.oid,'SELECT') as member_read,has_table_privilege('service_role',c.oid,'SELECT,INSERT,UPDATE') as backend_access from pg_class c join pg_namespace n on c.relnamespace=n.oid where n.nspname='public' and c.relname in ('wsn_book_devices','wsn_book_orders','wsn_book_receipts') order by c.relname",true);
 const functions=await query("select p.proname,has_function_privilege('anon',p.oid,'EXECUTE') as anon_execute,has_function_privilege('authenticated',p.oid,'EXECUTE') as member_execute from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'wsn_book_%'",true);
 const counts=await query("select (select count(*) from public.wsn_payments) as legacy_receipts,(select count(*) from public.wsn_licenses) as legacy_licenses,(select count(*) from public.wsn_book_orders) as book_orders",true);
 const bucket=await query("select id,public from storage.buckets where id='wsn-book-audio'",true);
 const report={tables,functions,counts,bucket};mkdirSync('.qa/book-commerce',{recursive:true});writeFileSync('.qa/book-commerce/database.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 if(tables.length!==3||tables.some(t=>!t.relrowsecurity||t.anon_read||t.member_read||!t.backend_access)||functions.some(f=>f.anon_execute||f.member_execute)||bucket.length!==1||bucket[0].public)throw Error('Database checks failed');
}else throw Error('Use apply, verify or test');
