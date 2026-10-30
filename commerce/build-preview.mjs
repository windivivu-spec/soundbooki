// Public checkout configuration only; provider tokens never enter the app bundle.
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { createQrUrl } from '../package qr pay/src/index.js';
const bank={bank:process.env.VOICE_BANK_BIN,account:process.env.VOICE_BANK_ACCOUNT,name:process.env.VOICE_BANK_NAME};
if(Object.values(bank).some(value=>!value))throw Error('Missing public bank configuration in .env.local');
const origin=new URL(process.env.SUPABASE_URL);
if(origin.protocol!=='https:'||origin.username||origin.password)throw Error('Use the selected HTTPS license service');
const childEnv=Object.fromEntries(['PATH','HOME','TMPDIR','USER','LOGNAME','SHELL','LANG','LC_ALL'].filter(key=>process.env[key]).map(key=>[key,process.env[key]]));
const result=spawnSync(resolve('.runtime/bin/python'),[
 'scripts/package_macos.py','--output',process.argv[2]||'dist/mac-0.6.3-preview-music',
 '--public-key-file','commerce/private/license-public.txt','--checkout-mode','qr',
 '--checkout-url',createQrUrl(bank,189000,''),
 '--license-base-url',new URL('/functions/v1/wsn-license/',origin).href,
],{cwd:resolve('.'),env:childEnv,stdio:'inherit'});
if(result.error)throw result.error;
process.exitCode=result.status??1;
