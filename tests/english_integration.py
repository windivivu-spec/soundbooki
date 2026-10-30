"""English PDF/OCR → lightweight Kitten → two voices → music/export/restart."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid
import wave
import zipfile
ROOT=Path(__file__).resolve().parents[1];HOME=ROOT/'.qa/english-library';HOME.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'backend'))
from model_manager import manifest
q=queue.Queue();report={};out=ROOT/'output/demo';out.mkdir(parents=True,exist_ok=True)
def start():
    process=subprocess.Popen([sys.executable,'-B',str(ROOT/'backend/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(ROOT/'.qa/english-worker.log','a'),text=True,env=os.environ|{'WINDI_SACH_HOME':str(HOME)})
    def reader():
        for line in process.stdout:q.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start();return process
p=start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Timeout')
def complete(kind,bid):wait(lambda e:e.get('event')=='job' and e['kind']==kind and e['bookId']==bid and not e['running'])
def get(bid):
    request=uuid.uuid4().hex;send(action='get',bookId=bid,requestId=request)
    return wait(lambda e:e.get('event')=='book' and e.get('requestId')==request)['book']
def imported(name):
    send(action='import',paths=[str(ROOT/'.qa/fixtures-data'/name)],language='en')
    b=wait(lambda e:e.get('event')=='book' and e['book']['title']==Path(name).stem)['book'];complete('import',b['id']);return get(b['id'])
try:
    b=imported('english-text.pdf');bid=b['id']
    assert b['language']=='en' and b['model']=='kitten' and b['voice']=='Jasper'
    assert b['pages'][0]['method']=='text' and 'Every book opens a new window on the world.' in b['pages'][0]['text']
    scan=imported('english-scan.png')
    assert scan['pages'][0]['method']=='ocr' and 'Every book opens a new window on the world.' in scan['pages'][0]['text']
    report['englishPDFAndVisionOCR']=True;report['modelBytes']=sum(f['size'] for f in manifest('kitten')['files'])
    for voice in ('Jasper','Bella'):
        send(action='settings',bookId=bid,voice=voice);b=get(bid);assert b['readyCount']==0
        begin=time.monotonic();send(action='generate',bookId=bid,scope={'type':'page','page':1});complete('audio',bid);b=get(bid)
        assert b['readyCount']==len(b['segments'])
        path=Path(b['segments'][0]['audio'])
        with wave.open(str(path),'rb') as wav:
            assert wav.getframerate()==24000 and wav.getnchannels()==1
            duration=wav.getnframes()/24000;assert duration>2
        meta=json.loads(path.with_suffix('.json').read_text());assert meta['model']=='kitten'
        report[voice]=dict(totalSeconds=time.monotonic()-begin,computeSeconds=meta['computeSeconds'],audioSeconds=duration,path=str(path))
        destination=out/('kitten-english-'+voice.lower()+'.m4a')
        send(action='export',bookId=bid,path=str(destination));wait(lambda e:e.get('event')=='exported');complete('export',bid)
    send(action='settings',bookId=bid,voice='Jasper',music={'track':'demo-91d9e20eb096','volume':.12});b=get(bid)
    assert b['segments'][0]['audio']==report['Jasper']['path']
    for ext in ('wav','m4a','zip'):
        path=out/('kitten-english-with-music.'+ext)
        send(action='export',bookId=bid,path=str(path));wait(lambda e:e.get('event')=='exported');complete('export',bid)
        assert path.stat().st_size>100
    with zipfile.ZipFile(out/'kitten-english-with-music.zip') as archive:
        data=json.loads(archive.read('book.json'));assert data['language']=='en' and data['segments'][0]['title'].startswith('Page 1 · Segment')
        assert b'lang="en"' in archive.read('index.html') and b'Listen here' in archive.read('index.html')
    decoded=ROOT/'.qa/english-m4a-decoded.wav';decoded.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(out/'kitten-english-with-music.m4a'),str(decoded)],check=True,capture_output=True)
    with wave.open(str(decoded),'rb') as wav:assert wav.getframerate()==24000 and abs(wav.getnframes()/24000-report['Jasper']['audioSeconds'])<.15
    import numpy as np
    with wave.open(str(out/'kitten-english-with-music.wav'),'rb') as wav:mixed=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)
    with wave.open(report['Jasper']['path'],'rb') as wav:dry=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)
    assert len(mixed)==len(dry) and np.sqrt(np.mean((mixed-dry*.94)**2))>100
    report['musicWAVM4AAndEnglishWebZIP']=True
    send(action='position',bookId=bid,segment=0,seconds=2.25);b=get(bid)
    send(action='shutdown');p.stdin.close();p.wait(timeout=10);p=start();b=get(bid)
    assert b['model']=='kitten' and b['language']=='en' and b['voice']=='Jasper' and b['readyCount']==1 and b['position']['seconds']==2.25
    send(action='settings',bookId=bid,language='vi');b=get(bid)
    assert b['language']=='vi' and b['model']=='nano' and b['readyCount']==0
    send(action='settings',bookId=bid,language='en');b=get(bid)
    assert b['model']=='kitten' and b['readyCount']==1
    assert b['segments'][0]['text']==b['segments'][0]['originalText']
    report['languageModelVoiceCacheAndRestart']=True;report['bookId']=bid;report['result']='PASS'
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/english-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
