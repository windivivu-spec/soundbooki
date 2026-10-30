"""Local reading search, edition-bound annotations and plain-text imports."""
import hashlib
import json
import re
import time
import unicodedata
import uuid
from core import atomic_json

COLORS=('yellow','green','blue','pink')

def edition(book):
    return hashlib.sha256(json.dumps([(s['id'],s['text']) for s in book['segments']],ensure_ascii=False).encode()).hexdigest()

def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold().replace('đ','d')) if unicodedata.category(c)!='Mn')

def search(book,query):
    from ebook_reader import assemble
    needle=folded(str(query).strip())
    if not 1<=len(needle)<=200:return []
    results=[]
    for cue in assemble(book)['sentences']:
        if needle in folded(cue['text']):
            results.append({k:cue[k] for k in ('id','text','page','segmentId')})
            if len(results)>=200:break
    return results

def read_notes(lib,bid):
    path=lib.directory(bid)/'annotations.json'
    try:return json.loads(path.read_text())
    except FileNotFoundError:return []

def annotation(lib,bid,r):
    book=lib.load(bid);items=read_notes(lib,bid)
    if r.get('remove'):
        items=[n for n in items if n['id']!=r['remove']]
    else:
        from ebook_reader import assemble
        if r.get('edition')!=edition(book):raise ValueError('Nội dung đã đổi. Chọn lại đoạn cần ghi chú.')
        note=r.get('note','');color=r.get('color','yellow')
        if not isinstance(note,str) or len(note)>10000 or color not in COLORS:raise ValueError('Ghi chú hoặc màu không hợp lệ.')
        cues={c['id']:c for c in assemble(book)['sentences']};ranges=r.get('ranges') or [r]
        if not isinstance(ranges,list) or len(ranges)>200:raise ValueError('Chọn một đoạn ngắn hơn để ghi chú.')
        validated=[]
        for part in ranges:
            cue=cues.get(part.get('cueId'));quote=part.get('quote','');start=part.get('start',0);end=part.get('end',0)
            if not cue or not isinstance(quote,str) or not quote or len(quote)>10000:raise ValueError('Đoạn chữ không hợp lệ.')
            if type(start)!=int or type(end)!=int or not 0<=start<end:raise ValueError('Vị trí đoạn chữ không hợp lệ.')
            try:actual=cue['text'].encode('utf-16-le')[start*2:end*2].decode('utf-16-le')
            except UnicodeError:raise ValueError('Vị trí đoạn chữ không hợp lệ.') from None
            if actual!=quote:raise ValueError('Vị trí đoạn chữ đã thay đổi.')
            validated.append(dict(cueId=cue['id'],page=cue['page'],quote=quote,start=start,end=end))
        if not validated or sum(len(p['quote']) for p in validated)>20000:raise ValueError('Chọn từ 1 đến 20.000 ký tự để ghi chú.')
        item=dict(validated[0],id=r.get('id') or uuid.uuid4().hex,edition=edition(book),quote=''.join(p['quote'] for p in validated),ranges=validated,note=note,color=color,updatedAt=time.time())
        items=[n for n in items if n['id']!=item['id']]+[item]
    if len(items)>10000:raise ValueError('Sổ tay của cuốn sách đã đầy.')
    atomic_json(lib.directory(bid)/'annotations.json',items)
    return items

def import_text(lib,title,text,language='vi'):
    if not isinstance(text,str) or not text.strip() or len(text)>1_000_000:raise ValueError('Dán từ 1 đến 1.000.000 ký tự.')
    if language not in ('vi','en'):raise ValueError('Ngôn ngữ không hợp lệ.')
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix='paste-',dir=lib.root) as tmp:
        source=Path(tmp)/'Van-ban.txt';source.write_text(text,encoding='utf-8');book=lib.create([source],language)
    book['title']=str(title).strip()[:160] or 'Văn bản của tôi'
    book.update(format='text',unitLabel='mục',totalPages=1,importedSources=1,status='ready')
    lib.add_page(book,0,dict(page=0,text=text,method='text',warning=''))
    from pdf_layout import process_book
    process_book(book,save=lambda:lib.save(book))
    return book
