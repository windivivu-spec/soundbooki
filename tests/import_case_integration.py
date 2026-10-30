"""Real native PDF/EPUB import → automatic case cleanup → immutable source.

Uses isolated generated fixtures. No TTS or cloud requests.
"""
from pathlib import Path
import hashlib,json,os,queue,subprocess,sys,threading,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json
from chapters import public_sections
from book_pricing import VOICES,snapshot
folder=ROOT/'.qa/import-case';folder.mkdir(parents=True,exist_ok=True)
epub=folder/'uppercase.epub'
with zipfile.ZipFile(epub,'w') as z:
    z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
    z.writestr('book.opf','<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Case QA</dc:title><dc:language>vi</dc:language></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>')
    z.writestr('one.xhtml','<html><body><h1>CHƯƠNG IV: AI VÀ TƯ DUY</h1><p>Tên Nguyễn Văn An và TP.HCM giữ nguyên.</p><p>..............</p></body></html>')
report=[]
for source in (epub,folder/'uppercase.pdf'):
    original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    lib=Library(folder/(source.suffix[1:]+'-library'));events=queue.Queue()
    log=(folder/(source.suffix[1:]+'-worker.log')).open('w')
    worker=subprocess.Popen([sys.executable,'-B','backend/worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,env=os.environ|dict(WINDI_SACH_HOME=str(lib.root)))
    def consume():
        for line in worker.stdout:events.put(json.loads(line))
    threading.Thread(target=consume,daemon=True).start()
    def send(value):worker.stdin.write(json.dumps(value,ensure_ascii=False)+'\n');worker.stdin.flush()
    try:
        send(dict(action='import',paths=[str(source)]));bid=None;deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            e=events.get(timeout=30)
            if e['event']=='error':raise AssertionError(e.get('message'))
            if e['event']=='book':bid=e['book']['id']
            if e['event']=='job' and e['kind']=='import' and not e['running']:break
        b=lib.load(bid);assert b['status']=='ready'
        text=''.join(s['text'] for s in b['segments']);raw=''.join(p['text'] for p in b['pages'])
        assert 'Chương 4: AI và tư duy' in text,text
        assert 'Tên Nguyễn Văn An và TP.HCM giữ nguyên.' in text
        assert 'CHƯƠNG IV: AI VÀ TƯ DUY' in raw
        assert ''.join(s['originalText'] for s in b['segments'])==raw
        assert '..............' not in text
        b.update(voice=VOICES[0]['id'],model='pro-cloud')
        assert ''.join(s['text'] for s in snapshot(b)['segments'])==text
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original_hash
        report.append(dict(format=source.suffix,passed=True,rawPreserved=True,normalizedBeforeProSnapshot=True,automaticCleanup=True,cloudRequests=0))
    finally:
        send(dict(action='shutdown'));worker.stdin.close();worker.wait(timeout=10);log.close()
atomic_json(folder/'integration.json',report);print(json.dumps(report,indent=2))
