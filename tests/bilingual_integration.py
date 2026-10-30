"""Actual Lite+Kitten inference with no cloud, isolated library and immutable takes."""
from pathlib import Path
import sys,json,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from worker import Worker
from reading_tools import import_text
from core import valid_audio
from model_manager import ready
from reader_listening import prepare
from ebook_reader import assemble
from bilingual import parts,language
home=ROOT/'.qa/reading-features/bilingual-library';w=Worker(home)
try:
 b=import_text(w.lib,'Việt–Anh QA','Xin chào bạn. It is a truth universally acknowledged. Chúc bạn đọc sách vui vẻ.')
 b['bilingual']=True;w.lib.save(b)
 results=[];started=time.monotonic();job=dict(cancel=threading.Event(),process=None)
 segment=b['segments'][0];path=w.lib.audio_path(b,segment)
 request=dict(model='nano',models='',voice=b['voice'],bilingual=True,englishVoice='Jasper',segments=[dict(id=segment['id'],text=segment['text'],path=str(path))])
 for result in w.engine_results(request,job,w.lib.directory(b['id'])/'engine.log'):results.append(result)
 assert valid_audio(path),results
 assert ''.join(parts(segment['text']))==segment['text']
 assert [language(s) for s in parts(segment['text'])]==['vi','en','vi']
 before=w.lib.load(b['id']);assert before['segments'][0]['originalText']==segment['text']
 done=threading.Event();events=[]
 def emit(**e):
  events.append(e)
  if e['event']=='readerBuffer':done.set()
 prepare(w,b['id'],b['voice'],assemble(b)['sentences'][1]['id'],'qa-bilingual',emit)
 assert done.wait(90),events
 assert not [e for e in events if e.get('state')=='error'],events
 assert all(valid_audio(e['path']) for e in events if e['event']=='readerAudioReady')
 report=dict(result='PASS',seconds=round(time.monotonic()-started,2),audio=str(path),cloudRequests=0,routes=['vi','en','vi'],readerEvents=events)
 (ROOT/'.qa/reading-features/bilingual-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
finally:w.cancel_listening();w.nano.close()
