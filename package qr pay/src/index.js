import { randomInt, randomBytes, randomUUID, createHash } from 'node:crypto';
import { configFromEnv } from './config.js';
import { PaymentError, readSepayWebhook, readJson, verifyAuthorization } from './sepay.js';
import { createSqliteStore, createPostgresStore } from './store.js';

export { configFromEnv, createSqliteStore, createPostgresStore, PaymentError };

function canonical(value, depth = 0) {
  if (depth > 25) throw new PaymentError('Metadata nesting exceeds 25 levels');
  if (Array.isArray(value)) return value.map(item => canonical(item, depth + 1));
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key], depth + 1)]));
  return value;
}
const digest = value => createHash('sha256').update(value).digest('hex');

export function parsePaymentCode(content, config) {
  const suffix = config.codeCharset === 'digits' ? '[0-9]' : '[A-Z0-9]';
  const expression = new RegExp(`(?<![A-Z0-9])${config.prefix}\\s*(${suffix}{${config.codeLength}})(?![A-Z0-9])`, 'g');
  const matches = [...String(content || '').toUpperCase().matchAll(expression)];
  return matches.length === 1 ? `${config.prefix}${matches[0][1]}` : null;
}

export function createQrUrl({ bank, account, name }, amount, code) {
  const url = new URL(`https://img.vietqr.io/image/${encodeURIComponent(bank)}-${encodeURIComponent(account)}-compact2.png`);
  url.search = new URLSearchParams({ amount: String(amount), addInfo: code, accountName: name }).toString();
  return url.toString();
}

function publicOrder(order, now) {
  return { id: order.id, amount: order.amount, currency: 'VND', code: order.code,
    status: order.status === 'pending' && order.expiresAt <= now ? 'expired' : order.status,
    createdAt: new Date(order.createdAt).toISOString(), expiresAt: new Date(order.expiresAt).toISOString(),
    paidAt: order.paidAt, bank: order.bank, qrUrl: createQrUrl(order.bank, order.amount, order.code) };
}

export async function createPaymentModule({ env = process.env, store: suppliedStore, now = Date.now } = {}) {
  const config = configFromEnv(env);
  let store = suppliedStore;
  if (!store) {
    if (config.databaseUrl) {
      const { Pool } = await import('pg');
      const pool = new Pool({ connectionString: config.databaseUrl, max: 5, connectionTimeoutMillis: 5000,
        idleTimeoutMillis: 10000, query_timeout: 10000 });
      try { store = await createPostgresStore(pool); }
      catch (error) { await pool.end(); throw error; }
    } else { store = await createSqliteStore(config.sqlitePath); }
  }
  const transaction = work => store.transaction(config.account, work);
  const find = async (query, sql, args) => (await query(sql, args)).rows[0];

  async function createOrder({ amount, idempotencyKey, metadata = {} }) {
    if (!Number.isSafeInteger(amount) || amount <= 0) throw new PaymentError('amount must be a positive integer in VND');
    if (typeof idempotencyKey !== 'string' || !idempotencyKey.trim() || idempotencyKey.length > 128) throw new PaymentError('idempotencyKey required (1..128 characters)');
    const meta = JSON.stringify(canonical(metadata));
    if (!meta || Buffer.byteLength(meta) > 8192) throw new PaymentError('Metadata too large');
    const fingerprint = digest(JSON.stringify({ amount, metadata: JSON.parse(meta) }));
    return transaction(async query => {
      const existing = await find(query, 'SELECT data, fingerprint FROM windi_qr_orders WHERE project=$1 AND idempotency_key=$2', [config.project, idempotencyKey]);
      if (existing) {
        if (existing.fingerprint !== fingerprint) throw new PaymentError('Idempotency key was used for different order data', 409);
        const order = JSON.parse(existing.data);
        return { ...publicOrder(order, now()), statusToken: order.statusToken };
      }
      const alphabet = config.codeCharset === 'digits' ? '0123456789' : '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      for (let attempt = 0; attempt < 20; attempt++) {
        const code = config.prefix + Array.from({ length: config.codeLength }, () => alphabet[randomInt(alphabet.length)]).join('');
        const order = { id: randomUUID(), code, amount, status: 'pending', createdAt: now(),
          expiresAt: now() + config.ttlSeconds * 1000, paidAt: null, transactionId: null,
          bank: { bank: config.bank, account: config.account, name: config.name },
          metadata: JSON.parse(meta), statusToken: randomBytes(32).toString('base64url') };
        const inserted = await query(`INSERT INTO windi_qr_orders(id,project,account,code,idempotency_key,fingerprint,data)
          VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING RETURNING id`,
        [order.id, config.project, config.account, code, idempotencyKey, fingerprint, JSON.stringify(order)]);
        if (inserted.rows.length) return { ...publicOrder(order, now()), statusToken: order.statusToken };
        // Another config using the same project may have won the idempotency key.
        const winner = await find(query, 'SELECT data, fingerprint FROM windi_qr_orders WHERE project=$1 AND idempotency_key=$2', [config.project, idempotencyKey]);
        if (winner) {
          if (winner.fingerprint !== fingerprint) throw new PaymentError('Idempotency conflict', 409);
          const saved = JSON.parse(winner.data);
          return { ...publicOrder(saved, now()), statusToken: saved.statusToken };
        }
      }
      throw new PaymentError('Payment code space is busy; increase QR_CODE_LENGTH', 503);
    });
  }

  // Trusted server API: includes private business metadata for fulfillment.
  async function getOrder(id) {
    return transaction(async query => {
      const row = await find(query, 'SELECT data FROM windi_qr_orders WHERE project=$1 AND id=$2', [config.project, id]);
      if (!row) return null;
      const order = JSON.parse(row.data);
      return { ...publicOrder(order, now()), metadata: order.metadata, transactionId: order.transactionId };
    });
  }

  async function webhook(request) {
    const transfer = await readSepayWebhook(request, { apiKey: config.sepayKey, account: config.account });
    if (!transfer) return { success: true, status: 'ignored' };
    // content is authoritative. Never let a code field hide two distinct codes in the narration.
    const contentCode = parsePaymentCode(transfer.content, config);
    const suppliedCode = parsePaymentCode(transfer.code, config);
    const code = contentCode || (!transfer.content.trim() ? suppliedCode : null);
    if (!code || suppliedCode && suppliedCode !== code) return { success: true, status: 'ignored', reason: 'ambiguous_code' };
    if (!transfer.paidAt) throw new PaymentError('Valid transactionDate required');
    return transaction(async query => {
      const event = await find(query, 'SELECT data FROM windi_qr_events WHERE account=$1 AND transaction_id=$2', [config.account, transfer.id]);
      if (event) return { success: true, status: 'duplicate' };
      const row = await find(query, 'SELECT data FROM windi_qr_orders WHERE project=$1 AND account=$2 AND code=$3', [config.project, config.account, code]);
      if (!row) return { success: true, status: 'ignored', reason: 'unknown_order' };
      const order = JSON.parse(row.data);
      const timestamp = Date.parse(transfer.paidAt);
      let reason = null;
      if (order.status === 'paid') reason = 'already_paid';
      else if (transfer.amount !== order.amount) reason = 'amount_mismatch';
      else if (timestamp < Math.floor(order.createdAt / 1000) * 1000) reason = 'before_order';
      else if (timestamp > now() + 300000) reason = 'future_transaction';
      else if (timestamp > order.expiresAt) reason = 'late_payment';
      if (!reason) {
        order.status = 'paid'; order.paidAt = transfer.paidAt; order.transactionId = transfer.id;
        await query('UPDATE windi_qr_orders SET data=$1 WHERE id=$2', [JSON.stringify(order), order.id]);
      }
      const outcome = { success: true, status: reason ? 'ignored' : 'paid', ...(reason ? { reason } : {}), orderId: order.id };
      await query('INSERT INTO windi_qr_events(account,transaction_id,order_id,data) VALUES($1,$2,$3,$4)',
        [config.account, transfer.id, order.id, JSON.stringify({ outcome, payload: transfer.payload, receivedAt: now() })]);
      return outcome;
    });
  }

  async function handle(request, { basePath = '/api/payments' } = {}) {
    const json = (body, status = 200) => Response.json(body, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
    try {
      const path = new URL(request.url).pathname;
      if (path === `${basePath}/webhook` && request.method === 'POST') return json(await webhook(request));
      if (path === `${basePath}/orders` && request.method === 'POST') {
        verifyAuthorization(request.headers.get('authorization'), `Bearer ${config.apiKey}`);
        return json(await createOrder(await readJson(request)), 201);
      }
      const prefix = `${basePath}/orders/`;
      if (path.startsWith(prefix) && request.method === 'GET') {
        const id = path.slice(prefix.length);
        if (!/^[a-f0-9-]{36}$/.test(id)) throw new PaymentError('Order not found', 404);
        const row = await transaction(query => find(query, 'SELECT data FROM windi_qr_orders WHERE project=$1 AND id=$2', [config.project, id]));
        if (!row) throw new PaymentError('Order not found', 404);
        const order = JSON.parse(row.data);
        const header = request.headers.get('authorization');
        if (header !== `Bearer ${config.apiKey}`) verifyAuthorization(header, `Bearer ${order.statusToken}`);
        return json(publicOrder(order, now()));
      }
      return json({ error: 'Not found' }, 404);
    } catch (error) {
      return json({ error: error instanceof PaymentError ? error.message : 'Payment storage temporarily unavailable' }, error instanceof PaymentError ? error.status : 503);
    }
  }
  return { createOrder, getOrder, webhook, handle, close: () => store.close() };
}
