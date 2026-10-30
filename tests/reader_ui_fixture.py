"""Private isolated reader fixture from the already tested PDF copy."""
import copy
import json
from pathlib import Path
import sys
import uuid
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json

folder=ROOT/'.qa/reader-ui'/uuid.uuid4().hex;folder.mkdir(parents=True)
previous=Library(ROOT/'.qa/pdf-layout/integration/library');original=previous.load(next(previous.root.iterdir()).name)
lib=Library(folder/'library');book=lib.create([previous.directory(original['id'])/original['sources'][0]['file']])
for key in ('pages','segments','chapters','chapterModel','layoutProcessing','totalPages'):book[key]=copy.deepcopy(original[key])
chapter=next(c for c in book['chapters'] if c.get('number')==1)
first=next(i for i,s in enumerate(book['segments']) if s.get('chapterId')==chapter['id'])
page=book['segments'][first]['page'];following=next(i for i,s in enumerate(book['segments']) if s['page']==page+1)
book.update(title='Đọc & nghe · PDF thử nghiệm',status='ready',importedSources=1,audiobooks=[],position=dict(segment=first,seconds=0))
book['layoutProcessing']['chapterCount']=20
lib.save(book)
from test_epub import CONTAINER,OPF,NAV,BODY
epub=folder/'fixture.epub'
with zipfile.ZipFile(epub,'w') as z:
    for path,text in {'META-INF/container.xml':CONTAINER,'mimetype':'application/epub+zip','OPS/book.opf':OPF,'OPS/nav.xhtml':NAV,'OPS/body.xhtml':BODY,'OPS/last.xhtml':'<html><body><h1>Lời kết</h1><p>Hẹn gặp lại.</p></body></html>'}.items():z.writestr(path,text)
atomic_json(folder/'fixture.json',dict(library=str(lib.root),bookID=book['id'],first=first,next=following,page=page,epub=str(epub)))
atomic_json(ROOT/'.qa/reader-ui/latest.json',dict(folder=str(folder)))
print(folder)
