#!/usr/bin/env python3
"""Owner-only immutable book queue. No customer token may confirm or run a job."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error
import uuid
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from core import atomic_json,valid_audio

def request(path,data=None,method=None,raw=None,mime='application/json'):
    base=os.environ['SUPABASE_URL'];key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
    if not base.startswith('https://'):raise ValueError('HTTPS Supabase required')
    req=urllib.request.Request(base+path,data=raw if raw is not None else json.dumps(data).encode() if data is not None else None,
        method=method,headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':mime})
    with urllib.request.urlopen(req,timeout=60) as r:body=r.read()
    return json.loads(body) if body else None

def rpc(name,**data):return request('/rest/v1/rpc/wsn_book_'+name,data)

def process(order_id=None,resume=None):
    # Explicit command only. Never called by importing this module or running tests.
    if os.environ.get('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')!='true':raise ValueError('Commercial voice rights have not been confirmed.')
    endpoint=os.environ['WSN_MODAL_BATCH_URL'];proxy_key=os.environ['WSN_MODAL_PROXY_KEY'];proxy_secret=os.environ['WSN_MODAL_PROXY_SECRET']
    if not endpoint.startswith('https://') or not endpoint.split('/')[2].endswith('.modal.run'):raise ValueError('Select an HTTPS Modal endpoint')
    if resume:
        rows=request('/rest/v1/wsn_book_orders?id=eq.'+str(uuid.UUID(resume))+'&select=*')
        o=rows[0] if rows else None
        if not o or o['state']!='processing':raise ValueError('Only an already claimed job can resume')
    else:o=rpc('claim',p_order=str(uuid.UUID(order_id)) if order_id else None)
    if not o:print('Không có đơn Modal đã thanh toán hoặc mẫu thử trong hàng đợi. Đơn HeyGen chờ dispatcher riêng.');return
    if o['payload'].get('revision')!='pro-cloud-modal-v1':raise ValueError('Snapshot này dành cho HeyGen. Không được chạy qua Modal.')
    folder=ROOT/'commerce/private/book-jobs'/o['id'];folder.mkdir(parents=True,exist_ok=True,mode=0o700);folder.chmod(0o700)
    atomic_json(folder/'order.json',o)
    completed={s['id'] for s in o['results']}
    for s in o['payload']['segments']:
        if s['id'] in completed:continue
        path=folder/(s['id']+'.wav');sent=folder/(s['id']+'.sent.json')
        if not valid_audio(path):
            # A crash/timeout may have consumed GPU. Do not silently submit twice.
            if sent.exists():raise ValueError('Uncertain Modal request: '+str(sent)+'. Reconcile it before retrying; no automatic second GPU call.')
            atomic_json(sent,dict(orderId=o['id'],segmentId=s['id'],textHash=hashlib.sha256(s['text'].encode()).hexdigest()))
            from narration_text import plan_f5_prosody
            units=[dict(id=i+1,text=u['text'],pause_after=u.get('pause',.4),author_comma=u.get('author_comma',False)) for i,u in enumerate(plan_f5_prosody(s['text']))]
            body=json.dumps(dict(units=units,voice_id=o['payload']['voice'],steps=22,cfg_strength=2.2,use_ai_director=True,quality_review=True,speed_factor=1.0)).encode()
            req=urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json','Modal-Key':proxy_key,'Modal-Secret':proxy_secret},method='POST')
            from book_cloud import NoRedirect
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=600) as r:result=json.load(r)
            if result.get('status')!='success':raise ValueError('Modal did not complete the requested batch')
            quality=result.get('quality_report')
            if not isinstance(quality,dict) or quality.get('revision')!='cloud-quality-v1' or quality.get('checkedUnits')!=len(units) or quality.get('textChanged') is not False or quality.get('sourceSHA256')!=hashlib.sha256(''.join(u['text'] for u in units).encode()).hexdigest() or not quality.get('audio',{}).get('passed'):
                raise ValueError('Modal quality review incomplete. Do not upload or resubmit this uncertain GPU request.')
            atomic_json(folder/(s['id']+'.review.json'),dict(orderId=o['id'],segmentId=s['id'],sourceText=s['text'],**quality))
            audio=base64.b64decode(result['audio_b64'],validate=True);part=path.with_suffix('.partial')
            part.write_bytes(audio)
            if not valid_audio(part):raise ValueError('Modal returned invalid audio')
            part.replace(path)
        audio=path.read_bytes();sha=hashlib.sha256(audio).hexdigest()
        review_path=folder/(s['id']+'.review.json')
        if not review_path.exists():raise ValueError('Existing audio has no quality report; reconcile it before uploading. No automatic paid retry.')
        review=json.loads(review_path.read_text())
        if review.get('orderId')!=o['id'] or review.get('segmentId')!=s['id'] or review.get('sourceText')!=s['text'] or review.get('revision')!='cloud-quality-v1':raise ValueError('Quality report does not match the paid snapshot')
        object_path=o['id']+'/'+s['id']+'.wav'
        # POST cannot overwrite a different generation. Existing object is verified.
        try:request('/storage/v1/object/wsn-book-audio/'+object_path,method='POST',raw=audio,mime='audio/wav')
        except urllib.error.HTTPError as e:
            if e.code not in (400,409):raise
            req=urllib.request.Request(os.environ['SUPABASE_URL']+'/storage/v1/object/authenticated/wsn-book-audio/'+object_path,headers={'Authorization':'Bearer '+os.environ['SUPABASE_SERVICE_ROLE_KEY']})
            with urllib.request.urlopen(req,timeout=60) as r:
                if hashlib.sha256(r.read()).hexdigest()!=sha:raise ValueError('Stored audio conflict')
        progress=rpc('audio',p_order=o['id'],p_claim=o['claim_token'],p_segment=s['id'],p_sha=sha)
        print(json.dumps(dict(orderId=o['id'],**progress)),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    confirm=sub.add_parser('confirm')
    for name in ('code','transaction','account','paid-at'):confirm.add_argument('--'+name,required=True)
    confirm.add_argument('--amount',type=int,required=True);confirm.add_argument('--confirm-received',action='store_true',required=True)
    run=sub.add_parser('process-next');run.add_argument('--order');run.add_argument('--resume')
    args=p.parse_args()
    if args.command=='list':
        rows=request('/rest/v1/wsn_book_orders?select=id,device_code,kind,state,amount_vnd,character_count,payment_code,paid_at&order=created_at.desc&limit=50');print(json.dumps(rows,ensure_ascii=False,indent=2))
    elif args.command=='confirm':print(json.dumps(rpc('confirm',p_code=args.code,p_transaction=args.transaction,p_account=args.account,p_expected_account=os.environ['VOICE_BANK_ACCOUNT'],p_amount=args.amount,p_paid_at=args.paid_at)))
    else:process(args.order,args.resume)
if __name__=='__main__':main()
