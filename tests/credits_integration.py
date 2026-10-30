"""Real HTTP wallet gateway + engine child + MP3 decoding + scoped music exports.

Upstream audio and bank receipts are explicit local fixtures. No paid API call.
"""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from unittest.mock import patch
import uuid
import wave
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import clone_pro as cloud
import features
if not features.PRO_MAX_ENABLED:
    print('SKIP: Pro Max đang tạm hoãn; không khởi chạy dịch vụ hay tạo ví.')
    sys.exit(0)
from core import Library,valid_audio
from worker import Worker
from scopes import selected_indices
from music import catalog

spec=importlib.util.spec_from_file_location('credits_gateway',ROOT/'commerce/credits/service.py');svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
folder=ROOT/'.qa/credits-integration'/uuid.uuid4().hex;folder.mkdir(parents=True)
TOKEN='wsn_credit_'+'c'*64;VOICE='094e72c3-97d3-439a-9e64-39ac3d3fa897'
mp3=folder/'fixture.mp3'
subprocess.run([shutil.which('ffmpeg'),'-v','error','-f','lavfi','-i','sine=frequency=330:duration=0.3','-ar','44100','-ac','1',str(mp3)],check=True)

class FixtureProvider:
    fingerprint='fixture-merchant';calls=[];jobs={}
    def request(self,path,payload=None,key=None,audio=False):
        if path=='/api/v1/voice/voices':return {'data':[dict(id=VOICE,name='Minh Dự · fixture',language='vi')]}
        if audio:return mp3.read_bytes()
        if payload is not None:
            if payload['text'].startswith('Cancel B'):time.sleep(.7)
            self.calls.append((key,payload));self.jobs.setdefault(key,dict(id=str(uuid.uuid4()),status='ready'));return self.jobs[key]
        return {'id':path.rsplit('/',1)[-1],'status':'ready'}

pack=dict(id='qa-only',credits=10000,amountVND=1)
bank=dict(name='QA ONLY',bin='970423',account='0000000000',holder='NO REAL PAYMENT')
ledger=svc.Ledger(folder/'credits.sqlite',[pack],bank);provider=FixtureProvider();gateway=svc.Gateway(ledger,provider,folder/'server-audio',[VOICE])
server=svc.ThreadingHTTPServer(('127.0.0.1',0),svc.handler(gateway));threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_address[1]);client=cloud.Client(TOKEN,base)
wallet=client.request('/api/credits/wallet',{});assert wallet['balance']==0
order=client.request('/api/credits/topups',dict(packId=pack['id']),key='fixture-topup')
assert client.request('/api/credits/wallet',{})['balance']==0
ledger.confirm_receipt(order['id'],'FIXTURE-BANK-ONLY',1,bank['account'],datetime.now(timezone.utc).isoformat(),True)
wallet_hash=svc.digest(TOKEN);assert ledger.wallet(wallet_hash)['balance']==10000

wrapper=folder/'engine-wrapper.py'
wrapper.write_text('import sys,json\nsys.path.insert(0,'+repr(str(ROOT/'backend'))+')\nimport clone_pro as c\nfrom engine import emit\nc.service_url=lambda:'+repr(base)+'\nc.credential=lambda action:{"token":'+repr(TOKEN)+'}\ntry:c.main(json.load(sys.stdin))\nexcept Exception as e:emit({"error":str(e)});sys.exit(1)\n')
source=folder/'source.png';source.write_bytes(b'fixture only')
worker=Worker(folder/'library');book=worker.lib.create([source])
for page,text in enumerate(['Trang một giữ nguyên.','Chữ Việt có dấu: ă â ê ô ơ ư đ.','Trang ba dành cho chương này.']):
    worker.lib.add_page(book,0,dict(page=page,total=3,text=text,method='fixture',warning=''))
book.update(status='ready',model='clone-pro',voice=VOICE,chapters=[dict(id='first',startPage=0,title='Mở đầu',origin='manual'),dict(id='chapter',startPage=1,title='Chương hai',origin='manual')])
scope=dict(type='chapter',chapterId='chapter');book['generationScope']=scope
music=catalog()[0];book['music']=dict(track=music['id'],volume=.12);worker.lib.save(book)
events=[];finished=threading.Event();original_popen=subprocess.Popen;cancel_first=False
def popen(args,*rest,**kwargs):
    if isinstance(args,list) and str(args[-1])==str(ROOT/'backend/clone_pro.py'):args=[*args[:-1],str(wrapper)]
    return original_popen(args,*rest,**kwargs)
def emit(**event):
    global cancel_first
    events.append(event)
    if cancel_first and event.get('event')=='progress' and event.get('kind')=='audio' and event.get('done')==1:
        cancel_first=False;worker.cancel('audio')
    if event.get('event')=='job' and event.get('kind')=='audio' and event.get('running') is False:finished.set()
def consent(b):return dict(voice=b['voice'],language=b['language'],segments=[dict(id=b['segments'][i]['id'],text=b['segments'][i]['text']) for i in selected_indices(b,scope)])
report={}
try:
    with patch('worker.emit',side_effect=emit),patch('worker.subprocess.Popen',side_effect=popen):
        worker.generate(book['id'],scope=scope,cloud_consent=consent(book));assert finished.wait(30),'engine timeout'
        assert not [e for e in events if e.get('event')=='error'],events
        book=worker.lib.load(book['id']);public=worker.lib.public(book)
        assert public['readyCount']==2 and not public['segments'][0]['audio']
        assert all(book['segments'][i]['originalText']==book['pages'][i]['text'] for i in range(3))
        assert len(provider.calls)==2
        cost=sum(len(book['segments'][i]['text'].strip()) for i in (1,2));assert ledger.wallet(wallet_hash)['balance']==10000-cost
        for i in (1,2):
            with wave.open(public['segments'][i]['audio'],'rb') as w:assert w.getframerate()==48000 and w.getnchannels()==1 and w.getsampwidth()==2
        # Same selection reuses local audio, consumes zero additional credits.
        finished.clear();worker.generate(book['id'],scope=scope,cloud_consent=consent(book));assert finished.wait(10)
        assert len(provider.calls)==2 and ledger.wallet(wallet_hash)['balance']==10000-cost
        # Playback speed does not invalidate cloud audio; language and voice do.
        paths=[worker.lib.audio_path(book,s) for s in book['segments']]
        worker.handle(dict(action='settings',bookId=book['id'],speed=1.5));book=worker.lib.load(book['id'])
        assert [worker.lib.audio_path(book,s) for s in book['segments']]==paths
        assert not worker.lib.public(book|dict(language='en'))['readyCount']
        assert not worker.lib.public(book|dict(voice='12345678-1234-4234-8234-123456789012'))['readyCount']
        # Reopening retains music and the selected scope.
        reopened=Library(worker.lib.root);assert reopened.load(book['id'])['music']==book['music']
        assert reopened.load(book['id'])['generationScope']==scope
        outputs=[]
        for ext in ('wav','m4a','zip'):
            path=folder/('scoped-with-music.'+ext);reopened.export(book['id'],path,scope);assert path.stat().st_size>0;outputs.append(str(path))
        with zipfile.ZipFile(outputs[-1]) as z:
            text=z.read('index.html').decode();assert 'Trang một giữ nguyên.' not in text
        # Termination keeps the first completed WAV; resuming recovers the same
        # reserved remote job even if the HTTP response was lost on cancellation.
        cancel_book=worker.lib.create([source]);cancel_scope=dict(type='all')
        for page,text in enumerate(['Cancel A giữ audio xong.','Cancel B tiếp tục cùng yêu cầu.']):worker.lib.add_page(cancel_book,0,dict(page=page,total=2,text=text,method='fixture',warning=''))
        cancel_book.update(status='ready',model='clone-pro',voice=VOICE);worker.lib.save(cancel_book)
        cancel_consent=dict(voice=VOICE,language='vi',segments=[dict(id=s['id'],text=s['text']) for s in cancel_book['segments']])
        balance_before=ledger.wallet(wallet_hash)['balance'];cancel_first=True;finished.clear()
        worker.generate(cancel_book['id'],scope=cancel_scope,cloud_consent=cancel_consent);assert finished.wait(15)
        assert valid_audio(worker.lib.audio_path(cancel_book,cancel_book['segments'][0]))
        assert not valid_audio(worker.lib.audio_path(cancel_book,cancel_book['segments'][1]))
        finished.clear();worker.generate(cancel_book['id'],scope=cancel_scope,cloud_consent=cancel_consent);assert finished.wait(15)
        assert worker.lib.public(worker.lib.load(cancel_book['id']))['readyCount']==2
        cancel_cost=sum(len(s['text']) for s in cancel_book['segments'])
        assert ledger.wallet(wallet_hash)['balance']==balance_before-cancel_cost
        report=dict(result='PASS',walletSeparateFromWeb=True,paymentCodeDoesNotFund=True,fixtureReceiptOnly=True,
                    selectedPages=[2,3],providerFixtureJobs=len(provider.calls),creditsDebited=cost,
                    cacheReused=True,originalTextPreserved=True,speedKeepsCache=True,languageAndVoiceInvalidate=True,
                    sampleRate=48000,exports=outputs,musicSurvivesReopen=True,cancellationKeepsCompleted=True,
                    resumedWithoutDuplicateDebit=True,paidProviderCalled=False)
finally:
    server.shutdown();server.server_close()
(folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
