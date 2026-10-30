"""Explicit launch-combo actions. A local display cache never grants book rights."""
from datetime import datetime,timezone
import json
import re
from core import atomic_json

OFFER_ID='launch-combo-v1'
STARTS_AT='2026-10-21T17:00:00Z'
ENDS_AT='2026-11-01T17:00:00Z'


def policy(now=None):
    now=now or datetime.now(timezone.utc)
    start=datetime.fromisoformat(STARTS_AT.replace('Z','+00:00'))
    end=datetime.fromisoformat(ENDS_AT.replace('Z','+00:00'))
    return dict(id=OFFER_ID,active=start<=now<end,amountVND=50000,books=5,
                endsAt=ENDS_AT,serverTime=now.isoformat())


def path(lib):return lib.root.parent/'launch-combo-state.json'


def cached_at(root):
    try:
        state=json.loads((root.parent/'launch-combo-state.json').read_text())
        return state if isinstance(state,dict) else {}
    except (OSError,ValueError):return {}

def cached(lib):return cached_at(lib.root)

def save(lib,result,request_key=None):
    with lib.lock:
        state=cached(lib)
        old=state.get('bundle');new=result.get('bundle')
        if isinstance(old,dict) and isinstance(new,dict) and old.get('id') and old.get('id')==new.get('id') and old.get('used',0)>new.get('used',0):
            result={**result,'bundle':old}
        state.update({k:result[k] for k in ('offer','bundle','order','bank','available') if k in result})
        if request_key:state['requestKey']=request_key
        atomic_json(path(lib),state)
    return result


def local_info(lib):
    from book_cloud import endpoint
    state=cached(lib)
    return dict(offer=policy(),bundle=state.get('bundle'),order=state.get('order'),bank=state.get('bank'),
                pendingRequestKey=state.get('requestKey'),configured=bool(endpoint()),available=state.get('available',False))


def refresh(lib):
    from book_cloud import Client,endpoint
    if not endpoint():return local_info(lib)
    result=save(lib,Client().post('bundle-status'))
    return dict(**result,configured=True,pendingRequestKey=cached(lib).get('requestKey'))


def quote(lib,key):
    from book_cloud import Client
    if not re.fullmatch('[a-f0-9]{32}',str(key)):raise ValueError('Yêu cầu combo không hợp lệ.')
    # Durable key before transport: closing/reopening cannot create another payment.
    with lib.lock:
        state=cached(lib);state['requestKey']=key;atomic_json(path(lib),state)
    return save(lib,Client().post('bundle-quote',requestKey=key),key)
