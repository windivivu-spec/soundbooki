#!/usr/bin/env node
import { createServer } from 'node:http';
import { createPaymentModule } from './index.js';
import { nodeHandler } from './node.js';

try {
  const port = Number(process.env.PORT || 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid PORT');
  const payments = await createPaymentModule();
  const server = createServer(nodeHandler(payments));
  server.requestTimeout = 15000;
  server.headersTimeout = 10000;
  server.listen(port, process.env.HOST || '127.0.0.1', () => console.log(`QR payment API listening on port ${port}`));
  server.on('error', () => { console.error('Cannot listen on payment port'); process.exitCode = 1; void payments.close(); });
  for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => server.close(async () => { await payments.close(); process.exit(0); }));
} catch (error) {
  // Do not print database URLs, provider payloads, tokens or connection errors.
  console.error(error?.name === 'PaymentError' ? error.message : 'Payment service initialization failed; check database connectivity');
  process.exitCode = 1;
}
