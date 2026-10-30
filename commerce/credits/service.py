"""Separate app credit wallet and Clone Pro gateway. No customer web account.

Run behind HTTPS. Default has no sale packs; setting prices is an explicit step.
Merchant Windi Voice credentials exist only in this server's environment.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import unicodedata
import urllib.error
import urllib.request
import uuid


class CreditError(ValueError):
    def __init__(self, message, code=400): super().__init__(message);self.code=code


def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


class Ledger:
    def __init__(self, path, packs=None, bank=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.packs=packs or [];self.bank=bank or {}
        for p in self.packs:
            if not isinstance(p,dict) or not re.fullmatch('[a-z0-9-]{1,40}',str(p.get('id',''))) or any(type(p.get(k)) is not int or p[k]<=0 for k in ('credits','amountVND')):
                raise CreditError('Cấu hình gói credit không hợp lệ.')
            if p['credits']>1000000000 or p['amountVND']>100000000:raise CreditError('Gói credit vượt giới hạn.')
        if len({p['id'] for p in self.packs})!=len(self.packs):raise CreditError('Trùng mã gói credit.')
        if self.packs and (not re.fullmatch('[0-9]{6}',self.bank.get('bin','')) or not re.fullmatch('[0-9]{6,32}',self.bank.get('account','')) or not self.bank.get('holder')):
            raise CreditError('Cần cấu hình ngân hàng trước khi bán credit.')
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS wallets(id TEXT PRIMARY KEY,balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0));
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,wallet TEXT NOT NULL,key TEXT NOT NULL,hash TEXT NOT NULL,payload TEXT NOT NULL,credits INTEGER NOT NULL,status TEXT NOT NULL,upstream_id TEXT,merchant TEXT NOT NULL,UNIQUE(wallet,key));
                CREATE TABLE IF NOT EXISTS topups(id TEXT PRIMARY KEY,wallet TEXT NOT NULL,key TEXT NOT NULL,pack TEXT NOT NULL,credits INTEGER NOT NULL,amount INTEGER NOT NULL,code TEXT UNIQUE NOT NULL,bank TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,UNIQUE(wallet,key));
                CREATE TABLE IF NOT EXISTS receipts(transaction_id TEXT PRIMARY KEY,topup TEXT UNIQUE NOT NULL,amount INTEGER NOT NULL,paid_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY,wallet TEXT NOT NULL,delta INTEGER NOT NULL,kind TEXT NOT NULL);
            ''')

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE');yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()

    def wallet(self, wallet, create=False):
        with self.db() as db:
            if create:db.execute('INSERT OR IGNORE INTO wallets(id) VALUES(?)',(wallet,))
            row=db.execute('SELECT balance FROM wallets WHERE id=?',(wallet,)).fetchone()
            if row is None:raise CreditError('Mở ví credit trong app trước.',401)
            orders=[self.order(dict(r)) for r in db.execute('SELECT * FROM topups WHERE wallet=? ORDER BY rowid DESC LIMIT 20',(wallet,))]
            return dict(walletId=wallet[:24],balance=row['balance'],packs=self.packs,orders=orders,charactersPerCredit=1,salesReady=bool(self.packs))

    def order(self,row):
        return dict(id=row['id'],packId=row['pack'],credits=row['credits'],amountVND=row['amount'],content=row['code'],bank=json.loads(row['bank']),status=row['status'])

    def topup(self,wallet,pack,key):
        with self.db() as db:
            old=db.execute('SELECT * FROM topups WHERE wallet=? AND key=?',(wallet,key)).fetchone()
            if old:
                if old['pack']!=pack:raise CreditError('Mã mua credit đã dùng cho gói khác.',409)
                return self.order(dict(old))
            p=next((p for p in self.packs if p['id']==pack),None)
            if not p:raise CreditError('Giá gói credit chưa công bố hoặc gói không còn bán.',409)
            if not db.execute('SELECT 1 FROM wallets WHERE id=?',(wallet,)).fetchone():raise CreditError('Chưa có ví credit.',401)
            order=dict(id=uuid.uuid4().hex,wallet=wallet,key=key,pack=pack,credits=p['credits'],amount=p['amountVND'],code='SC'+secrets.token_hex(8).upper(),bank=encoded(self.bank),status='pending',created_at=datetime.now(timezone.utc).isoformat())
            db.execute('INSERT INTO topups VALUES(:id,:wallet,:key,:pack,:credits,:amount,:code,:bank,:status,:created_at)',order)
            return self.order(order)

    def confirm_receipt(self,order_id,transaction_id,amount,account,paid_at,confirmed=False):
        if not confirmed:raise CreditError('Phải đối chiếu tiền vào ngân hàng trước khi cộng credit.')
        if not re.fullmatch('[A-Za-z0-9_-]{1,128}',transaction_id):raise CreditError('Mã giao dịch ngân hàng không hợp lệ.')
        try:
            paid=datetime.fromisoformat(paid_at.replace('Z','+00:00'))
            if paid.tzinfo is None or paid>datetime.now(timezone.utc):raise ValueError()
        except (ValueError,TypeError):raise CreditError('Thời điểm tiền vào không hợp lệ.')
        with self.db() as db:
            row=db.execute('SELECT * FROM topups WHERE id=?',(order_id,)).fetchone()
            if not row:raise CreditError('Không có yêu cầu mua credit này.',404)
            if paid<datetime.fromisoformat(row['created_at']):raise CreditError('Giao dịch có trước yêu cầu mua credit.')
            if type(amount) is not int or row['amount']!=amount or json.loads(row['bank'])['account']!=account:
                raise CreditError('Số tiền hoặc tài khoản nhận không khớp yêu cầu.')
            receipt=db.execute('SELECT * FROM receipts WHERE transaction_id=?',(transaction_id,)).fetchone()
            if receipt:
                if receipt['topup']!=order_id:raise CreditError('Giao dịch ngân hàng đã cấp credit cho đơn khác.',409)
                return self.order(dict(row))
            if row['status']!='pending':raise CreditError('Đơn đã được đối chiếu bằng giao dịch khác.',409)
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)',(transaction_id,order_id,amount,paid_at))
            db.execute('UPDATE wallets SET balance=balance+? WHERE id=?',(row['credits'],row['wallet']))
            db.execute('INSERT INTO entries VALUES(?,?,?,?)',('topup:'+order_id,row['wallet'],row['credits'],'topup'))
            db.execute("UPDATE topups SET status='paid' WHERE id=?",(order_id,))
            value=dict(row);value['status']='paid';return self.order(value)

    def reserve(self,wallet,key,payload,merchant):
        h=digest(encoded(payload));credits=len(payload['text'])
        with self.db() as db:
            old=db.execute('SELECT * FROM jobs WHERE wallet=? AND key=?',(wallet,key)).fetchone()
            if old:
                if old['hash']!=h:raise CreditError('Mã yêu cầu đã dùng cho nội dung khác.',409)
                return dict(old)
            row=db.execute('SELECT balance FROM wallets WHERE id=?',(wallet,)).fetchone()
            if not row or row['balance']<credits:raise CreditError('Không đủ credit trong app.',402)
            job=dict(id=str(uuid.uuid4()),wallet=wallet,key=key,hash=h,payload=encoded(payload),credits=credits,status='pending',upstream_id=None,merchant=merchant)
            db.execute('UPDATE wallets SET balance=balance-? WHERE id=?',(credits,wallet))
            db.execute('INSERT INTO jobs VALUES(:id,:wallet,:key,:hash,:payload,:credits,:status,:upstream_id,:merchant)',job)
            db.execute('INSERT INTO entries VALUES(?,?,?,?)',('reserve:'+job['id'],wallet,-credits,'reserve'))
            return job

    def job(self,wallet,jid):
        with self.db() as db:
            row=db.execute('SELECT * FROM jobs WHERE wallet=? AND id=?',(wallet,jid)).fetchone()
            if not row:raise CreditError('Không có lượt tạo sách này.',404)
            return dict(row)

    def update(self,jid,status,upstream_id=None):
        with self.db() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
            if row['status'] in ('ready','failed'):return
            if status=='failed':
                db.execute('UPDATE wallets SET balance=balance+? WHERE id=?',(row['credits'],row['wallet']))
                db.execute('INSERT INTO entries VALUES(?,?,?,?)',('refund:'+jid,row['wallet'],row['credits'],'refund'))
            db.execute('UPDATE jobs SET status=?,upstream_id=COALESCE(?,upstream_id) WHERE id=?',(status,upstream_id,jid))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


class Upstream:
    def __init__(self,token):
        if not re.fullmatch('windi_voice_[A-Za-z0-9_-]{32,480}',token):raise CreditError('Chưa cấu hình API phía dịch vụ.',503)
        self.token=token;self.fingerprint=digest(token);self.opener=urllib.request.build_opener(NoRedirect)

    def request(self,path,payload=None,key=None,audio=False):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
        from features import require_pro_max
        require_pro_max()
        headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'}
        if payload is not None:headers['Content-Type']='application/json'
        if key:headers['Idempotency-Key']=key
        req=urllib.request.Request('https://windistudio.app'+path,data=encoded(payload).encode() if payload is not None else None,headers=headers)
        try:
            try:r=self.opener.open(req,timeout=125)
            except urllib.error.HTTPError as error:
                if audio and error.code==307:
                    from urllib.parse import urlsplit
                    location=error.headers.get('Location','');u=urlsplit(location);error.close()
                    if u.scheme!='https' or not u.hostname or u.username or u.password:raise CreditError('Địa chỉ audio không hợp lệ.',502)
                    r=self.opener.open(urllib.request.Request(location),timeout=60)
                else:raise
            with r:
                limit=64*1024**2 if audio else 4*1024**2;data=r.read(limit+1)
                if len(data)>limit:raise CreditError('Kết quả API vượt giới hạn.',502)
                return data if audio else json.loads(data)
        except urllib.error.HTTPError as error:
            code=error.code;error.close();raise CreditError('API tạo giọng chưa trả kết quả.',code) from None
        except (OSError,ValueError):raise CreditError('Kết nối API tạo giọng gián đoạn.',503) from None


class Gateway:
    def __init__(self,ledger,upstream,audio_root,voice_ids=()):
        self.ledger=ledger;self.upstream=upstream;self.audio_root=Path(audio_root);self.audio_root.mkdir(parents=True,exist_ok=True)
        self.voice_ids={str(uuid.UUID(v)) for v in voice_ids}
        if ledger.packs and not self.voice_ids:raise CreditError('Cần chọn giọng dùng cho app trước khi bán credit.')
        self.lock=threading.Lock();self.job_locks={}

    def voices(self):
        result=[];cursor=None;seen=set()
        if not self.voice_ids:return {'data':[]}
        for _ in range(50):
            path='/api/v1/voice/voices'+('?cursor='+str(uuid.UUID(cursor)) if cursor else '')
            page=self.upstream.request(path)
            for v in page.get('data',[]):
                if isinstance(v,dict) and v.get('id') in self.voice_ids and v['id'] not in seen:
                    seen.add(v['id']);result.append({k:v[k] for k in ('id','name','language') if k in v})
            if not page.get('has_more'):return {'data':result}
            next_cursor=page.get('next_page')
            if not next_cursor or next_cursor==cursor:break
            cursor=next_cursor
        raise CreditError('Danh sách giọng chưa tải đủ.',503)

    def input(self,value):
        if not isinstance(value.get('text'),str):raise CreditError('Nội dung phải là chữ.')
        text=unicodedata.normalize('NFC',value['text']).strip()
        try:voice=str(uuid.UUID(value.get('voice_id','')))
        except (ValueError,TypeError,AttributeError):raise CreditError('Giọng không hợp lệ.')
        if voice not in self.voice_ids:raise CreditError('Giọng này chưa được mở cho app.',403)
        if not text or len(text)>10000 or value.get('language') not in ('vi','en') or value.get('speed',1)!=1:
            raise CreditError('Nội dung, ngôn ngữ hoặc tốc độ tạo không hợp lệ.')
        return dict(text=text,voice_id=voice,language=value['language'],speed=1)

    def result(self,job):return {k:job[k] for k in ('id','status','credits')}

    def generate(self,wallet,key,payload):
        job=self.ledger.reserve(wallet,key,self.input(payload),self.upstream.fingerprint)
        return self.reconcile(wallet,job['id'])

    def reconcile(self,wallet,jid):
        with self.lock:lock=self.job_locks.setdefault(jid,threading.Lock())
        with lock:
            job=self.ledger.job(wallet,jid)
            if job['status'] in ('ready','failed'):return self.result(job)
            if not job['upstream_id'] and job['merchant']!=self.upstream.fingerprint:
                return self.result(job)  # Never use a new upstream identity for an uncertain POST.
            try:
                path='/api/v1/voice/generations'
                remote=self.upstream.request(path+'/'+job['upstream_id']) if job['upstream_id'] else self.upstream.request(path,json.loads(job['payload']),key='sachnoi:'+jid)
                remote_id=str(uuid.UUID(remote['id']))
                # Save the upstream receipt before attempting the audio download.
                self.ledger.update(jid,'pending',remote_id)
                if remote['status']=='failed':self.ledger.update(jid,'failed')
                elif remote['status']=='ready':
                    target=self.audio_root/(jid+'.mp3');temp=target.with_suffix('.partial')
                    try:
                        audio=self.upstream.request(path+'/'+remote_id+'/audio',audio=True)
                        if not audio:raise CreditError('Audio trống.',502)
                        temp.write_bytes(audio);temp.replace(target);self.ledger.update(jid,'ready')
                    finally:temp.unlink(missing_ok=True)
                else:self.ledger.update(jid,'unknown' if remote['status']=='unknown' else 'pending')
            except CreditError as error:
                # Only pre-generation validation failures are safe to refund.
                # A timeout/502/409 can have produced paid audio: retain and reconcile.
                current=self.ledger.job(wallet,jid)
                if not current['upstream_id'] and error.code in (400,401,402,403,422):self.ledger.update(jid,'failed')
                else:self.ledger.update(jid,'unknown')
            except (OSError,KeyError,ValueError,TypeError):self.ledger.update(jid,'unknown')
            return self.result(self.ledger.job(wallet,jid))


def handler(gateway):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,value,code=200,audio=False):
            data=value if audio else encoded(value).encode()
            try:
                self.send_response(code);self.send_header('Content-Type','audio/mpeg' if audio else 'application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass  # Cancelled client; keep completed job/receipt.
        def dispatch(self,post=False):
            try:
                auth=self.headers.get('Authorization','')
                if not re.fullmatch('Bearer wsn_credit_[a-f0-9]{64}',auth):raise CreditError('Ví credit không hợp lệ.',401)
                wallet=digest(auth[7:]);path=self.path
                body={}
                if post:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=65536:raise CreditError('Nội dung vượt giới hạn.')
                    body=json.loads(self.rfile.read(n))
                    if not isinstance(body,dict):raise CreditError('Nội dung không hợp lệ.')
                if path=='/api/credits/wallet' and post:return self.reply(gateway.ledger.wallet(wallet,create=True))
                gateway.ledger.wallet(wallet)
                if path=='/api/v1/voice/voices' and not post:return self.reply(gateway.voices())
                if post:
                    key=self.headers.get('Idempotency-Key','')
                    if not re.fullmatch('[A-Za-z0-9:_-]{1,200}',key):raise CreditError('Thiếu mã yêu cầu hợp lệ.')
                    if path=='/api/credits/topups':return self.reply(gateway.ledger.topup(wallet,body.get('packId'),key),201)
                    if path=='/api/v1/voice/generations':return self.reply(gateway.generate(wallet,key,body),201)
                match=re.fullmatch('/api/v1/voice/generations/([a-f0-9-]{36})(/audio)?',path)
                if match and not post:
                    jid=str(uuid.UUID(match[1]));job=gateway.ledger.job(wallet,jid)
                    if match[2]:
                        if job['status']!='ready':raise CreditError('Audio chưa sẵn sàng.',409)
                        return self.reply((gateway.audio_root/(jid+'.mp3')).read_bytes(),audio=True)
                    return self.reply(gateway.reconcile(wallet,jid))
                raise CreditError('Không có đường dẫn này.',404)
            except CreditError as error:self.reply({'error':str(error)},error.code if error.code in (400,401,402,403,404,409,422,429,502,503) else 503)
            except (ValueError,TypeError,KeyError):self.reply({'error':'Nội dung không hợp lệ.'},400)
            except Exception:self.reply({'error':'Dịch vụ chưa sẵn sàng.'},503)
        def do_POST(self):self.dispatch(True)
        def do_GET(self):self.dispatch()
    return Handler


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
    from features import require_pro_max
    try:require_pro_max()
    except ValueError as error:sys.exit(str(error))
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['serve','confirm']);parser.add_argument('--db',default='commerce/private/credits.sqlite');parser.add_argument('--port',type=int,default=8789)
    parser.add_argument('--order');parser.add_argument('--transaction');parser.add_argument('--amount',type=int);parser.add_argument('--account');parser.add_argument('--paid-at');parser.add_argument('--confirm-received',action='store_true');args=parser.parse_args()
    ledger=Ledger(args.db,json.loads(os.environ.get('WSN_CREDIT_PACKS','[]')),json.loads(os.environ.get('WSN_CREDIT_BANK','{}')))
    if args.action=='confirm':
        print(encoded(ledger.confirm_receipt(args.order,args.transaction,args.amount,args.account,args.paid_at,args.confirm_received)))
    else:
        gateway=Gateway(ledger,Upstream(os.environ.get('WSN_CLONE_PRO_API_TOKEN','')),Path(args.db).parent/'credit-audio',json.loads(os.environ.get('WSN_CREDIT_VOICE_IDS','[]')))
        print('App credit service: 127.0.0.1:'+str(args.port),flush=True)
        ThreadingHTTPServer(('127.0.0.1',args.port),handler(gateway)).serve_forever()
