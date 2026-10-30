import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { createPaymentModule, configFromEnv, parsePaymentCode, createSqliteStore } from '../src/index.js';
import { transactionTime } from '../src/sepay.js';
import { nodeHandler } from '../src/node.js';

const baseline = Date.parse('2026-10-15T03:00:00.500Z');
const env = { QR_BANK_BIN: '970422', QR_BANK_ACCOUNT: '00123456789', QR_BANK_NAME: 'TEST ACCOUNT',
  QR_API_KEY: 'backend-test-key-00000000000000000000', SEPAY_WEBHOOK_API_KEY: 'sepay-test-key-00000000000',
  QR_CODE_PREFIX: 'WD', QR_CODE_LENGTH: '6', QR_PROJECT_ID: 'fixture', QR_SQLITE_PATH: ':memory:' };
async function fixture(t, overrides = {}, options = {}) {
  let time = baseline;
  const payments = await createPaymentModule({ env: { ...env, ...overrides }, now: () => time, ...options });
  t.after(() => payments.close());
  return { payments, setTime: value => { time = value; } };
}
const input = { amount: 69000, idempotencyKey: 'invoice-1', metadata: { invoiceId: 'invoice-1', privateCustomer: 'hidden' } };
function webhook(order, overrides = {}, secret = env.SEPAY_WEBHOOK_API_KEY) {
  return new Request('http://localhost/api/payments/webhook', { method: 'POST', headers: { Authorization: `Apikey ${secret}` },
    body: JSON.stringify({ id: 123, accountNumber: env.QR_BANK_ACCOUNT, transferType: 'in', transferAmount: order.amount,
      content: `Thanh toan ${order.code}`, transactionDate: '2026-10-15 10:00:01', ...overrides }) });
}
function orderRequest(data = input, token = env.QR_API_KEY) {
  return new Request('http://localhost/api/payments/orders', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
}
const statusRequest = (order, token = order.statusToken) => new Request(`http://localhost/api/payments/orders/${order.id}`, { headers: { Authorization: `Bearer ${token}` } });

test('configuration is isolated, fails closed and supports WD029292', () => {
  const config = configFromEnv(env);
  assert.equal(parsePaymentCode('Thanh toan WD029292!', config), 'WD029292');
  assert.equal(parsePaymentCode('wd 029292', config), 'WD029292');
  for (const key of ['QR_BANK_BIN', 'QR_BANK_ACCOUNT', 'QR_BANK_NAME', 'QR_API_KEY', 'SEPAY_WEBHOOK_API_KEY']) {
    assert.throws(() => configFromEnv({ ...env, [key]: '' }), /Missing/);
  }
  for (const patch of [{ QR_CODE_PREFIX: 'A+' }, { QR_CODE_LENGTH: '5' }, { QR_CODE_LENGTH: '11' },
    { QR_API_KEY: 'short' }, { QR_CODE_CHARSET: 'regex' }, { QR_ORDER_TTL_SECONDS: '-1' },
    { QR_API_KEY: env.SEPAY_WEBHOOK_API_KEY }, { VERCEL: '1' }]) assert.throws(() => configFromEnv({ ...env, ...patch }));
});
test('code boundaries, conflicting matches and alpha formats are unambiguous', () => {
  const config = configFromEnv(env);
  for (const content of ['AWD029292', 'WD0292929', 'WD029292X', 'WD029292 WD123456', 'WD029292 WD029292', 'WD02929']) {
    assert.equal(parsePaymentCode(content, config), null);
  }
  assert.equal(parsePaymentCode('AB1A2B3C', configFromEnv({ ...env, QR_CODE_PREFIX: 'AB', QR_CODE_CHARSET: 'alphanumeric' })), 'AB1A2B3C');
});
test('time parsing is deterministic and rejects invalid dates or ambiguous server timezone', () => {
  assert.equal(transactionTime('2026-10-15 10:00:01'), '2026-10-15T03:00:01.000Z');
  assert.equal(transactionTime('2026-10-15T10:00:01+07:00'), '2026-10-15T03:00:01.000Z');
  for (const value of ['2026-02-30 10:00:00', '2026-10-15 25:00:00', '2026-10-15', 'invalid', null]) assert.equal(transactionTime(value), null);
});
test('complete order → QR → webhook → paid → scoped browser status flow', async t => {
  const { payments } = await fixture(t);
  const created = await payments.handle(orderRequest()); assert.equal(created.status, 201);
  const order = await created.json();
  assert.match(order.code, /^WD\d{6}$/);
  const qr = new URL(order.qrUrl);
  assert.equal(qr.searchParams.get('addInfo'), order.code); assert.equal(qr.searchParams.get('amount'), '69000');
  assert.match(qr.pathname, /970422-00123456789/);
  assert.equal((await (await payments.handle(webhook(order))).json()).status, 'paid');
  const response = await payments.handle(statusRequest(order)); assert.equal(response.headers.get('cache-control'), 'no-store');
  const publicStatus = await response.json(); assert.equal(publicStatus.status, 'paid');
  for (const key of ['metadata', 'statusToken', 'transactionId', 'sepayKey', 'apiKey']) assert.equal(key in publicStatus, false);
  assert.equal((await payments.getOrder(order.id)).metadata.privateCustomer, 'hidden');
});
test('idempotent creation is stable under retries and rejects changed price/metadata', async t => {
  const { payments } = await fixture(t);
  const orders = await Promise.all(Array.from({ length: 20 }, () => payments.createOrder(input)));
  assert.equal(new Set(orders.map(order => order.id)).size, 1);
  assert.equal(new Set(orders.map(order => order.statusToken)).size, 1);
  await assert.rejects(payments.createOrder({ ...input, amount: 1 }), /Idempotency/);
  await assert.rejects(payments.createOrder({ ...input, metadata: { invoiceId: 'other' } }), /Idempotency/);
  const reordered = await payments.createOrder({ ...input, metadata: { privateCustomer: 'hidden', invoiceId: 'invoice-1' } });
  assert.equal(reordered.id, orders[0].id);
});
test('browser cannot create orders or read another order without its token', async t => {
  const { payments } = await fixture(t);
  const order = await payments.createOrder(input);
  assert.equal((await payments.handle(orderRequest(input, order.statusToken))).status, 401);
  assert.equal((await payments.handle(statusRequest(order, 'wrong'))).status, 401);
  const other = await payments.createOrder({ ...input, idempotencyKey: 'invoice-2' });
  assert.equal((await payments.handle(statusRequest(other, order.statusToken))).status, 401);
  assert.equal((await payments.handle(statusRequest(order, env.QR_API_KEY))).status, 200);
});
for (const [name, patch] of [['outbound', { transferType: 'out' }], ['wrong account', { accountNumber: '999' }],
  ['unknown code', { content: 'WD9999999' }], ['two codes', { content: 'WD029292 WD123456' }], ['conflicting code field', { code: 'WD987654' }]]) {
  test(`${name} cannot pay an order`, async t => {
    const { payments } = await fixture(t); const order = await payments.createOrder(input);
    assert.equal((await payments.webhook(webhook(order, patch))).status, 'ignored');
    assert.equal((await payments.getOrder(order.id)).status, 'pending');
  });
}
test('empty content can fall back to SePay code field', async t => {
  const { payments } = await fixture(t); const order = await payments.createOrder(input);
  assert.equal((await payments.webhook(webhook(order, { content: '', code: order.code }))).status, 'paid');
});
for (const [name, amount] of [['short', 68999], ['over', 69001]]) {
  test(`${name} amount is audited but never auto-settled or summed`, async t => {
    const { payments } = await fixture(t); const order = await payments.createOrder(input);
    assert.equal((await payments.webhook(webhook(order, { transferAmount: amount }))).reason, 'amount_mismatch');
    assert.equal((await payments.webhook(webhook(order, { transferAmount: amount, id: 124 }))).reason, 'amount_mismatch');
    assert.equal((await payments.getOrder(order.id)).status, 'pending');
  });
}
for (const patch of [{ transferAmount: '69000' }, { transferAmount: 1.5 }, { transferAmount: 0 }, { transferAmount: -1 },
  { id: {} }, { id: 0 }, { transactionDate: null }, { transactionDate: '2026-02-30 01:00:00' }]) {
  test(`invalid authenticated payload ${JSON.stringify(patch)} returns 400`, async t => {
    const { payments } = await fixture(t); const order = await payments.createOrder(input);
    assert.equal((await payments.handle(webhook(order, patch))).status, 400);
    assert.equal((await payments.getOrder(order.id)).status, 'pending');
  });
}
test('spoofed webhook, invalid JSON, and chunked oversized payload are rejected', async t => {
  const { payments } = await fixture(t); const order = await payments.createOrder(input);
  assert.equal((await payments.handle(webhook(order, {}, 'wrong'))).status, 401);
  const malformed = new Request('http://localhost/api/payments/webhook', { method: 'POST', headers: { Authorization: `Apikey ${env.SEPAY_WEBHOOK_API_KEY}` }, body: 'null' });
  assert.equal((await payments.handle(malformed)).status, 400);
  const huge = webhook(order, { content: 'x'.repeat(33000) }); assert.equal((await payments.handle(huge)).status, 413);
});
test('parallel duplicate webhooks cause exactly one paid transition', async t => {
  const { payments } = await fixture(t); const order = await payments.createOrder(input);
  const results = await Promise.all(Array.from({ length: 25 }, () => payments.webhook(webhook(order))));
  assert.equal(results.filter(result => result.status === 'paid').length, 1);
  assert.equal(results.filter(result => result.status === 'duplicate').length, 24);
  assert.equal((await payments.webhook(webhook(order, { id: 124 }))).reason, 'already_paid');
});
test('one bank transaction cannot settle two orders even with a modified replay code', async t => {
  const { payments } = await fixture(t); const order = await payments.createOrder(input);
  const second = await payments.createOrder({ ...input, idempotencyKey: 'second' });
  await payments.webhook(webhook(order));
  assert.equal((await payments.webhook(webhook(second))).status, 'duplicate');
  assert.equal((await payments.getOrder(second.id)).status, 'pending');
});
test('bank time, rather than webhook arrival time, decides expiration', async t => {
  const { payments, setTime } = await fixture(t); const order = await payments.createOrder(input);
  setTime(baseline + 3600000);
  assert.equal((await payments.getOrder(order.id)).status, 'expired');
  assert.equal((await payments.webhook(webhook(order))).status, 'paid');
  assert.equal((await payments.getOrder(order.id)).status, 'paid');
  const late = await payments.createOrder({ ...input, idempotencyKey: 'late' });
  setTime(baseline + 7200000);
  assert.equal((await payments.webhook(webhook(late, { id: 456, transactionDate: '2026-10-15 11:30:01' }))).reason, 'late_payment');
});
test('payments before creation and far in the future are ignored', async t => {
  const { payments } = await fixture(t); const order = await payments.createOrder(input);
  assert.equal((await payments.webhook(webhook(order, { transactionDate: '2026-10-15 09:59:59' }))).reason, 'before_order');
  assert.equal((await payments.webhook(webhook(order, { id: 125, transactionDate: '2026-10-15 10:10:00' }))).reason, 'future_transaction');
});
test('SQLite persists orders, tokens, and replay prevention across restart', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'qr-payment-')); t.after(() => rm(dir, { recursive: true, force: true }));
  const fileEnv = { ...env, QR_SQLITE_PATH: join(dir, 'nested/pay.sqlite') };
  const first = await createPaymentModule({ env: fileEnv, now: () => baseline });
  const order = await first.createOrder(input); await first.webhook(webhook(order)); await first.close();
  const second = await createPaymentModule({ env: fileEnv, now: () => baseline });
  try {
    assert.equal((await second.getOrder(order.id)).status, 'paid');
    assert.equal((await second.webhook(webhook(order))).status, 'duplicate');
    assert.equal((await second.createOrder(input)).statusToken, order.statusToken);
  } finally { await second.close(); }
});
test('multiple SQLite connections and namespaces share replay protection', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'qr-shared-')); t.after(() => rm(dir, { recursive: true, force: true }));
  const path = join(dir, 'pay.sqlite');
  const a = await fixture(t, { QR_SQLITE_PATH: path }); const b = await fixture(t, { QR_SQLITE_PATH: path });
  const order = await a.payments.createOrder(input);
  const results = await Promise.all([a.payments.webhook(webhook(order)), b.payments.webhook(webhook(order))]);
  assert.deepEqual(results.map(x => x.status).sort(), ['duplicate', 'paid']);
  const other = await fixture(t, { QR_SQLITE_PATH: path, QR_PROJECT_ID: 'other', QR_CODE_PREFIX: 'AB' });
  assert.equal(await other.payments.getOrder(order.id), null);
  const own = await other.payments.createOrder(input);
  assert.equal((await other.payments.webhook(webhook(own))).status, 'duplicate');
  assert.equal((await other.payments.getOrder(own.id)).status, 'pending');
});
test('storage failure rolls back paid state and event and allows a safe retry', async t => {
  const store = await createSqliteStore(':memory:'); let fail = true;
  const wrapped = { close: () => store.close(), transaction: (account, work) => store.transaction(account, query => work((sql, args) => {
    if (fail && sql.startsWith('INSERT INTO windi_qr_events')) throw new Error('simulated storage failure');
    return query(sql, args);
  })) };
  const { payments } = await fixture(t, {}, { store: wrapped }); const order = await payments.createOrder(input);
  assert.equal((await payments.handle(webhook(order))).status, 503);
  assert.equal((await payments.getOrder(order.id)).status, 'pending');
  fail = false; assert.equal((await payments.webhook(webhook(order))).status, 'paid');
});
test('invalid order amounts, idempotency keys and large metadata fail before writes', async t => {
  const { payments } = await fixture(t);
  for (const patch of [{ amount: 0 }, { amount: 1.2 }, { amount: '69000' }, { idempotencyKey: '' }, { metadata: 'x'.repeat(8200) }]) {
    assert.equal((await payments.handle(orderRequest({ ...input, ...patch }))).status, 400);
  }
});
test('real Node HTTP adapter works without Express and handles chunked bodies', async t => {
  const { payments } = await fixture(t);
  const server = createServer(nodeHandler(payments)); server.listen(0, '127.0.0.1');
  await once(server, 'listening'); t.after(() => new Promise(resolve => server.close(resolve)));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const created = await fetch(`${origin}/api/payments/orders`, { method: 'POST', headers: { Authorization: `Bearer ${env.QR_API_KEY}` }, body: JSON.stringify(input) });
  assert.equal(created.status, 201); const order = await created.json();
  const response = await fetch(`${origin}/api/payments/webhook`, { method: 'POST', headers: { Authorization: `Apikey ${env.SEPAY_WEBHOOK_API_KEY}` }, body: await webhook(order).text() });
  assert.equal((await response.json()).status, 'paid');
  const status = await fetch(`${origin}/api/payments/orders/${order.id}`, { headers: { Authorization: `Bearer ${order.statusToken}` } });
  assert.equal((await status.json()).status, 'paid');
});
