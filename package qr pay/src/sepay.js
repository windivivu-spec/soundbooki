import { timingSafeEqual } from 'node:crypto';
import { Buffer } from 'node:buffer';

export class PaymentError extends Error {
  constructor(message, status = 400) { super(message); this.name = 'PaymentError'; this.status = status; }
}

export function verifyAuthorization(supplied, expected) {
  if (!expected) throw new PaymentError('Payment authentication is not configured', 503);
  const a = Buffer.from(supplied || '');
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) throw new PaymentError('Unauthorized', 401);
}

export function transactionTime(value) {
  if (typeof value !== 'string') return null;
  const local = value.trim().match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})$/);
  // SePay bank timestamps have Vietnam's UTC+07 offset, independent of server TZ.
  const iso = local ? `${local[1]}T${local[2]}+07:00` : value;
  if (!local && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(iso)) return null;
  const clock = iso.slice(0, 19);
  const calendar = Date.parse(`${clock}Z`);
  if (!Number.isFinite(calendar) || new Date(calendar).toISOString().slice(0, 19) !== clock) return null;
  const parsed = Date.parse(iso);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
}

export async function readJson(request, maxBytes = 32768) {
  if (Number(request.headers.get('content-length')) > maxBytes) throw new PaymentError('Payload too large', 413);
  if (!request.body) throw new PaymentError('JSON body required');
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maxBytes) { await reader.cancel(); throw new PaymentError('Payload too large', 413); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  try {
    const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error();
    return body;
  } catch { throw new PaymentError('Invalid JSON object'); }
}

export async function readSepayWebhook(request, { apiKey, account }) {
  if (!apiKey || !account) throw new PaymentError('SePay is not configured', 503);
  verifyAuthorization(request.headers.get('authorization'), `Apikey ${apiKey}`);
  const body = await readJson(request);
  if (body.transferType !== 'in' || String(body.accountNumber) !== account) return null;
  if (!Number.isSafeInteger(body.transferAmount) || body.transferAmount <= 0 ||
      !(typeof body.id === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(body.id) || Number.isSafeInteger(body.id) && body.id > 0)) {
    throw new PaymentError('Invalid payment');
  }
  return { id: String(body.id), amount: body.transferAmount, content: typeof body.content === 'string' ? body.content : '',
    code: typeof body.code === 'string' ? body.code : '', paidAt: transactionTime(body.transactionDate), payload: body };
}
