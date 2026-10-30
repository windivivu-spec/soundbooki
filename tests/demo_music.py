"""Mix both user-provided demo tracks with the same already-tested narration."""
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library,valid_audio
from music import catalog
ROOT=Path(__file__).resolve().parents[1]
lib=Library(ROOT/'.qa/enhanced-library')
b=None
for item in lib.summaries():
    candidate=lib.load(item['id'])
    if len(candidate['segments'])>=2 and all(valid_audio(lib.audio_path(candidate,s)) for s in candidate['segments'][:2]):b=candidate;break
if b is None:raise AssertionError('Cần chạy enhanced_integration.py trước.')
out=ROOT/'output/demo';out.mkdir(parents=True,exist_ok=True)
demos=[m for m in catalog() if m.get('origin')=='user-demo'];assert len(demos)==2
report=[]
for n,track in enumerate(demos,1):
    b['music']={'track':track['id'],'volume':.12};lib.save(b)
    path=out/f'warm-reflections-ban-{n}.m4a'
    lib.export(b['id'],path,{'type':'range','fromPage':1,'toPage':2})
    info=subprocess.check_output(['/usr/bin/afinfo',str(path)],text=True)
    assert 'aac' in info and path.stat().st_size>1000
    report.append(dict(track=track['title'],musicDuration=track['duration'],sourceSHA256=track['sourceSHA256'],path=str(path),bytes=path.stat().st_size,volume=.12))
b['music']={'track':demos[0]['id'],'volume':.12};lib.save(b)
web=ROOT/'.qa/demo-web.zip';lib.export(b['id'],web,{'type':'range','fromPage':1,'toPage':2})
import zipfile
with zipfile.ZipFile(web) as z:
    assert z.testzip() is None
    dest=ROOT/'.qa/enhanced-web';dest.mkdir(exist_ok=True);z.extractall(dest)
(ROOT/'.qa/music-demo-results.json').write_text(json.dumps({'result':'PASS','demos':report},ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
