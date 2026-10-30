"""Real chapter preview/edit → scoped local inference → immutable takes → music exports."""
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

ROOT=Path(__file__).resolve().parents[1];HOME=ROOT/'.qa/workspace-library';HOME.mkdir(parents=True,exist_ok=True)
out=ROOT/'.qa/workspace-artifacts';out.mkdir(exist_ok=True)
q=queue.Queue();report={}
fixture=out/'Chapter Studio.epub'
sample='Every book opens a new window on the world. Take your time, listen carefully, and let the story come to life.'
with zipfile.ZipFile(fixture,'w') as z:
    z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
    z.writestr('book.opf','<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Chapter Studio</dc:title></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>')
    z.writestr('one.xhtml',f'<html><body><h1>Opening</h1><p>{sample}</p><p>.................................</p><p>***</p><p>42</p><p>{sample}</p></body></html>')
    z.writestr('two.xhtml','<html><body><h1>A new chapter</h1><p>The second chapter must remain untouched and must not be generated when only the opening is selected.</p></body></html>')
def start():
    p=subprocess.Popen([sys.executable,'-B',str(ROOT/'backend/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(out/'worker.log','a'),text=True,env=os.environ|{'WINDI_SACH_HOME':str(HOME)})
    def read():
        for line in p.stdout:q.put(json.loads(line))
    threading.Thread(target=read,daemon=True).start();return p
p=start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Worker timeout')
def get(bid):
    token=uuid.uuid4().hex;send(action='get',bookId=bid,requestId=token)
    return wait(lambda e:e.get('event')=='book' and e.get('requestId')==token)['book']
def complete(kind,bid):wait(lambda e:e.get('event')=='job' and e['kind']==kind and e['bookId']==bid and not e['running'])
def save(b,c,text):
    token=uuid.uuid4().hex;send(action='editChapter',bookId=b['id'],chapterId=c['id'],text=text,expected=c['text'],token=token)
    wait(lambda e:e.get('event')=='chapterSaved' and e['token']==token);return get(b['id'])
try:
    send(action='import',paths=[str(fixture)],language='en')
    b=wait(lambda e:e.get('event')=='book' and e['book']['title'] in ('Chapter Studio',))['book'];bid=b['id'];complete('import',bid);b=get(bid)
    assert len(b['sections'])==2 and b['model']=='kitten'
    c=b['sections'][0];source=[p['text'] for p in b['pages']];second=b['sections'][1]['text']
    token=uuid.uuid4().hex;send(action='cleanChapter',bookId=bid,chapterId=c['id'],text=c['text'],token=token,options={'decorations':True})
    cleaned=wait(lambda e:e.get('event')=='cleanup' and e['token']==token)
    assert cleaned['count']==2 and '42' in cleaned['text'] and get(bid)['sections'][0]['text']==c['text']
    b=save(b,c,sample);scope={'type':'chapter','chapterId':c['id']}
    started=time.monotonic();send(action='generate',bookId=bid,scope=scope);complete('audio',bid);b=get(bid)
    take=b['audiobooks'][0];take_id=take['id']
    assert take['status']=='ready' and take['voice']=='Jasper' and len(take['segments'])==1
    assert take['segments'][0]['text']==sample and b['sections'][1]['text']==second
    assert all(not b['segments'][i]['audio'] for i in b['sections'][1]['indices'])
    report['chapterQuickGeneration']=dict(seconds=time.monotonic()-started,takeId=take_id,duration=take['duration'])
    send(action='settings',bookId=bid,voice='Bella',music={'track':'demo-91d9e20eb096','volume':.12});b=get(bid)
    b=save(b,b['sections'][0],'A shorter version, with a different voice.');send(action='generate',bookId=bid,scope=scope);complete('audio',bid);b=get(bid)
    assert len(b['audiobooks'])==2 and b['audiobooks'][1]['status']=='ready' and b['audiobooks'][1]['voice']=='Jasper'
    assert b['audiobooks'][1]['segments'][0]['text']==sample and b['pages'][0]['text']==source[0]
    report['immutableTakesAcrossTextAndVoice']=True
    for ext in ('wav','m4a','zip'):
        dest=out/('original-jasper-with-music.'+ext)
        send(action='export',bookId=bid,takeId=take_id,path=str(dest));wait(lambda e:e.get('event')=='exported' and e.get('takeId')==take_id);complete('export',bid)
        assert dest.stat().st_size>100
    with zipfile.ZipFile(out/'original-jasper-with-music.zip') as z:
        data=json.loads(z.read('book.json'));assert data['segments'][0]['text']==sample and data['language']=='en'
    decode=out/'decoded.wav';decode.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(out/'original-jasper-with-music.m4a'),str(decode)],check=True,capture_output=True)
    with wave.open(str(decode),'rb') as w:assert abs(w.getnframes()/w.getframerate()-take['duration'])<.15
    b=get(bid);assert len(next(t for t in b['audiobooks'] if t['id']==take_id)['exports'])==3
    report['archivedWAVM4AZIPWithMusic']=True
    token=uuid.uuid4().hex;before=b['position']
    send(action='voicePreview',model='kitten',voice='Jasper',language='en',token=token)
    demo=wait(lambda e:e.get('event')=='voiceDemo' and e['token']==token)
    assert Path(demo['path']).is_file() and get(bid)['position']==before
    report['cachedVoicePreviewIndependentOfBook']=True
    # Cancel after a completed chunk; keep that chunk and the independent take.
    b=save(b,b['sections'][0],('This is a longer chapter for checking interruption and saved narration. '*45))
    send(action='generate',bookId=bid,scope=scope)
    wait(lambda e:e.get('event')=='progress' and e.get('kind')=='audio' and e.get('bookId')==bid and e.get('done',0)>0)
    send(action='cancel',kind='audio');complete('audio',bid);b=get(bid)
    assert b['audiobooks'][0]['readyCount']>0 and len(b['audiobooks'])==3
    assert [p['text'] for p in b['pages']]==source
    send(action='shutdown');p.stdin.close();p.wait(timeout=10);p=start();b=get(bid)
    assert len(b['audiobooks'])==3 and next(t for t in b['audiobooks'] if t['id']==take_id)['status']=='ready'
    assert [p['text'] for p in b['pages']]==source
    report['cancellationRestartAndOriginalText']=True
    # Leave a short clean chapter for native UI checks without more inference.
    b=save(b,b['sections'][0],sample+'\n\n.................................\n\n'+sample)
    report.update(result='PASS',bookId=bid)
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/workspace-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
