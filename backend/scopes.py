"""Page/chapter selections. Page numbers in UI/API are one-based."""
import uuid

def chapters(book):
    count=len(book['pages'])
    items=book.get('chapters',[])
    if book.get('chapterModel')=='segments-v1':
        result=[]
        for c in items:
            indices=[i for i,s in enumerate(book['segments']) if s.get('chapterId')==c['id']]
            result.append(dict(c,indices=indices,endPage=book['segments'][indices[-1]]['page'] if indices else c['startPage']))
        return result
    starts={}
    for c in items:
        start=c.get('startPage',-1)
        if isinstance(start,int) and start>=0:
            starts.setdefault(start,dict(c))
    if starts and 0 not in starts:
        starts[0]=dict(id='preface',title='Phần mở đầu',startPage=0,origin='automatic')
    result=sorted(starts.values(),key=lambda c:c['startPage'])
    for i,c in enumerate(result):
        c['endPage']=(result[i+1]['startPage']-1) if i+1<len(result) else max(count,book.get('totalPages',0))-1
    return result

def selected_indices(book, scope):
    scope=scope or {'type':'all'}
    kind=scope.get('type','all');count=len(book['pages'])
    if kind=='all': first,last=0,count-1
    elif kind in ('page','range'):
        try:
            first=int(scope.get('page') if kind=='page' else scope['fromPage'])-1
            last=first if kind=='page' else int(scope['toPage'])-1
        except (TypeError,KeyError,ValueError): raise ValueError('Chọn số trang hợp lệ.')
        if not 0<=first<=last<count:raise ValueError('Khoảng trang chưa được trích chữ hoặc không hợp lệ.')
    elif kind=='chapter':
        c=next((c for c in chapters(book) if c['id']==scope.get('chapterId')),None)
        if not c and scope.get('chapterId')=='document' and not chapters(book):c=dict(startPage=0,endPage=count-1)
        if not c:raise ValueError('Chọn chương từ mục lục hoặc đặt mốc chương trước.')
        if book.get('chapterModel')=='segments-v1':
            from cleanup import narratable
            return [i for i in c['indices'] if narratable(book['segments'][i]['text'])]
        first,last=c['startPage'],c['endPage']
        if last>=count:raise ValueError('Chương này chưa được trích chữ xong. Tiếp tục trích chữ trước khi tạo cả chương.')
    else:raise ValueError('Phạm vi không hợp lệ.')
    from cleanup import narratable
    return [i for i,s in enumerate(book['segments']) if first<=s['page']<=last and narratable(s['text'])]

def mark_chapter(book,page,title):
    if not isinstance(page,int) or not 0<=page<len(book['pages']):raise ValueError('Trang mở đầu chương không hợp lệ.')
    title=str(title).strip()
    if not 1<=len(title)<=160:raise ValueError('Tên chương cần từ 1 đến 160 ký tự.')
    if book.get('chapterModel')=='segments-v1':
        # A manual page marker begins at the first segment of that page. Keep
        # subsequent visual boundaries even when another chapter shares a page.
        first=next((i for i,s in enumerate(book['segments']) if s['page']==page),None)
        if first is None:raise ValueError('Trang này không có chữ để đặt mốc.')
        current=book['segments'][first].get('chapterId')
        old=next((c for c in book['chapters'] if c['id']==current),None)
        if old and old['startPage']==page and old.get('sourceOffset',0)==0:
            old['title']=title;old['origin']='manual';return old
        c=dict(id=uuid.uuid4().hex,title=title,startPage=page,sourceOffset=0,origin='manual',originalText='')
        for s in book['segments'][first:]:
            if s.get('chapterId')!=current:break
            s['chapterId']=c['id']
        at=book['chapters'].index(old)+1 if old else 0;book['chapters'].insert(at,c)
        rebuild_originals(book)
        return c
    items=[dict(c) for c in book.get('chapters',[]) if c['startPage']!=page]
    items.append(dict(id=uuid.uuid4().hex,title=title,startPage=page,origin='manual'))
    book['chapters']=sorted(items,key=lambda c:c['startPage'])
    return next(c for c in items if c['startPage']==page)

def remove_chapter(book,chapter_id):
    items=book.get('chapters',[]);at=next((i for i,c in enumerate(items) if c['id']==chapter_id),None)
    if at is None:return
    if book.get('chapterModel')=='segments-v1':
        if len(items)==1:raise ValueError('Giữ ít nhất một phần nội dung cho cuốn sách.')
        target=items[at-1] if at else items[1]
        source=items[at].get('originalText','')
        target['originalText']=(target.get('originalText','')+source) if at else (source+target.get('originalText',''))
        if not at:target.update(startPage=items[at]['startPage'],sourceOffset=items[at].get('sourceOffset',0))
        for s in book['segments']:
            if s.get('chapterId')==chapter_id:s['chapterId']=target['id']
    book['chapters']=[c for c in items if c['id']!=chapter_id]

def rebuild_originals(book):
    items=book['chapters']
    for at,c in enumerate(items):
        following=items[at+1] if at+1<len(items) else None;value=''
        last=following['startPage'] if following else len(book['pages'])-1
        for page in range(c['startPage'],last+1):
            start=c.get('sourceOffset',0) if page==c['startPage'] else 0
            end=following.get('sourceOffset',0) if following and page==following['startPage'] else len(book['pages'][page]['text'])
            value+=book['pages'][page]['text'][start:end]
        c['originalText']=value
