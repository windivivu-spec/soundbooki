export { PaymentError } from './sepay.js';
export type Environment = Record<string, string | undefined>;
export interface PaymentConfig {
  bank: string; account: string; name: string; sepayKey: string; apiKey: string;
  prefix: string; codeLength: number; codeCharset: 'digits' | 'alphanumeric';
  ttlSeconds: number; project: string; databaseUrl: string; sqlitePath: string;
}
export interface PaymentOrder {
  id: string; amount: number; currency: 'VND'; code: string; status: 'pending' | 'paid' | 'expired';
  createdAt: string; expiresAt: string; paidAt: string | null;
  bank: { bank: string; account: string; name: string }; qrUrl: string;
}
export interface PaymentResult { success: true; status: 'paid' | 'ignored' | 'duplicate'; reason?: string; orderId?: string; }
export type Query = (sql: string, args?: unknown[]) => Promise<{ rows: Record<string, unknown>[] }>;
export interface PaymentStore {
  transaction<T>(account: string, work: (query: Query) => Promise<T>): Promise<T>;
  close(): Promise<void>;
}
export interface PostgresPool {
  connect(): Promise<{ query: Query; release(): void }>;
  end(): Promise<void>;
}
export interface PaymentModule {
  createOrder(input: { amount: number; idempotencyKey: string; metadata?: unknown }): Promise<PaymentOrder & { statusToken: string }>;
  getOrder(id: string): Promise<(PaymentOrder & { metadata: unknown; transactionId: string | null }) | null>;
  webhook(request: Request): Promise<PaymentResult>;
  handle(request: Request, options?: { basePath?: string }): Promise<Response>;
  close(): Promise<void>;
}
export function configFromEnv(env?: Environment): Readonly<PaymentConfig>;
export function createPaymentModule(options?: { env?: Environment; store?: PaymentStore; now?: () => number }): Promise<PaymentModule>;
export function createSqliteStore(path: string): Promise<PaymentStore>;
export function createPostgresStore(pool: PostgresPool): Promise<PaymentStore>;
export function parsePaymentCode(content: unknown, config: Pick<PaymentConfig, 'prefix' | 'codeLength' | 'codeCharset'>): string | null;
export function createQrUrl(bank: PaymentOrder['bank'], amount: number, code: string): string;
