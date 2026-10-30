"""Import user-selected demo recordings into project-local PCM music assets."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import wave
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main(paths):
    dest=ROOT/'assets/music';dest.mkdir(parents=True,exist_ok=True)
    manifest=dest/'demo-catalog.json';entries=json.loads(manifest.read_text()) if manifest.exists() else []
    items=[]
    for index,name in enumerate(paths,1):
        source=Path(name);digest=hashlib.sha256(source.read_bytes()).hexdigest();bid='demo-'+digest[:12]
        label=re.sub(r'\s*\(\d+\)$','',source.stem)+f' · Bản {index}'
        target=dest/(bid+'.wav')
        with tempfile.TemporaryDirectory(prefix='music-import-',dir=dest) as temp:
            raw=Path(temp)/'decoded.wav'
            subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16@24000','-c','1',str(source),str(raw)],check=True,capture_output=True)
            with wave.open(str(raw),'rb') as w:
                if w.getnchannels()!=1 or w.getframerate()!=24000 or w.getsampwidth()!=2:raise ValueError('Định dạng nhạc chưa phù hợp.')
                audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
            if len(audio)<48000:raise ValueError('Nhạc nền cần dài ít nhất hai giây.')
            peak=float(np.max(np.abs(audio)))
            if peak<.0001:raise ValueError('Bài nhạc không có tiếng hợp lệ.')
            audio*=.5/peak
            fade=min(16800,len(audio)//4);ramp=np.linspace(0,1,fade);audio[:fade]*=ramp;audio[-fade:]*=ramp[::-1]
            ready=Path(temp)/'ready.wav'
            with wave.open(str(ready),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(np.rint(audio*32767).astype('<i2').tobytes())
            ready.replace(target)
        duration=len(audio)/24000
        item=dict(id=bid,title=label,description=f'Nhạc demo bạn cung cấp · {int(duration)//60}:{int(duration)%60:02d}',file=target.name,duration=duration,origin='user-demo',sourceFile=source.name,sourceSHA256=digest)
        entries=[e for e in entries if e['id']!=bid];entries.append(item);items.append(item)
    manifest.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
    import music
    music.main()
    print(json.dumps(items,ensure_ascii=False,indent=2))
if __name__=='__main__':
    if len(sys.argv)<2:raise SystemExit('Chọn đường dẫn nhạc để nhập.')
    main(sys.argv[1:])
