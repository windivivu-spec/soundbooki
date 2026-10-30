import { createQrUrl } from '../package qr pay/src/index.js';
const bank={bank:process.env.VOICE_BANK_BIN,account:process.env.VOICE_BANK_ACCOUNT,name:process.env.VOICE_BANK_NAME};
for (const value of Object.values(bank)) if (!value) throw Error('Missing bank configuration');
process.stdout.write(createQrUrl(bank,189000,'')+'\n');
