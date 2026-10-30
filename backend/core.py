"""Document state and audio cache. Standard library; no network or model import."""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid
import wave

MODEL_VERSION = 'vieneu-3.8.1-nano-aba295eb-16steps-v1'

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)

def split_text(text, limit=420):
    """Partition verbatim, including whitespace; do not split decimals or words."""
    chunks = []
    while len(text) > limit:
        candidates = [m.end() for m in re.finditer(r'[.!?…](?:[”’"\')\]]*)\s+|\n+', text[:limit])]
        cut = next((n for n in reversed(candidates) if n >= limit // 3), 0)
        if not cut:
            cut = text.rfind(' ', 0, limit) + 1
        if not cut:
            cut = limit
        chunks.append(text[:cut]); text = text[cut:]
    if text:
        chunks.append(text)
    return chunks

def signature(text, voice, model_id='nano', language='vi', model_revision=None):
    from model_manager import revision
    parts=[model_revision or revision(model_id), voice, text]
    if model_id=='clone-pro':parts.append(language)
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()

def valid_audio(path):
    try:
        with wave.open(str(path), 'rb') as w:
            return w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() in (24000,48000) and w.getnframes() > 0 and Path(path).stat().st_size >= 44 + w.getnframes()*2
    except (OSError, EOFError, wave.Error):
        return False

class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def directory(self, book_id):
        if not re.fullmatch(r'[a-f0-9]{32}', book_id):
            raise ValueError('Mã sách không hợp lệ.')
        return self.root / book_id

    def load(self, book_id):
        folder=self.directory(book_id);book=json.loads((folder/'book.json').read_text())
        completed={t.get('cloudOrderId') for t in book.get('audiobooks',[]) if t.get('status')=='ready'}
        pending=any(o.get('kind')=='trial' and (o.get('order') or {}).get('id') not in completed for o in book.get('cloudOrders',[]))
        # Opening/reading must not wait behind a processing job's library lock.
        if pending and self.lock.acquire(blocking=False):
            try:
                from audiobooks import restore_cloud_trials
                book=json.loads((folder/'book.json').read_text())
                if restore_cloud_trials(self,book):self.save(book)
            finally:self.lock.release()
        try:
            reader=json.loads((folder/'reader.json').read_text())
            if isinstance(reader,dict):book['reader']=reader
        except (OSError,ValueError):pass
        return book

    def trash(self,book_id):
        source=self.directory(book_id)
        if source.is_symlink() or source.resolve().parent!=self.root.resolve():raise ValueError('Đường dẫn sách không hợp lệ.')
        self.load(book_id)
        token=book_id+'-'+uuid.uuid4().hex
        dest=self.root/'.trash'/token;dest.parent.mkdir(exist_ok=True)
        if dest.parent.is_symlink() or dest.parent.resolve().parent!=self.root.resolve():raise ValueError('Thư mục đã xóa không hợp lệ.')
        source.rename(dest)
        os.utime(dest,None)
        return token

    def last_deleted(self):
        trash=self.root/'.trash'
        if trash.is_symlink():return None
        for folder in sorted(trash.glob('*'),key=lambda p:p.lstat().st_mtime,reverse=True):
            if folder.is_symlink() or not re.fullmatch(r'[a-f0-9]{32}-[a-f0-9]{32}',folder.name):continue
            try:
                book=json.loads((folder/'book.json').read_text())
                if book['id']!=folder.name[:32]:continue
                return dict(undoToken=folder.name,bookId=book['id'],title=book['title'])
            except (OSError,ValueError,KeyError,TypeError):continue
        return None

    def restore(self,token):
        if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{32}-[a-f0-9]{32}',token):raise ValueError('Mã khôi phục không hợp lệ.')
        source=self.root/'.trash'/token;dest=self.directory(token[:32])
        if source.parent.is_symlink():raise ValueError('Thư mục đã xóa không hợp lệ.')
        if source.is_symlink() or source.resolve().parent!=(self.root/'.trash').resolve() or not (source/'book.json').is_file():raise ValueError('Không tìm thấy sách đã xóa.')
        if dest.exists():raise ValueError('Sách này đã có trong thư viện.')
        if json.loads((source/'book.json').read_text()).get('id')!=token[:32]:raise ValueError('Sách đã xóa không khớp mã khôi phục.')
        source.rename(dest)
        return token[:32]

    def save(self, book):
        atomic_json(self.directory(book['id']) / 'book.json', book)

    def create(self, sources, language='vi'):
        if language not in ('vi','en'):raise ValueError('Ngôn ngữ sách không hợp lệ.')
        bid = uuid.uuid4().hex
        b = dict(schema=1, id=bid, title=Path(sources[0]).stem, sources=[], pages=[], segments=[],
                 importedSources=0, totalPages=0, status='importing', error='', voice='Đức Trí',
                 model='kitten' if language=='en' else 'nano',language=language,speed=1.0, music=dict(track='none',volume=.12), chapters=[], generationScope=dict(type='all'), position=dict(segment=0, seconds=0.0), finished=False)
        if language=='en':b['voice']='Jasper'
        d = self.directory(bid); (d / 'audio').mkdir(parents=True)
        import shutil
        for i, path in enumerate(sources):
            name = f'source-{i:04d}{Path(path).suffix.lower()}'
            if Path(path).is_dir():
                if Path(path).suffix.lower() != '.epub':
                    raise ValueError('Chỉ hỗ trợ thư mục sách có đuôi .epub.')
                from epub import copy_directory
                copy_directory(path, d / name)
            else:
                shutil.copyfile(path, d / name)
            b['sources'].append(dict(file=name, name=Path(path).name))
        self.save(b)
        return b

    def add_page(self, b, source, page):
        index = len(b['pages'])
        b['pages'].append(dict(source=source, sourcePage=page['page'], text=page['text'],
                               method=page['method'], warning=page['warning']))
        for key in ('title', 'href', 'layout', 'pageWidth'):
            if key in page: b['pages'][-1][key]=page[key]
        if page['text'].strip():
            for chunk in split_text(page['text']):
                b['segments'].append(dict(id=uuid.uuid4().hex, page=index, text=chunk, originalText=chunk))
        self.save(b)

    def audio_path(self, b, s):
        from bilingual import cache_signature
        return self.directory(b['id']) / 'audio' / (cache_signature(b,s['text']) + '.wav')

    def public(self, b):
        b = json.loads(json.dumps(b))
        from model_manager import profile
        b.setdefault('model','nano')
        b.setdefault('language','vi')
        b['sampleRate']=profile(b['model'])['sampleRate']
        for s in b['segments']:
            p = self.audio_path(b, s)
            s['audio'] = str(p) if valid_audio(p) else None
            s['duration'] = 0.0
            if s['audio']:
                with wave.open(str(p),'rb') as wav: s['duration']=wav.getnframes()/wav.getframerate()
        b['readyCount'] = sum(bool(s['audio']) for s in b['segments'])
        from scopes import chapters
        from music import music_settings, music_unavailable
        b['chapters']=chapters(b)
        from chapters import public_sections
        from audiobooks import public as public_take
        b['sections']=public_sections(b)
        # Geometry is an extractor checkpoint, never needed by the web editor.
        # Avoid repeatedly sending thousands of bounding boxes over the bridge.
        for page in b['pages']:page.pop('layout',None)
        b['audiobooks']=[public_take(self,b['id'],t) for t in b.get('audiobooks',[])]
        from entitlements import status
        allowed=status()['allowedModels']
        for item in [b,*b['audiobooks']]:
            item['locked']=item.get('model','nano') not in allowed
            if item['locked']:
                for s in item['segments']:s['audio']=None;s['duration']=0
                item['readyCount']=0
        # A missing local music asset must not prevent opening the source book.
        # Preserve the saved selection; explicit settings/export remain strict.
        b['music']=music_settings(b.get('music'),allow_unavailable=True)
        b['musicUnavailable']=music_unavailable(b['music'])
        b.setdefault('generationScope',{'type':'all'})
        return b

    def summaries(self):
        result=[]
        for p in sorted(self.root.glob('*/book.json'), key=lambda p:p.stat().st_mtime, reverse=True):
            try:
                b=json.loads(p.read_text())
                result.append({k:b[k] for k in ('id','title','status','position','finished')} | {'segments':len(b['segments']), 'pages':len(b['pages']), 'unitLabel':b.get('unitLabel','trang')})
            except (OSError,ValueError,KeyError):
                continue
        return result

    def position(self, bid, segment, seconds, finished=False):
        with self.lock:
            b=self.load(bid)
            if not 0 <= segment < len(b['segments']):
                raise ValueError('Đoạn nghe không hợp lệ.')
            import math
            seconds=float(seconds)
            if not math.isfinite(seconds): raise ValueError('Vị trí nghe không hợp lệ.')
            b['position']=dict(segment=segment, seconds=max(0, seconds)); b['finished']=bool(finished)
            self.save(b)

    def export(self, bid, destination, scope=None, **kwargs):
        from entitlements import require_model
        b=self.load(bid)
        if kwargs.get('take_id'):
            from audiobooks import find
            require_model(find(b,kwargs['take_id']).get('model','nano'))
        else:require_model(b.get('model','nano'))
        from exporting import export_book
        return export_book(self,bid,destination,scope,**kwargs)
