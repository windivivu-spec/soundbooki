"""Immutable narration snapshots; editing a book never discards a completed take."""
from datetime import datetime,timezone
import uuid
import re
import wave
import shutil
from core import signature,valid_audio

def restore_cloud_trials(lib,book):
    """Expose already downloaded samples as immutable, exportable local takes.

    Also runs on reopen to recover pre-upgrade samples without any network or
    quota debit. Keep the original trial files for old popup/history playback.
    """
    from book_cloud import cloud_signature
    changed=False
    for entry in book.get('cloudOrders',[]):
        order=entry.get('order') or {}
        if entry.get('kind')!='trial' or not order.get('id'):continue
        data=entry['snapshot'];folder=lib.directory(book['id'])
        available=False
        for segment in data['segments']:
            name=cloud_signature(segment,data)+'.wav'
            source=folder/'cloud-trials'/name;target=folder/'audio'/name
            if not valid_audio(source):continue
            available=True
            if not valid_audio(target):
                partial=target.with_suffix('.trial-partial')
                shutil.copyfile(source,partial)
                if not valid_audio(partial):partial.unlink(missing_ok=True);continue
                partial.replace(target)
        if not available:continue
        take=next((t for t in book.get('audiobooks',[]) if t.get('cloudOrderId')==order['id']),None)
        if not take:
            labels=entry.get('exportChapterLabels',{})
            title=next((v['chapterTitle'] for v in labels.values() if v.get('chapterTitle')),None)
            take=dict(id=order['id'].replace('-',''),title='Mẫu Pro'+(' · '+title if title else ''),
                      createdAt=order.get('createdAt',datetime.now(timezone.utc).isoformat()),
                      voice=data['voice'],model='pro-cloud',language=data['language'],cloudOrderId=order['id'],cloudKind='trial',
                      scope=dict(type='cloud-trial',chapterId=entry.get('trialChapterId')),error='',status='generating',
                      segments=[dict(s,**labels.get(s['id'],{}),file=cloud_signature(s,data)+'.wav') for s in data['segments']])
            book.setdefault('audiobooks',[]).insert(0,take);changed=True
        complete=all(valid_audio(folder/'audio'/s['file']) for s in take['segments'])
        status='ready' if complete else 'failed' if order.get('state')=='failed' else 'generating'
        if take['status']!=status:take['status']=status;changed=True
    return changed

def create(book,indices,title,scope):
    take=dict(id=uuid.uuid4().hex,title=title,createdAt=datetime.now(timezone.utc).isoformat(),
              voice=book['voice'],model=book.get('model','nano'),language=book.get('language','vi'),
              scope=scope or {'type':'all'},status='generating',error='',segments=[])
    from bilingual import cache_signature
    from scopes import chapters
    catalog=chapters(book)
    take['bilingual']=book.get('bilingual',False)
    for i in indices:
        s=book['segments'][i]
        take['segments'].append(dict(id=s['id'],page=s['page'],text=s['text'],index=i,
                                     file=cache_signature(book,s['text'])+'.wav'))
        chapter=next((c for c in catalog if i in c.get('indices',[]) or ('indices' not in c and c['startPage']<=s['page']<=c['endPage'])),None)
        take['segments'][-1].update(chapterId=chapter['id'] if chapter else 'document',chapterTitle=chapter['title'] if chapter else title)
    book.setdefault('audiobooks',[]).insert(0,take)
    return take

def find(book,take_id):
    take=next((t for t in book.get('audiobooks',[]) if t['id']==take_id),None)
    if not take:raise ValueError('Bản sách nói không tồn tại.')
    return take

def path(lib,bid,segment):
    name=segment.get('file','')
    if not re.fullmatch('[a-f0-9]{64}\\.wav',name):raise ValueError('Đường dẫn audio không hợp lệ.')
    return lib.directory(bid)/'audio'/name

def public(lib,bid,take):
    result={k:v for k,v in take.items() if k!='segments'};result['segments']=[];duration=0
    for s in take['segments']:
        p=path(lib,bid,s);ready=valid_audio(p);seconds=0
        if ready:
            with wave.open(str(p),'rb') as w:seconds=w.getnframes()/w.getframerate()
        result['segments'].append(s|dict(audio=str(p) if ready else None,duration=seconds));duration+=seconds
    result['readyCount']=sum(bool(s['audio']) for s in result['segments']);result['duration']=duration
    result['status']='ready' if result['readyCount']==len(result['segments']) and result['segments'] else ('partial' if result['readyCount'] else 'empty')
    result['interrupted']=take['status']=='generating'
    return result

def archive_existing(lib,book):
    if book.get('audiobooks') or not book['segments']:return
    from cleanup import narratable
    indices=[i for i,s in enumerate(book['segments']) if narratable(s['text']) and valid_audio(lib.audio_path(book,s))]
    if indices:
        take=create(book,indices,'Audio đã có',{'type':'existing'});take['status']='ready'
