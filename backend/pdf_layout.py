"""Automatic, conservative import cleanup with verbatim source provenance.

Line layout and same-book evidence repair clear wraps. High-confidence running
headers and decoration lines are omitted from narration while raw text survives.
"""
from collections import Counter
import re
import statistics
import uuid
from cleanup import clean_text, repeated_headers, normalize_import_text

REVISION='pdf-layout-v1'
AUTO_CLEAN_REVISION='auto-clean-v2-case-roman'
WORD=re.compile(r'[^\W\d_]+',re.UNICODE)

def plain(text):return re.sub(r'\s','',text)

def source_chunks(raw,chunks):
    """Map cleaned chunks to contiguous verbatim source spans in reading order."""
    if not chunks:return []
    offset=0;result=[]
    for at,chunk in enumerate(chunks):
        cursor=offset;last=None
        for char in chunk:
            if char.isspace():continue
            while cursor<len(raw) and raw[cursor]!=char:cursor+=1
            if cursor==len(raw):
                # Keep the source intact even if an unusual extractor result cannot
                # be aligned exactly; never manufacture or discard source text.
                return [raw]+['']*(len(chunks)-1)
            last=cursor;cursor+=1
        end=len(raw) if at==len(chunks)-1 else (last+1 if last is not None else offset)
        result.append(raw[offset:end]);offset=end
    return result

def _ordered_without_layout_hyphens(value,source):
    """True when value preserves source characters, allowing removed line-wrap hyphens."""
    wanted=iter(plain(source));
    for char in plain(value):
        while True:
            candidate=next(wanted,None)
            if candidate is None:return False
            if candidate==char:break
            if candidate not in '-‐‑':return False
    return True

def reflow_unpositioned(text,freq):
    """Join only obvious OCR line wraps when page geometry is unavailable."""
    lines=text.splitlines();out='';previous='';changes=[]
    for value in lines:
        value=value.strip()
        if not value:
            if out and not out.endswith('\n\n'):out=out.rstrip()+'\n\n'
            previous='';continue
        if not out:
            out=value;previous=value;continue
        left=re.search(r'([^\W\d_]+)[-‐‑]$',out,re.UNICODE)
        right=WORD.match(value)
        boundary='\n'
        if left and right:
            out=out.rstrip()[:-1];boundary=' '
            changes.append(dict(before=left.group(1)+'- / '+right.group(),after=left.group(1)+' '+right.group(),evidence='ocr-line-wrap'))
        else:
            left_word=re.search(r'([^\W\d_]+)$',out,re.UNICODE)
            if left_word and right:
                a,b=left_word.group(),right.group();joined=(a+b).casefold()
                if freq[joined]>=2 and (freq[a.casefold()]==0 or freq[b.casefold()]==0 or min(len(a),len(b))==1):
                    boundary='';changes.append(dict(before=a+' / '+b,after=a+b,evidence=freq[joined]))
                elif value[0].islower() and not re.search(r'[.!?…][”’"\')\]]*$',out.rstrip()):boundary=' '
        out=out.rstrip()+boundary+value;previous=value
    trailing=len(text)-len(text.rstrip('\r\n'))
    if trailing:out=out.rstrip('\r\n')+'\n'*trailing
    if not _ordered_without_layout_hyphens(out,text):return text,[]
    return out,changes

def rows(page):
    # Native offsets are UTF-16; Python indexes Unicode code points.
    text=page['text'];mapping={0:0};units=0
    for i,ch in enumerate(text):
        units+=2 if ord(ch)>0xffff else 1;mapping[units]=i+1
    result=[]
    for row in page.get('layout',[]):
        r=dict(row);offset=r.get('startUTF16')
        if offset not in mapping:continue
        r['start']=mapping[offset]
        result.append(r)
    return result

def lexicon(book):
    return Counter(m.group().casefold() for p in book['pages'] for r in p.get('layout',[])
                   if r.get('w',0)>120 for m in WORD.finditer(r['text']) if len(m.group())>=2)

def headings(book):
    """Read actual large-font number/title pairs, including across page breaks."""
    fonts=[r.get('size',0) for p in book['pages'] for r in p.get('layout',[]) if len(r['text'])>40 and r.get('size',0)>0]
    if not fonts:return []
    threshold=max(18,statistics.median(fonts)*1.35)
    large=[(i,r) for i,p in enumerate(book['pages']) for r in rows(p) if r.get('size',0)>=threshold]
    candidates=[]
    for at,(page,r) in enumerate(large):
        match=re.fullmatch(r'(?:CHƯƠNG\s+|Chương\s+|Chapter\s+)?(\d{1,3})[.:]?',r['text'].strip())
        if not match:continue
        titles=[]
        for p,t in large[at+1:at+5]:
            value=t['text'].strip()
            if p>page+1 or re.fullmatch(r'\d+[.:]?',value):break
            letters=[c for c in value if c.isalpha()]
            if not letters or sum(c.isupper() for c in letters)/len(letters)<.75:break
            titles.append(value)
        if titles:
            candidates.append(dict(id='pdf-heading-'+str(page)+'-'+str(r['start']),title=' '.join(titles),
                number=int(match[1]),startPage=page,sourceOffset=r['start'],origin='pdf-heading'))
    # A sequence is structural evidence. A standalone number in a figure isn't.
    best=[]
    for i,c in enumerate(candidates):
        if c['number']!=1:continue
        run=[c]
        for following in candidates[i+1:]:
            if following['number']==run[-1]['number']+1:run.append(following)
        if len(run)>len(best):best=run
    return best if len(best)>=2 and len({c['startPage'] for c in best})>=2 else []

def reflow(text,line_rows,freq):
    if not line_rows:return text,[],0
    # Keep extracted reading order. Layout identifies tight wrapping; it is not
    # permission to interleave columns or reorder the author's characters.
    by_offset={r['start']:r for r in line_rows}
    lines=text.splitlines(keepends=True);offset=0;out='';previous=None;changes=[];uncertain=0
    for line in lines:
        value=line.strip();row=by_offset.get(offset);offset+=len(line)
        if not value:
            if out and not out.endswith('\n\n'):out=out.rstrip()+'\n\n'
            previous=None;continue
        if not out:out=value;previous=row;continue
        narrow=bool(previous and previous.get('w',999)<65 and previous.get('size',0)<19)
        heading=bool((row and row.get('size',0)>=19) or (previous and previous.get('size',0)>=19))
        paragraph=bool(row and previous and row.get('y',0)-previous.get('y',0)>previous.get('h',20)*1.6)
        separator='\n\n' if heading or previous is None or paragraph else ' '
        if narrow:
            left=re.search(r'([^\W\d_]+)$',out,re.UNICODE);right=WORD.match(value)
            if left and right:
                a,b=left.group(),right.group();joined=(a+b).casefold()
                if freq[joined]>=2 and (freq[a.casefold()]==0 or freq[b.casefold()]==0 or min(len(a),len(b))==1):
                    separator='';changes.append(dict(before=a+' / '+b,after=a+b,evidence=freq[joined]))
                elif freq[a.casefold()]==0 or freq[b.casefold()]==0:uncertain+=1
        if value[0] in ',.;:!?)]}”’':separator=''
        hyphenated=re.search(r'([^\W\d_]+)[-‐‑]$',out,re.UNICODE)
        next_word=WORD.match(value)
        if hyphenated and next_word and not heading and not paragraph:
            # A terminal hyphen between adjacent body lines is a printed wrap.
            # Keep both source pieces and record the correction; only drop the hyphen.
            out=out[:-1];separator=' '
            changes.append(dict(before=hyphenated.group(1)+'- / '+next_word.group(),after=hyphenated.group(1)+' '+next_word.group(),evidence='line-wrap'))
        if out.endswith('\n\n'):separator=''
        out+=separator+value;previous=row
    # Refuse a whole piece if an extraction quirk would lose or reorder text.
    if not _ordered_without_layout_hyphens(out,text):return text,[],1
    return out,changes,uncertain

def auto_clean_import(book,save=lambda:None,progress=lambda **kw:None,cancel=lambda:False):
    """Clean high-confidence import noise while retaining each source span verbatim."""
    from core import split_text
    repeated=repeated_headers(book);options=dict(decorations=True,repeatedHeaders=True)
    freq=Counter(m.group().casefold() for p in book['pages'] for m in WORD.finditer(p['text']))
    by_page={i:[] for i in range(len(book['pages']))}
    for segment in book['segments']:
        by_page.setdefault(segment.get('page',0),[]).append(segment)
    completed=[]
    for i,page in enumerate(book['pages']):
        if cancel():return False
        current=[];page_text='';page_removed=0
        for segment in by_page.get(i,[]):
            value=segment['text']
            if book.get('format')!='epub' and page.get('method')=='ocr':value,_=reflow_unpositioned(value,freq)
            cleaned=clean_text(value,options,repeated)
            page_removed+=cleaned['count'];page_text+=cleaned['text']
            chunks=split_text(cleaned['text'])
            source=segment.get('originalText',segment['text'])
            if not chunks and source:chunks=['']
            originals=source_chunks(source,chunks)
            for at,(chunk,original) in enumerate(zip(chunks,originals)):
                updated=dict(segment,text=chunk,originalText=original)
                if at:updated['id']=uuid.uuid4().hex
                current.append(updated)
        page_text=normalize_page_case(current,page_text,book.get('language','vi'))
        completed.extend(current)
        future=[s for s in book['segments'] if s.get('page',0)>i]
        book['segments']=completed+future
        page['narrationText']=page_text;page['autoCleanupRevision']=AUTO_CLEAN_REVISION
        page['autoCleanupRemovedLines']=page_removed or page.get('autoCleanupRemovedLines',0)
        book['processing']=dict(phase='layout',done=i+1,total=len(book['pages']))
        save();progress(**book['processing'])
    book['autoCleanup']=dict(revision=AUTO_CLEAN_REVISION,removedLines=sum(p.get('autoCleanupRemovedLines',0) for p in book['pages']))
    save();return True

def normalize_page_case(segments,text,language='vi'):
    # Apply on the whole page so a long uppercase line crossing 420-character
    # reader chunks gets exactly one initial capital, never one per chunk.
    value,edits=normalize_import_text(text,language)
    def boundary(position):
        delta=0
        for start,end,replacement in edits:
            if position>=end:delta+=len(replacement)-(end-start)
            elif position>start:return start+delta+len(replacement)
            else:break
        return position+delta
    offset=0
    for segment in segments:
        end=offset+len(segment['text'])
        segment['text']=value[boundary(offset):boundary(end)];offset=end
    return value

def process_book(book,save=lambda:None,progress=lambda **kw:None,cancel=lambda:False):
    from core import split_text
    if book.get('format')=='epub' or not any(p.get('layout') for p in book['pages']):
        return auto_clean_import(book,save,progress,cancel)
    # Explicit outlines/manual chapters take precedence over inferred typography.
    existing=book.get('chapters',[])
    meaningful=[c for c in existing if c.get('origin') not in ('automatic','pdf-heading') and c.get('title','').strip().casefold() not in ('start','begin','beginning')]
    detected=headings(book) if not meaningful else []
    markers=[dict(c) for c in detected] if detected else [dict(c,sourceOffset=c.get('sourceOffset',0)) for c in existing]
    if not markers or markers[0]['startPage']>0 or markers[0].get('sourceOffset',0)>0:
        markers.insert(0,dict(id='preface',title='Phần mở đầu' if markers else 'Nội dung sách',startPage=0,sourceOffset=0,origin='automatic'))
    markers=sorted(markers,key=lambda c:(c['startPage'],c.get('sourceOffset',0)))
    for c in markers:c['originalText']=''
    freq=lexicon(book);repeated=repeated_headers(book);book['chapters']=markers;book['chapterModel']='segments-v1'
    old={}
    for s in book['segments']:old.setdefault((s['page'],s.get('originalText',s['text']),s.get('chapterId')),[]).append(s)
    active=markers[0];all_segments=[];audit=[];review=0
    progress(phase='layout',done=0,total=len(book['pages']))
    for i,page in enumerate(book['pages']):
        if cancel():return False
        text=page['text'];line_rows=rows(page);cuts=[(c.get('sourceOffset',0),c) for c in markers if c['startPage']==i]
        boundaries=[0]+[off for off,_ in cuts if off>0]+[len(text)]
        page_segments=[];narration='';page_review=0;page_removed=0
        for start,end in zip(boundaries,boundaries[1:]):
            for off,c in cuts:
                if off==start:active=c
            raw=text[start:end];active['originalText']+=raw
            local=[dict(r,start=r['start']-start) for r in line_rows if start<=r['start']<end]
            value,changes,uncertain=reflow(raw,local,freq)
            cleaned=clean_text(value,dict(decorations=True,repeatedHeaders=True),repeated)
            value=cleaned['text'];page_removed+=cleaned['count']
            if end<len(text):value+='\n\n'
            narration+=value;audit.extend(dict(page=i+1,**change) for change in changes);review+=uncertain;page_review+=uncertain
            chunks=split_text(value)
            if not chunks and raw:chunks=['']
            for chunk,original in zip(chunks,source_chunks(raw,chunks)):
                matches=old.get((i,original,active['id']),[])
                segment=dict(matches.pop(0)) if matches else dict(id=uuid.uuid4().hex,page=i,text=chunk,originalText=chunk)
                segment['text']=chunk
                segment['originalText']=original
                segment['chapterId']=active['id'];page_segments.append(segment)
        narration=normalize_page_case(page_segments,narration,book.get('language','vi'))
        page['narrationText']=narration;page['layoutRevision']=REVISION;page['autoCleanupRevision']=AUTO_CLEAN_REVISION
        page['autoCleanupRemovedLines']=page_removed or page.get('autoCleanupRemovedLines',0)
        page['layoutReviewCount']=page_review
        page['layoutWarning']=f'{page_review} ranh giới từ trên trang {i+1} chưa đủ bằng chứng để tự nối. Đối chiếu bản gốc trước khi tạo.' if page_review else ''
        all_segments.extend(page_segments)
        # Retain all unfinished source segments if cancelled between checkpoints.
        book['segments']=all_segments+[s for s in book['segments'] if s['page']>i]
        book['processing']=dict(phase='layout',done=i+1,total=len(book['pages']),repairs=len(audit),reviewCount=review)
        save();progress(**book['processing'])
    book['layoutProcessing']=dict(revision=REVISION,repairs=len(audit),reviewCount=review,changes=audit[:500],chapterCount=len(detected))
    book['autoCleanup']=dict(revision=AUTO_CLEAN_REVISION,removedLines=sum(p.get('autoCleanupRemovedLines',0) for p in book['pages']))
    book['position']=dict(segment=0,seconds=0);book['finished']=False
    save();return True
