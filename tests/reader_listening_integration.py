"""Real Lite inference from an explicitly chosen sentence; isolated QA library."""
from pathlib import Path
import json
import sys
import threading
import time
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from worker import Worker
from reader_listening import prepare
from ebook_reader import assemble
import model_manager as models
folder=ROOT/'.qa/reader-lite'/uuid.uuid4().hex;folder.mkdir(parents=True);source=folder/'fixture.pdf';source.write_bytes(b'fixture text only; original viewer not used')
resources=folder/'resources';resources.mkdir();(resources/'config.json').write_text(json.dumps(dict(profiles=dict(nano=str(models.verified_location('nano'))))))
w=Worker(folder/'library');book=w.lib.create([source]);w.lib.add_page(book,0,dict(page=0,text='Đây là câu đầu tiên. Bạn đang nghe từ câu thứ hai. Câu thứ ba được đọc tiếp.',method='text',warning=''));book.update(status='ready',model='pro-cloud',voice='Production voice unchanged');w.lib.save(book)
cues=assemble(book)['sentences'];voice=next(v['id'] for v in models.voices('nano') if v['default']);events=[];done=threading.Event();started=time.monotonic()
def emit(**e):
 events.append(e)
 if e['event']=='readerBuffer':done.set()
try:
 prepare(w,book['id'],voice,cues[1]['id'],'a'*32,emit);assert done.wait(60),'Timed out'
 ready=[e for e in events if e['event']=='readerAudioReady'];assert [e['text'] for e in ready]==[c['text'] for c in cues[1:]],events
 assert all(e['duration']>0 for e in ready);assert not [e for e in events if e.get('state')=='error'];assert w.lib.load(book['id'])['model']=='pro-cloud'
 result=dict(result='PASS',seconds=round(time.monotonic()-started,2),cloudRequests=0,voice=voice,selectedCue=cues[1]['id'],audio=[dict(path=e['path'],duration=e['duration'],text=e['text']) for e in ready]);(folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
finally:w.cancel_listening();w.nano.close()
