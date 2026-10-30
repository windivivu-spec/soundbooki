import { createPaymentModule, PaymentError, type PaymentModule } from '@windi/qr-payment';

export const runtime = 'nodejs';
const globalPayments = globalThis as typeof globalThis & { qrPayments?: Promise<PaymentModule> };

async function handler(request: Request) {
  try {
    // Cache the connection pool across dev reloads and warm serverless requests.
    globalPayments.qrPayments ??= createPaymentModule().catch(error => {
      delete globalPayments.qrPayments;
      throw error;
    });
    return (await globalPayments.qrPayments).handle(request);
  } catch (error) {
    return Response.json({ error: error instanceof PaymentError ? error.message : 'Payment service unavailable' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
export const GET = handler;
export const POST = handler;
