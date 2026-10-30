"""Chapter editing with page provenance, untouched source and immutable audio cache."""
from collections import defaultdict
from difflib import SequenceMatcher
import uuid
from scopes import chapters
from cleanup import clean_text, repeated_headers, narratable

LIMIT=500_000

def sections(book):
    items=chapters(book)
    if items:return items
    # Without a source TOC, use a single explicitly labelled document section.
    # This does not infer invented semantic chapter boundaries.
    return [dict(id='document',title='Nội dung sách',startPage=0,endPage=max(0,len(book['pages'])-1),origin='document')]

def section(book,chapter_id):
    found=next((c for c in sections(book) if c['id']==chapter_id),None)
    if not found:raise ValueError('Chương không còn tồn tại. Mở lại sách để tiếp tục.')
    if book['status']!='ready':raise ValueError('Hãy trích chữ xong trước khi sửa nội dung chương.')
    return found

def page_text(book,page,original=False):
    if original:return book['pages'][page]['text']
    if 'narrationText' in book['pages'][page]:return book['pages'][page]['narrationText']
    return ''.join(s['text'] for s in book['segments'] if s['page']==page)

def text_and_spans(book,c,original=False):
    if book.get('chapterModel')=='segments-v1':
        if original:return c.get('originalText',''),[]
        text='';spans=[]
        for s in book['segments']:
            if s.get('chapterId')!=c['id']:continue
            start=len(text);text+=s['text']
            if spans and spans[-1][2]==s['page']:spans[-1]=(spans[-1][0],len(text),s['page'])
            else:spans.append((start,len(text),s['page']))
        if not spans:spans=[(0,0,c['startPage'])]
        return text,spans
    text='';spans=[]
    for page in range(c['startPage'],min(c['endPage']+1,len(book['pages']))):
        # Separators belong to the following page, preserving the previous page
        # scope and keeping the joined chapter an exact segment partition.
        value=page_text(book,page,original)
        prefix='\n\n' if text and value and not text.endswith('\n\n') and not value.startswith('\n\n') else ''
        start=len(text);text+=prefix+value;spans.append((start,len(text),page))
    return text,spans

def public_sections(book):
    result=[]
    for c in sections(book):
        text,_=text_and_spans(book,c)
        result.append(c|dict(text=text,originalText=text_and_spans(book,c,True)[0],characters=len(text),
                      noiseLines=clean_text(text)['count'],
                      indices=[i for i,s in enumerate(book['segments']) if (s.get('chapterId')==c['id'] if book.get('chapterModel')=='segments-v1' else c['startPage']<=s['page']<=c['endPage']) and narratable(s['text'])]))
    return result

def edit_chapter(book,chapter_id,text,expected=None):
    from core import split_text
    c=section(book,chapter_id)
    if not isinstance(text,str) or len(text)>LIMIT:raise ValueError('Mỗi chương tối đa 500.000 ký tự.')
    before,spans=text_and_spans(book,c)
    if expected is not None and before!=expected:raise ValueError('Nội dung đã thay đổi ở nơi khác. Mở lại chương trước khi lưu.')
    if before==text:return c
    # Map unchanged characters and edits back to their source page. Replacements
    # and insertions inherit the page at the edit boundary. No source is rewritten.
    assigned=defaultdict(list)
    def page_at(offset):
        return next((p for start,end,p in spans if start<=offset<end),spans[-1][2])
    if not spans:raise ValueError('Chưa có nội dung để sửa.')
    # Trim matching edges first: normal edits in long chapters should not run a
    # quadratic character diff across the entire document.
    prefix=0;end=min(len(before),len(text))
    while prefix<end and before[prefix]==text[prefix]:prefix+=1
    suffix=0
    while suffix<end-prefix and before[-suffix-1]==text[-suffix-1]:suffix+=1
    anchored=book.get('chapterModel')=='segments-v1'
    if anchored:
        # A wholesale replacement must not scatter common individual letters
        # (or its final full stop) across the old chapter's many source pages.
        if prefix<24:prefix=0
        if suffix<24:suffix=0
    old_end=len(before)-suffix;new_end=len(text)-suffix
    middle=SequenceMatcher(None,before[prefix:old_end],text[prefix:new_end],autojunk=True)
    ops=[('equal',0,prefix,0,prefix)]
    if anchored:
        a=b=prefix
        for op,a0,a1,b0,b1 in middle.get_opcodes():
            if op=='equal' and a1-a0>=24:
                a0+=prefix;a1+=prefix;b0+=prefix;b1+=prefix
                if a0>a or b0>b:ops.append(('replace',a,a0,b,b0))
                ops.append(('equal',a0,a1,b0,b1));a=a1;b=b1
        if a<old_end or b<new_end:ops.append(('replace',a,old_end,b,new_end))
    else:ops += [(op,a0+prefix,a1+prefix,b0+prefix,b1+prefix) for op,a0,a1,b0,b1 in middle.get_opcodes()]
    ops.append(('equal',old_end,len(before),new_end,len(text)))
    for op,a0,a1,b0,b1 in ops:
        if op=='equal':
            for start,end,page in spans:
                lo=max(start,a0);hi=min(end,a1)
                if hi>lo:assigned[page].append(text[b0+lo-a0:b0+hi-a0])
        elif op in ('replace','insert'):assigned[page_at(a0)].append(text[b0:b1])
    assert ''.join(''.join(assigned[p]) for _,_,p in spans)==text
    old={}
    for s in book['segments']:
        if book.get('chapterModel')!='segments-v1' or s.get('chapterId')==c['id']:old.setdefault((s['page'],s['text']),[]).append(s)
    replacement=[]
    for _,_,page in spans:
        value=''.join(assigned[page]);book['pages'][page]['narrationText']=value
        for chunk in split_text(value):
            matches=old.get((page,chunk),[])
            segment=matches.pop(0) if matches else dict(id=uuid.uuid4().hex,page=page,text=chunk,originalText=chunk)
            if book.get('chapterModel')=='segments-v1':segment=dict(segment,chapterId=c['id'])
            replacement.append(segment)
    # Keep initial segment originals for legacy segment edits and source audit.
    if 'sourceSegments' not in book:book['sourceSegments']=[dict(s) for s in book['segments']]
    first=c['startPage'];last=c['endPage']
    if book.get('chapterModel')=='segments-v1':
        # The previous chapter may end on this very same physical page.
        at=next((i for i,s in enumerate(book['segments']) if s.get('chapterId')==c['id']),None)
        if at is None:
            order={item['id']:i for i,item in enumerate(book['chapters'])}
            at=next((i for i,s in enumerate(book['segments']) if order.get(s.get('chapterId'),-1)>order[c['id']]),len(book['segments']))
        kept=[s for s in book['segments'] if s.get('chapterId')!=c['id']]
        book['segments']=kept[:at]+replacement+kept[at:]
        for _,_,page in spans:book['pages'][page]['narrationText']=''.join(s['text'] for s in book['segments'] if s['page']==page)
    else:book['segments']=[s for s in book['segments'] if s['page']<first]+replacement+[s for s in book['segments'] if s['page']>last]
    first_index=next((i for i,s in enumerate(book['segments']) if (s.get('chapterId')==c['id'] if book.get('chapterModel')=='segments-v1' else s['page']>=first)),max(0,len(book['segments'])-1))
    book['position']=dict(segment=first_index,seconds=0);book['finished']=False
    return c

def preview_cleanup(book,chapter_id,text,options=None):
    section(book,chapter_id)
    if not isinstance(text,str) or len(text)>LIMIT:raise ValueError('Mỗi chương tối đa 500.000 ký tự.')
    return clean_text(text,options,repeated_headers(book))
