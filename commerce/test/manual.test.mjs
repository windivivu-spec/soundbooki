import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync, verify } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { resolve,join } from 'node:path';
import { issueManual } from '../manual/issue.mjs';
async function fixture(t){
  const directory=await mkdtemp(resolve('../.qa/manual-')),{privateKey,publicKey}=generateKeyPairSync('ed25519'),keyFile=join(directory,'key.pem');
  await writeFile(keyFile,privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600});t.after(()=>rm(directory,{recursive:true,force:true}));
  const input={deviceCode:'SNABCDEF123456',transactionId:'bank-test-001',receivedAmount:189000,paidAt:'2026-10-20T03:00:00Z',confirmed:true,keyFile,ledgerFile:join(directory,'ledger.sqlite'),now:Date.parse('2026-10-20T03:05:00Z')};
  return {input,publicKey};
}
test('device QR needs actual merchant confirmation, exact amount and valid bank transaction',async t=>{
  const {input}=await fixture(t);for(const patch of [{confirmed:false},{receivedAmount:188999},{receivedAmount:189001},{deviceCode:'SNinvalid'},{transactionId:''},{paidAt:'2026-10-22T03:00:00Z'}])assert.throws(()=>issueManual({...input,...patch}));
});
test('device receipt signs annual license without email; transaction cannot unlock a second machine',async t=>{
  const {input,publicKey}=await fixture(t),license=issueManual(input);assert.deepEqual(issueManual(input),license);assert.ok(verify(null,Buffer.from(license.payload,'base64'),publicKey,Buffer.from(license.signature,'base64')));
  const data=JSON.parse(Buffer.from(license.payload,'base64'));assert.equal(data.schema,2);assert.equal(data.deviceCode,input.deviceCode);assert.equal(data.expiresAt,'2027-10-20T03:00:00.000Z');assert.equal(data.email,undefined);assert.notEqual(data.orderId,input.transactionId);
  assert.throws(()=>issueManual({...input,deviceCode:'SN000000000000'}));
});
test('same device renews with a new bank transaction and retrying old receipt never shortens license',async t=>{
  const {input}=await fixture(t);issueManual(input);const renewed=issueManual({...input,transactionId:'bank-test-002'});
  assert.equal(JSON.parse(Buffer.from(renewed.payload,'base64')).expiresAt,'2028-10-20T03:00:00.000Z');assert.deepEqual(issueManual(input),renewed);
});
