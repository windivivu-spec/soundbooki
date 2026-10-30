#!/usr/bin/env python3
"""Owner-only explicit selected-PDF upload. Never ship merchant keys in the app."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.parse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from book_cloud import NoRedirect
from core import atomic_json

def upload(path,output,language,consent=False):
    if consent is not True:raise ValueError('Explicit selected-file upload is required')
    endpoint=os.environ['WSN_PDF_PROCESS_URL'];url=urllib.parse.urlsplit(endpoint)
    if url.scheme!='https' or not url.hostname or not url.hostname.endswith('.modal.run') or url.username or url.password or url.fragment or url.query:raise ValueError('Select the authenticated HTTPS PDF service')
    path=Path(path)
    if path.suffix.lower()!='.pdf' or not 0<path.stat().st_size<=25*1024*1024:raise ValueError('Select one PDF up to 25 MiB')
    raw=path.read_bytes()
    if not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF')
    digest=hashlib.sha256(raw).hexdigest()
    body=json.dumps(dict(pdf_b64=base64.b64encode(raw).decode(),sourceSHA256=digest,language=language)).encode()
    request=urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json','Modal-Key':os.environ['WSN_MODAL_PROXY_KEY'],'Modal-Secret':os.environ['WSN_MODAL_PROXY_SECRET']},method='POST')
    # A timeout is uncertain work; no automatic paid retry.
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=185) as response:
        data=response.read(20_000_001)
    if len(data)>20_000_000:raise ValueError('PDF result exceeds limit')
    result=json.loads(data)
    if result.get('revision')!='docling-pdf-v1' or result.get('sourceSHA256')!=digest or result.get('requiresReview') is not True or not isinstance(result.get('pages'),list):raise ValueError('PDF review result does not match the selected book')
    atomic_json(output,result)
    return dict(output=str(output),pages=len(result['pages']),requiresReview=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pdf',required=True);p.add_argument('--output',required=True);p.add_argument('--language',choices=['vi','en'],default='vi');p.add_argument('--allow-upload',action='store_true',required=True)
    a=p.parse_args();print(json.dumps(upload(a.pdf,a.output,a.language,a.allow_upload),ensure_ascii=False))
