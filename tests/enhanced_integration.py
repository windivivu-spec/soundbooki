"""Real native PDF chapters, scoped inference, persisted music and portable exports."""
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
ROOT=Path(__file__).resolve().parents[1]
MUSIC_TRACK=next(x['id'] for x in json.loads((ROOT/'assets/music/catalog.json').read_text()) if x.get('origin')=='user-library')
HOME=ROOT/'.qa/enhanced-library';HOME.mkdir(parents=True,exist_ok=True)
q=queue.Queue();report={}
p=subprocess.Popen([sys.executable,'-B','backend/worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(ROOT/'.qa/enhanced-worker.log','w'),text=True,env=os.environ|{'WINDI_SACH_HOME':str(HOME),'WINDI_EXTRACTOR':str(ROOT/'.build/windi-extract')})
def reader():
    for line in p.stdout:q.put(json.loads(line))
threading.Thread(target=reader,daemon=True).start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Timeout')
def get(bid):
    send(action='get',bookId=bid)
    return wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book']
def completed(kind,bid):wait(lambda e:e.get('event')=='job' and e['kind']==kind and e['bookId']==bid and not e['running'])
try:
    send(action='import',paths=[str(ROOT/'.qa/fixtures-data/chapters-viet.pdf')])
    b=wait(lambda e:e.get('event')=='book')['book'];bid=b['id'];completed('import',bid);b=get(bid)
    assert [(c['title'],c['startPage'],c['endPage']) for c in b['chapters']]==[('Chương 1',0,1),('Chương 2',2,2)]
    report['pdfOutlineChapters']=b['chapters']
    send(action='generate',bookId=bid,scope={'type':'page','page':2});completed('audio',bid);b=get(bid)
    assert b['readyCount']==1 and b['segments'][1]['audio'] and b['segments'][0]['audio'] is None and b['segments'][2]['audio'] is None
    report['pageOnlyTTS']=True
    first=Path(b['segments'][1]['audio']);mtime=first.stat().st_mtime_ns
    chapter={'type':'chapter','chapterId':b['chapters'][0]['id']}
    send(action='generate',bookId=bid,scope=chapter);completed('audio',bid);b=get(bid)
    assert b['readyCount']==2 and b['segments'][2]['audio'] is None and first.stat().st_mtime_ns==mtime
    report['chapterOnlyTTSAndCache']=True
    send(action='settings',bookId=bid,music={'track':MUSIC_TRACK,'volume':.25},scope={'type':'page','page':2});b=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book']
    assert b['music']=={'track':MUSIC_TRACK,'volume':.25} and first.stat().st_mtime_ns==mtime
    report['musicSavedWithoutRegeneratingVoice']=True
    exports={}
    for ext in ['wav','m4a','zip']:
        path=ROOT/'.qa'/('mixed-page2.'+ext)
        send(action='export',bookId=bid,scope={'type':'page','page':2},path=str(path))
        wait(lambda e:e.get('event')=='exported');completed('export',bid)
        assert path.exists() and path.stat().st_size>100
        exports[ext]={'bytes':path.stat().st_size}
    import numpy as np
    with wave.open(str(ROOT/'.qa/mixed-page2.wav'),'rb') as w:
        mixed=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2');duration=len(mixed)/24000
    with wave.open(str(first),'rb') as w:dry=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
    assert len(mixed)==len(dry) and np.sqrt(np.mean((mixed.astype(float)-dry)**2))>100
    exports['wav']['seconds']=duration;exports['wav']['musicActuallyMixed']=True
    decoded=ROOT/'.qa/m4a-decoded.wav';decoded.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(ROOT/'.qa/mixed-page2.m4a'),str(decoded)],check=True,capture_output=True)
    with wave.open(str(decoded),'rb') as w:
        seconds=w.getnframes()/w.getframerate();assert abs(seconds-duration)<.12
        audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2');assert np.max(np.abs(audio.astype(float)))>100
        exports['m4a']['decodedSeconds']=seconds
    with zipfile.ZipFile(ROOT/'.qa/mixed-page2.zip') as z:
        assert set(z.namelist())=={'audio.m4a','index.html','player.css','player.js','book.json','book.js'}
        portable=json.loads(z.read('book.json'));assert len(portable['segments'])==1 and portable['segments'][0]['title'].startswith('Trang 2')
        folder=ROOT/'.qa/enhanced-web';folder.mkdir(exist_ok=True);z.extractall(folder)
        exports['zip']['verifiedPlayerAndAudio']=True
    report['exports']=exports
    send(action='chapter',bookId=bid,page=2,title='Chương do người dùng đặt')
    b=wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book'];assert any(c['title']=='Chương do người dùng đặt' and c['startPage']==1 for c in b['chapters'])
    report['manualChapter']=True
    saved=json.loads((HOME/bid/'book.json').read_text());assert saved['music']=={'track':MUSIC_TRACK,'volume':.25}
    report['persistedMusic']=True;report['result']='PASS'
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/enhanced-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
