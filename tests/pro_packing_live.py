"""Explicit single synthetic QA trial via the shared dispatcher, never direct TTS.

Run manually, never by unittest discovery. Reuses its saved credential/order;
does not touch the owner's library, Keychain, device quota or payment ledger.
"""
from pathlib import Path
import hashlib
import json
import secrets
import sys
import time
import urllib.request
import wave
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json
from book_pricing import VOICES
import book_cloud as cloud

folder=ROOT/'.qa/pro-batching/live';folder.mkdir(parents=True,exist_ok=True)
private=folder/'credential.private.json'
if not private.exists():
    atomic_json(private,dict(token='wsn_book_'+secrets.token_hex(32),device='SN'+secrets.token_hex(6).upper(),request=secrets.token_hex(16)))
    private.chmod(0o600)
credentials=json.loads(private.read_text())
class QAClient(cloud.Client):
    def __init__(self):
        self.base=cloud.endpoint();self.token=credentials['token'];self.device=credentials['device']
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),cloud.NoRedirect())

lib=Library(folder/'library');saved=folder/'book-id.json'
if saved.exists():bid=json.loads(saved.read_text())['id']
else:
    sentences=[
        'Đây là bản đọc thử kỹ thuật của Soundbooki, sử dụng nội dung tự viết để kiểm tra một yêu cầu tạo giọng nói. ',
        'Buổi sáng, tôi mở cửa sổ và nhìn những hàng cây đón nắng; tiếng chim vang lên giữa khu vườn yên tĩnh. ',
        'Chúng ta đọc chậm rãi, giữ nguyên dấu tiếng Việt, các đoạn văn và những khoảng nghỉ tự nhiên. ',
        'Mỗi trang sách mang đến một điều mới, để người nghe có thể theo dõi câu chuyện liền mạch từ đầu đến cuối. ',
        'Ở cuối câu, giọng đọc cần dừng vừa đủ trước khi chuyển sang ý tiếp theo, tránh ngắt giữa những từ đang đọc. ',
    ]
    text=('\n\n'.join(sentences)*20)[:4976]+'.'
    assert len(text)==4977
    source=folder/'fixture.txt';source.write_text(text)
    b=lib.create([source]);lib.add_page(b,0,dict(page=0,text=text,method='QA',warning=''))
    b.update(status='ready',model='pro-cloud',voice=VOICES[0]['id'],title='QA · Một request 4977 ký tự');lib.save(b)
    bid=b['id'];atomic_json(saved,dict(id=bid))

with patch.object(cloud,'Client',QAClient):
    b=lib.load(bid)
    existing=next((o for o in b.get('cloudOrders',[]) if o['requestKey']==credentials['request']),None)
    if existing and existing.get('order'):
        result=cloud.sync_order(lib,bid,existing['order']['id'])
    else:result=cloud.create_order(lib,bid,'trial',credentials['request'],True)
    order_id=result['order']['id'];started=time.monotonic()
    for attempt in range(31):
        state=result['order']['state']
        print(json.dumps(dict(state=state,requests=result['order'].get('total'),done=result['order'].get('done'),seconds=round(time.monotonic()-started))),flush=True)
        if result.get('localReady') or state in ('failed','expired'):break
        if attempt==30:break
        time.sleep(10)
        result=cloud.sync_order(lib,bid,order_id)
    b=lib.load(bid);entry=next(o for o in b['cloudOrders'] if o['order']['id']==order_id)
    report=dict(passed=result.get('localReady') is True,syntheticFixtureOnly=True,ownerQuotaUsed=0,ownerLibraryModified=False,
                characters=sum(len(s['text']) for s in entry['snapshot']['segments']),requests=len(entry['snapshot']['segments']),state=result['order']['state'],sharedDispatcher=True)
    if report['passed']:
        take=next(t for t in b['audiobooks'] if t.get('cloudOrderId')==order_id)
        destination=folder/'trial-export.wav';lib.export(bid,destination,take_id=take['id'])
        with wave.open(str(destination),'rb') as wav:
            report.update(audioSeconds=round(wav.getnframes()/wav.getframerate(),3),sampleRate=wav.getframerate(),exported=True,localTakeReady=take['status']=='ready')
        report['sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
    atomic_json(folder/'report.json',report);print(json.dumps(report,indent=2))
    if not report['passed']:sys.exit(1)
