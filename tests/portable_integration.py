"""Exercise a relocated consumer bundle using generated EPUBs in an isolated QA library."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid
import wave
import zipfile

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--app',type=Path,required=True);args=parser.parse_args()
app=args.app.resolve();runtime=app/'Contents/Resources/App'
MUSIC_TRACK=next((x['id'] for x in json.loads((runtime/'assets/music/catalog.json').read_text())),None)
qa=ROOT/'.qa/portable-integration';qa.mkdir(parents=True,exist_ok=True)
home=qa/('run-'+uuid.uuid4().hex)/'library';home.mkdir(parents=True)
clean_home=home.parent/'clean-home';clean_home.mkdir()
env={'HOME':str(clean_home),'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','TMPDIR':str(home.parent),'LANG':'en_US.UTF-8'};env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None);env.update(WINDI_SACH_HOME=str(home),PYTHONNOUSERSITE='1',WINDI_EXTRACTOR=str(runtime/'.build/windi-extract'))
events=queue.Queue();report={'app':str(app),'library':str(home),'fixtureOnly':True,'models':{}}
def launch():
    process=subprocess.Popen([str(runtime/'.runtime/bin/python'),'-B',str(runtime/'backend/worker.py')],cwd=qa,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(qa/'worker.log').open('a'),text=True,env=env)
    def read():
        for line in process.stdout:events.put(json.loads(line))
    threading.Thread(target=read,daemon=True).start();return process
p=launch()
def send(**value):p.stdin.write(json.dumps(value,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(predicate,timeout=180,expect_error=False):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:event=events.get(timeout=1)
        except queue.Empty:continue
        if event.get('event')=='error' and not expect_error:raise AssertionError(event)
        if predicate(event):return event
    raise TimeoutError('Worker operation timed out.')
def get(bid):
    token=uuid.uuid4().hex;send(action='get',bookId=bid,requestId=token)
    return wait(lambda e:e.get('event')=='book' and e.get('requestId')==token)['book']
def complete(kind):return wait(lambda e:e.get('event')=='job' and e.get('kind')==kind and not e['running'])
def epub(language,text):
    path=qa/(language+'.epub')
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('mimetype','application/epub+zip')
        archive.writestr('META-INF/container.xml','<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
        archive.writestr('book.opf',f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>QA {language}</dc:title><dc:language>{language}</dc:language></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>')
        archive.writestr('one.xhtml',f'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>QA</h1><p>{text}</p></body></html>')
    return path
try:
    send(action='init');catalog=wait(lambda e:e.get('event')=='models')
    assert catalog['entitlement']['tier']=='free'
    for language,model,text in [('vi','nano','Xin chào bạn. Mỗi trang sách mở ra một thế giới mới.'),('en','kitten','Every book opens a new world. Take a moment to listen.')]:
        send(action='import',paths=[str(epub(language,text))],language=language)
        imported=wait(lambda e:e.get('event')=='book')['book'];bid=imported['id'];complete('import');b=get(bid)
        assert b['model']==model and text in ''.join(s['text'] for s in b['segments'])
        start=time.monotonic();send(action='generate',bookId=bid,scope={'type':'all'});complete('audio');b=get(bid)
        assert b['readyCount']==len(b['segments']) and b['readyCount']>0
        paths=[s['audio'] for s in b['segments']]
        for path in paths:
            with wave.open(path) as wav:assert wav.getframerate()==24000 and wav.getnframes()>2400
        send(action='settings',bookId=bid,speed=1.25,**({'music':{'track':MUSIC_TRACK,'volume':.12}} if MUSIC_TRACK else {}));b=get(bid);assert [s['audio'] for s in b['segments']]==paths
        for ext in ('wav','m4a','zip'):
            path=home.parent/(model+'.'+ext);send(action='export',bookId=bid,path=str(path),scope={'type':'all'});wait(lambda e:e.get('event')=='exported');complete('export');assert path.stat().st_size>100
        report['models'][model]={'bookId':bid,'segments':len(paths),'seconds':round(time.monotonic()-start,2),'exported':['wav','m4a','web-zip']}
    send(action='shutdown');p.stdin.close();p.wait(timeout=10);p=launch();send(action='init');wait(lambda e:e.get('event')=='models')
    for model,info in report['models'].items():
        b=get(info['bookId']);assert b['readyCount']==info['segments'] and b['speed']==1.25 and (not MUSIC_TRACK or b['music']=={'track':MUSIC_TRACK,'volume':.12})
    report['restartAndSettings']=True;report['passed']=True
    (qa/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
finally:
    if p.poll() is None:
        send(action='shutdown');p.stdin.close()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10)
