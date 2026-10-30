"""Real Nano/Turbo switch, isolated caches, native-rate music/export and restart."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import wave
import zipfile
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
from model_manager import verified_location
HOME=ROOT/'.qa/turbo-library';HOME.mkdir(parents=True,exist_ok=True)
lib=Library(HOME);source=ROOT/'.qa/quality-source.txt'
text='Mỗi cuốn sách mở ra một cách nhìn mới. Hãy chậm lại một chút, lắng nghe từng câu chữ, rồi tự tìm câu trả lời của riêng mình.'
source.write_text(text);b=lib.create([source]);bid=b['id']
lib.add_page(b,0,dict(page=0,text=text,method='text',warning=''))
lib.add_page(b,0,dict(page=1,text='Phần tiếp theo không nằm trong phạm vi thử.',method='text',warning=''))
b['status']='ready';b['totalPages']=2;lib.save(b)
report={};q=queue.Queue()
def start():
    process=subprocess.Popen([sys.executable,'-B',str(ROOT/'backend/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(ROOT/'.qa/turbo-worker.log','a'),text=True,env=os.environ|{'WINDI_SACH_HOME':str(HOME)})
    def reader():
        for line in process.stdout:q.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start();return process
p=start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=300):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Timeout')
def complete(kind):wait(lambda e:e.get('event')=='job' and e['kind']==kind and e['bookId']==bid and not e['running'])
def get():
    request=uuid.uuid4().hex
    send(action='get',bookId=bid,requestId=request);return wait(lambda e:e.get('event')=='book' and e.get('requestId')==request)['book']
scope=dict(type='page',page=1);out=ROOT/'output/demo';out.mkdir(parents=True,exist_ok=True)
try:
    verified_location('turbo');report['pinnedSHA256Verified']=True
    for model,rate in [('nano',24000),('turbo',48000)]:
        send(action='settings',bookId=bid,model=model);b=get();assert b['readyCount']==0
        begin=time.monotonic();send(action='generate',bookId=bid,scope=scope);complete('audio');b=get()
        assert b['readyCount']==1 and b['segments'][1]['audio'] is None
        path=Path(b['segments'][0]['audio'])
        with wave.open(str(path),'rb') as wav:
            assert wav.getframerate()==rate and wav.getnchannels()==1
            duration=wav.getnframes()/rate;assert duration>2
        report[model]=dict(seconds=time.monotonic()-begin,audioSeconds=duration,rate=rate,voice=b['voice'],path=str(path))
        if model=='turbo':
            assert b['voice']=='Minh Quân Pro'
            send(action='settings',bookId=bid,music=dict(track='demo-91d9e20eb096',volume=.12));b=get()
        destination=out/('vieneu-'+model+'-quality.m4a')
        send(action='export',bookId=bid,path=str(destination),scope=scope);wait(lambda e:e.get('event')=='exported');complete('export')
        decoded=ROOT/'.qa'/('quality-'+model+'-decoded.wav');decoded.unlink(missing_ok=True)
        subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(destination),str(decoded)],check=True,capture_output=True)
        with wave.open(str(decoded),'rb') as wav:
            assert wav.getframerate()==rate and abs(wav.getnframes()/rate-duration)<.15
        report[model]['m4aBytes']=destination.stat().st_size
    # Switching back reuses Nano exactly; changing rate/profile never plays stale audio.
    send(action='settings',bookId=bid,model='nano');b=get()
    assert b['readyCount']==1 and b['segments'][0]['audio']==report['nano']['path']
    send(action='settings',bookId=bid,model='turbo');b=get()
    assert b['segments'][0]['audio']==report['turbo']['path']
    send(action='position',bookId=bid,segment=0,seconds=2.5);b=get()
    send(action='shutdown');p.stdin.close();p.wait(timeout=10);p=start();b=get()
    assert b['model']=='turbo' and b['voice']=='Minh Quân Pro' and b['readyCount']==1 and b['position']['seconds']==2.5
    report['switchBackCacheAndRestart']=True
    # Confirm full-rate WAV includes the selected background music.
    import numpy as np
    path=ROOT/'.qa/turbo-mixed.wav'
    send(action='export',bookId=bid,path=str(path),scope=scope);wait(lambda e:e.get('event')=='exported');complete('export')
    with wave.open(str(path),'rb') as wav:
        assert wav.getframerate()==48000;mixed=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)
    with wave.open(report['turbo']['path'],'rb') as wav:dry=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)
    assert len(mixed)==len(dry) and np.sqrt(np.mean((mixed-dry*.94)**2))>100
    report['musicAt48kHz']=True;report['result']='PASS'
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/turbo-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
