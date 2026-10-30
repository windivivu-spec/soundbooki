export class PaymentError extends Error { status: number; constructor(message: string, status?: number); }
export function verifyAuthorization(supplied: string | null, expected: string): void;
export function transactionTime(value: unknown): string | null;
export function readJson(request: Request, maxBytes?: number): Promise<Record<string, unknown>>;
export interface SepayTransfer {
  id: string; amount: number; content: string; code: string; paidAt: string | null; payload: Record<string, unknown>;
}
export function readSepayWebhook(request: Request, config: { apiKey: string; account: string }): Promise<SepayTransfer | null>;
