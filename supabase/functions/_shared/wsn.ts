// Reuse the framework-independent QR package's bounded parser and API-key auth.
import { readSepayWebhook, transactionTime, PaymentError } from '../../../package qr pay/src/sepay.js';
export type Env = (name: string) => string | undefined;
export type Fetch = typeof fetch;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
});
export function deviceCode(content: unknown): string | null {
  if (typeof content !== 'string' || content.length > 8192) return null;
  const codes = [...content.toUpperCase().matchAll(/(?<![A-Z0-9])SN[A-F0-9]{12}(?![A-Z0-9])/g)];
  return codes.length === 1 ? codes[0][0] : null;
}
export function bookCode(content:unknown):string|null {
 if(typeof content!=='string'||content.length>8192)return null;
 const codes=[...content.toUpperCase().matchAll(/(?<![A-Z0-9])SB[A-F0-9]{32}(?![A-Z0-9])/g)];
 return codes.length===1&&!deviceCode(content)?codes[0][0]:null;
}
function money(value: unknown): number {
  if (typeof value !== 'string' || !/^\d{1,12}(?:\.0{1,2})?$/.test(value)) return -1;
  return Number(value);
}
function required(env: Env, name: string): string {
  const value = env(name); if (!value) throw new PaymentError('Service not configured', 503); return value;
}
async function db(env: Env, fetcher: Fetch, path: string, init: RequestInit = {}) {
  const key = required(env, 'SUPABASE_SERVICE_ROLE_KEY');
  const response = await fetcher(required(env, 'SUPABASE_URL') + '/rest/v1/' + path, {
    ...init, signal: AbortSignal.timeout(10000),
    headers: { apikey: key, authorization: `Bearer ${key}`, 'content-type': 'application/json', ...init.headers },
  });
  if (!response.ok) throw new PaymentError('Database unavailable', 503);
  return response.json();
}
export async function webhook(request: Request, env: Env, fetcher: Fetch = fetch): Promise<Response> {
  if (request.method !== 'POST') return json({ success: false }, 405);
  try {
    const receipt = await readSepayWebhook(request, {
      apiKey: required(env, 'WSN_SEPAY_WEBHOOK_API_KEY'), account: required(env, 'WSN_BANK_ACCOUNT'),
    });
    const book=bookCode(receipt?.content);
    const code = book ? null : deviceCode(receipt?.content);
    if (!receipt || (deviceCode(receipt.content)&&/SB[A-F0-9]{32}/i.test(receipt.content)) || (!book && (receipt.amount !== 189000 || !code))) return json({ success: true, status: 'ignored' });
    // The webhook test tool alone must never create a paid entitlement.
    const check = await fetcher('https://my.sepay.vn/userapi/transactions/details/' + encodeURIComponent(receipt.id), {
      headers: { authorization: 'Bearer ' + required(env, 'WSN_SEPAY_API_TOKEN') },
      signal: AbortSignal.timeout(10000),
    });
    if (check.status === 404) return json({ success: true, status: 'ignored' });
    if (!check.ok) throw new PaymentError('Bank verification unavailable', 503);
    const result = await check.json();
    const tx = result.transaction;
    if (Number(result.status) !== 200 || result.error || !tx) throw new PaymentError('Bank verification unavailable', 503);
    const paidAt = transactionTime(tx.transaction_date);
    if (String(tx.id) !== receipt.id || String(tx.account_number) !== required(env, 'WSN_BANK_ACCOUNT') ||
      money(tx.amount_in) !== receipt.amount || money(tx.amount_out) !== 0 ||
      (book ? bookCode(tx.transaction_content) !== book : deviceCode(tx.transaction_content) !== code) || !paidAt) return json({ success: true, status: 'ignored' });
    if(book){
      const accepted=await db(env,fetcher,'rpc/wsn_book_confirm',{method:'POST',body:JSON.stringify({p_code:book,p_transaction:receipt.id,p_account:String(tx.account_number),p_expected_account:required(env,'WSN_BANK_ACCOUNT'),p_amount:receipt.amount,p_paid_at:paidAt})});
      return json({success:true,status:accepted.status});
    }
    const accepted = await db(env, fetcher, 'rpc/wsn_accept_payment', { method: 'POST', body: JSON.stringify({
      p_transaction_id: receipt.id, p_bank_account: String(tx.account_number), p_device_code: code,
      p_amount_vnd: 189000, p_paid_at: paidAt,
    }) });
    return json({ success: true, status: accepted.status });
  } catch (error) {
    const status = error instanceof PaymentError ? error.status : 503;
    return json({ success: false, error: status === 401 ? 'Unauthorized' : 'Payment not accepted' }, status);
  }
}
function b64(bytes: Uint8Array): string { return btoa(String.fromCharCode(...bytes)); }
export async function signedLicense(payload: unknown, pem: string) {
  const der = atob(pem.replace(/-----[^-]+-----/g, '').replace(/\s/g, ''));
  const key = await crypto.subtle.importKey('pkcs8', Uint8Array.from(der, c => c.charCodeAt(0)), 'Ed25519', false, ['sign']);
  const data = new TextEncoder().encode(JSON.stringify(payload));
  return { payload: b64(data), signature: b64(new Uint8Array(await crypto.subtle.sign('Ed25519', key, data))) };
}
export async function license(request: Request, env: Env, fetcher: Fetch = fetch): Promise<Response> {
  if (request.method !== 'GET') return json({ error: 'Method not allowed' }, 405);
  const path = new URL(request.url).pathname;
  if (path.endsWith('/wsn-license/health')) {
    try {
      await db(env, fetcher, 'wsn_licenses?select=device_code&limit=0');
      return json(await signedLicense({ schema: 0, product: 'windi-sach-noi-pro', purpose: 'service-health', at: new Date().toISOString() }, required(env, 'WSN_LICENSE_PRIVATE_KEY_PEM')));
    } catch { return json({ error: 'Service unavailable' }, 503); }
  }
  const match = path.match(/\/wsn-license\/(SN[A-F0-9]{12})\.windilicense$/);
  if (!match) return json({ error: 'Not found' }, 404);
  try {
    const records = await db(env, fetcher, 'wsn_licenses?select=license_payload,expires_at&device_code=eq.' + match[1] + '&limit=1');
    const record = records[0];
    if (!record) return json({ error: 'License not found' }, 404);
    if (Date.parse(record.expires_at) <= Date.now()) return json({ error: 'License expired' }, 410);
    return json(await signedLicense(record.license_payload, required(env, 'WSN_LICENSE_PRIVATE_KEY_PEM')));
  } catch { return json({ error: 'License unavailable' }, 503); }
}
