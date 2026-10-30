import { DatabaseSync } from 'node:sqlite';
import { createPrivateKey, createHash, sign } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function issueManual({deviceCode,transactionId,receivedAmount,paidAt,confirmed=false,keyFile,ledgerFile,now=Date.now()}) {
  if(!confirmed)throw Error('Cần xác nhận đã kiểm tra tiền vào trong ngân hàng. Mã máy hoặc ảnh chụp của khách không xác nhận tiền vào.');
  const paid=Date.parse(paidAt);
  if(receivedAmount!==189000)throw Error('Chỉ cấp Pro một năm khi nhận đúng 189000 VND.');
  if(typeof deviceCode!=='string'||!/^SN[A-F0-9]{12}$/.test(deviceCode))throw Error('Cần đúng mã SN + 12 ký tự từ giao dịch ngân hàng.');
  if(typeof transactionId!=='string'||!/^[A-Za-z0-9_-]{1,128}$/.test(transactionId))throw Error('Cần ID giao dịch ngân hàng.');
  if(!Number.isFinite(paid)||paid>now+300000||paid<Date.parse('2026-10-20T00:00:00+07:00'))throw Error('Ngày giao dịch không hợp lệ.');
  const key=createPrivateKey(readFileSync(keyFile));if(key.asymmetricKeyType!=='ed25519')throw Error('Cần private key Ed25519.');
  mkdirSync(dirname(resolve(ledgerFile)),{recursive:true,mode:0o700});const db=new DatabaseSync(ledgerFile);
  db.exec('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS device_licenses(transaction_id TEXT PRIMARY KEY,device_code TEXT NOT NULL,expires INTEGER NOT NULL,envelope TEXT NOT NULL);');
  try {
    db.exec('BEGIN IMMEDIATE');
    const old=db.prepare('SELECT * FROM device_licenses WHERE transaction_id=?').get(transactionId);
    if(old){if(old.device_code!==deviceCode)throw Error('ID giao dịch đã được dùng cho máy khác.');const latest=db.prepare('SELECT envelope FROM device_licenses WHERE device_code=? ORDER BY expires DESC LIMIT 1').get(deviceCode);db.exec('COMMIT');return JSON.parse(latest.envelope);}
    const previous=db.prepare('SELECT MAX(expires) AS expires FROM device_licenses WHERE device_code=?').get(deviceCode)?.expires||0;
    const end=new Date(Math.max(previous,paid)),month=end.getUTCMonth();end.setUTCFullYear(end.getUTCFullYear()+1);if(end.getUTCMonth()!==month)end.setUTCDate(0);
    const orderId='manual-'+createHash('sha256').update(transactionId).digest('hex').slice(0,32);
    const payload=Buffer.from(JSON.stringify({schema:2,product:'windi-sach-noi-pro',orderId,deviceCode,issuedAt:new Date(Math.min(paid,now)).toISOString(),expiresAt:end.toISOString()}));
    const envelope={payload:payload.toString('base64'),signature:sign(null,payload,key).toString('base64')};
    db.prepare('INSERT INTO device_licenses VALUES(?,?,?,?)').run(transactionId,deviceCode,end.getTime(),JSON.stringify(envelope));db.exec('COMMIT');return envelope;
  }catch(error){try{db.exec('ROLLBACK');}catch{}throw error;}finally{db.close();}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
  const args=process.argv.slice(2),value=name=>{const at=args.indexOf(name);return at<0?undefined:args[at+1];};
  try {
    const deviceCode=value('--device-code');
    const envelope=issueManual({deviceCode,transactionId:value('--transaction-id'),receivedAmount:Number(value('--received-amount')),paidAt:value('--paid-at'),confirmed:args.includes('--confirm-received'),keyFile:value('--key-file')||'commerce/private/license-private.pem',ledgerFile:value('--ledger')||'commerce/private/manual.sqlite'});
    const output=resolve(value('--output-dir')||'output/licenses'),path=resolve(output,deviceCode+'.windilicense');mkdirSync(output,{recursive:true});
    // This public, signed file is replaced on renewal; the ledger retains every receipt.
    const temp=path+'.tmp';writeFileSync(temp,JSON.stringify(envelope,null,2),{mode:0o600});
    const {renameSync}=await import('node:fs');renameSync(temp,path);
    process.stdout.write(`Đã lưu bản quyền máy: ${path}\nChỉ upload tệp .windilicense vào thư mục licenses/ của hosting tĩnh.\n`);
  }catch(error){process.stderr.write(error.message+'\n');process.exitCode=1;}
}
