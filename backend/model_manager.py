"""Pinned preset-only resources. Network access exists only in explicit install()."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from core import atomic_json
import features

ROOT=Path(__file__).resolve().parents[1]
PROFILES={
    'nano':dict(label='Lite',manifest='models.json',mode='v3nano',sampleRate=24000,minRAM=8,recommendedRAM=8,languages=['vi'],
                description='Nhẹ và nhanh. Ngữ điệu đơn giản hơn, phù hợp nghe thử hoặc máy ít RAM.'),
    'turbo':dict(label='VieNeu Turbo · Chất lượng cao',manifest='models-turbo.json',mode='v3turbo',sampleRate=48000,minRAM=8,recommendedRAM=16,languages=['vi','en'],
                 description='Nhiều lựa chọn giọng cho tiếng Việt và tiếng Anh. Hãy nghe thử để chọn giọng phù hợp với cuốn sách.'),
    'kitten':dict(label='KittenTTS Mini · English',manifest='models-kitten.json',mode='kitten',sampleRate=24000,minRAM=8,recommendedRAM=8,languages=['en'],
                  description='8 giọng nam và nữ cho sách tiếng Anh. Gói tải nhẹ, phù hợp để bắt đầu nghe.'),
    'f5-private':dict(label='Giọng đọc riêng · F5',manifest='models-f5-private.json',mode='f5',sampleRate=24000,minRAM=8,recommendedRAM=16,languages=['vi'],
                     description='6 giọng đọc riêng cho sách tiếng Việt. Tạo bản đọc ngay trên Mac với gói Pro.'),
    'pro-cloud':dict(label='Pro · Tạo từ Cloud',mode='cloud',sampleRate=24000,minRAM=8,recommendedRAM=8,languages=['vi'],
                     description='Giọng đọc giàu ngữ điệu, xử lý trên cloud để Mac luôn nhẹ. Thanh toán một lần cho từng cuốn; tải audio về để nghe và xuất kèm nhạc.'),
    'clone-pro':dict(label='Pro Max · Clone Pro 2.1',mode='cloud',sampleRate=48000,minRAM=8,recommendedRAM=8,languages=['vi','en'],
                     description='Tạo sách nói với giọng Clone Pro 2.1 qua mạng. Mua credit riêng trong app, không cần tài khoản web Clone Pro. Audio tải về nghe và xuất trên máy.')
}

def profile(model_id='nano'):
    if model_id not in PROFILES:raise ValueError('Gói giọng không hợp lệ.')
    return PROFILES[model_id]

def manifest(model_id):
    return json.loads((ROOT/'backend'/profile(model_id)['manifest']).read_text())

@lru_cache(maxsize=4)
def revision(model_id='nano'):
    profile(model_id)
    if model_id=='pro-cloud':
        from book_pricing import AUDIO_REVISION
        return AUDIO_REVISION
    if model_id=='clone-pro':
        from clone_pro import REVISION
        return REVISION
    if model_id=='nano':return 'vieneu-3.8.1-nano-aba295eb-16steps-v1'
    data=manifest(model_id)
    if model_id=='f5-private':return 'f5-private-'+data.get('inferenceRevision',data['revision'])+'-mps-fp16-24nfe-seed42-prosody-v8-clean'
    if model_id=='kitten':return 'kitten-mini-'+data['revision']+'-espeak-0.2.4-phonemizer-3.4.0-adapter-v1'
    return 'vieneu-3.8.1-turbo-fp32-'+data['revision']+'-codec-'+data['files'][-1]['revision']+'-v1'

def config():
    path=resource_root()/'config.json'
    return json.loads(path.read_text()) if path.exists() else {}

def resource_root():
    from entitlements import release, data_root
    return data_root()/'resources' if release().get('channel')=='consumer' else ROOT/'.resources'

def location(model_id):
    profile(model_id);cfg=config()
    saved=cfg.get('profiles',{}).get(model_id)
    if saved:return Path(saved)
    if model_id=='nano' and cfg.get('models'):return Path(cfg['models'])
    bundled=ROOT/'.resources'/('tts-'+model_id)
    return bundled if bundled.is_dir() else resource_root()/('tts-'+model_id)

def verify(path,item):
    if not path.is_file() or path.stat().st_size!=item['size']:return False
    digest=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(1024*1024):digest.update(data)
    return digest.hexdigest()==item['sha256']

@lru_cache(maxsize=8)
def _verified_files(root,fingerprint):
    return all(verify(Path(root)/name,dict(size=size,sha256=sha)) for name,size,sha,mtime,ctime in fingerprint)

def ready(model_id):
    if model_id=='pro-cloud':return True
    if model_id=='clone-pro':
        from clone_pro import connected
        return features.PRO_MAX_ENABLED and connected()
    root=location(model_id);fingerprint=[]
    if model_id=='f5-private' and not (ROOT/'.runtime-f5/bin/python').is_file():return False
    for item in manifest(model_id)['files']:
        path=root/item['file']
        if not path.is_file():return False
        info=path.stat()
        if info.st_size!=item['size']:return False
        fingerprint.append((item['file'],item['size'],item['sha256'],info.st_mtime_ns,info.st_ctime_ns))
    return _verified_files(str(root),tuple(fingerprint))

def verified_location(model_id):
    root=location(model_id)
    if not ready(model_id):
        raise ValueError('Gói giọng chưa đầy đủ hoặc bị lỗi. Mở Gói giọng đọc để tải lại.')
    return root

def voices(model_id='nano',root=None):
    if model_id=='pro-cloud':
        from book_pricing import VOICES
        return VOICES
    if model_id=='clone-pro':
        from clone_pro import voices as cloud_voices
        return cloud_voices()
    if model_id=='f5-private':
        root=Path(root) if root is not None else location('f5-private')
        items=[];data=manifest('f5-private')
        for entry in data['files']:
            name=entry['file']
            if name=='model.pt' or (name.startswith('voices/') and name.endswith('/model.pt')):
                vid='voice-001' if name=='model.pt' else Path(name).parent.name
                if vid in data.get('excludedVoices',[]) or not (root/name).is_file():continue
                vdir=(root/name).parent
                meta=json.loads((vdir/'voice_manifest.json').read_text()) if (vdir/'voice_manifest.json').is_file() else {}
                default_label='Giọng của tôi · Giọng nữ 002' if vid=='voice-002' else 'Giọng của tôi · Bản train '+vid.split('-')[-1]
                label=(meta.get('label') or default_label).replace('Bản train','Giọng').replace('Giọng của tôi · ','')
                aliases=meta.get('aliases') or (['ref voice nu'] if vid=='voice-002' else [])
                items.append(dict(id=vid,label=label,aliases=aliases,default=vid==data.get('defaultVoice','voice-001')))
        if items and not any(v['default'] for v in items):items[0]['default']=True
        return items
    if model_id=='kitten':
        return [dict(id=name,label=name+' · English · '+gender,aliases=[],default=name=='Jasper') for name,gender in [('Bella','Female'),('Jasper','Male'),('Luna','Female'),('Bruno','Male'),('Rosie','Female'),('Hugo','Male'),('Kiki','Female'),('Leo','Male')]]
    spec=importlib.util.find_spec('vieneu')
    if not spec:return []
    data=json.loads((Path(spec.origin).parent/('assets/voices_v3_'+('nano' if model_id=='nano' else 'turbo')+'.json')).read_text())
    result=[dict(id=k,label=k+' · '+v.get('description',''),aliases=v.get('aliases',[]),default=k==data.get('default_voice')) for k,v in data['presets'].items()
            if k not in {'Adam','Ái Hân','Xuân Tiên','Minh Quân'}]
    if result and not any(v['default'] for v in result):
        next((v for v in result if v['id']=='Đức Trí'),result[0])['default']=True
    return result

def resolve_voice(model_id,voice):
    available=voices(model_id)
    found=next((v for v in available if voice==v['id'] or voice in v['aliases']),None)
    return found['id'] if found else next((v['id'] for v in available if v['default']),available[0]['id'] if available else '')

def hardware():
    memory=int(os.environ.get('WINDI_MEMORY_BYTES','0'))
    if not memory:
        try:memory=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],stderr=subprocess.DEVNULL,text=True))
        except (OSError,ValueError,subprocess.SubprocessError):pass
    return dict(memoryGB=round(memory/1024**3,1) if memory else None,cores=os.cpu_count(),architecture=platform.machine())

def catalog():
    from entitlements import status
    access=status()
    hw=hardware();free=shutil.disk_usage(ROOT).free
    result=[]
    for key,p in PROFILES.items():
        if key=='f5-private':continue  # Existing takes remain accessible; new Pro uses cloud.
        if key=='pro-cloud':
            result.append(dict(id=key,**{k:v for k,v in p.items() if k!='mode'},bytes=0,ready=True,supported=True,
                entitled=True,canDownload=False,cloud=True,hardwareNote='Trả theo cuốn · 5 lượt thử, tối đa 5.000 ký tự/lượt',voices=voices(key),revision=revision(key)))
            continue
        if key=='turbo' and not features.TURBO_ENABLED:continue
        if key=='clone-pro':
            if not features.PRO_MAX_ENABLED:continue
            result.append(dict(id=key,**{k:v for k,v in p.items() if k!='mode'},bytes=0,ready=ready(key),supported=True,
                entitled=True,canDownload=False,cloud=True,hardwareNote='Cần mạng khi tạo · Nghe audio đã tải không cần mạng',voices=voices(key),revision=revision(key)))
            continue
        # Show the Pro offer before activation only in editions that include F5.
        # This exposes metadata, never locked voice assets or generation access.
        if key=='f5-private' and not access.get('privateVoiceIncluded',access.get('privateVoiceAvailable')):continue
        data=manifest(key);size=sum(i['size'] for i in data['files']);installed=ready(key)
        supported=hw['architecture']=='arm64' and (hw['memoryGB'] is None or hw['memoryGB']>=p['minRAM'])
        recommendation='Phù hợp với máy này' if supported and hw['memoryGB'] is not None and hw['memoryGB']>=p['recommendedRAM'] else 'Nên dùng máy có RAM '+str(p['recommendedRAM'])+' GB trở lên'
        entitled=key in access['allowedModels']
        result.append(dict(id=key,entitled=entitled,**{k:v for k,v in p.items() if k not in ('manifest','mode')},bytes=size,ready=installed,supported=supported,
                           canDownload=entitled and key!='f5-private' and supported and free>=size+256*1024**2,localOnly=key=='f5-private',hardwareNote=recommendation,voices=voices(key) if entitled else [],revision=data['revision']))
    from clone_pro import config as credit_config
    return dict(models=result,hardware=hw,freeBytes=free,entitlement=access,credits=credit_config().get('wallet') if features.PRO_MAX_ENABLED else None)

def install(model_id,progress=lambda **kw:None,reuse=None):
    """Resumable download; a resource is visible only after SHA-256 verification."""
    features.require_local_model(model_id)
    from entitlements import require_model
    require_model(model_id)
    if model_id=='clone-pro':raise ValueError('Mở Pro Max để quản lý credit trong app; không cần tải model.')
    if model_id=='f5-private':raise ValueError('Gói giọng riêng chưa đầy đủ. Vui lòng cài lại gói giọng Pro đã nhận.')
    import urllib.request
    data=manifest(model_id);files=data['files'];total=sum(i['size'] for i in files)
    root=resource_root()/('tts-'+model_id)
    if reuse and all(verify(Path(reuse)/i['file'],i) for i in files):root=Path(reuse).resolve()
    else:
        root.mkdir(parents=True,exist_ok=True)
        remaining=sum(i['size'] for i in files if not verify(root/i['file'],i))
        if shutil.disk_usage(root).free<remaining+256*1024**2:raise ValueError('Không đủ dung lượng trống để tải model. Cần thêm khoảng '+str(round(remaining/1024**2)+256)+' MB.')
        done=0;last=0
        for item in files:
            target=root/item['file'];target.parent.mkdir(parents=True,exist_ok=True)
            if verify(target,item):
                done+=item['size'];progress(done=done,total=total,file=item['file'],phase='download');continue
            partial=target.with_suffix(target.suffix+'.download')
            offset=partial.stat().st_size if partial.exists() else 0
            if offset==item['size'] and verify(partial,item):
                partial.replace(target);done+=item['size'];progress(done=done,total=total,file=item['file'],phase='verify');continue
            if offset>=item['size']:partial.unlink();offset=0
            request=urllib.request.Request(item['url'],headers={'Range':f'bytes={offset}-','User-Agent':'WindiSachNoi/0.4'})
            with urllib.request.urlopen(request,timeout=45) as response:
                append=offset>0 and response.status==206 and response.headers.get('Content-Range','').startswith(f'bytes {offset}-')
                if response.status==206 and offset and not append:raise ValueError('Tải giọng đọc bị gián đoạn. Hãy bấm tải lại để tiếp tục.')
                with partial.open('ab' if append else 'wb') as out:
                    while block:=response.read(256*1024):
                        out.write(block)
                        if out.tell()>item['size']:raise ValueError('Tệp giọng đọc tải về bị lỗi. Hãy thử tải lại.')
                        if time.monotonic()-last>.15:
                            last=time.monotonic();progress(done=done+out.tell(),total=total,file=item['file'],phase='download')
            progress(done=done+item['size'],total=total,file=item['file'],phase='verify')
            if not verify(partial,item):
                partial.unlink(missing_ok=True)
                raise ValueError('Tệp giọng đọc tải về bị lỗi. Hãy thử tải lại.')
            partial.replace(target);done+=item['size']
    cfg=config();cfg.setdefault('profiles',{})[model_id]=str(root)
    if model_id=='nano':cfg.update(models=str(root),revision=data['revision'],readOnlyCache=bool(reuse and root==Path(reuse).resolve()))
    atomic_json(resource_root()/'config.json',cfg)
    progress(done=total,total=total,file='',phase='ready')
    return root

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',choices=list(PROFILES),required=True);parser.add_argument('--reuse-cache',type=Path);args=parser.parse_args()
    def emit(**event):print(json.dumps(event,ensure_ascii=False),flush=True)
    try:
        path=install(args.install,emit,args.reuse_cache);emit(installed=str(path),modelId=args.install)
    except Exception as error:
        print(repr(error),file=sys.stderr)
        emit(error=str(error) if isinstance(error,ValueError) else 'Chưa tải được gói giọng. Kiểm tra mạng rồi bấm tải lại; phần đã tải vẫn được giữ.');sys.exit(1)
