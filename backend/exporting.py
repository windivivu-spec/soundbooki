"""Streaming narration/music mix and Mac AAC export; no network."""
import html
import json
from pathlib import Path
import subprocess
import tempfile
import wave
import zipfile
from music import music_settings, music_playlist
from scopes import selected_indices

class ExportCancelled(ValueError):pass

class MusicBed:
    """Read a stable playlist timeline, loading only the currently needed track."""
    def __init__(self,settings,sample_rate):
        self.items=music_playlist(settings);self.rate=sample_rate;self.loop=settings.get('loop',True)
        self.lengths=[];self.cached_index=None;self.cached=None
        for item in self.items:
            with wave.open(item['path'],'rb') as w:
                if w.getnchannels()!=1 or w.getsampwidth()!=2 or not w.getnframes():raise ValueError('Bài nhạc chưa sẵn sàng. Hãy chọn lại nhạc nền.')
                self.lengths.append(round(w.getnframes()*sample_rate/w.getframerate()))
        self.total=sum(self.lengths)
    def read(self,start,count):
        import numpy as np
        out=np.zeros(count,dtype=np.float32);written=0
        while written<count and self.total:
            pos=start+written
            if pos>=self.total and not self.loop:break
            pos%=self.total;idx=0
            while pos>=self.lengths[idx]:pos-=self.lengths[idx];idx+=1
            if self.cached_index!=idx:
                with wave.open(self.items[idx]['path'],'rb') as w:
                    self.cached=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
                    if w.getframerate()!=self.rate:
                        import soxr
                        self.cached=soxr.resample(self.cached,w.getframerate(),self.rate)
                self.cached_index=idx
            n=min(count-written,self.lengths[idx]-pos)
            out[written:written+n]=self.cached[pos:pos+n];written+=n
        return out

def mix_wav(paths,destination,settings,progress=lambda a,b:None,cancelled=lambda:False,music_offset=0,sample_rate=24000):
    import numpy as np
    settings=music_settings(settings)
    bed=MusicBed(settings,sample_rate) if settings['track']!='none' and settings['volume']>0 else None
    total=0
    for path in paths:
        with wave.open(str(path),'rb') as w:
            if w.getframerate()!=sample_rate:raise ValueError('Tần số audio không khớp model đang chọn. Hãy tạo lại đoạn này.')
            total+=w.getnframes()
    if total*2+44>0xffffffff:raise ValueError('File vượt giới hạn WAV 4 GB. Hãy xuất từng chương hoặc khoảng trang nhỏ hơn.')
    done=0;offset=int(music_offset)
    with wave.open(str(destination),'wb') as out:
        out.setparams((1,2,sample_rate,0,'NONE','not compressed'))
        for path in paths:
            with wave.open(str(path),'rb') as src:
                while data:=src.readframes(65536):
                    if cancelled():raise ExportCancelled('Đã hủy xuất audio.')
                    count=len(data)//2
                    if bed is not None:
                        voice=np.frombuffer(data,dtype='<i2').astype(np.float32)/32768
                        frame=np.arange(count)+done
                        fade=np.minimum(1,np.minimum(frame/(sample_rate*.7),(total-1-frame)/(sample_rate*.7)))
                        background=bed.read(done+offset,count)*settings['volume']*np.clip(fade,0,1)
                        mixed=np.clip(voice*.94+background,-1,32767/32768)
                        data=np.rint(mixed*32768).astype('<i2').tobytes()
                    out.writeframesraw(data);done+=count
                    progress(done,total)
    return total/sample_rate

def portable_page(title,segments,durations,unit_label='Trang',language='vi'):
    data=[];offset=0
    for s,d in zip(segments,durations):
        data.append(dict(title=f"{unit_label} {s['page']+1} · {"Segment" if language=="en" else "Đoạn"} {s['index']+1}",seconds=offset,text=s['text']));offset+=d
    # JSON is an external file, never inserted as executable source or raw HTML.
    markup='''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>__TITLE__</title><link rel="stylesheet" href="player.css"></head><body><main><p class="brand">Windi Sách Nói</p><h1>__TITLE__</h1><p>Nghe ở đây hoặc tải audio về thiết bị của bạn.</p><audio id="audio" controls preload="metadata" src="audio.m4a"></audio><div class="actions"><label>Tốc độ <select id="speed"><option value=".75">0,75×</option><option value="1" selected>1×</option><option value="1.25">1,25×</option><option value="1.5">1,5×</option><option value="2">2×</option></select></label><a href="audio.m4a" download>Tải audio có nhạc nền</a></div><p id="notice" role="status"></p><nav id="chapters" aria-label="Các đoạn đọc"></nav><article id="text"></article><small>Vị trí nghe được lưu trên trình duyệt này. Trang không gửi dữ liệu đến dịch vụ khác.</small></main><script src="book.js"></script><script src="player.js"></script></body></html>'''
    css='''body{font:16px/1.7 system-ui;margin:0;background:#f2f5fa;color:#202a39}main{max-width:740px;margin:auto;padding:36px 22px}h1{font-size:clamp(25px,5vw,38px);line-height:1.2;overflow-wrap:anywhere}.brand{color:#4375b8;font-weight:600}audio{width:100%;margin:15px 0}.actions{display:flex;gap:20px;align-items:center;flex-wrap:wrap}select{font:inherit;padding:5px;border-radius:7px}a{color:#2968bf}nav{display:flex;gap:8px;overflow:auto;margin:25px 0}button{font:inherit;font-size:13px;white-space:nowrap;border:1px solid #bdcde3;background:transparent;border-radius:9px;padding:8px 11px;color:inherit;cursor:pointer}button[aria-current=true]{background:#3779d5;color:white}article{white-space:pre-wrap;border-top:1px solid #b5c4d733;padding-top:20px;min-height:110px}small{display:block;color:#667387;margin-top:35px}button:focus-visible,a:focus-visible{outline:3px solid #4389e8;outline-offset:3px}@media(prefers-color-scheme:dark){body{background:#18202c;color:#ecf1f9}a{color:#83b4f8}small{color:#a2b0c5}}'''
    js=(Path(__file__).resolve().parents[1]/'ui/web-player.js').read_text()
    if language=='en':
        replacements={'lang="vi"':'lang="en"','Nghe ở đây hoặc tải audio về thiết bị của bạn.':'Listen here or download the audio to your device.','Tốc độ':'Speed','Tải audio có nhạc nền':'Download audio with background music','Các đoạn đọc':'Reading segments','Vị trí nghe được lưu trên trình duyệt này. Trang không gửi dữ liệu đến dịch vụ khác.':'Listening progress is saved in this browser. This page does not send data to other services.'}
        for before,after in replacements.items():markup=markup.replace(before,after)
    markup=markup.replace('__TITLE__',html.escape(title))
    manifest=json.dumps(dict(schema=1,title=title,language=language,segments=data),ensure_ascii=False,indent=2)
    script='window.windiBook='+manifest.replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')+';\n'
    return {'index.html':markup,'player.css':css,'player.js':js,'book.json':manifest,'book.js':script}

def export_book(lib,bid,destination,scope=None,progress=lambda a,b:None,cancelled=lambda:False,process=lambda p:None,take_id=None):
    take=None
    with lib.lock:
        b=lib.load(bid)
        if take_id:
            from audiobooks import find,path as take_path
            take=find(b,take_id);segments=take['segments'];paths=[take_path(lib,bid,s) for s in segments]
            indices=[s['index'] for s in segments];model_id=take['model'];language=take['language'];title=b['title']+' — '+take['title']
        else:
            indices=selected_indices(b,scope);segments=[b['segments'][i]|{'index':i} for i in indices]
            paths=[lib.audio_path(b,s) for s in segments];model_id=b.get('model','nano');language=b.get('language','vi');title=b['title']
        if not indices:raise ValueError('Phạm vi này chưa có đoạn chữ để xuất.')
        if not take_id and (scope or {}).get('type','all')=='all' and b['status']!='ready':raise ValueError('Cần trích chữ xong trước khi xuất cả sách.')
        from core import valid_audio
        if not all(valid_audio(p) for p in paths):raise ValueError('Hãy tạo đủ giọng đọc trong phạm vi đang chọn trước khi tải về.')
        settings=music_settings(b.get('music'))
        from model_manager import profile
        rate=profile(model_id)['sampleRate']
        music_offset=0
        for s in ([] if take_id else b['segments'][:indices[0]]):
            p=lib.audio_path(b,s)
            if valid_audio(p):
                with wave.open(str(p),'rb') as w:music_offset+=w.getnframes()
    dest=Path(destination);ext=dest.suffix.lower()
    if ext not in ('.mp3','.wav','.m4a','.m4b','.zip'):raise ValueError('Chọn MP3, M4A, M4B, WAV hoặc gói nghe web ZIP.')
    if dest.resolve().is_relative_to(lib.root.resolve()):raise ValueError('Xuất ra ngoài thư viện để giữ an toàn dữ liệu.')
    exports=lib.directory(bid)/'exports';exports.mkdir(exist_ok=True)
    temp_dest=dest.with_name(dest.stem+'.partial'+dest.suffix)
    try:
        with tempfile.TemporaryDirectory(prefix='render-',dir=exports) as tmp:
            pcm=Path(tmp)/'mixed.wav'
            mix_wav(paths,pcm,settings,progress,cancelled,music_offset,rate)
            if cancelled():raise ExportCancelled('Đã hủy xuất audio.')
            if ext=='.wav':
                import shutil
                shutil.copyfile(pcm,temp_dest)
            elif ext=='.m4b':
                from m4b import export
                export(lib,b,segments,paths,pcm,temp_dest,tmp,title,process,cancelled,take)
            elif ext=='.mp3':
                import shutil
                ffmpeg_bin=shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
                p=subprocess.Popen([ffmpeg_bin,'-y','-i',str(pcm),'-ar','44100','-codec:a','libmp3lame','-b:a','192k',str(temp_dest)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                process(p)
                _,err=p.communicate()
                if cancelled():raise ExportCancelled('Đã hủy xuất audio.')
                if p.returncode or not temp_dest.is_file() or temp_dest.stat().st_size==0:
                    import sys
                    print(err.decode(errors='replace'),file=sys.stderr)
                    raise ValueError('Chưa lưu được tệp MP3 (192k). Hãy thử lại.')
            else:
                aac=Path(tmp)/'audio.m4a'
                p=subprocess.Popen(['/usr/bin/afconvert','-f','m4af','-d','aac','-b',str(128000 if rate==48000 else 64000),str(pcm),str(aac)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                process(p)
                _,err=p.communicate()
                if cancelled():raise ExportCancelled('Đã hủy xuất audio.')
                if p.returncode or not aac.is_file() or aac.stat().st_size==0:
                    import sys
                    print(err.decode(errors='replace'),file=sys.stderr)
                    raise ValueError('Chưa lưu được tệp M4A. Hãy thử lại hoặc chọn định dạng WAV.')
                if ext=='.m4a':
                    import shutil
                    shutil.copyfile(aac,temp_dest)
                else:
                    durations=[]
                    for path in paths:
                        with wave.open(str(path),'rb') as w:durations.append(w.getnframes()/w.getframerate())
                    with zipfile.ZipFile(temp_dest,'w',zipfile.ZIP_DEFLATED) as z:
                        z.write(aac,'audio.m4a')
                        label=('Section' if b.get('unitLabel')=='mục' else 'Page') if language=='en' else b.get('unitLabel','trang').capitalize()
                        for name,content in portable_page(title,segments,durations,label,language).items():z.writestr(name,content)
            if cancelled():raise ExportCancelled('Đã hủy xuất audio.')
            temp_dest.replace(dest)
    finally:temp_dest.unlink(missing_ok=True)
    return str(dest)
