"""Explicit initial setup only: install pinned private resources; never invoked by inference."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from model_manager import manifest, verify


def _sha256_and_size(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest(), path.stat().st_size


def install():
    data=manifest('f5-private')
    previous_files=data['files']
    root=ROOT/'.resources/tts-f5-private';root.mkdir(parents=True,exist_ok=True)
    source=ROOT/'training/f5/artifacts/voice-001'
    mappings={'model.pt':'vi_f5_tts_private_fp16.pt','vocab.txt':'vocab.txt',
              'ref_audio.wav':'ref_audio.wav','ref_text.txt':'ref_text.txt'}
    base_files=[item for item in data['files'] if not item['file'].startswith('voices/')]
    for item in base_files:
        target=root/item['file']
        if verify(target,item):continue
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix(target.suffix+'.download')
        if item['file'].startswith('vocos/'):
            url='https://huggingface.co/charactr/vocos-mel-24khz/resolve/'+data['vocoderRevision']+'/'+target.name
            with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as out:shutil.copyfileobj(response,out)
        else:
            path=source/mappings[item['file']]
            if path.exists():shutil.copyfile(path,temp)
            elif item['file'] in ('ref_audio.wav','ref_text.txt'):
                with tarfile.open(source/'vi_f5_prepared_dataset.tar.gz') as archive:
                    with archive.extractfile('outputs/'+item['file']) as stream,temp.open('wb') as out:shutil.copyfileobj(stream,out)
            else:raise ValueError('Thiếu bản model riêng: '+str(path))
        if not verify(temp,item):
            temp.unlink(missing_ok=True)
            raise ValueError('Checksum không đúng: '+item['file'])
        temp.replace(target)

    extra_entries=[]
    artifacts_root=ROOT/'training/f5/artifacts'
    for v_src in sorted(artifacts_root.glob('voice-*')):
        vid=v_src.name
        if vid in data.get('excludedVoices',[]) or vid=='voice-001' or not (v_src/'vi_f5_tts_private_fp16.pt').is_file():
            continue
        v_dst=root/'voices'/vid;v_dst.mkdir(parents=True,exist_ok=True)
        for dst_name,src_name in mappings.items():
            p=v_src/src_name
            if p.is_file():
                tmp=v_dst/(dst_name+'.download');shutil.copyfile(p,tmp);tmp.replace(v_dst/dst_name)
                sha,sz=_sha256_and_size(v_dst/dst_name)
                extra_entries.append(dict(file=f'voices/{vid}/{dst_name}',size=sz,sha256=sha))
        if (v_src/'voice_manifest.json').is_file():
            shutil.copyfile(v_src/'voice_manifest.json',v_dst/'voice_manifest.json')

    data['files']=base_files+extra_entries
    vids=[Path(i['file']).parent.name.replace('-','') if i['file']!='model.pt' else 'voice001' for i in data['files'] if i['file']=='model.pt' or i['file'].endswith('/model.pt')]
    data['revision']='local-'+'-'.join(vids)+'-fp16-v3'
    if data['files']!=previous_files:data['inferenceRevision']=data['revision']
    (ROOT/'backend/models-f5-private.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'Giọng riêng đã được cài và xác minh trên máy ({len(vids)} giọng: {", ".join(vids)}).')


if __name__=='__main__':install()
