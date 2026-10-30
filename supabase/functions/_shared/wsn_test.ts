import { webhook, license, signedLicense, deviceCode, type Env, type Fetch } from './wsn.ts';
function assert(value: unknown, message = 'Assertion failed'): asserts value { if (!value) throw Error(message); }
const code = 'SN123456ABCDEF';
const account = '55111685555';
const variables: Record<string, string> = { WSN_SEPAY_WEBHOOK_API_KEY: 'test-webhook', WSN_SEPAY_API_TOKEN: 'test-api', WSN_BANK_ACCOUNT: account, SUPABASE_URL: 'https://test.supabase.co', SUPABASE_SERVICE_ROLE_KEY: 'test-server' };
const env: Env = name => variables[name];
const request = (change: Record<string, unknown> = {}, key = 'test-webhook') => new Request('https://test/functions/v1/wsn-sepay-webhook', { method: 'POST', headers: { authorization: 'Apikey ' + key }, body: JSON.stringify({ id: 123, accountNumber: account, transferType: 'in', transferAmount: 189000, content: 'Mua sach ' + code, transactionDate: '2026-10-20 12:00:00', ...change }) });
const transaction = { id: '123', account_number: account, amount_in: '189000.00', amount_out: '0.00', transaction_content: 'Mua sach ' + code, transaction_date: '2026-10-20 12:00:00' };
const fake = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
Deno.test('device codes are exact, bounded and unambiguous', () => {
  assert(deviceCode(code) === code); assert(deviceCode('mua ' + code.toLowerCase()) === code);
  for (const text of [code + '0', 'X' + code, code + ' ' + code, 'SN1234567890', '', null]) assert(deviceCode(text) === null);
});
Deno.test('wrong webhook key cannot reach bank API or database', async () => {
  const response = await webhook(request({}, 'wrong'), env, (() => { throw Error('must not fetch'); }) as Fetch);
  assert(response.status === 401);
});
Deno.test('outflow, another account, wrong amount and ambiguous code do not activate', async () => {
  for (const change of [{ transferType: 'out' }, { accountNumber: '12345678' }, { transferAmount: 188999 }, { content: code + ' ' + code }]) {
    const response = await webhook(request(change), env, (() => { throw Error('must not fetch'); }) as Fetch);
    assert((await response.json()).status === 'ignored');
  }
});
Deno.test('synthetic test receipt absent from SePay API does not activate', async () => {
  let calls = 0;
  const response = await webhook(request(), env, (async () => { calls++; return fake({}, 404); }) as Fetch);
  assert(calls === 1); assert((await response.json()).status === 'ignored');
});
Deno.test('API lookup failure asks SePay to retry without creating a receipt', async () => {
  const response = await webhook(request(), env, (async () => fake({}, 429)) as Fetch);
  assert(response.status === 503);
});
Deno.test('confirmed receipt alone reaches atomic RPC, duplicate preserved', async () => {
  for (const status of ['paid', 'duplicate']) {
    let calls = 0;
    const response = await webhook(request(), env, (async (url, init) => {
      calls++;
      if (calls === 1) { assert(String(url).endsWith('/123')); assert(new Headers(init?.headers).get('authorization') === 'Bearer test-api'); return fake({ status: 200, error: null, transaction }); }
      assert(String(url).endsWith('/rpc/wsn_accept_payment'));
      const args = JSON.parse(init?.body as string);
      assert(args.p_device_code === code && args.p_amount_vnd === 189000 && args.p_paid_at === '2026-10-20T05:00:00.000Z');
      return fake({ status });
    }) as Fetch);
    assert(calls === 2); assert((await response.json()).status === status);
  }
});
Deno.test('authoritative bank mismatch never reaches RPC', async () => {
  for (const change of [{ id: '456' }, { amount_in: '189000.50' }, { amount_out: '1.00' }, { account_number: '12345678' }, { transaction_content: 'SNAAAAAAAAAAAA' }, { transaction_date: '2026-02-30 12:00:00' }]) {
    let calls = 0;
    const response = await webhook(request(), env, (async () => { calls++; return fake({ status: 200, error: null, transaction: { ...transaction, ...change } }); }) as Fetch);
    assert(calls === 1); assert((await response.json()).status === 'ignored');
  }
});
Deno.test('license Ed25519 envelope verifies offline and is bound to payload', async () => {
  const pair = await crypto.subtle.generateKey('Ed25519', true, ['sign', 'verify']) as CryptoKeyPair;
  const der = new Uint8Array(await crypto.subtle.exportKey('pkcs8', pair.privateKey));
  const pem = '-----BEGIN PRIVATE KEY-----\n' + btoa(String.fromCharCode(...der)) + '\n-----END PRIVATE KEY-----';
  const payload = { schema: 2, product: 'windi-sach-noi-pro', orderId: 'test', deviceCode: code, issuedAt: '2026-10-20T05:00:00.000Z', expiresAt: '2027-10-20T05:00:00.000Z' };
  const envelope = await signedLicense(payload, pem);
  const decode = (text: string) => Uint8Array.from(atob(text), c => c.charCodeAt(0));
  assert(await crypto.subtle.verify('Ed25519', pair.publicKey, decode(envelope.signature), decode(envelope.payload)));
  assert(!await crypto.subtle.verify('Ed25519', pair.publicKey, decode(envelope.signature), new TextEncoder().encode('changed')));
  const response = await license(new Request('https://test/functions/v1/wsn-license/' + code + '.windilicense'), name => name === 'WSN_LICENSE_PRIVATE_KEY_PEM' ? pem : env(name), (async () => fake([{ license_payload: payload, expires_at: payload.expiresAt }])) as Fetch);
  assert(response.status === 200); assert((await response.json()).signature === envelope.signature);
});
Deno.test('unknown and expired licenses do not unlock; path traversal rejected', async () => {
  for (const [rows, status] of [[[], 404], [[{ expires_at: '2020-01-01T00:00:00Z' }], 410]] as const) {
    const response = await license(new Request('https://test/functions/v1/wsn-license/' + code + '.windilicense'), env, (async () => fake(rows)) as Fetch);
    assert(response.status === status);
  }
  const bad = await license(new Request('https://test/functions/v1/wsn-license/SNwrong.windilicense'), env, (() => { throw Error('must not fetch'); }) as Fetch);
  assert(bad.status === 404);
});
