import { PaymentError } from './sepay.js';

function required(env, name) {
  const value = env[name]?.trim();
  if (!value) throw new PaymentError(`Missing environment variable: ${name}`, 503);
  return value;
}
function integer(value, fallback, min, max, label) {
  const n = value === undefined || value === '' ? fallback : Number(value);
  if (!Number.isSafeInteger(n) || n < min || n > max) throw new PaymentError(`Invalid ${label}`, 503);
  return n;
}
export function configFromEnv(env = process.env) {
  const config = {
    bank: required(env, 'QR_BANK_BIN'), account: required(env, 'QR_BANK_ACCOUNT'), name: required(env, 'QR_BANK_NAME'),
    sepayKey: required(env, 'SEPAY_WEBHOOK_API_KEY'), apiKey: required(env, 'QR_API_KEY'),
    prefix: (env.QR_CODE_PREFIX || 'WD').trim().toUpperCase(),
    codeLength: integer(env.QR_CODE_LENGTH, 10, 6, 10, 'QR_CODE_LENGTH (6..10)'),
    codeCharset: env.QR_CODE_CHARSET || 'digits',
    ttlSeconds: integer(env.QR_ORDER_TTL_SECONDS, 900, 60, 86400, 'QR_ORDER_TTL_SECONDS'),
    project: env.QR_PROJECT_ID || 'default', databaseUrl: env.QR_DATABASE_URL || '',
    sqlitePath: env.QR_SQLITE_PATH || './data/qr-payments.sqlite',
  };
  if (!/^[A-Z]{2,5}$/.test(config.prefix)) throw new PaymentError('QR_CODE_PREFIX must contain 2..5 letters', 503);
  if (!['digits', 'alphanumeric'].includes(config.codeCharset)) throw new PaymentError('Invalid QR_CODE_CHARSET', 503);
  if (!/^[A-Za-z0-9]{2,20}$/.test(config.bank) || !/^[A-Za-z0-9]{1,64}$/.test(config.account)) throw new PaymentError('Invalid bank/account', 503);
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(config.project)) throw new PaymentError('Invalid QR_PROJECT_ID', 503);
  if (config.apiKey.length < 32 || config.sepayKey.length < 16 || config.apiKey === config.sepayKey) {
    throw new PaymentError('Use distinct QR_API_KEY (32+ chars) and SEPAY_WEBHOOK_API_KEY (16+ chars)', 503);
  }
  if (!config.databaseUrl && (env.VERCEL || env.AWS_LAMBDA_FUNCTION_NAME || env.K_SERVICE || env.NETLIFY)) {
    throw new PaymentError('Set QR_DATABASE_URL for a persistent PostgreSQL database on serverless', 503);
  }
  return Object.freeze(config);
}
