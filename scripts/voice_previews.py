#!/usr/bin/env python3
"""Prepare short demos for already-installed models. Never downloads weights."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import model_manager as models
from core import valid_audio
from voice_previews import request

for model in ('kitten','nano','turbo'):
    if not models.ready(model):continue
    rows=[]
    for voice in models.voices(model):
        text,path=request(model,voice['id'],'en' if model=='kitten' else 'vi')
        path.parent.mkdir(parents=True,exist_ok=True)
        if not valid_audio(path):rows.append(dict(id=voice['id'],text=text,path=str(path)))
    payload=dict(model=model,models=str(models.verified_location(model)),voice='',segments=[])
    # Engine inference is one voice per request, retaining its existing contract.
    # Explicit development preparation happens once; cached samples ship as assets.
    for s in rows:
        payload.update(voice=s['id'],segments=[s])
        with (s_path:=Path(s['path']).parent/'engine.log').open('ab') as log:
            p=subprocess.run([sys.executable,'-B',str(ROOT/'backend/engine.py')],input=json.dumps(payload,ensure_ascii=False),stdout=subprocess.PIPE,stderr=log,text=True)
        if p.returncode or not valid_audio(s['path']):raise RuntimeError(p.stdout)
        print(json.dumps(dict(model=model,voice=s['id'],ready=True),ensure_ascii=False),flush=True)
    print(json.dumps(dict(model=model,total=len(models.voices(model)),result='PASS')),flush=True)
