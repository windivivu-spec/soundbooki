"""User-selected EPUB demo → chapter-only VieNeu → music/M4A → restart.

Run explicitly; the copyrighted source remains local and is never bundled.
"""
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
sys.path.insert(0,str(ROOT/'backend'))
from epub import extract
from core import Library
from scopes import selected_indices
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/Users/win/Documents/Tư Duy Phản Biện.epub')
HOME=ROOT/'.qa/epub-library';HOME.mkdir(parents=True,exist_ok=True)
q=queue.Queue();report={}
p=subprocess.Popen([sys.executable,'-B',str(ROOT/'backend/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(ROOT/'.qa/epub-worker.log','w'),text=True,env=os.environ|{'WINDI_SACH_HOME':str(HOME)})
def reader():
    for line in p.stdout:q.put(json.loads(line))
threading.Thread(target=reader,daemon=True).start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn,seconds=300):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:e=q.get(timeout=1)
        except queue.Empty:continue
        if e.get('event')=='error':raise AssertionError(e)
        if fn(e):return e
    raise TimeoutError('Timeout')
def complete(kind,bid):wait(lambda e:e.get('event')=='job' and e['kind']==kind and e['bookId']==bid and not e['running'])
def get(bid):
    send(action='get',bookId=bid)
    return wait(lambda e:e.get('event')=='book' and e['book']['id']==bid)['book']
try:
    begin=time.monotonic();send(action='import',paths=[str(SOURCE)])
    b=wait(lambda e:e.get('event')=='book')['book'];bid=b['id'];complete('import',bid);b=get(bid)
    assert b['status']=='ready' and b['format']=='epub' and b['unitLabel']=='mục'
    assert b['title']=='Tư Duy Phản Biện' and len(b['chapters'])==10
    assert b['chapters'][0]['title']=='GIỚI THIỆU' and b['chapters'][-2]['title']=='LỜI KẾT'
    assert all(page['method']=='epub' for page in b['pages'])
    for i,page in enumerate(b['pages']):
        assert ''.join(s['text'] for s in b['segments'] if s['page']==i)==page['text']
    report['import']={'seconds':time.monotonic()-begin,'title':b['title'],'sections':len(b['pages']),'segments':len(b['segments']),'chapterTitles':[c['title'] for c in b['chapters']],'noOCR':True,'textPreserved':True}
    # Verify recovery from an on-disk checkpoint, with no duplicate chapters/text.
    lib=Library(HOME);partial=lib.create([SOURCE]);units=extract(SOURCE)
    partial.update(format='epub',unitLabel='mục',title=units[0]['bookTitle'],chapters=units[0]['chapters'],totalPages=len(units),status='paused')
    for page in units[:3]:lib.add_page(partial,0,page)
    send(action='resume',bookId=partial['id']);complete('import',partial['id'])
    resumed=get(partial['id']);assert [p['text'] for p in resumed['pages']]==[p['text'] for p in b['pages']]
    assert len(resumed['chapters'])==10
    report['resumeCheckpoint']={'savedSections':3,'resumedSections':10,'noDuplicates':True}
    chapter={'type':'chapter','chapterId':b['chapters'][0]['id']}
    indices=selected_indices(b,chapter);begin=time.monotonic()
    send(action='generate',bookId=bid,scope=chapter);complete('audio',bid);b=get(bid)
    assert b['readyCount']==len(indices) and all(s['audio'] is None for s in b['segments'] if s['page']>0)
    assert b['voice']=='Minh Quân'
    report['vieneuIntroOnly']={'seconds':time.monotonic()-begin,'readySegments':b['readyCount'],'otherChaptersNotGenerated':True,'voice':b['voice']}
    settings={'track':'demo-91d9e20eb096','volume':.12}
    send(action='settings',bookId=bid,music=settings,scope=chapter);b=get(bid)
    exports={}
    for ext in ('m4a','zip'):
        path=ROOT/'.qa'/('epub-gioi-thieu.'+ext)
        send(action='export',bookId=bid,path=str(path),scope=chapter)
        wait(lambda e:e.get('event')=='exported');complete('export',bid)
        exports[ext]={'bytes':path.stat().st_size}
    decoded=ROOT/'.qa/epub-decoded.wav';decoded.unlink(missing_ok=True)
    subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(ROOT/'.qa/epub-gioi-thieu.m4a'),str(decoded)],check=True,capture_output=True)
    with wave.open(str(decoded),'rb') as wav:
        seconds=wav.getnframes()/wav.getframerate();assert seconds>10
        exports['m4a']['decodedSeconds']=seconds
    with zipfile.ZipFile(ROOT/'.qa/epub-gioi-thieu.zip') as z:
        content=json.loads(z.read('book.json'))
        assert len(content['segments'])==len(indices) and all(s['title'].startswith('Mục 1') for s in content['segments'])
    persisted=Library(HOME).public(Library(HOME).load(bid))
    assert persisted['music']==settings and persisted['generationScope']==chapter and persisted['readyCount']==len(indices)
    report['exports']=exports;report['persistedSettingsAndAudio']=True;report['bookId']=bid;report['result']='PASS'
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=10)
    (ROOT/'.qa/epub-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
