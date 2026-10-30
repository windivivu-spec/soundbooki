"""Prepare folder-based music for local playback; never modify originals/upload."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import unicodedata
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def prepare():
    dest=ROOT/'assets/music';prepared=dest/'prepared';prepared.mkdir(exist_ok=True)
    entries=[]
    folders=sorted(p for p in dest.iterdir() if p.is_dir() and p.name!='prepared' and not p.name.startswith('.'))
    for folder in folders:
        category=unicodedata.normalize('NFC',folder.name)
        for source in sorted(folder.iterdir()):
            if not source.is_file() or source.suffix.lower() not in ('.mp3','.m4a','.wav','.aac','.aif','.aiff'):continue
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            bid='music-'+hashlib.sha256((category+'\0'+source.name+'\0'+digest).encode()).hexdigest()[:16]
            target=prepared/(bid+'.wav')
            if not target.exists():
                with tempfile.TemporaryDirectory(dir=prepared) as tmp:
                    raw=Path(tmp)/'decoded.wav'
                    decoded=subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16@24000','-c','1',str(source),str(raw)],capture_output=True)
                    if decoded.returncode:
                        # Some supplied M4A codecs are not supported by AudioToolbox.
                        # This is a development preparation tool, no ffmpeg is bundled.
                        ffmpeg=shutil.which('ffmpeg')
                        if not ffmpeg:raise ValueError('Cần ffmpeg để chuẩn bị bài: '+str(source))
                        subprocess.run([ffmpeg,'-v','error','-y','-i',str(source),'-ac','1','-ar','24000','-c:a','pcm_s16le',str(raw)],check=True,capture_output=True)
                    with wave.open(str(raw),'rb') as w:
                        if w.getnchannels()!=1 or w.getframerate()!=24000 or w.getsampwidth()!=2:raise ValueError('Unsupported decoded music: '+str(source))
                        audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
                    peak=float(np.max(np.abs(audio))) if len(audio) else 0
                    if peak<.0001 or len(audio)<48000:raise ValueError('Empty/short music: '+str(source))
                    audio*=.5/peak
                    ramp=np.linspace(0,1,min(2400,len(audio)//4));audio[:len(ramp)]*=ramp;audio[-len(ramp):]*=ramp[::-1]
                    ready=Path(tmp)/'ready.wav'
                    with wave.open(str(ready),'wb') as w:
                        w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(np.rint(audio*32767).astype('<i2').tobytes())
                    ready.replace(target)
            with wave.open(str(target),'rb') as w:duration=w.getnframes()/w.getframerate()
            title=f'Bài {int(source.stem):02d}' if source.stem.isdigit() else unicodedata.normalize('NFC',source.stem)
            entries.append(dict(id=bid,title=title,category=category,description=category,file=str(target.relative_to(dest)),duration=duration,origin='user-library',sourceFile=str(source.relative_to(dest)),sourceSHA256=digest))
    (dest/'library-catalog.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
    return entries

if __name__=='__main__':print(f'Prepared {len(prepare())} local music tracks; originals preserved.')
