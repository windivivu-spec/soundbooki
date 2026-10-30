"""Real local Nano generation + page events + reader metadata + delete/restore.

Uses synthetic Vietnamese fixture text; no network, customer book or cloud TTS.
"""
import hashlib
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
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json,valid_audio
import model_manager as models

folder=ROOT/'.qa/reader-audio'/uuid.uuid4().hex;folder.mkdir(parents=True)
resources=folder/'resources';resources.mkdir();atomic_json(resources/'config.json',dict(profiles=dict(nano=str(models.verified_location('nano')))))
source=folder/'fixture.txt';source.write_text('Sách thử nghiệm riêng cho QA, không phải nội dung khách hàng.')
lib=Library(folder/'library');b=lib.create([source]);lib.add_page(b,0,dict(page=0,text='Mỗi ngày, tôi dành thời gian đọc sách. Tiếng Việt cần được giữ nguyên dấu.',method='fixture',warning=''));b.update(status='ready',audiobooks=[]);lib.save(b);bid=b['id']
events=queue.Queue();log=(folder/'worker.log').open('w')
p=subprocess.Popen([sys.executable,'-B','backend/worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,env=os.environ|dict(WINDI_SACH_HOME=str(lib.root)))
def consume():
    for line in p.stdout:events.put(json.loads(line))
threading.Thread(target=consume,daemon=True).start()
def send(**value):p.stdin.write(json.dumps(value,ensure_ascii=False)+'\n');p.stdin.flush()
progress=[]
def wait(predicate):
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        e=events.get(timeout=60)
        if e['event']=='error':raise AssertionError(e)
        if e['event']=='progress':progress.append(e)
        if predicate(e):return e
    raise TimeoutError('Reader audio integration')
report=dict(fixtureOnly=True,cloudRequests=0)
try:
    start=time.monotonic();send(action='generate',bookId=bid,scope=dict(type='page',page=1))
    wait(lambda e:e['event']=='job' and e['kind']=='audio' and not e['running'])
    saved=lib.load(bid);audio=lib.audio_path(saved,saved['segments'][0]);assert valid_audio(audio)
    with wave.open(str(audio),'rb') as w:duration=w.getnframes()/w.getframerate();assert duration>1
    digest=hashlib.sha256(audio.read_bytes()).hexdigest()
    assert any(e.get('page')==0 and e.get('index')==0 for e in progress)
    send(action='readerPage',bookId=bid,page=0,token='qa-reading')
    page=wait(lambda e:e['event']=='readerPage');assert len(page['sentences'])==2 and page['timing']=='estimated'
    assert all(c['sourceRange'] for c in page['sentences'])
    send(action='readerSettings',bookId=bid,reader=dict(mode='read',variant='text',page=0,fontSize=24,follow=True))
    send(action='deleteBook',bookId=bid);deleted=wait(lambda e:e['event']=='bookDeleted')
    assert not lib.directory(bid).exists() and source.is_file()
    send(action='restoreBook',undoToken=deleted['undoToken']);wait(lambda e:e['event']=='bookRestored')
    restored=lib.load(bid);assert restored['reader']['mode']=='read' and restored['reader']['fontSize']==24
    assert hashlib.sha256(audio.read_bytes()).hexdigest()==digest
    assert lib.public(restored)['audiobooks'][0]['readyCount']==1
    report.update(result='PASS',seconds=round(time.monotonic()-start,2),audioSeconds=round(duration,2),model='nano',voice=saved['voice'],
        generationPageEvents=True,readerSentenceAnchors=True,timing='estimated',restoreSameAudioSHA256=digest,readerSettingsRetained=True)
finally:
    send(action='shutdown');p.stdin.close();p.wait(timeout=15);atomic_json(folder/'result.json',report);print(json.dumps(dict(folder=str(folder),**report),ensure_ascii=False,indent=2))
