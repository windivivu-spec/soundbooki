"""Real native PDF → worker JSONL → durable layout/chapter pipeline.

Pass a selected PDF explicitly. Writes only to a fresh .qa library. Export audio
is a fixture signal to verify chapter selection, not an inference quality test.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import wave

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json
from pdf_layout import plain
from chapters import public_sections,edit_chapter
from book_pricing import sample_segments
from scopes import selected_indices

def run(source,expected):
    folder=ROOT/'.qa/pdf-layout'/('worker-'+str(time.time_ns()));folder.mkdir(parents=True)
    lib=Library(folder/'library');events=queue.Queue();counts=Counter();first_progress=None
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    with (folder/'worker.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-B','backend/worker.py'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,
            env=os.environ|dict(WINDI_SACH_HOME=str(lib.root),WINDI_EXTRACTOR=str(ROOT/'.build/windi-extract')))
        def consume():
            for line in process.stdout:events.put(json.loads(line))
        threading.Thread(target=consume,daemon=True).start()
        started=time.monotonic();process.stdin.write(json.dumps(dict(action='import',paths=[str(source)]))+'\n');process.stdin.flush();bid=None
        try:
            deadline=started+180
            while time.monotonic()<deadline:
                event=events.get(timeout=30)
                if event['event']=='error':raise AssertionError(event)
                if event['event']=='processing':
                    counts[event['phase']]+=1
                    if first_progress is None:first_progress=time.monotonic()-started
                if event['event']=='book':bid=event['book']['id']
                if event['event']=='job' and event['kind']=='import' and not event['running']:break
            else:raise TimeoutError('PDF import did not finish')
            elapsed=time.monotonic()-started;book=lib.load(bid)
            assert book['status']=='ready' and not book['error']
            assert all(plain(p['text'])==plain(p.get('narrationText',p['text'])) for p in book['pages'])
            sections=public_sections(book);headings=[c for c in sections if c.get('origin')=='pdf-heading']
            if expected is not None:assert len(headings)==expected,(len(headings),expected)
            assert ''.join(c['originalText'] for c in sections)==''.join(p['text'] for p in book['pages'])
            indices=[i for c in sections for i in selected_indices(book,dict(type='chapter',chapterId=c['id']))]
            assert sorted(indices)==selected_indices(book,dict(type='all')) and len(indices)==len(set(indices))
            sample=''.join(s['text'] for s in sample_segments(book));assert len(sample)<=4000
            original_hash=hashlib.sha256(source.read_bytes()).hexdigest();assert before==original_hash
            # Shared physical page: edit + selection + WAV export stay in chapter.
            target=next((c for c in sections[1:] if c['startPage']==sections[sections.index(c)-1]['endPage']),None)
            if target:
                originals={c['id']:c['text'] for c in sections};text='Nội dung thử phạm vi chương. Giữ nguyên dấu tiếng Việt.'
                edit_chapter(book,target['id'],text,expected=target['text']);lib.save(book)
                assert all(c['text']==originals[c['id']] for c in public_sections(book) if c['id']!=target['id'])
                scope=dict(type='chapter',chapterId=target['id']);chosen=selected_indices(book,scope)
                assert ''.join(book['segments'][i]['text'] for i in chosen)==text
                for i in chosen:
                    with wave.open(str(lib.audio_path(book,book['segments'][i])),'wb') as wav:
                        wav.setparams((1,2,24000,0,'NONE','not compressed'));wav.writeframes(b'\x10\0'*2400)
                dest=folder/'chapter.wav';lib.export(bid,dest,scope)
                with wave.open(str(dest),'rb') as wav:assert wav.getnframes()==len(chosen)*2400
            report=dict(result='PASS',sourceSHA256=before,pages=len(book['pages']),chapterCount=len(headings),sections=len(sections),
                seconds=round(elapsed,2),firstProgressSeconds=round(first_progress,2),progressEvents=dict(counts),
                rawPreserved=True,chaptersPartitionSelection=True,sharedPageEditAndFixtureExport=bool(target),
                layout=book['layoutProcessing'],sample=sample[:50])
            atomic_json(folder/'result.json',report)
            atomic_json(ROOT/'.qa/pdf-layout/latest-integration.json',dict(folder=str(folder),**report))
            print(json.dumps({k:v for k,v in report.items() if k!='layout'},ensure_ascii=False,indent=2))
        finally:
            process.stdin.write('{"action":"shutdown"}\n');process.stdin.flush();process.stdin.close();process.wait(timeout=10)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('--expected-chapters',type=int);args=p.parse_args();run(args.pdf,args.expected_chapters)
