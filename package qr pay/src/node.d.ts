import type { IncomingMessage, ServerResponse } from 'node:http';
import type { PaymentModule } from './index.js';
export function nodeHandler(payments: PaymentModule, options?: { basePath?: string }): (req: IncomingMessage, res: ServerResponse) => Promise<void>;
