import { DatabaseSync } from 'node:sqlite';
import { createHash, randomBytes, randomUUID, scrypt as scryptCallback, timingSafeEqual, createPrivateKey, sign } from 'node:crypto';
import { promisify } from 'node:util';
import { mkdirSync, readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { createPaymentModule, PaymentError } from '../package qr pay/src/index.js';
import { readJson } from '../package qr pay/src/sepay.js';

const scrypt=promisify(scryptCallback);
const digest=value=>createHash('sha256').update(value).digest('hex');
const fail=(message,status=400)=>{throw new PaymentError(message,status);};
const json=(value,status=200,headers={})=>Response.json(value,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers}});
export const PRICE_VND=189000;
export const PRODUCT='windi-sach-noi-pro';

export async function createCommerce({env=process.env,now=Date.now}={}) {
  const origin=new URL(env.WSN_PUBLIC_ORIGIN);
  if(origin.origin!==env.WSN_PUBLIC_ORIGIN||!(origin.protocol==='https:'||origin.protocol==='http:'&&['localhost','127.0.0.1'].includes(origin.hostname)))fail('Configure an HTTPS WSN_PUBLIC_ORIGIN',503);
  const directory=resolve(env.WSN_DATA_DIR||'./data');mkdirSync(directory,{recursive:true,mode:0o700});
  const privateKey=createPrivateKey(readFileSync(env.WSN_SIGNING_KEY_FILE));
  if(privateKey.asymmetricKeyType!=='ed25519')fail('Ed25519 signing key required',503);
  const sales=env.WSN_SALES_ENABLED==='true';
  const payments=await createPaymentModule({now,env:{...env,
    QR_BANK_BIN:env.VOICE_BANK_BIN||'TPB',QR_BANK_ACCOUNT:env.VOICE_BANK_ACCOUNT||'55111685555',QR_BANK_NAME:env.VOICE_BANK_NAME||'BUI QUOC HUNG',
    QR_PROJECT_ID:env.QR_PROJECT_ID||'windi-sach-noi',QR_CODE_PREFIX:env.QR_CODE_PREFIX||'WSN',
    QR_SQLITE_PATH:join(directory,'payments.sqlite')}});
  const db=new DatabaseSync(join(directory,'accounts.sqlite'));
  db.exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL,recovery TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS purchases(order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS licenses(order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL,envelope TEXT NOT NULL);`);
  const limits=new Map();
  function rate(ip,kind,max) {
    const key=kind+':'+ip,old=limits.get(key),item=old&&old.until>now()?old:{count:0,until:now()+900000};
    if(limits.size>10000){for(const [k,v]of limits)if(v.until<=now())limits.delete(k);if(limits.size>10000)fail('Thử lại sau ít phút.',429);}
    item.count++;limits.set(key,item);if(item.count>max)fail('Thử lại sau ít phút.',429);
  }
  function user(request) {
    const cookie=request.headers.get('cookie')||'';
    const token=cookie.match(/(?:^|;\s*)wsn_session=([A-Za-z0-9_-]{43})(?:;|$)/)?.[1];
    const row=token&&db.prepare('SELECT u.id,u.email,u.name FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?').get(digest(token),now());
    if(!row)fail('Vui lòng đăng nhập.',401);return row;
  }
  const cookie=token=>`wsn_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800${origin.protocol==='https:'?'; Secure':''}`;
  function session(account) {
    const token=randomBytes(32).toString('base64url');
    db.prepare('DELETE FROM sessions WHERE expires<=?').run(now());
    db.prepare('INSERT INTO sessions VALUES(?,?,?)').run(digest(token),account.id,now()+604800000);
    return cookie(token);
  }
  function credentials(body) {
    const email=String(body.email||'').trim().toLowerCase(),password=body.password;
    if(email.length>254||!/^\S+@[^\s@]+\.[^\s@]+$/.test(email))fail('Nhập địa chỉ email hợp lệ.');
    if(typeof password!=='string'||password.length<12||Buffer.byteLength(password)>256)fail('Mật khẩu cần từ 12 ký tự, tối đa 256 byte.');
    return {email,password};
  }
  function fulfill(order,account) {
    if(order.status!=='paid'||order.amount!==PRICE_VND||order.metadata.userId!==account.id||order.metadata.product!==PRODUCT||order.metadata.period!=='year')fail('Đơn chưa được xác nhận thanh toán.',409);
    const existing=db.prepare('SELECT envelope FROM licenses WHERE order_id=? AND user_id=?').get(order.id,account.id);
    if(existing)return JSON.parse(existing.envelope);
    db.exec('BEGIN IMMEDIATE');
    try {
      const paid=Date.parse(order.paidAt);
      if(!Number.isFinite(paid))fail('Đơn thiếu ngày thanh toán.',503);
      const previous=db.prepare('SELECT MAX(expires) AS expires FROM licenses WHERE user_id=?').get(account.id)?.expires||0;
      const end=new Date(Math.max(paid,previous)),month=end.getUTCMonth();
      end.setUTCFullYear(end.getUTCFullYear()+1);
      if(end.getUTCMonth()!==month)end.setUTCDate(0); // February 29 -> February 28.
      const value={schema:1,product:PRODUCT,orderId:order.id,email:account.email,issuedAt:new Date(Math.min(paid,now())).toISOString(),expiresAt:end.toISOString()};
      const payload=Buffer.from(JSON.stringify(value));
      const envelope={payload:payload.toString('base64'),signature:sign(null,payload,privateKey).toString('base64')};
      db.prepare('INSERT INTO licenses VALUES(?,?,?,?)').run(order.id,account.id,end.getTime(),JSON.stringify(envelope));
      db.exec('COMMIT');return envelope;
    }catch(error){db.exec('ROLLBACK');throw error;}
  }
  async function handle(request,{ip='local'}={}) {
    try {
      const path=new URL(request.url).pathname;
      if(path==='/api/payments/webhook'&&request.method==='POST')return await payments.handle(request);
      if(request.method==='POST'&&(request.headers.get('origin')!==origin.origin||request.headers.get('content-type')?.split(';')[0]!=='application/json'))fail('Yêu cầu không hợp lệ.',403);
      if(path==='/api/catalog'&&request.method==='GET')return json({product:PRODUCT,priceVND:PRICE_VND,period:'year',salesEnabled:sales,freeModels:['nano','kitten'],proModels:['turbo'],privateVoiceAvailable:false});
      if(path==='/api/register'&&request.method==='POST') {
        rate(ip,'auth',20);const body=await readJson(request),{email,password}=credentials(body);
        const name=String(body.name||'').trim();if(!name||name.length>120)fail('Nhập tên của bạn (tối đa 120 ký tự).');
        const salt=randomBytes(16).toString('hex'),hash=await scrypt(password,salt,64),id=randomUUID(),recovery=randomBytes(32).toString('base64url');
        try{db.prepare('INSERT INTO users VALUES(?,?,?,?,?,?)').run(id,email,name,salt,hash.toString('hex'),digest(recovery));}catch(error){if(error.code?.includes('CONSTRAINT')||error.message.includes('UNIQUE'))fail('Không tạo được tài khoản. Hãy đăng nhập hoặc khôi phục tài khoản.',409);throw error;}
        return json({user:{id,email,name},recoveryCode:recovery},201,{'Set-Cookie':session({id})});
      }
      if(path==='/api/login'&&request.method==='POST') {
        rate(ip,'auth',20);const {email,password}=credentials(await readJson(request));
        const account=db.prepare('SELECT * FROM users WHERE email=?').get(email);
        const hash=await scrypt(password,account?.salt||'invalid-account-salt',64);
        if(!account||!timingSafeEqual(hash,Buffer.from(account.password,'hex')))fail('Email hoặc mật khẩu không đúng.',401);
        return json({user:{id:account.id,email:account.email,name:account.name}},200,{'Set-Cookie':session(account)});
      }
      if(path==='/api/recover'&&request.method==='POST') {
        rate(ip,'auth',20);const body=await readJson(request),{email,password}=credentials(body);
        const account=db.prepare('SELECT * FROM users WHERE email=?').get(email);
        const code=String(body.recoveryCode||'');
        if(!account||!timingSafeEqual(Buffer.from(account.recovery,'hex'),Buffer.from(digest(code),'hex')))fail('Thông tin khôi phục không đúng.',401);
        const salt=randomBytes(16).toString('hex'),hash=await scrypt(password,salt,64),recovery=randomBytes(32).toString('base64url');
        db.exec('BEGIN IMMEDIATE');try{const updated=db.prepare('UPDATE users SET salt=?,password=?,recovery=? WHERE id=? AND recovery=?').run(salt,hash.toString('hex'),digest(recovery),account.id,account.recovery);if(updated.changes!==1)fail('Mã khôi phục đã được dùng. Hãy đăng nhập hoặc dùng mã mới.',401);db.prepare('DELETE FROM sessions WHERE user_id=?').run(account.id);db.exec('COMMIT');}catch(error){db.exec('ROLLBACK');throw error;}
        return json({user:{id:account.id,email:account.email,name:account.name},recoveryCode:recovery},200,{'Set-Cookie':session(account)});
      }
      if(path==='/api/me'&&request.method==='GET')return json({user:user(request)});
      if(path==='/api/logout'&&request.method==='POST') {
        const token=(request.headers.get('cookie')||'').match(/wsn_session=([A-Za-z0-9_-]{43})/)?.[1];
        if(token)db.prepare('DELETE FROM sessions WHERE token=?').run(digest(token));
        return json({ok:true},200,{'Set-Cookie':`wsn_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0${origin.protocol==='https:'?'; Secure':''}`});
      }
      if(path==='/api/orders'&&request.method==='POST') {
        const account=user(request);rate(ip,'order',30);
        if(!sales)fail('Bản Pro chưa mở bán.',503);
        const body=await readJson(request);
        if(typeof body.idempotencyKey!=='string'||!/^[a-f0-9-]{36}$/.test(body.idempotencyKey))fail('Mã yêu cầu mua không hợp lệ.');
        const order=await payments.createOrder({amount:PRICE_VND,idempotencyKey:account.id+':'+body.idempotencyKey,metadata:{userId:account.id,product:PRODUCT,period:'year'}});
        db.prepare('INSERT OR IGNORE INTO purchases VALUES(?,?,?)').run(order.id,account.id,now());
        return json(order,201);
      }
      if(path==='/api/orders'&&request.method==='GET') {
        const account=user(request);const rows=db.prepare('SELECT order_id FROM purchases WHERE user_id=? ORDER BY created DESC LIMIT 100').all(account.id);
        const orders=[];for(const row of rows){const order=await payments.getOrder(row.order_id);if(order){if(order.status==='paid')fulfill(order,account);orders.push({id:order.id,amount:order.amount,status:order.status,createdAt:order.createdAt,expiresAt:order.expiresAt,licenseExpiresAt:db.prepare('SELECT expires FROM licenses WHERE order_id=?').get(order.id)?.expires||null});}}
        return json({orders});
      }
      const match=path.match(/^\/api\/orders\/([a-f0-9-]{36})(\/license)?$/);
      if(match&&request.method==='GET') {
        const account=user(request),order=await payments.getOrder(match[1]);
        if(!order||order.metadata.userId!==account.id)fail('Không tìm thấy đơn.',404);
        if(match[2])return json(fulfill(order,account),200,{'Content-Disposition':`attachment; filename="Windi-Pro-${order.id}.windilicense"`});
        if(order.status==='paid')fulfill(order,account);
        return json({id:order.id,amount:order.amount,code:order.code,status:order.status,expiresAt:order.expiresAt,bank:order.bank,qrUrl:order.qrUrl});
      }
      return json({error:'Không tìm thấy.'},404);
    }catch(error){return json({error:error instanceof PaymentError?error.message:'Dịch vụ tạm thời gián đoạn. Vui lòng thử lại.'},error instanceof PaymentError?error.status:503);}
  }
  return {handle,close:async()=>{db.close();await payments.close();}};
}
