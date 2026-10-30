"""Conservative Vietnamese/English routing. Never rewrites stored text."""
import re
from pathlib import Path
import hashlib
import json
import wave
from core import signature,valid_audio,atomic_json

REVISION='vi-en-sentences-v1'
WORDS=set('the a an is are was were be been being this that these those it its of to in on at for from with by and or but not as if then than we you he she they my your their our his her have has had do does did will would can could should shall must may might i me us them who what where when why how which there here into about over under out up down so some any all no yes very more most such one two three said says say truth universally acknowledged hello world english language book chapter read reading life time people think never always'.split())

def language(text,override=None):
    if override in ('vi','en'):return override
    words=re.findall(r"[A-Za-zÀ-ỹĐđ]+(?:'[A-Za-z]+)?",text.casefold())
    if re.search('[à-ỹđ]',text.casefold()) or len(words)<3:return 'vi'
    hits=sum(w in WORDS for w in words)
    return 'en' if hits>=2 and hits/len(words)>=.35 else 'vi'

def parts(text):
    # Keep punctuation/whitespace and partition verbatim, including emoji.
    return [m.group() for m in re.finditer(r'.+?(?:[.!?]+[”’"\')\]]*(?:\s+|$)|\n+|$)',text,re.S)]

def cache_signature(book,text):
    if book.get('bilingual') and book.get('model','nano')=='nano':
        import model_manager as models
        rev=json.dumps([models.revision('nano'),models.revision('kitten'),REVISION,book.get('englishVoice','Jasper'),book.get('languageOverrides',{})],sort_keys=True)
        return signature(text,book['voice'],'nano',model_revision=rev)
    return signature(text,book['voice'],book.get('model','nano'),book.get('language','vi'))

def synthesize(worker,request,job,log):
    import model_manager as models
    for segment in request['segments']:
        if job['cancel'].is_set():return
        target=Path(segment['path']);yield dict(processingSegment=segment['id'])
        if not valid_audio(target):
            files=[]
            for text in parts(segment['text']):
                route=language(text,request.get('languageOverrides',{}).get(hashlib.sha256(text.encode()).hexdigest()))
                model='kitten' if route=='en' else 'nano';voice=request.get('englishVoice','Jasper') if route=='en' else request['voice']
                if not models.ready(model):raise ValueError('Tải Kitten tiếng Anh trong Quản lý giọng trước khi đọc Việt–Anh.')
                path=target.parent/(signature(text,voice,model)+'.wav')
                payload=dict(model=model,models=str(models.verified_location(model)),voice=voice,segments=[dict(id=segment['id'],text=text,path=str(path))])
                for result in worker.engine_results(payload,job,log):
                    if 'error' in result:raise ValueError(result['error'])
                if job['cancel'].is_set():return
                if not valid_audio(path):raise ValueError('Đoạn Việt–Anh chưa hoàn tất.')
                files.append(path)
            temp=target.with_suffix('.partial.wav')
            try:
                with wave.open(str(temp),'wb') as out:
                    out.setparams((1,2,24000,0,'NONE','not compressed'))
                    for path in files:
                        with wave.open(str(path),'rb') as src:
                            if src.getframerate()!=24000:raise ValueError('Tần số giọng Việt–Anh không khớp.')
                            while data:=src.readframes(65536):
                                if job['cancel'].is_set():return
                                out.writeframesraw(data)
                if job['cancel'].is_set():return
                if not valid_audio(temp):raise ValueError('Chưa tạo xong đoạn Việt–Anh.')
                temp.replace(target)
            finally:temp.unlink(missing_ok=True)
        with wave.open(str(target),'rb') as src:duration=src.getnframes()/src.getframerate()
        atomic_json(target.with_suffix('.json'),dict(model='nano',routing=REVISION,duration=duration))
        yield dict(segment=segment['id'],path=str(target),duration=duration)
