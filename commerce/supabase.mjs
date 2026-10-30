// Explicitly targets this app's two tables/functions in the shared Supabase project.
import { readFileSync, writeFileSync, mkdirSync, unlinkSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
const ref = 'zpjphixcttehkkgxlmsn';
const root = resolve(import.meta.dirname, '..');
const migration = resolve(root, 'supabase/migrations/20261020074917_wsn_device_commerce.sql');
const cli = process.env.SUPABASE_CLI || '/Users/win/.npm/_npx/aa8e5c70f9d8d161/node_modules/.bin/supabase';
const token = process.env.SUPABASE_ACCESS_TOKEN;
const url = process.env.SUPABASE_URL;
if (url !== `https://${ref}.supabase.co`) throw Error('Unexpected Supabase target; stopped.');
if (!token) throw Error('Add SUPABASE_ACCESS_TOKEN to .env.local; never send it in chat.');
mkdirSync(resolve(root, '.qa/supabase'), { recursive: true, mode: 0o700 });
async function query(sql, readOnly = false) {
  // CLI 2.120 db query requires an IPv4 DB link on this host. Use its documented
  // Management API equivalent, authenticated by the explicitly supplied PAT.
  const response = await fetch(`https://api.supabase.com/v1/projects/${ref}/database/query`, {
    method: 'POST', headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json' },
    body: JSON.stringify({ query: sql, read_only: readOnly }), signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) throw Error('Supabase SQL HTTP ' + response.status + ': ' + (await response.text()).replaceAll(token, '[redacted]').slice(0, 1000));
  return response.json();
}

function run(args) {
  const result = spawnSync(cli, args, { cwd: root, encoding: 'utf8', env: {
    ...process.env, DO_NOT_TRACK: '1', SUPABASE_TELEMETRY_DISABLED: 'true',
  } });
  if (result.status !== 0) throw Error('Supabase operation failed: ' + result.stderr.replaceAll(token, '[redacted]').slice(-1800));
  console.log('Completed:', args.slice(0, 2).join(' '));
}
const command = process.argv[2] || 'status';
if (command === 'apply') {
  const before = await query("select to_regclass('public.wsn_payments')::text as payments, to_regclass('public.wsn_licenses')::text as licenses;", true);
  console.log('Preflight:', JSON.stringify(before));
  // SQL CREATE TABLE deliberately fails instead of changing an existing table.
  await query(readFileSync(migration, 'utf8'));
  console.log('Created only wsn_payments, wsn_licenses and wsn_accept_payment.');
} else if (command === 'advisors') {
  const response = await fetch(`https://api.supabase.com/v1/projects/${ref}/advisors/security`, {
    headers: { authorization: 'Bearer ' + token }, signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) throw Error('Advisors HTTP ' + response.status);
  const result = await response.json();
  const lints = (result.lints || []).filter(item => JSON.stringify(item).includes('wsn_'));
  console.log(JSON.stringify({ checkedAt: new Date().toISOString(), wsnFindings: lints }, null, 2));
} else if (command === 'verify') {
  console.log(JSON.stringify(await query(readFileSync(resolve(root, 'supabase/verify-wsn.sql'), 'utf8')), null, 2));
} else if (command === 'deploy' || command === 'secrets') {
  const secrets = {
    WSN_SEPAY_API_TOKEN: process.env.SEPAY_API_TOKEN,
    WSN_SEPAY_WEBHOOK_API_KEY: process.env.SEPAY_WEBHOOK_API_KEY,
    WSN_BANK_ACCOUNT: process.env.VOICE_BANK_ACCOUNT,
    WSN_LICENSE_PRIVATE_KEY_PEM: readFileSync(resolve(root, 'commerce/private/license-private.pem'), 'utf8').trim(),
  };
  for (const [key, value] of Object.entries(secrets)) if (!value) throw Error('Missing ' + key);
  const file = resolve(root, '.qa/supabase/secrets.env');
  // dotenv double-quoted strings preserve PEM newlines via literal \\n escapes.
  writeFileSync(file, Object.entries(secrets).map(([key, value]) => key + '=' + JSON.stringify(value)).join('\n') + '\n', { mode: 0o600 });
  try { run(['secrets', 'set', '--project-ref', ref, '--env-file', file]); } finally { unlinkSync(file); }
  if (command === 'deploy') run(['functions', 'deploy', 'wsn-sepay-webhook', 'wsn-license', '--project-ref', ref, '--no-verify-jwt', '--use-api']);
} else if (command === 'status') {
  const result = await query(`select c.relname, c.relrowsecurity as rls,
    has_table_privilege('anon', c.oid, 'SELECT') as anon_read,
    has_table_privilege('authenticated', c.oid, 'SELECT') as member_read,
    has_table_privilege('service_role', c.oid, 'SELECT,INSERT,UPDATE') as backend_access
    from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname in ('wsn_payments','wsn_licenses') order by c.relname;`);
  const counts = await query(`select (select count(*) from public.wsn_payments) as receipts,
    (select count(*) from public.wsn_licenses) as licenses,
    has_function_privilege('anon', 'public.wsn_accept_payment(text,text,text,integer,timestamptz)', 'EXECUTE') as anon_can_accept_payment,
    has_function_privilege('authenticated', 'public.wsn_accept_payment(text,text,text,integer,timestamptz)', 'EXECUTE') as member_can_accept_payment;`, true);
  console.log(JSON.stringify({ tables: result, counts }, null, 2));
} else throw Error('Use apply, verify, secrets, deploy, advisors or status.');
