"""Real private F5 worker → WAV/export/restart. Project-local QA library only."""
import json,queue,sys,time,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import worker
from core import Library,valid_audio
import model_manager as models
HOME=ROOT/'.qa/f5-library';OUT=ROOT/'.qa/f5-integration'
OUT.mkdir(parents=True,exist_ok=True)
source=OUT/'book-excerpt.txt'
# Verbatim excerpt already used by the previous real-book probe.
text=json.loads((OUT/'request.json').read_text())['segments'][0]['text']
source.write_text(text)
q=queue.Queue();worker.emit=lambda **e:q.put(e)
w=worker.Worker(HOME);b=w.lib.create([source]);w.lib.add_page(b,0,dict(page=0,text=text,method='text',warning=''))
b['title']='Tư Duy Phản Biện · thử giọng F5';b['status']='ready';w.lib.save(b);bid=b['id']
def settings(**kw):w.handle(dict(action='settings',bookId=bid,**kw));return w.lib.load(bid)
def wait(kind):
 deadline=time.monotonic()+360
 while time.monotonic()<deadline:
  try:e=q.get(timeout=1)
  except queue.Empty:continue
  if e.get('event')=='error':raise AssertionError(e)
  if e.get('event')=='job' and e.get('kind')==kind and not e.get('running'):return
 raise TimeoutError(kind)
assert models.ready('f5-private')
b=settings(model='f5-private');assert b['voice']=='voice-002'
start=time.monotonic();w.generate(bid,scope={'type':'page','page':1});wait('audio')
b=w.lib.load(bid);public=w.lib.public(b);assert public['readyCount']==1
path=w.lib.audio_path(b,b['segments'][0]);assert valid_audio(path)
meta=json.loads(path.with_suffix('.json').read_text());assert meta['model']=='f5-private'
with wave.open(str(path),'rb') as f:duration=f.getnframes()/f.getframerate();assert duration>2 and f.getframerate()==24000
assert b['segments'][0]['text']==text and b['segments'][0]['originalText']==text
saved=path.stat().st_mtime_ns
settings(speed=1.25);assert w.lib.audio_path(w.lib.load(bid),b['segments'][0])==path
settings(model='nano');assert w.lib.public(w.lib.load(bid))['readyCount']==0
settings(model='f5-private');assert w.lib.public(w.lib.load(bid))['readyCount']==1
w.generate(bid,scope={'type':'page','page':1});wait('audio');assert saved==path.stat().st_mtime_ns
for ext in ('wav','m4a','zip'):
 out=OUT/('book-first-export.'+ext);w.lib.export(bid,out,scope={'type':'page','page':1});assert out.stat().st_size>100
reopened=Library(HOME).load(bid);assert reopened['model']=='f5-private' and reopened['voice']=='voice-002' and w.lib.public(reopened)['readyCount']==1
report=dict(bookId=bid,qaLibrary=str(HOME),audio=str(path),duration=duration,computeSeconds=meta['computeSeconds'],cacheReused=True,textVerbatim=True,exports=['wav','m4a','zip'],reopen=True,modelBytes=sum(f['size'] for f in models.manifest('f5-private')['files']))
(OUT/'integration-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
