"""App credit wallet client. Merchant Clone Pro credentials never enter the app."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from core import atomic_json, valid_audio
from features import require_pro_max

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'clone-pro'
REVISION = 'clone-pro-2.1-sonic-3.6-speed1-pcm48-v1'
# Customer wallet service is separate from the Clone Pro web account.
def service_url():
    require_pro_max()
    from entitlements import release
    value=release().get('creditsBaseURL','').rstrip('/')
    url=urllib.parse.urlsplit(value)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Dịch vụ credit trong app chưa được cấu hình. Giá gói sẽ được công bố sau.')
    return value


def credential(action):
    require_pro_max()
    payload = dict(action=action)
    try:
        p = subprocess.run([str(ROOT/'.build/windi-cloud-keychain')], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=30, check=True)
        return json.loads(p.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ValueError('Chưa truy cập được ví credit trong Keychain. Hãy mở khóa Mac rồi thử lại.') from None


def config_path():
    from entitlements import data_root
    return data_root()/'clone-pro.json'


def config():
    try:
        value = json.loads(config_path().read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError): return {}


def voices():
    return config().get('voices', [])


def connected():
    return config().get('connected') is True and bool(voices())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class Client:
    def __init__(self, token, api=None):
        if not re.fullmatch(r'wsn_credit_[a-f0-9]{64}', token):
            raise ValueError('Thông tin ví credit không hợp lệ.')
        self.token = token
        self.api = (api or service_url()).rstrip('/')
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, path, body=None, key=None, audio=False):
        require_pro_max()
        headers = {'Authorization':'Bearer '+self.token, 'Accept':'application/json'}
        if key: headers['Idempotency-Key'] = key
        if body is not None: headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.api+path, headers=headers,
            data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
        try:
            try: response = self.opener.open(req, timeout=125)
            except urllib.error.HTTPError as error:
                if audio and error.code == 307:
                    location = urllib.parse.urljoin(self.api, error.headers.get('Location', ''))
                    url = urllib.parse.urlsplit(location)
                    error.close()
                    if url.scheme != 'https' or not url.hostname or url.username or url.password:
                        raise ValueError('Địa chỉ tải audio không hợp lệ.')
                    # Signed download URL: never forward the Windi bearer token.
                    response = self.opener.open(urllib.request.Request(location), timeout=60)
                else:
                    code = error.code; error.close()
                    message = {401:'Chưa xác thực được ví credit của app.',
                        403:'Ví credit chưa có quyền tạo sách.',
                        402:'Không đủ credit trong app. Mở Pro Max để mua thêm.',
                        429:'Đang giới hạn lượt gọi. Hãy thử tiếp sau.'}.get(code,
                        'Clone Pro 2.1 chưa trả kết quả. Bấm tạo tiếp để kiểm tra cùng yêu cầu; credit đang chờ được giữ theo cùng mã yêu cầu.')
                    raise ValueError(message)
            with response:
                limit = 64*1024*1024 if audio else 4*1024*1024
                data = response.read(limit+1)
                if len(data)>limit: raise ValueError('Kết quả Clone Pro 2.1 vượt giới hạn cho một đoạn.')
                if audio: return data
                value = json.loads(data)
                if not isinstance(value, dict): raise ValueError('Phản hồi Clone Pro 2.1 không hợp lệ.')
                return value
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ValueError('Kết nối Clone Pro 2.1 gián đoạn. Bấm tạo tiếp để kiểm tra cùng yêu cầu; credit đang chờ được giữ theo cùng mã yêu cầu.') from None

    def list_voices(self):
        result=[];cursor='';seen=set()
        for _ in range(50):
            page=self.request('/api/v1/voice/voices'+('?cursor='+urllib.parse.quote(cursor, safe='') if cursor else ''))
            for v in page.get('data',[]):
                if not isinstance(v,dict): continue
                try: vid=str(uuid.UUID(v.get('id','')))
                except (ValueError, TypeError, AttributeError): continue
                if vid in seen: continue
                seen.add(vid)
                result.append(dict(id=vid,label=str(v.get('name') or 'Giọng Clone Pro 2.1')[:200],
                    language=v.get('language','vi'),aliases=[],default=not result))
            if not page.get('has_more'): return result
            next_cursor=page.get('next_page')
            if not isinstance(next_cursor,str) or not next_cursor or next_cursor==cursor: break
            cursor=next_cursor
        raise ValueError('Danh sách giọng chưa tải đủ. Hãy kết nối lại.')


def refresh_wallet(refresh_voices=True):
    # Resolve service configuration before creating a wallet on this Mac.
    api=service_url()
    secret=credential('create')['token']
    client=Client(secret,api)
    wallet=client.request('/api/credits/wallet',{})
    items=client.list_voices() if refresh_voices or not voices() else voices()
    preferred=next((v for v in items if v['id']=='094e72c3-97d3-439a-9e64-39ac3d3fa897'),items[0] if items else None)
    for v in items:v['default']=v is preferred
    atomic_json(config_path(),dict(connected=True,voices=items,wallet=wallet))
    return wallet


def purchase_credits(pack,key):
    if not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Mã mua credit không hợp lệ.')
    client=Client(credential('read')['token'])
    order=client.request('/api/credits/topups',dict(packId=pack),key=key)
    cfg=config();cfg['pendingOrder']=order;atomic_json(config_path(),cfg)
    return order


def generate_segment(client, segment, voice, language):
    """Journal before POST; reuse the server idempotency key after every failure."""
    target=Path(segment['path'])
    if valid_audio(target): return
    state_path=target.with_suffix('.remote.json')
    key=hashlib.sha256((str(target.resolve())+'\0'+REVISION+'\0'+voice+'\0'+language+'\0'+segment['text']).encode()).hexdigest()
    fingerprint=hashlib.sha256(client.token.encode()).hexdigest()
    state=json.loads(state_path.read_text()) if state_path.exists() else dict(key=key,credential=fingerprint)
    if state.get('base',state.get('key'))!=key: raise ValueError('Nội dung yêu cầu đã đổi. Hãy chọn lại giọng và tạo lại.')
    if state.get('status')=='failed' and state.get('id') and state.get('credential')==fingerprint:
        # A new explicit user confirmation may retry a known refunded failure.
        # Unknown/interrupted requests always keep their original key.
        history=state.get('history',[])+[dict(id=state['id'],key=state['key'])]
        state=dict(base=key,key=hashlib.sha256((key+uuid.uuid4().hex).encode()).hexdigest(),credential=fingerprint,history=history)
    if not state.get('id') and state.get('credential')!=fingerprint:
        raise ValueError('Yêu cầu trước đang chờ kết quả với ví credit trước. Dùng lại ví credit trước để tránh tạo trùng.')
    atomic_json(state_path,state)
    if state.get('id'):
        job=client.request('/api/v1/voice/generations/'+str(uuid.UUID(state['id'])))
    else:
        job=client.request('/api/v1/voice/generations',dict(text=segment['text'],voice_id=voice,language=language,speed=1),key=state['key'])
        state['id']=str(uuid.UUID(job['id']));atomic_json(state_path,state)
    for _ in range(40):
        state['status']=job.get('status');atomic_json(state_path,state)
        if job.get('status')=='ready': break
        if job.get('status') not in ('reserved','pending'):
            raise ValueError('Lượt tạo đang cần kiểm tra trên Clone Pro 2.1 ('+str(job.get('status'))+'). App giữ mã yêu cầu và không tạo lượt mới.')
        time.sleep(3)
        job=client.request('/api/v1/voice/generations/'+state['id'])
    else: raise ValueError('Lượt tạo vẫn đang xử lý. Bấm tạo tiếp sau để lấy kết quả cùng yêu cầu.')
    mp3=target.with_suffix('.partial.mp3');wav=target.with_suffix('.partial.wav')
    try:
        mp3.write_bytes(client.request('/api/v1/voice/generations/'+state['id']+'/audio',audio=True))
        wav.unlink(missing_ok=True)
        subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16@48000','-c','1',str(mp3),str(wav)],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=60)
        if not valid_audio(wav): raise ValueError('Audio Clone Pro 2.1 chưa hợp lệ.')
        wav.replace(target)
    except subprocess.SubprocessError:
        raise ValueError('Chưa chuyển được audio Clone Pro 2.1. Bấm tạo tiếp để tải lại kết quả đã có.') from None
    finally:
        mp3.unlink(missing_ok=True);wav.unlink(missing_ok=True)


def main(request):
    require_pro_max()
    from engine import emit
    if request.get('cloudConfirmed') is not True: raise ValueError('Xác nhận gửi phần chữ đã chọn và dùng credit trước khi tạo.')
    client=Client(credential('read')['token'])
    for segment in request['segments']:
        generate_segment(client,segment,request['voice'],request['language'])
        emit(dict(segment=segment['id'],path=segment['path'],model=MODEL))


if __name__=='__main__':
    import sys
    from engine import emit
    try: main(json.load(sys.stdin))
    except Exception as error:
        emit({'error':str(error) if isinstance(error,ValueError) else 'Chưa nhận được audio Clone Pro 2.1. Bấm tạo tiếp để kiểm tra cùng yêu cầu.'})
        sys.exit(1)
