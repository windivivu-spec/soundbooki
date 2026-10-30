"""Chapter metadata for immutable narration snapshots and local M4B export."""
from pathlib import Path
import base64
import subprocess
import shutil
import wave

def chapter_marks(book,segments,paths,take=None):
    from scopes import chapters
    catalog=chapters(book);result=[];offset=0;previous=None
    # A snapshot carries chapter ids/titles, so later editing cannot relabel it.
    for segment,path in zip(segments,paths):
        chapter=segment.get('chapterTitle')
        identity=segment.get('chapterId')
        if chapter is None and take is not None:
            chapter=take.get('title') or book['title'];identity='snapshot'
        if chapter is None:
            index=segment.get('index',0)
            match=next((c for c in catalog if index in c.get('indices',[]) or ('indices' not in c and c['startPage']<=segment['page']<=c['endPage'])),None)
            chapter=match['title'] if match else (take or {}).get('title') or book['title'];identity=match['id'] if match else 'document'
        with wave.open(str(path),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
        if identity!=previous or not result:result.append(dict(title=chapter,start=offset,end=offset+duration));previous=identity
        else:result[-1]['end']=offset+duration
        offset+=duration
    return result

def escape(value):
    return str(value).replace('\\','\\\\').replace('\n',' ').replace('\r',' ').replace('=','\\=').replace(';','\\;').replace('#','\\#')

def export(lib,book,segments,paths,pcm,dest,tmp,title,process,cancelled,take=None):
    from exporting import ExportCancelled
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise ValueError('Xuất M4B cần ffmpeg local. Các định dạng M4A/WAV vẫn dùng được.')
    marks=chapter_marks(book,segments,paths,take)
    meta=[';FFMETADATA1','title='+escape(title),'artist='+escape(book.get('author','')),'album='+escape(book['title']),'genre=Audiobook']
    for c in marks:meta += ['[CHAPTER]','TIMEBASE=1/1000',f"START={round(c['start']*1000)}",f"END={round(c['end']*1000)}",'title='+escape(c['title'])]
    metadata=Path(tmp)/'chapters.txt';metadata.write_text('\n'.join(meta)+'\n',encoding='utf-8')
    from covers import cover
    try:picture=cover(lib,book['id'])
    except (OSError,ValueError,KeyError,IndexError):picture=None
    if not picture:
        from PIL import Image,ImageDraw
        img=Image.new('RGB',(600,800),'#DFE8F1');draw=ImageDraw.Draw(img)
        import textwrap
        draw.text((45,100),'\n'.join(textwrap.wrap(title,25))[:600],fill='#20334B',font_size=30)
        draw.text((45,710),'SOUNDBOOKI',fill='#20334B',font_size=24)
        image=Path(tmp)/'cover.jpg';img.save(image)
    else:
        image=Path(tmp)/'cover.jpg';image.write_bytes(base64.b64decode(picture.split(',',1)[1]))
    cmd=[ffmpeg,'-v','error','-y','-i',str(pcm),'-f','ffmetadata','-i',str(metadata),'-i',str(image),'-map','0:a','-map','2:v','-map_metadata','1','-map_chapters','1','-c:a','aac','-b:a','64k','-c:v','mjpeg','-disposition:v','attached_pic','-f','mp4',str(dest)]
    p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);process(p);_,error=p.communicate()
    if cancelled():raise ExportCancelled('Đã hủy xuất M4B.')
    if p.returncode or not Path(dest).is_file() or not Path(dest).stat().st_size:raise ValueError('Chưa xuất được M4B: '+error.decode(errors='replace')[-500:])

def freeze_labels(book,segments):
    from scopes import chapters
    catalog=chapters(book);labels={}
    for segment in segments:
        source=(segment.get('sourceSpans') or [segment])[0]
        index=source.get('index',-1)
        current=book['segments'][index] if 0<=index<len(book['segments']) else None
        if not current or current['id']!=source['id']:continue
        if 'sourceSpans' not in segment and current['text']!=segment['text']:continue
        match=next((c for c in catalog if index in c.get('indices',[]) or ('indices' not in c and c['startPage']<=segment['page']<=c['endPage'])),None)
        if match:labels[segment['id']]=dict(chapterId=match['id'],chapterTitle=match['title'])
    return labels
