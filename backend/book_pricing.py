"""Per-book pricing and a verbatim, automatically selected opening sample."""
import math
from scopes import chapters
from cleanup import narratable
from cloud_chunking import pack_segments, cut_at, VERSION as CHUNKING_VERSION

REVISION = 'pro-cloud-heygen-v1'
AUDIO_REVISION = 'pro-cloud-heygen-v1-audio-v1'
CHARS_PER_MINUTE = 900
TRIAL_LIMIT = 5
TRIAL_CHARACTERS = 5000
TRIAL_MAX_UNITS = 4
VOICES = [
    dict(id='3414fd7fdaa64e619fb8b021534ce368', label='Đình Mạnh · Nam (Podcast)', aliases=['voice-003', 'Đình Mạnh', 'dinh manh', 'Podcast', 'podcast'], gender='male', default=True),
    dict(id='3ab886ca76924521bbed407e45762540', label='Đình Gia · Nam', aliases=['voice-002', 'Đình Gia', 'dinh gia'], gender='male', default=False),
    dict(id='eff592346cac4febbba5d5fef4621ff0', label='Minh Bùi · Nam', aliases=['voice-004', 'Minh Bùi', 'minh bui'], gender='male', default=False),
    dict(id='b241299543834cd8994186e600280e25', label='Minh Tài · Nam', aliases=['voice-006', 'Minh Tài', 'minh tai'], gender='male', default=False),
    dict(id='60dce6af562449f294ceeddb4130a9ee', label='Kim Thoa · Nữ', aliases=['voice-007', 'Kim Thoa', 'kim thoa'], gender='female', default=False),
    dict(id='6a92e2ed9d3843f2b059ef8e6809366c', label='Ngân Quỳnh · Nữ', aliases=['voice-008', 'Ngân Quỳnh', 'ngan quynh'], gender='female', default=False),
    dict(id='5ee4ba10bd0446ba85421ab177462aba', label='Thanh Thảo · Nữ', aliases=['voice-001', 'Thanh Thảo', 'thanh thao'], gender='female', default=False),
]

def price(characters):
    if type(characters) is not int or not 0 < characters <= 2_000_000:
        raise ValueError('Sách cần từ 1 đến 2.000.000 ký tự.')
    if characters <= 27000: amount=10000
    elif characters <= 54000: amount=25000
    elif characters <= 108000: amount=40000
    else: amount=40000+math.ceil((characters-108000)/54000)*10000
    return dict(characters=characters, estimatedMinutes=math.ceil(characters/CHARS_PER_MINUTE),
                amountVND=amount, pricingVersion='book-v1')

def opening_page(book):
    # Use actual source/manual chapter markers; never classify prose as a chapter.
    items=[c for c in chapters(book) if c.get('origin')!='automatic' and c['id']!='preface']
    import re
    first=next((c for c in items if c.get('number')==1 or re.search(r'\b(?:chương|chapter|hồi)\s+(?:1|i|một|one)(?:\b|:)',c['title'],re.I)),None)
    return (first or (items[0] if items else {})).get('startPage',0)

def sample_segments(book,limit=TRIAL_CHARACTERS,chapter_id=None):
    start=opening_page(book);result=[];remaining=limit
    selected=None
    if chapter_id:
        from scopes import selected_indices
        if not any(c['id']==chapter_id for c in chapters(book)):raise ValueError('Chương đã thay đổi. Hãy chọn lại.')
        selected=set(selected_indices(book,dict(type='chapter',chapterId=chapter_id)))
        start=0
    first_index=0
    if book.get('chapterModel')=='segments-v1':
        opening=next((c for c in chapters(book) if c.get('number')==1),None)
        if opening and opening.get('indices'):first_index=opening['indices'][0]
    for i,s in enumerate(book['segments']):
        if (selected is not None and i not in selected) or (selected is None and (i<first_index or s['page']<start)) or not narratable(s['text']):continue
        text=s['text'][:remaining]
        if text:result.append(dict(id=s['id'],page=s['page'],index=i,text=text))
        remaining-=len(text)
        if remaining<=0:break
    return result

def trial_snapshot(book,chapter_id=None,units=1):
    if type(units) is not int or not 1<=units<=TRIAL_MAX_UNITS:
        raise ValueError('Mỗi lần chỉ được dùng từ 1 đến 4 lượt Pro.')
    if units>1 and not chapter_id:raise ValueError('Chọn một chương để gộp lượt Pro.')
    limit=TRIAL_CHARACTERS*units
    preview=sample_segments(book,limit=limit+1,chapter_id=chapter_id)
    text=''.join(s['text'] for s in preview)
    selected=cut_at(text,limit)
    segments=sample_segments(book,limit=selected,chapter_id=chapter_id)
    used=math.ceil(sum(len(s['text']) for s in segments)/TRIAL_CHARACTERS)
    if used<1:raise ValueError('Chương chưa có chữ để tạo Pro.')
    result=snapshot(book)|dict(segments=pack_segments(segments,book),openingPage=0)
    if used>1:result['trialUnits']=used
    return result

def chapter_trial_units(book,chapter_id):
    if not chapter_id:return 1
    count=sum(len(s['text']) for s in sample_segments(book,limit=2_000_000,chapter_id=chapter_id))
    return max(1,min(TRIAL_MAX_UNITS,math.ceil(count/TRIAL_CHARACTERS)))

def snapshot(book):
    if book.get('status')!='ready':raise ValueError('Trích chữ xong và lưu nội dung trước khi báo giá.')
    segments=[dict(id=s['id'],page=s['page'],index=i,text=s['text']) for i,s in enumerate(book['segments']) if narratable(s['text'])]
    price(sum(len(s['text']) for s in segments))
    voice=next((v['id'] for v in VOICES if book['voice']==v['id'] or book['voice'] in v['aliases']),None)
    if voice is None:raise ValueError('Chọn lại giọng Pro trong danh sách hiện tại trước khi tạo đơn mới.')
    return dict(title=book['title'],language=book.get('language','vi'),voice=voice,
                revision=REVISION,audioRevision=AUDIO_REVISION,chunkingVersion=CHUNKING_VERSION,
                segments=pack_segments(segments,book),openingPage=opening_page(book))
