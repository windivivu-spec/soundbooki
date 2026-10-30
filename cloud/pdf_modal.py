"""Unpublished, owner-authenticated PDF processing service. No deployment on import."""
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[1]
app=modal.App('windi-book-pdf')

def cache_models():
    import subprocess
    subprocess.run(['docling-tools','models','download'],check=True)

image=(modal.Image.debian_slim(python_version='3.12')
    .apt_install('tesseract-ocr','tesseract-ocr-vie','tesseract-ocr-eng','libgl1','libglib2.0-0')
    .pip_install('docling>=2.70,<3','fastapi>=0.115,<1')
    .run_function(cache_models)
    .add_local_file(ROOT/'cloud/pdf_processing.py','/root/pdf_processing.py'))

@app.function(image=image,gpu='L4',timeout=180,memory=8192,max_containers=1,scaledown_window=60)
@modal.fastapi_endpoint(method='POST',requires_proxy_auth=True)
def process(request:dict):
    import base64,hashlib,tempfile
    from fastapi import HTTPException
    from pdf_processing import process_pdf,MAX_BYTES
    encoded=request.get('pdf_b64','')
    if not isinstance(encoded,str) or len(encoded)>(MAX_BYTES+2)//3*4:raise HTTPException(413,'PDF too large')
    try:raw=base64.b64decode(encoded,validate=True)
    except ValueError:raise HTTPException(400,'Invalid PDF encoding')
    if not 0<len(raw)<=MAX_BYTES or hashlib.sha256(raw).hexdigest()!=request.get('sourceSHA256'):raise HTTPException(400,'Source hash mismatch')
    # Ephemeral container file only. No book content in logs or persistent volumes.
    with tempfile.TemporaryDirectory(prefix='book-pdf-') as temp:
        path=Path(temp)/'selected.pdf';path.write_bytes(raw)
        return process_pdf(path,request.get('language','vi'))
