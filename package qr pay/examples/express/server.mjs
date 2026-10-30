import express from 'express';
import { createPaymentModule } from '@windi/qr-payment';
import { nodeHandler } from '@windi/qr-payment/node';

const app = express();
const payments = await createPaymentModule();
// Register before express.json(), which consumes the incoming request stream.
app.use('/api/payments', nodeHandler(payments));
app.use(express.json());
app.listen(Number(process.env.PORT || 8787));
