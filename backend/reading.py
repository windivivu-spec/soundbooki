"""On-demand reading pages and conservative source anchors; never changes audio."""
import hashlib
import re
from cleanup import narratable

def sentences(text):
    # Partition verbatim. Keep decimals together and tolerate
    # headings without sentence punctuation. Timing is explicitly estimated.
    ends=[m.end() for m in re.finditer(r'[.!?…]+[”’"\')\]]*(?:\s+|$)|\n\s*\n',text)
          if not (m.group().startswith('.') and m.start()>0 and text[m.start()-1:m.start()].isdigit() and text[m.end():m.end()+1].isdigit())]
    result=[];start=0
    for end in ends+[len(text)]:
        if end<=start:continue
        value=text[start:end]
        if not value.strip() and not result:continue
        if value.strip():result.append(dict(start=start,end=end,text=value))
        elif result:result[-1]['text']+=value;result[-1]['end']=end
        start=end
    return result

def folded(text):return ''.join(c for c in text if not c.isspace())

def page_data(book,page,take_id=None,include_all=False):
    if type(page) is not int or not 0<=page<len(book['pages']):raise ValueError('Trang chưa có trong sách.')
    p=book['pages'][page];raw=p['text'];raw_positions=[i for i,c in enumerate(raw) if not c.isspace()]
    selected=book['segments']
    if take_id:
        from audiobooks import find
        selected=find(book,take_id)['segments']
    raw_fold=folded(raw);items=[(s.get('index',i) if take_id else i,s) for i,s in enumerate(selected) if s['page']==page]
    verbatim=folded(''.join(s['text'] for _,s in items))==raw_fold
    count=0;result=[]
    for index,s in items:
        cues=sentences(s['text']);weight=sum(max(1,len(folded(c['text']))) for c in cues);offset=0
        for number,cue in enumerate(cues):
            target=folded(cue['text']);lo=count+len(folded(s['text'][:cue['start']])) if verbatim else -1
            if not verbatim and target:
                matches=[m.start() for m in re.finditer(re.escape(target),raw_fold)]
                if len(matches)==1:lo=matches[0]
            anchor=None
            if target and lo>=0 and lo+len(target)<=len(raw_positions):
                a=raw_positions[lo];b=raw_positions[lo+len(target)-1]+1
                anchor=dict(location=len(raw[:a].encode('utf-16-le'))//2,length=len(raw[a:b].encode('utf-16-le'))//2)
            size=max(1,len(target));cue.update(id=s['id']+':'+str(number),segmentId=s['id'],index=index,
                startFraction=offset/max(1,weight),endFraction=(offset+size)/max(1,weight),sourceRange=anchor)
            offset+=size
            if include_all or narratable(cue['text']):result.append(cue)
        count+=len(folded(s['text']))
    source=book['sources'][p['source']]
    return dict(page=page,total=len(book['pages']),sourcePage=p['sourcePage'],source=p['source'],file=source['file'],
        format='epub' if book.get('format')=='epub' else source['file'].rsplit('.',1)[-1],title=p.get('title') or book['title'],
        sentences=result,rawText=raw,timing='estimated',language=book.get('language','vi'),
        contentKey=hashlib.sha256(''.join(s['id']+s['text'] for _,s in items).encode()).hexdigest())
