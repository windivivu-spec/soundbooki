"""Offline signed annual licenses. Consumer policy is pinned in the app bundle."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import os
import re
from functools import lru_cache
from core import atomic_json

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = 'windi-sach-noi-pro'
FREE = ('nano', 'kitten')
CREDIT_MODELS = ('clone-pro', 'pro-cloud')  # Per-book service authorizes every cloud job.

def release():
    path = ROOT / 'release.json'
    if not path.exists():
        return {'channel': 'development'}
    # A malformed consumer configuration must fail closed.
    try:
        data = json.loads(path.read_text())
        if not isinstance(data,dict) or data.get('channel') != 'consumer':
            return {'channel': 'consumer'}
        return data
    except (ValueError, OSError):
        return {'channel': 'consumer'}

def data_root():
    return Path(os.environ.get('WINDI_SACH_HOME', str(Path.home() / 'Library/Application Support/Windi Sach Noi/library'))).parent

@lru_cache(maxsize=1)
def device_code():
    try:
        result=subprocess.run([str(ROOT/'.build/windi-license'),'--device-code'],capture_output=True,timeout=5,check=True)
        code=json.loads(result.stdout)['deviceCode']
        if not re.fullmatch('SN[A-F0-9]{12}',code):raise ValueError()
        return code
    except (ValueError,KeyError,OSError,subprocess.SubprocessError):
        raise ValueError('Chưa đọc được mã máy để kiểm tra bản quyền.') from None

def decode_license(envelope, config=None, now=None):
    config = config if config is not None else release()
    pub_key = config.get('licensePublicKey', 'upviPkOPSvGhvo5vHL5K/7pj+Zg6sIjipXvvKszeSts=')
    try:
        payload, signature = envelope['payload'], envelope['signature']
        raw = base64.b64decode(payload, validate=True)
        if len(raw) > 8192 or len(base64.b64decode(signature, validate=True)) != 64:
            raise ValueError()
        result = subprocess.run([str(ROOT / '.build/windi-license'), pub_key, payload, signature],
                                capture_output=True, timeout=5, check=False)
        if result.returncode != 0 or json.loads(result.stdout).get('valid') is not True:
            raise ValueError()
        value = json.loads(raw)
        issued = datetime.fromisoformat(value['issuedAt'].replace('Z', '+00:00'))
        expires = datetime.fromisoformat(value['expiresAt'].replace('Z', '+00:00'))
        current = now or datetime.now(timezone.utc)
        if value['product'] != PRODUCT or value['schema'] not in (1,2) or not value['orderId']:
            raise ValueError()
        if value['schema']==2:
            if value['deviceCode']!=device_code():raise ValueError()
        elif not value.get('email') or config.get('licenseMode')=='device':raise ValueError()
        if issued > current or expires <= current or expires <= issued:
            raise ValueError()
        return value
    except (KeyError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        raise ValueError('Bản quyền không hợp lệ hoặc đã hết hạn. Kiểm tra lại bản quyền với đúng mã máy.') from None

def status():
    config = release()
    if config.get('channel') == 'development':
        return dict(tier='development', label='Bản dùng thử', allowedModels=[*FREE, 'turbo', 'f5-private', *CREDIT_MODELS], privateVoiceAvailable=True, privateVoiceIncluded=True, checkoutURL='')
    value = None
    try:code=device_code()
    except ValueError:code=''
    try:
        value = decode_license(json.loads((data_root() / 'license.json').read_text()), config)
    except (ValueError, OSError):
        pass
    private_voice=value is not None and config.get('privateVoiceAvailable') is not False
    allowed=([*FREE, 'turbo']+(['f5-private'] if private_voice else []) if value else list(FREE))+list(CREDIT_MODELS)
    return dict(tier='pro' if value else 'free', label='Pro' if value else 'Free',
                allowedModels=allowed,
                email=value.get('email','') if value else '', deviceCode=code, expiresAt=value['expiresAt'] if value else None,
                checkoutURL=config.get('checkoutURL', ''), priceVND=189000, period='year',
                licenseBaseURL=config.get('licenseBaseURL',''),
                privateVoiceAvailable=private_voice,privateVoiceIncluded=config.get('privateVoiceAvailable') is not False)

def require_model(model_id):
    if model_id not in status()['allowedModels']:
        if model_id == 'f5-private':
            raise ValueError('Giọng riêng cần bản Pro còn hạn (189.000đ/năm).')
        raise ValueError('VieNeu Turbo cần bản Pro còn hạn (189.000đ/năm). Bạn vẫn có thể dùng Nano và tiếng Anh miễn phí.')

def install(path):
    path = Path(path)
    if path.stat().st_size > 16384:
        raise ValueError('Tệp bản quyền quá lớn.')
    envelope = json.loads(path.read_text())
    return install_envelope(envelope)

def install_envelope(envelope,after_expires_at=None):
    value=decode_license(envelope)
    if after_expires_at is not None:
        try:
            baseline=datetime.fromisoformat(after_expires_at.replace('Z','+00:00'))
            if baseline.tzinfo is None:raise ValueError()
        except (ValueError,TypeError,AttributeError):
            raise ValueError('Chưa kiểm tra được lần gia hạn. Hãy mở lại cửa sổ thanh toán.') from None
        if datetime.fromisoformat(value['expiresAt'].replace('Z','+00:00'))<=baseline:return None
    atomic_json(data_root() / 'license.json', envelope)
    return status()
