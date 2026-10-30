"""Derived local covers, separate from source text, narration and book metadata."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

from core import atomic_json

ROOT = Path(__file__).resolve().parents[1]


def epub_cover(source):
    from epub import Package, local, resource, xml
    from html.parser import HTMLParser

    class Images(HTMLParser):
        def __init__(self):
            super().__init__(); self.images = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'img' and attrs.get('src'):
                self.images.append(attrs['src'])
            if tag == 'image' and (attrs.get('href') or attrs.get('xlink:href')):
                self.images.append(attrs.get('href') or attrs['xlink:href'])

    package = Package(source)
    try:
        container = xml(package.read('META-INF/container.xml'))
        rootfile = next(n for n in container.iter() if local(n.tag) == 'rootfile')
        opf, _ = resource('', rootfile.get('full-path', ''))
        root = xml(package.read(opf))
        manifest = {n.get('id'): n for n in root.iter() if local(n.tag) == 'item'}
        candidates = [n.get('href', '') for n in manifest.values() if 'cover-image' in n.get('properties', '').split()]
        for meta in root.iter():
            if local(meta.tag) == 'meta' and meta.get('name') == 'cover':
                item = manifest.get(meta.get('content'))
                if item is not None:
                    candidates.append(item.get('href', ''))
        candidates += [n.get('href', '') for n in root.iter() if local(n.tag) == 'reference' and 'cover' in n.get('type', '').split()]
        for href in candidates:
            try:
                name, _ = resource(opf, href)
                if Path(name).suffix.lower() in ('.xhtml', '.html', '.htm', '.svg'):
                    parser = Images(); parser.feed(package.read(name).decode('utf-8-sig'))
                    if not parser.images:
                        continue
                    name, _ = resource(name, parser.images[0])
                if Path(name).suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif'):
                    continue
                return package.read(name)
            except (OSError, ValueError, UnicodeError):
                continue
        return None
    finally:
        package.close()


def cover(lib, book_id):
    folder = lib.directory(book_id).resolve()
    if folder.parent != lib.root.resolve():
        raise ValueError('Đường dẫn sách không hợp lệ.')
    book = lib.load(book_id)
    name = book['sources'][0]['file']
    if not re.fullmatch(r'source-[0-9]+\.(pdf|epub|png|jpg|jpeg|heic|tiff|tif|webp)', name):
        return None
    source = (folder / name).resolve()
    if source.parent != folder:
        raise ValueError('Đường dẫn bản gốc không hợp lệ.')
    info = source.stat()
    key = [name, info.st_size, info.st_mtime_ns]
    cache = folder / 'cover-v1.json'
    if cache.is_symlink() or cache.with_suffix('.tmp').is_symlink():
        raise ValueError('Đường dẫn bìa không hợp lệ.')
    try:
        if cache.stat().st_size < 400000:
            saved = json.loads(cache.read_text())
            if saved.get('key') == key:
                return saved.get('image')
    except (OSError, ValueError):
        pass
    executable = ROOT / '.build/windi-cover'
    if not executable.is_file():
        return None

    def thumbnail(path):
        result = subprocess.run([str(executable), str(path)], capture_output=True, text=True, timeout=15)
        if result.returncode or len(result.stdout) > 400000:
            return None
        image = json.loads(result.stdout).get('image')
        return image if isinstance(image, str) and re.fullmatch(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', image) else None

    if source.suffix == '.epub':
        data = epub_cover(source)
        if data:
            with tempfile.NamedTemporaryFile(dir=folder, prefix='.cover-', suffix='.image') as temporary:
                temporary.write(data); temporary.flush()
                image = thumbnail(temporary.name)
        else:
            image = None
    else:
        image = thumbnail(source)
    atomic_json(cache, {'key': key, 'image': image})
    return image
