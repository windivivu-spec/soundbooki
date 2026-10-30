"""Derived, reflowable local EPUB; source text/audio are never mutated."""
import base64
import hashlib
from html import escape
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import zipfile
from core import atomic_json
from reading import page_data

REVISION='ebook-reader-v3'
ROOT=Path(__file__).resolve().parents[1]
_LOCKS={}
_LOCK_GUARD=threading.Lock()

def selected(book,take_id=None):
    if take_id:
        from audiobooks import find
        return find(book,take_id)['segments']
    return book['segments']

def content_key(book,take_id=None):
    value=[REVISION,book['title'],book.get('language','vi'),[(s['id'],s['page'],s['text']) for s in selected(book,take_id)],
           [(c.get('id'),c.get('title'),c.get('startPage'),c.get('sourceOffset')) for c in book.get('chapters',[])],
           [(p['source'],p['sourcePage']) for p in book['pages']]]
    return hashlib.sha256(json.dumps(value,ensure_ascii=False).encode()).hexdigest()

def raster(package,name):
    from PIL import Image,UnidentifiedImageError
    import io
    try:
        image=Image.open(io.BytesIO(package.read(name)))
        if image.width*image.height>20_000_000:return None
        image.thumbnail((1200,1600));image=image.convert('RGB');out=io.BytesIO();image.save(out,format='JPEG',quality=82);return out.getvalue()
    except (ValueError,OSError,UnidentifiedImageError):return None

def epub_figures(book,folder,destination):
    # Only raster assets directly referenced by the imported spine resource.
    # No original markup, SVG, script, remote URL or arbitrary path enters UI.
    from epub import Package,HTML,resource
    figures=[];used=set();total=0
    for source,item in enumerate(book['sources']):
        if not item['file'].endswith('.epub'):continue
        package=Package(folder/item['file'])
        try:
            for page,p in enumerate(book['pages']):
                if p['source']!=source or not p.get('href'):continue
                name=p['href'].split('#',1)[0]
                tree=HTML(package.read(name)).root
                def walk(node):
                    if node.tag in ('script','style','iframe','object'):return
                    if node.tag=='img' and node.attrs.get('src'):
                        try:
                            path,_=resource(name,node.attrs['src'])
                            if path in used:return
                            data=raster(package,path)
                            if data:used.add(path);yield data
                        except ValueError:return
                    for child in node.children:
                        if not isinstance(child,str):yield from walk(child)
                for data in walk(tree):
                    if total+len(data)>24*1024*1024 or len(figures)>=500:return figures
                    file=f'epub-{len(figures)}.jpg';(destination/file).write_bytes(data);total+=len(data)
                    from PIL import Image
                    import io
                    picture=Image.open(io.BytesIO(data))
                    figures.append(dict(page=page,file=file,y=0,width=picture.width,pixelsHigh=picture.height))
        finally:package.close()
    return figures

def source_figures(book,folder,destination):
    figures=[];helper=ROOT/'.build/windi-ebook-assets'
    if any(s['file'].endswith('.pdf') for s in book['sources']) and helper.is_file():
        try:
            result=subprocess.run([str(helper),str(folder/'book.json'),str(destination)],capture_output=True,timeout=18)
            if result.returncode==0:figures=json.loads((destination/'figures.json').read_text())
        except (OSError,ValueError,subprocess.TimeoutExpired):pass
    try:figures+=epub_figures(book,folder,destination)
    except (OSError,ValueError,KeyError):pass
    return figures

def assemble(book,take_id=None,figures=()):
    cues=[];pages=[]
    for i in range(len(book['pages'])):
        data=page_data(book,i,take_id,include_all=True)
        items=[{k:c[k] for k in ('id','text','segmentId','index','startFraction','endFraction')}|dict(page=i) for c in data['sentences']]
        for fig in [f for f in figures if f['page']==i]:
            before=items[0]['id'] if items else None
            rows=book['pages'][i].get('layout',[]);height=fig.get('height',1)
            starts=[r['startUTF16'] for r in rows if r.get('y',0)/height>=fig.get('y',0)-.008]
            if starts:
                at=min(starts)
                before=next((c['id'] for c in data['sentences'] if c.get('sourceRange') and c['sourceRange']['location']+c['sourceRange']['length']>at),before)
            fig['before']=before
        pages.append(dict(page=i,first=items[0]['id'] if items else None));cues+=items
    from chapters import public_sections
    sections=public_sections(book)
    chapters=[]
    for c in sections:
        ids={book['segments'][i]['id'] for i in c['indices']}
        cue=next((s for s in cues if s['segmentId'] in ids),None)
        if cue:chapters.append(dict(id=c['id'],title=c['title'],cue=cue['id'],page=cue['page']))
    # Saved takes may contain only a selection. Their content stays immutable.
    return dict(title=book['title'],language=book.get('language','vi'),sentences=cues,pages=pages,chapters=chapters,
                figures=list(figures),timing='estimated',revision=REVISION)

def write_epub(data,destination,assets):
    title=escape(data['title']);lang=escape(data['language']);body=[];last_page=None;modified=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for cue in data['sentences']:
        if cue['page']!=last_page:
            last_page=cue['page'];body.append(f'<span epub:type="pagebreak" id="source-{last_page}" title="{last_page+1}"/>')
        for f in data['figures']:
            if f.get('before')==cue['id']:body.append(f'<figure><img src="images/{escape(f["file"])}" alt="Ảnh minh họa · Trang {f["page"]+1}"/></figure>')
        # Keep exact narration text in DOM and EPUB, with only presentation markup.
        body.append(f'<span id="s-{escape(cue["id"])}" data-source-page="{cue["page"]}">{escape(cue["text"])}</span>')
    nav=''.join(f'<li><a href="book.xhtml#s-{escape(c["cue"])}">{escape(c["title"])}</a></li>' for c in data['chapters'])
    if not nav:nav='<li><a href="book.xhtml">'+title+'</a></li>'
    image_manifest=''.join(f'<item id="image-{i}" href="images/{escape(f["file"])}" media-type="image/jpeg"/>' for i,f in enumerate(data['figures']))
    with zipfile.ZipFile(destination,'w') as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml','<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('EPUB/package.opf',f'''<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">urn:sha256:{data['contentKey']}</dc:identifier><dc:title>{title}</dc:title><dc:language>{lang}</dc:language><meta property="dcterms:modified">{modified}</meta></metadata><manifest><item id="book" href="book.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="reader.css" media-type="text/css"/>{image_manifest}</manifest><spine><itemref idref="book"/></spine></package>''')
        z.writestr('EPUB/nav.xhtml',f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}"><head><title>{title}</title></head><body><nav epub:type="toc"><h1>{title}</h1><ol>{nav}</ol></nav></body></html>')
        z.writestr('EPUB/book.xhtml',f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}"><head><title>{title}</title><link rel="stylesheet" href="reader.css"/></head><body>{"".join(body)}</body></html>')
        z.writestr('EPUB/reader.css','body{font-family:serif;line-height:1.7;white-space:pre-wrap}figure{break-inside:avoid;margin:1em 0}img{max-width:100%;max-height:85vh;object-fit:contain}span[epub\\:type=pagebreak]{display:none}@media(prefers-color-scheme:dark){body{background:#171d27;color:#e7e8eb}}')
        for f in data['figures']:z.write(assets/f['file'],'EPUB/images/'+f['file'],compress_type=zipfile.ZIP_DEFLATED)

def _prepare(lib,book,take_id=None,with_images=True,include_images=True):
    if book.get('status')!='ready':raise ValueError('Chờ xử lý sách xong để mở bản ebook.')
    key=content_key(book,take_id);folder=lib.directory(book['id']);root=folder/'reader'
    if folder.is_symlink() or folder.resolve().parent!=lib.root.resolve():raise ValueError('Thư mục sách không hợp lệ.')
    root.mkdir(exist_ok=True)
    if root.is_symlink():raise ValueError('Thư mục đọc sách không hợp lệ.')
    cached=root/key
    if not (cached/'manifest.json').is_file():
        temp=Path(tempfile.mkdtemp(prefix='.preparing-',dir=root))
        try:
            assets=temp/'images';assets.mkdir()
            figures=source_figures(book,folder,assets) if with_images else []
            data=assemble(book,take_id,figures);data['contentKey']=key
            write_epub(data,temp/'book.epub',assets);atomic_json(temp/'manifest.json',data)
            try:temp.rename(cached)
            except OSError:
                if not (cached/'manifest.json').is_file():raise
                shutil.rmtree(temp)
        except BaseException:shutil.rmtree(temp,ignore_errors=True);raise
    if cached.is_symlink():raise ValueError('Bản ebook không hợp lệ.')
    data=json.loads((cached/'manifest.json').read_text())
    result=json.loads(json.dumps(data));total=0
    for f in result['figures'] if include_images else []:
        if not re.fullmatch(r'(p\d+-\d+|epub-\d+)\.jpg',f['file']):continue
        path=cached/'images'/f['file']
        if not path.is_symlink() and path.is_file():
            image=path.read_bytes();total+=len(image)
            if total<=24*1024*1024:f['image']='data:image/jpeg;base64,'+base64.b64encode(image).decode()
    return result,cached/'book.epub'


def prepare(lib,book,take_id=None,with_images=True,include_images=True):
    with _LOCK_GUARD:lock=_LOCKS.setdefault(str(lib.directory(book['id'])),threading.RLock())
    with lock:return _prepare(lib,book,take_id,with_images,include_images)


def image(lib,book_id,key,file):
    if not isinstance(key,str) or not re.fullmatch(r'[a-f0-9]{64}',key) or not isinstance(file,str) or not re.fullmatch(r'(p\d+-\d+|epub-\d+)\.jpg',file):raise ValueError('Ảnh ebook không hợp lệ.')
    folder=lib.directory(book_id);path=folder/'reader'/key/'images'/file
    if folder.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or any(p.is_symlink() for p in [folder/'reader',folder/'reader'/key,path.parent,path]):raise ValueError('Ảnh ebook nằm ngoài sách.')
    if path.stat().st_size>4*1024*1024:raise ValueError('Ảnh minh họa quá lớn.')
    return 'data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()
