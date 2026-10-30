import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync, verify, randomUUID } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { createCommerce } from '../service.mjs';

async function fixture(t,overrides={}) {
  const directory=await mkdtemp(resolve('../.qa/commerce-'));
  const {privateKey,publicKey}=generateKeyPairSync('ed25519');
  const keyFile=join(directory,'private.pem');await writeFile(keyFile,privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600});
  let time=Date.parse('2026-10-20T03:00:00Z');
  const env={WSN_PUBLIC_ORIGIN:'http://localhost',WSN_DATA_DIR:directory,WSN_SIGNING_KEY_FILE:keyFile,WSN_SALES_ENABLED:'true',QR_API_KEY:'fixture-backend-secret-00000000000000000000',SEPAY_WEBHOOK_API_KEY:'fixture-sepay-secret-00000000',...overrides};
  let service=await createCommerce({env,now:()=>time});
  t.after(async()=>{await service.close();await rm(directory,{recursive:true,force:true});});
  async function req(path,{body,cookie='',origin='http://localhost',headers={}}={}){
    const response=await service.handle(new Request('http://localhost'+path,{method:body===undefined?'GET':'POST',headers:{Origin:origin,Cookie:cookie,'Content-Type':'application/json',...headers},body:body===undefined?undefined:JSON.stringify(body)}));
    return {status:response.status,body:await response.json(),cookie:response.headers.get('set-cookie')?.split(';')[0]};
  }
  const register=async(email='reader@example.test')=>req('/api/register',{body:{email,password:'fixture-password-12',name:'Độc giả'}});
  const order=async cookie=>req('/api/orders',{cookie,body:{idempotencyKey:randomUUID(),amount:1,product:'f5-private'}});
  const webhook=async(order,patch={},key=env.SEPAY_WEBHOOK_API_KEY)=>req('/api/payments/webhook',{body:{id:randomUUID(),accountNumber:'55111685555',transferType:'in',transferAmount:189000,content:order.code,transactionDate:new Date(time+1000).toISOString(),...patch},headers:{Authorization:'Apikey '+key}});
  return {req,register,order,webhook,publicKey,setTime:value=>time=value,restart:async()=>{await service.close();service=await createCommerce({env,now:()=>time});}};
}
test('annual price is server-owned; idempotency and user isolation',async t=>{
  const f=await fixture(t),a=await f.register(),b=await f.register('other@example.test');
  assert.equal(a.status,201);assert.ok(a.body.recoveryCode);
  const key=randomUUID(),input={idempotencyKey:key,amount:1};
  const first=await f.req('/api/orders',{cookie:a.cookie,body:input}),again=await f.req('/api/orders',{cookie:a.cookie,body:input});
  assert.equal(first.body.amount,189000);assert.equal(first.body.bank.bank,'TPB');assert.equal(first.body.bank.account,'55111685555');assert.equal(first.body.bank.name,'BUI QUOC HUNG');
  assert.equal(first.body.id,again.body.id);
  assert.equal((await f.req('/api/orders/'+first.body.id,{cookie:b.cookie})).status,404);
  assert.equal((await f.req('/api/orders/'+first.body.id+'/license',{cookie:b.cookie})).status,404);
  assert.equal((await f.req('/api/orders/'+first.body.id+'/license',{cookie:a.cookie})).status,409);
});
test('webhook settlement, replay, annual signature and persistence',async t=>{
  const f=await fixture(t),a=await f.register(),order=(await f.order(a.cookie)).body;
  assert.equal((await f.webhook(order,{},'wrong-key')).status,401);
  assert.equal((await f.webhook(order,{transferAmount:188999})).body.reason,'amount_mismatch');
  assert.equal((await f.webhook(order,{accountNumber:'other'})).body.status,'ignored');
  const id=randomUUID();assert.equal((await f.webhook(order,{id})).body.status,'paid');assert.equal((await f.webhook(order,{id})).body.status,'duplicate');
  const result=await f.req('/api/orders/'+order.id+'/license',{cookie:a.cookie});assert.equal(result.status,200);
  assert.ok(verify(null,Buffer.from(result.body.payload,'base64'),f.publicKey,Buffer.from(result.body.signature,'base64')));
  const payload=JSON.parse(Buffer.from(result.body.payload,'base64'));assert.equal(payload.product,'windi-sach-noi-pro');assert.equal(payload.expiresAt,'2027-10-20T03:00:01.000Z');
  await f.restart();assert.deepEqual((await f.req('/api/orders/'+order.id+'/license',{cookie:a.cookie})).body,result.body);
  assert.equal((await f.req('/api/orders',{cookie:a.cookie})).body.orders[0].status,'paid');
});
test('renewal adds one year to existing term, not current date',async t=>{
  const f=await fixture(t),a=await f.register();
  for(let i=0;i<2;i++){const order=(await f.order(a.cookie)).body;await f.webhook(order);const result=await f.req('/api/orders/'+order.id+'/license',{cookie:a.cookie});const data=JSON.parse(Buffer.from(result.body.payload,'base64'));assert.equal(data.expiresAt,`${2027+i}-10-20T03:00:01.000Z`);}
});
test('late webhook can settle an in-time transfer; out-of-time transfer never issues',async t=>{
  const f=await fixture(t),a=await f.register(),order=(await f.order(a.cookie)).body;
  f.setTime(Date.parse('2026-10-20T03:30:00Z'));
  assert.equal((await f.req('/api/orders/'+order.id,{cookie:a.cookie})).body.status,'expired');
  assert.equal((await f.webhook(order,{transactionDate:'2026-10-20T03:20:00Z'})).body.reason,'late_payment');
  assert.equal((await f.req('/api/orders/'+order.id+'/license',{cookie:a.cookie})).status,409);
  assert.equal((await f.webhook(order,{transactionDate:'2026-10-20T03:01:00Z'})).body.status,'paid');
});
test('authentication, CSRF, recovery and session revocation',async t=>{
  const f=await fixture(t),a=await f.register();
  assert.equal((await f.req('/api/orders',{body:{idempotencyKey:randomUUID()}})).status,401);
  assert.equal((await f.req('/api/orders',{cookie:a.cookie,origin:'https://evil.example',body:{idempotencyKey:randomUUID()}})).status,403);
  assert.equal((await f.req('/api/login',{body:{email:'reader@example.test',password:'wrong-password-12'}})).status,401);
  const reset=await f.req('/api/recover',{body:{email:'reader@example.test',password:'replacement-password',recoveryCode:a.body.recoveryCode}});assert.equal(reset.status,200);
  assert.equal((await f.req('/api/me',{cookie:a.cookie})).status,401);
  assert.equal((await f.req('/api/recover',{body:{email:'reader@example.test',password:'replacement-password',recoveryCode:a.body.recoveryCode}})).status,401);
  assert.equal((await f.req('/api/login',{body:{email:'reader@example.test',password:'replacement-password'}})).status,200);
});
test('sales default closed; catalog does not promise private voice',async t=>{
  const f=await fixture(t,{WSN_SALES_ENABLED:'false'}),a=await f.register();
  assert.equal((await f.order(a.cookie)).status,503);const catalog=(await f.req('/api/catalog')).body;
  assert.equal(catalog.salesEnabled,false);assert.equal(catalog.privateVoiceAvailable,false);assert.deepEqual(catalog.proModels,['turbo']);
});
