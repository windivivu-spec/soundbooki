"""Real native extraction + local inference + restart. Run from project root."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave
ROOT=Path(__file__).resolve().parents[1]
HOME=ROOT/'.qa/integration-library'
HOME.mkdir(parents=True,exist_ok=True)
env=os.environ|{'WINDI_SACH_HOME':str(HOME),'WINDI_EXTRACTOR':str(ROOT/'.build/windi-extract')}
q=queue.Queue()

def start():
    p=subprocess.Popen([sys.executable,'-B','backend/worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(ROOT/'.qa/worker.log','a'),text=True,env=env)
    def read():
        for line in p.stdout:q.put(json.loads(line))
    threading.Thread(target=read,daemon=True).start()
    return p
p=start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Không nhận được sự kiện yêu cầu')
def imported(name):
    send(action='import',paths=[str(ROOT/'.qa/fixtures-data'/name)])
    e=wait(lambda e:e.get('event')=='book' and e['book']['title']==Path(name).stem)
    bid=e['book']['id']
    e=wait(lambda e:e.get('event')=='job' and e.get('kind')=='import' and e.get('bookId')==bid and not e['running'])
    return json.loads((HOME/bid/'book.json').read_text())
report={}
try:
    begin=time.monotonic();b=imported('text-viet.pdf');bid=b['id']
    assert len(b['pages'])==3 and all(x['method']=='text' for x in b['pages'])
    assert all('Tiếng Việt có dấu: ă â ê ô ơ ư đ.' in x['text'] for x in b['pages'])
    report['textPDF']={'pages':3,'seconds':time.monotonic()-begin,'verbatimVietnamese':True}
    begin=time.monotonic();image=imported('chu-viet.png')
    assert image['pages'][0]['method']=='ocr' and 'Mỗi ngày' in image['pages'][0]['text']
    report['imageOCR']={'seconds':time.monotonic()-begin,'text':image['pages'][0]['text']}
    begin=time.monotonic();scan=imported('scan-viet.pdf')
    assert len(scan['pages'])==2 and all(x['method']=='ocr' for x in scan['pages'])
    report['scanPDF']={'pages':2,'seconds':time.monotonic()-begin,'text':scan['pages'][0]['text']}
    send(action='import',paths=[str(ROOT/'.qa/fixtures-data/long-scan.pdf')])
    partial=wait(lambda e:e.get('event')=='book' and e['book']['title']=='long-scan' and len(e['book']['pages'])>=1)['book'];longid=partial['id']
    send(action='cancel',kind='import')
    wait(lambda e:e.get('event')=='job' and e.get('bookId')==longid and not e['running'])
    paused=json.loads((HOME/longid/'book.json').read_text());assert paused['status']=='paused'
    assert 1<=len(paused['pages'])<10
    send(action='resume',bookId=longid)
    wait(lambda e:e.get('event')=='job' and e.get('bookId')==longid and not e['running'])
    resumed=json.loads((HOME/longid/'book.json').read_text());assert len(resumed['pages'])==10
    assert [x['sourcePage'] for x in resumed['pages']]==list(range(10))
    report['cancelResumeImport']={'savedBeforeCancel':len(paused['pages']),'resumedPages':10,'noDuplicates':True}
    begin=time.monotonic();send(action='generate',bookId=bid,start=0,all=True)
    first=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid and e['book']['readyCount']>=1)
    firsttime=time.monotonic()-begin
    send(action='cancel',kind='audio')
    wait(lambda e:e.get('event')=='job' and e.get('kind')=='audio' and e.get('bookId')==bid and not e['running'])
    send(action='generate',bookId=bid,start=0,all=True)
    final=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid and e['book']['readyCount']==len(e['book']['segments']))['book']
    wait(lambda e:e.get('event')=='job' and e.get('kind')=='audio' and e.get('bookId')==bid and not e['running'])
    paths=[Path(s['audio']) for s in final['segments']]
    assert len(paths)==3
    metadata=[json.loads(a.with_suffix('.json').read_text()) for a in paths]
    report['tts']={'firstAudioSeconds':firsttime,'segments':3,'durationSeconds':sum(x['duration'] for x in metadata),'computeSeconds':[x['computeSeconds'] for x in metadata]}
    before=paths[0].stat().st_mtime_ns
    send(action='generate',bookId=bid,start=0,all=True)
    wait(lambda e:e.get('event')=='job' and e.get('kind')=='audio' and not e['running'])
    assert paths[0].stat().st_mtime_ns==before
    report['audioResumeAndCache']=True
    send(action='position',bookId=bid,segment=1,seconds=3.25)
    send(action='get',bookId=bid)
    state=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book'];assert state['position']=={'segment':1,'seconds':3.25}
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    p=start();send(action='get',bookId=bid)
    state=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book'];assert state['position']=={'segment':1,'seconds':3.25}
    report['positionRestart']=True
    out=ROOT/'.qa/sach-noi-demo.wav';send(action='export',bookId=bid,path=str(out))
    wait(lambda e:e.get('event')=='exported')
    with wave.open(str(out),'rb') as w:
        assert w.getframerate()==24000 and w.getnframes()>0
        report['export']={'format':'PCM16 mono 24kHz WAV','seconds':w.getnframes()/24000,'bytes':out.stat().st_size}
    wait(lambda e:e.get('event')=='job' and e.get('kind')=='export' and not e['running'])
    send(action='edit',bookId=bid,index=0,text='Sách là người bạn tốt. Tôi đọc sách mỗi ngày.')
    edited=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book'];assert edited['segments'][0]['audio'] is None
    assert edited['segments'][0]['originalText']==b['segments'][0]['originalText']
    report['editInvalidatesAudio']=True
    send(action='settings',bookId=bid,voice='Mỹ Duyên')
    changed=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book'];assert changed['readyCount']==0
    report['voiceInvalidatesAudio']=True
    report['result']='PASS'
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/integration-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
