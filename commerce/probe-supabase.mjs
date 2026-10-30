import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createPublicKey, verify } from 'node:crypto';
const base = process.env.SUPABASE_URL;
if (base !== 'https://zpjphixcttehkkgxlmsn.supabase.co') throw Error('Wrong target');
const checks = {};
async function get(url, init) { return fetch(url, { ...init, signal: AbortSignal.timeout(20000) }); }
const bank = await get('https://my.sepay.vn/userapi/transactions/count?account_number=' + encodeURIComponent(process.env.VOICE_BANK_ACCOUNT), { headers: { authorization: 'Bearer ' + process.env.SEPAY_API_TOKEN } });
const bankBody = await bank.json().catch(() => ({}));
checks.sepayApiTokenValid = bank.ok && Number(bankBody.status) === 200 && !bankBody.error;
if (!checks.sepayApiTokenValid) { checks.sepayApiHttp = bank.status; checks.sepayApiResponseCode = bankBody.status ?? null; }
if (checks.sepayApiTokenValid) {
  const accounts = await get('https://my.sepay.vn/userapi/bankaccounts/list?short_name=TPBank&limit=100', {
    headers: { authorization: 'Bearer ' + process.env.SEPAY_API_TOKEN },
  });
  const data = await accounts.json().catch(() => ({}));
  checks.bankLinkedAndActive = accounts.ok && Array.isArray(data.bankaccounts) && data.bankaccounts.some(account =>
    String(account.account_number) === process.env.VOICE_BANK_ACCOUNT && String(account.active) === '1' &&
    (account.bank_code === 'TPB' || String(account.bank_bin) === '970423'));
}
// No bank count, balances, transaction contents or secrets enter the report.
for (const table of ['wsn_payments', 'wsn_licenses']) {
  const anon = await get(base + '/rest/v1/' + table + '?select=*&limit=0', { headers: { apikey: process.env.VITE_SUPABASE_ANON_KEY } });
  checks[table + 'AnonBlocked'] = [401, 403].includes(anon.status);
  const backend = await get(base + '/rest/v1/' + table + '?select=*&limit=0', { headers: { apikey: process.env.SUPABASE_SERVICE_ROLE_KEY, authorization: 'Bearer ' + process.env.SUPABASE_SERVICE_ROLE_KEY } });
  checks[table + 'BackendReady'] = backend.status === 200;
}
const health = await get(base + '/functions/v1/wsn-license/health');
if (health.ok) {
  const envelope = await health.json();
  const raw = readFileSync('commerce/private/license-public.txt', 'utf8').trim();
  const key = createPublicKey({ key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), Buffer.from(raw, 'base64')]), format: 'der', type: 'spki' });
  checks.remoteSigningMatchesAppKey = verify(null, Buffer.from(envelope.payload, 'base64'), key, Buffer.from(envelope.signature, 'base64'));
  const payload = JSON.parse(Buffer.from(envelope.payload, 'base64'));
  checks.healthCannotUnlockPro = payload.schema === 0 && payload.purpose === 'service-health';
} else { checks.remoteSigningMatchesAppKey = false; checks.healthHttp = health.status; }
const missing = await get(base + '/functions/v1/wsn-license/SN000000000000.windilicense');
checks.unknownLicenseBlocked = missing.status === 404;
const bad = await get(base + '/functions/v1/wsn-sepay-webhook', { method: 'POST', headers: { authorization: 'Apikey wrong' }, body: '{}' });
checks.badWebhookKeyBlocked = bad.status === 401; if (bad.status !== 401) checks.badWebhookHttp = bad.status;
const ignored = await get(base + '/functions/v1/wsn-sepay-webhook', { method: 'POST', headers: { authorization: 'Apikey ' + process.env.SEPAY_WEBHOOK_API_KEY, 'content-type': 'application/json' }, body: JSON.stringify({ id: 'qa-no-bank-lookup', accountNumber: process.env.VOICE_BANK_ACCOUNT, transferType: 'in', transferAmount: 1, content: 'SN000000000000' }) });
checks.authenticatedWrongPriceIgnored = ignored.ok && (await ignored.json()).status === 'ignored'; if (!checks.authenticatedWrongPriceIgnored) checks.validWebhookHttp = ignored.status;
if (checks.sepayApiTokenValid) {
  // A nonexistent numeric receipt exercises the deployed SePay API secret.
  // There is no bank transfer and the code must never receive a license.
  const synthetic = await get(base + '/functions/v1/wsn-sepay-webhook', {
    method: 'POST', headers: { authorization: 'Apikey ' + process.env.SEPAY_WEBHOOK_API_KEY, 'content-type': 'application/json' },
    body: JSON.stringify({ id: '999999999999999', accountNumber: process.env.VOICE_BANK_ACCOUNT, transferType: 'in', transferAmount: 189000, content: 'SNEEEEEEEEEEEE' }),
  });
  const result = await synthetic.json().catch(() => ({}));
  checks.syntheticFullPriceReceiptIgnored = synthetic.ok && result.status === 'ignored';
  if (!checks.syntheticFullPriceReceiptIgnored) checks.syntheticHttp = synthetic.status;
}
mkdirSync('.qa/supabase', { recursive: true });
writeFileSync('.qa/supabase/live-probe.json', JSON.stringify({ at: new Date().toISOString(), checks }, null, 2));
console.log(JSON.stringify(checks, null, 2));
if (Object.values(checks).some(value => value !== true)) process.exitCode = 1;
