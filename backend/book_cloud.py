"""Explicit per-book cloud actions. No network during catalog/open/playback."""
import hashlib
import io
import wave
import json
import os
from pathlib import Path
import re
import subprocess
import socket
import urllib.error
import urllib.parse
import urllib.request
from book_pricing import snapshot,sample_segments,trial_snapshot,chapter_trial_units,price,TRIAL_LIMIT,TRIAL_CHARACTERS,TRIAL_MAX_UNITS
from core import atomic_json,signature,valid_audio
from datetime import datetime,timezone
import entitlements

ROOT=Path(__file__).resolve().parents[1]

def cloud_signature(segment,data):
    # Previously purchased snapshots keep their original cache revision even
    # after an app upgrade. New orders opt into the quality-reviewed pipeline.
    return signature(segment['text'],data['voice'],'pro-cloud',data['language'],model_revision=data.get('audioRevision',data['revision']))

def endpoint():
    config=entitlements.release()
    value=config.get('booksBaseURL','')
    if config.get('channel')=='development':value=os.environ.get('WSN_BOOKS_API',value)
    u=urllib.parse.urlsplit(value)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:return ''
    return value.rstrip('/')

def credential():
    p=subprocess.run([str(ROOT/'.build/windi-cloud-keychain')],input=json.dumps(dict(action='create',domain='books')).encode(),capture_output=True,timeout=10)
    try:token=json.loads(p.stdout)['token']
    except (ValueError,KeyError):raise ValueError('Mở khóa Keychain trên Mac trước khi dùng Pro Cloud.') from None
    if not re.fullmatch('wsn_book_[a-f0-9]{64}',token):raise ValueError('Khóa Pro Cloud không hợp lệ.')
    return token

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Dịch vụ chuyển hướng ngoài địa chỉ đã chọn.')

class Client:
    def __init__(self):
        self.base=endpoint()
        if not self.base:raise ValueError('Pro Cloud chưa kết nối dịch vụ. Bạn vẫn có thể dùng Lite miễn phí.')
        self.token=credential();self.device=entitlements.device_code()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def post(self,path,*,timeout=35,**value):
        req=urllib.request.Request(self.base+'/'+path,data=json.dumps(dict(deviceCode=self.device,**value),ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token},method='POST')
        try:
            with self.opener.open(req,timeout=timeout) as r:return json.loads(r.read(12_000_001))
        except urllib.error.HTTPError as e:
            try:message=json.loads(e.read(8192)).get('error')
            except ValueError:message=None
            raise ValueError(message or 'Chưa kiểm tra được đơn Pro Cloud. Mở lại cửa sổ để thử lại.') from None
        except (urllib.error.URLError,TimeoutError,socket.timeout):
            raise ValueError('Kết nối đang gián đoạn. Yêu cầu đã được giữ để tiếp tục kiểm tra; không cần tạo thêm yêu cầu.') from None

def service_info():
    result=Client().post('profile',timeout=8)
    return dict(configured=True,reachable=True,trialAvailable=result.get('trialAvailable') is True,
                purchaseAvailable=result.get('purchaseAvailable') is True,paymentRequired=True,
                **trial_state(result),trialCharacters=result.get('trialCharacters',TRIAL_CHARACTERS))

def cached_trial_audio(root,book,entry):
    if root is None or not entry:return []
    folder=Path(root)/book['id']/'cloud-trials';data=entry['snapshot'];result=[]
    for segment in data['segments']:
        path=folder/(cloud_signature(segment,data)+'.wav')
        if not valid_audio(path):break
        result.append(dict(audio=str(path),duration=0))
    return result


def cached_trials_remaining(state, prefix=''):
    """Upgrade the display cache without resetting previously used trials.

    The database remains authoritative. Old caches had a lifetime limit of 3.
    """
    remaining=state.get(prefix+'TrialsRemaining' if prefix else 'trialsRemaining')
    if type(remaining) is not int:return TRIAL_LIMIT
    limit=state.get(prefix+'TrialsLimit' if prefix else 'trialLimit',3)
    if type(limit) is not int or limit<0:limit=3
    return max(0,min(TRIAL_LIMIT,TRIAL_LIMIT-max(0,limit-remaining)))

def save_trial_cache(book,result):
    # Results from an older gateway keep its old limit until it is upgraded.
    book['cloudTrialsRemaining']=result.get('trialsRemaining',book.get('cloudTrialsRemaining',TRIAL_LIMIT))
    book['cloudTrialsLimit']=result.get('trialLimit',3)

def trial_state(result):
    return dict(trialsRemaining=cached_trials_remaining(result),trialLimit=TRIAL_LIMIT)

def same_trial_prefix(old,new):
    """A pending pre-upgrade excerpt must retry its immutable original body."""
    if old.get('trialUnits',1)>1 or new.get('trialUnits',1)>1:return same_snapshot(old,new)
    if {k:v for k,v in old.items() if k not in ('segments','chunkingVersion')}!={k:v for k,v in new.items() if k not in ('segments','chunkingVersion')}:return False
    from cloud_chunking import source_items
    a=source_items(old);b=source_items(new)
    return bool(a) and len(a)<=len(b) and all(
        item[0]==b[i][0] and (b[i][1].startswith(item[1]) if i==len(a)-1 else b[i][1]==item[1])
        for i,item in enumerate(a))

def same_snapshot(old,new):
    from cloud_chunking import source_items
    return ({k:v for k,v in old.items() if k not in ('segments','chunkingVersion')}==
            {k:v for k,v in new.items() if k not in ('segments','chunkingVersion')}
            and source_items(old)==source_items(new))

def trial_reference(book,chapter_id,units):
    # Pre-upgrade samples at the exact cap must retry their original body.
    data=snapshot(book)|dict(segments=sample_segments(book,limit=TRIAL_CHARACTERS*units,chapter_id=chapter_id),openingPage=0)
    debit=(sum(len(s['text']) for s in data['segments'])+TRIAL_CHARACTERS-1)//TRIAL_CHARACTERS
    if debit>1:data['trialUnits']=debit
    return data

def local_info(book,root=None,chapter_id=None,group_trial=False):
    data=snapshot(book)
    units=chapter_trial_units(book,chapter_id) if group_trial else 1
    trial_data=trial_snapshot(book,chapter_id,units);sample=trial_data['segments']
    reference=trial_reference(book,chapter_id,units)
    chapter_characters=sum(len(s['text']) for s in sample_segments(book,limit=2_000_000,chapter_id=chapter_id)) if chapter_id else None
    remaining=cached_trials_remaining(book,'cloud')
    if root is not None:
        try:remaining=min(remaining,cached_trials_remaining(json.loads((Path(root).parent/'book-cloud-state.json').read_text())))
        except (OSError,ValueError,KeyError):pass
    matching=[o for o in book.get('cloudOrders',[]) if o['kind']=='book' and same_snapshot(o['snapshot'],data) and o.get('order')]
    trials=[o for o in book.get('cloudOrders',[]) if o['kind']=='trial' and (same_trial_prefix(o['snapshot'],trial_data) or same_trial_prefix(o['snapshot'],reference)) and o.get('order')]
    saved=(matching or [None])[-1]
    pending_trial=next((o['requestKey'] for o in reversed(book.get('cloudOrders',[])) if o['kind']=='trial' and (same_trial_prefix(o['snapshot'],trial_data) or same_trial_prefix(o['snapshot'],reference)) and not o.get('order')),None)
    from launch_offer import policy,cached_at
    launch=cached_at(Path(root)) if root is not None else {}
    pending_combo=next((o['requestKey'] for o in reversed(book.get('cloudOrders',[])) if o.get('purchaseMode')=='combo' and same_snapshot(o['snapshot'],data) and not o.get('order')),None)
    pending_quote=next((o['requestKey'] for o in reversed(book.get('cloudOrders',[])) if o['kind']=='book' and o.get('purchaseMode')!='combo' and same_snapshot(o['snapshot'],data) and not o.get('order')),None)
    return dict(**price(sum(len(s['text']) for s in data['segments'])),sampleText=''.join(s['text'] for s in sample),configured=bool(endpoint()),serviceCheckPending=bool(endpoint()),launchOffer=policy(),launchBundle=launch.get('bundle'),pendingComboKey=pending_combo,
                pendingTrialKey=pending_trial,pendingQuoteKey=pending_quote,savedTrialOrder=trials[-1]['order'] if trials else None,savedOrder=saved.get('order') if saved else None,bank=saved.get('bank') if saved else None,trialsRemaining=remaining,trialLimit=TRIAL_LIMIT,trialCharacters=TRIAL_CHARACTERS,
                trialAudio=cached_trial_audio(root,book,trials[-1] if trials else None),
                trialMaxUnits=TRIAL_MAX_UNITS,trialUnits=trial_data.get('trialUnits',1),trialRequestCount=len(sample),trialChapterCharacters=chapter_characters,trialSelectedCharacters=sum(len(s['text']) for s in sample),trialCompleteChapter=chapter_characters is not None and sum(len(s['text']) for s in sample)==chapter_characters)

def create_order(lib,bid,kind,key,consent,chapter_id=None,trial_units=1,on_progress=None):
    if consent is not True:raise ValueError('Xác nhận gửi chữ lên cloud trước khi tạo thử hoặc đặt mua.')
    if kind not in ('book','trial','combo') or not re.fullmatch('[a-f0-9]{32}',str(key)):raise ValueError('Yêu cầu tạo sách không hợp lệ.')
    stored_kind='book' if kind=='combo' else kind
    with lib.lock:
        b=lib.load(bid);data=snapshot(b)
        if b.get('model')!='pro-cloud':raise ValueError('Chọn Pro · Tạo từ Cloud trước.')
        if kind=='trial':data=trial_snapshot(b,chapter_id,trial_units)
        # Persist before submitting: retry after a timeout uses the exact same key/body.
        existing=next((o for o in b.get('cloudOrders',[]) if o['requestKey']==key),None)
        if existing:
            if kind=='trial' and (same_trial_prefix(existing['snapshot'],data) or same_trial_prefix(existing['snapshot'],trial_reference(b,chapter_id,trial_units))):data=existing['snapshot']
            elif same_snapshot(existing['snapshot'],data):data=existing['snapshot']
            if existing['snapshot']!=data or existing['kind']!=stored_kind or (existing.get('purchaseMode')=='combo')!=(kind=='combo'):raise ValueError('Nội dung đã đổi. Tạo đơn mới với giá mới.')
        # Missing endpoint/locked Keychain must not leave a phantom pending order.
        client=Client()
        if not existing:
            from m4b import freeze_labels
            existing=dict(requestKey=key,kind=stored_kind,purchaseMode='combo' if kind=='combo' else 'book',snapshot=data,order=None,exportChapterLabels=freeze_labels(b,data['segments']),trialChapterId=chapter_id if kind=='trial' else None)
            b.setdefault('cloudOrders',[]).append(existing);lib.save(b)
    path='quote'
    if kind=='combo':path='bundle-redeem'
    elif kind=='trial':path='trial-group' if data.get('trialUnits',1)>1 else 'trial'
    result=client.post(path,snapshot=data,requestKey=key,consent=True)
    if kind=='combo':
        from launch_offer import save
        save(lib,{k:result[k] for k in ('offer','bundle') if k in result})
    with lib.lock:
        b=lib.load(bid);item=next(o for o in b['cloudOrders'] if o['requestKey']==key);item['order']=result['order'];item['bank']=result.get('bank');save_trial_cache(b,result);lib.save(b)
    atomic_json(lib.root.parent/'book-cloud-state.json',trial_state(result))
    if result['order'].get('state')=='ready' or result['order'].get('done',0)>0:
        return sync_order(lib,bid,result['order']['id'],on_progress=on_progress)
    return result


def prepare_cloud_audio(raw,data):
    """Verify the provider's bytes first; adapt new HeyGen WAVs to our 24 kHz player/export contract."""
    if data.get('revision')!='pro-cloud-heygen-v1':return raw
    try:
        with wave.open(io.BytesIO(raw),'rb') as source:
            rate=source.getframerate();count=source.getnframes()
            if source.getnchannels()!=1 or source.getsampwidth()!=2 or not 8000<=rate<=96000 or count<=0:
                raise ValueError('Dịch vụ trả định dạng WAV chưa được hỗ trợ.')
            frames=source.readframes(count)
            if len(frames)!=count*2:raise ValueError('Audio tải chưa đầy đủ.')
        if rate==24000:return raw
        import numpy as np
        import soxr
        samples=soxr.resample(np.frombuffer(frames,dtype='<i2').astype(np.float32)/32768,rate,24000,quality='HQ')
        pcm=np.rint(np.clip(samples,-1,32767/32768)*32768).astype('<i2').tobytes()
        target=io.BytesIO()
        with wave.open(target,'wb') as output:
            output.setparams((1,2,24000,0,'NONE','not compressed'));output.writeframes(pcm)
        return target.getvalue()
    except (wave.Error,EOFError) as error:
        raise ValueError('Audio tải về không phải WAV PCM hoàn chỉnh.') from error


def valid_audio_location(audio,base_url,order_id):
    try:
        u=urllib.parse.urlsplit(audio['url']);base=urllib.parse.urlsplit(base_url)
        if u.scheme!='https' or u.username or u.password:return False
        if audio.get('delivery')=='provider':
            return u.port in (None,443) and any(u.hostname==h or (u.hostname or '').endswith('.'+h) for h in ('heygen.ai','heygen.com','cloudfront.net','amazonaws.com'))
        return u.netloc==base.netloc and u.path.startswith('/storage/v1/object/sign/wsn-book-audio/'+order_id+'/')
    except (ValueError,KeyError,TypeError):return False


def sync_order(lib,bid,order_id,on_progress=None):
    if not re.fullmatch('[a-f0-9-]{36}',str(order_id)):raise ValueError('Mã đơn không hợp lệ.')
    with lib.lock:
        b=lib.load(bid);entry=next((o for o in b.get('cloudOrders',[]) if (o.get('order') or {}).get('id')==order_id),None)
        if not entry:raise ValueError('Đơn không thuộc sách trên máy này.')
        data=entry['snapshot'];is_trial=entry['kind']=='trial'
    folder=lib.directory(bid)/('cloud-trials' if is_trial else 'audio')
    known=[s['id'] for s in data['segments'] if valid_audio(folder/(cloud_signature(s,data)+'.wav'))]
    client=Client();result=client.post('status',orderId=order_id,knownSegments=known)
    if result['order']['id']!=order_id:raise ValueError('Dịch vụ trả sai đơn.')
    if result.get('audio') and result['order']['state'] in ('awaiting_payment','expired'):
        raise ValueError('Đơn chưa được xác nhận thanh toán. Chưa thể nhận audio của cuốn sách này.')
    def progress():
        if on_progress:
            on_progress(dict(order=result['order'],stage='receiving',
                receivedSegments=sum(valid_audio(folder/(cloud_signature(s,data)+'.wav')) for s in data['segments']),
                trialAudio=cached_trial_audio(lib.root,b,entry) if is_trial else []))
    if result.get('audio'):progress()
    for audio in result.get('audio',[]):
        segment=next((s for s in data['segments'] if s['id']==audio['id']),None)
        if segment is None:raise ValueError('Audio không thuộc nội dung đã mua.')
        folder=lib.directory(bid)/('cloud-trials' if is_trial else 'audio');folder.mkdir(exist_ok=True)
        name=cloud_signature(segment,data)+'.wav'
        target=folder/name
        if valid_audio(target):continue
        if not valid_audio_location(audio,client.base,order_id):
            raise ValueError('Địa chỉ audio không hợp lệ.')
        # Signed URL is limited to this result; merchant/device secrets never go to storage.
        with client.opener.open(audio['url'],timeout=60) as r:raw=r.read(52_428_801)
        if len(raw)>52_428_800 or hashlib.sha256(raw).hexdigest()!=audio['sha256']:raise ValueError('Audio tải chưa đầy đủ.')
        partial=target.with_suffix('.partial');partial.write_bytes(prepare_cloud_audio(raw,data))
        if not valid_audio(partial):partial.unlink(missing_ok=True);raise ValueError('Audio tải về không hợp lệ.')
        partial.replace(target)
        with lib.lock:
            b=lib.load(bid);lib.save(b)
        progress()
    with lib.lock:
        b=lib.load(bid);entry=next(o for o in b['cloudOrders'] if (o.get('order') or {}).get('id')==order_id);entry['order']=result['order'];save_trial_cache(b,result);entry['bank']=result.get('bank') or result['order'].get('bank') or entry.get('bank');result['bank']=entry.get('bank')
        if not is_trial and result['order']['state'] in ('queued','processing','ready','failed'):
            take=next((t for t in b.get('audiobooks',[]) if t.get('cloudOrderId')==order_id),None)
            if not take:
                take=dict(id=order_id.replace('-',''),title='Toàn bộ sách · Pro',createdAt=entry['order'].get('createdAt',datetime.now(timezone.utc).isoformat()),model='pro-cloud',voice=data['voice'],language=data['language'],scope={'type':'all'},status='generating',error='',cloudOrderId=order_id,
                  segments=[dict(s,**entry.get('exportChapterLabels',{}).get(s['id'],{}),file=cloud_signature(s,data)+'.wav') for s in data['segments']])
                b.setdefault('audiobooks',[]).insert(0,take)
            complete=all(valid_audio(lib.directory(bid)/'audio'/(cloud_signature(s,data)+'.wav')) for s in data['segments'])
            take['status']='ready' if result['order']['state']=='ready' and complete else 'failed' if result['order']['state']=='failed' else 'generating'
        if is_trial:
            from audiobooks import restore_cloud_trials
            restore_cloud_trials(lib,b)
        lib.save(b)
    atomic_json(lib.root.parent/'book-cloud-state.json',trial_state(result))
    result['trialAudio']=[]
    if is_trial:
        result['trialAudio']=cached_trial_audio(lib.root,b,entry)
    result['receivedSegments']=sum(valid_audio(folder/(cloud_signature(s,data)+'.wav')) for s in data['segments'])
    result['localReady']=result['order']['state']=='ready' and result['receivedSegments']==len(data['segments'])
    return result
