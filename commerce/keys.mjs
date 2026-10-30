import { generateKeyPairSync } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const directory=resolve(process.argv[2]||'private');
await mkdir(directory,{recursive:true,mode:0o700});
const {privateKey,publicKey}=generateKeyPairSync('ed25519');
await writeFile(resolve(directory,'license-private.pem'),privateKey.export({type:'pkcs8',format:'pem'}),{flag:'wx',mode:0o600});
await writeFile(resolve(directory,'license-public.txt'),publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('base64')+'\n',{flag:'wx'});
process.stdout.write('Created signing key. Keep the private key on the backend only.\n');
