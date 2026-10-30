"""Local EPUB 2/3 text and navigation. Never execute HTML or fetch resources."""
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import json
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

MAX_FILE = 16 * 1024 * 1024
MAX_BOOK = 512 * 1024 * 1024
MAX_TEXT = 128 * 1024 * 1024
MAX_FILES = 20000
BLOCKS = set('p div section article header footer h1 h2 h3 h4 h5 h6 li blockquote pre table tr dl dt dd hr figure figcaption'.split())
SKIP = {'head', 'script', 'style', 'noscript', 'template', 'nav', 'iframe', 'object'}

def local(tag):
    return tag.rsplit('}', 1)[-1]

def xml(data):
    # Ordinary EPUB DOCTYPE declarations are fine; entity declarations are not.
    if b'<!ENTITY' in data.upper():
        raise ValueError('EPUB chứa khai báo XML entity không được hỗ trợ.')
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError('Cấu trúc EPUB bị lỗi: ' + str(e)) from e

def resource(base, href):
    u = urlsplit(href)
    if u.scheme or u.netloc or u.query or '\\' in href:
        raise ValueError('EPUB chứa đường dẫn tài nguyên không hợp lệ.')
    path = unquote(u.path)
    if path.startswith('/') or '\x00' in path or '\\' in path:
        raise ValueError('Đường dẫn EPUB nằm ngoài sách.')
    name = posixpath.normpath(posixpath.join(posixpath.dirname(base), path)) if path else base
    if name in ('', '.', '..') or name.startswith('../'):
        raise ValueError('Đường dẫn EPUB nằm ngoài sách.')
    return name, unquote(u.fragment)

class Package:
    def __init__(self, source):
        self.root = Path(source)
        self.archive = None
        if self.root.is_dir():
            if self.root.is_symlink():
                raise ValueError('Chọn thư mục EPUB thật, không dùng liên kết symbolic.')
            self.names = []
            total = 0
            for p in self.root.rglob('*'):
                if p.is_symlink():
                    raise ValueError('Thư mục EPUB chứa symbolic link không được hỗ trợ.')
                if p.is_file():
                    self.names.append(p.relative_to(self.root).as_posix())
                    total += p.stat().st_size
                if len(self.names) > MAX_FILES or total > MAX_BOOK:
                    raise ValueError('EPUB quá lớn để nhập an toàn (tối đa 512 MB / 20.000 tệp).')
        else:
            try:
                self.archive = zipfile.ZipFile(self.root)
                infos = self.archive.infolist()
                self.names = [i.filename for i in infos if not i.is_dir()]
                if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_BOOK:
                    raise ValueError('EPUB quá lớn để nhập an toàn (tối đa 512 MB / 20.000 tệp).')
                if len(set(self.names)) != len(self.names):
                    raise ValueError('EPUB có tên tài nguyên trùng nhau.')
                if any(i.flag_bits & 1 for i in infos):
                    raise ValueError('EPUB được mã hóa hoặc đặt mật khẩu; cần bản EPUB không khóa.')
            except zipfile.BadZipFile as e:
                raise ValueError('File EPUB không phải gói ZIP hợp lệ.') from e
        for name in self.names:
            if name.startswith('/') or '\\' in name or '..' in PurePosixPath(name).parts:
                self.close()
                raise ValueError('EPUB chứa đường dẫn nằm ngoài sách.')
        self.total_read = 0

    def close(self):
        if self.archive:
            self.archive.close()

    def read(self, name):
        if name not in self.names:
            raise ValueError('EPUB thiếu tài nguyên: ' + name)
        size = self.archive.getinfo(name).file_size if self.archive else (self.root / name).stat().st_size
        self.total_read += size
        if size > MAX_FILE or self.total_read > MAX_TEXT:
            raise ValueError('Nội dung EPUB vượt giới hạn đọc (16 MB mỗi mục / 128 MB tổng).')
        if self.archive:
            return self.archive.read(name)
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError('Đường dẫn EPUB nằm ngoài sách.')
        return path.read_bytes()

def copy_directory(source, destination):
    """Normalize an unpacked EPUB to a private ZIP, without following symlinks."""
    package = Package(source)
    try:
        # Validate the container before accepting a directory selected in Finder.
        xml(package.read('META-INF/container.xml'))
        with zipfile.ZipFile(destination, 'w') as out:
            if 'mimetype' in package.names:
                out.write(package.root / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
            for name in package.names:
                if name == 'mimetype':
                    continue
                path = package.root / name
                if path.is_symlink() or not path.resolve().is_relative_to(package.root.resolve()):
                    raise ValueError('Đường dẫn EPUB nằm ngoài sách.')
                out.write(path, name, compress_type=zipfile.ZIP_DEFLATED)
    finally:
        package.close()

class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

class HTML(HTMLParser):
    def __init__(self, data):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        # EPUB content is UTF-8 by default; honor an explicit XML encoding.
        match = re.search(br'<\?xml[^>]+encoding=[\'"]([^\'"]+)', data[:200], re.I)
        encoding = match.group(1).decode('ascii') if match else 'utf-8-sig'
        try:
            self.feed(data.decode(encoding))
        except (UnicodeError, LookupError) as e:
            raise ValueError('Không đọc được mã hóa chữ trong EPUB.') from e

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            if len(self.stack) > 256:
                raise ValueError('HTML trong EPUB lồng quá sâu.')
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

def walk(node):
    if isinstance(node, Node):
        yield node
        for child in node.children:
            yield from walk(child)

def label(node):
    if isinstance(node, str):
        return node
    return ''.join(label(c) for c in node.children)

def text_content(root):
    parts, anchors, headings = [], {}, []
    length = 0
    def append(value):
        nonlocal length
        parts.append(value)
        length += len(value)
    def visit(node):
        if isinstance(node, str):
            append(re.sub(r'\s+', ' ', node))
            return
        attrs = node.attrs
        if node.tag in SKIP or 'hidden' in attrs or attrs.get('aria-hidden') == 'true' or re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', attrs.get('style', ''), re.I):
            return
        if node.tag in BLOCKS or node.tag == 'br':
            append('\n')
        for key in ('id', 'name'):
            if attrs.get(key):
                anchors.setdefault(attrs[key], length)
        if node.tag in ('h1', 'h2'):
            title = re.sub(r'\s+', ' ', label(node)).strip()
            if title:
                headings.append((length, title))
        for child in node.children:
            visit(child)
        if node.tag in BLOCKS:
            append('\n')
    bodies = [n for n in walk(root) if n.tag == 'body']
    visit(bodies[0] if bodies else root)
    return ''.join(parts), anchors, headings

def extract(source):
    package = Package(source)
    try:
        container = xml(package.read('META-INF/container.xml'))
        roots = [n for n in container.iter() if local(n.tag) == 'rootfile']
        if not roots:
            raise ValueError('EPUB thiếu package document.')
        opf, _ = resource('', roots[0].get('full-path', ''))
        root = xml(package.read(opf))
        manifest = {n.get('id'): n for n in root.iter() if local(n.tag) == 'item'}
        spine = next((n for n in root.iter() if local(n.tag) == 'spine'), None)
        if spine is None:
            raise ValueError('EPUB thiếu thứ tự đọc (spine).')
        title = next((''.join(n.itertext()).strip() for n in root.iter() if local(n.tag) == 'title'), Path(source).stem)
        toc = []
        navs = [n for n in manifest.values() if 'nav' in n.get('properties', '').split()]
        for nav in navs:
            name, _ = resource(opf, nav.get('href', ''))
            html = HTML(package.read(name)).root
            for n in walk(html):
                if n.tag == 'nav' and set(n.attrs.get('epub:type', '').split()) & {'toc', 'landmarks'}:
                    for a in walk(n):
                        if a.tag == 'a' and a.attrs.get('href'):
                            target, fragment = resource(name, a.attrs['href'])
                            text = re.sub(r'\s+', ' ', label(a)).strip()
                            if text:
                                toc.append((target, fragment, text))
        if not toc:
            ncx = manifest.get(spine.get('toc'))
            if ncx is None:
                ncx = next((n for n in manifest.values() if n.get('media-type') == 'application/x-dtbncx+xml'), None)
            if ncx is not None:
                name, _ = resource(opf, ncx.get('href', ''))
                tree = xml(package.read(name))
                for n in tree.iter():
                    if local(n.tag) != 'navPoint':
                        continue
                    content = next((c for c in n if local(c.tag) == 'content'), None)
                    navlabel = next((c for c in n if local(c.tag) == 'navLabel'), None)
                    if content is not None and navlabel is not None:
                        target, fragment = resource(name, content.get('src', ''))
                        toc.append((target, fragment, ''.join(navlabel.itertext()).strip()))
        encrypted = set()
        if 'META-INF/encryption.xml' in package.names:
            tree = xml(package.read('META-INF/encryption.xml'))
            for n in tree.iter():
                if local(n.tag) == 'CipherReference':
                    encrypted.add(resource('', n.get('URI', ''))[0])
        units, chapters, warnings = [], [], []
        blank = 0
        for ref in spine:
            if local(ref.tag) != 'itemref' or ref.get('linear') == 'no':
                continue
            item = manifest.get(ref.get('idref'))
            if item is None:
                raise ValueError('EPUB thiếu một mục trong manifest.')
            name, _ = resource(opf, item.get('href', ''))
            if name in encrypted:
                raise ValueError('Nội dung EPUB bị mã hóa/DRM; cần bản EPUB không khóa.')
            if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
                raise ValueError('EPUB có mục đọc không phải HTML; chưa hỗ trợ loại nội dung này.')
            raw, anchors, headings = text_content(HTML(package.read(name)).root)
            if not raw.strip():
                blank += 1
                continue
            starts = {}
            for target, fragment, text in toc:
                if target != name:
                    continue
                if fragment and fragment not in anchors:
                    warnings.append('Một mốc mục lục không có vị trí tương ứng: ' + text)
                    continue
                starts.setdefault(anchors[fragment] if fragment else 0, (text, 'epub-toc', fragment))
            if not starts:
                for offset, text in headings:
                    starts.setdefault(offset, (text, 'epub-heading', ''))
            # Whitespace before the first heading belongs to that heading, not a fake preface.
            if starts and not raw[:min(starts)].strip():
                starts[0] = starts.pop(min(starts))
            starts.setdefault(0, ('Mục ' + str(len(units)+1), 'epub-section', ''))
            offsets = sorted(starts)
            for i, offset in enumerate(offsets):
                text = raw[offset:offsets[i+1] if i+1 < len(offsets) else len(raw)]
                text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)
                text = re.sub(r'\n{3,}', '\n\n', text).strip()
                if not text:
                    continue
                heading, origin, fragment = starts[offset]
                page = len(units)
                units.append(dict(page=page, text=text, method='epub', warning='', title=heading, href=name + ('#'+fragment if fragment else '')))
                chapters.append(dict(id='epub-'+str(page), title=heading, startPage=page, origin=origin))
        if not units:
            raise ValueError('EPUB không có chữ đọc được. Sách chỉ chứa ảnh cần chuyển sang PDF/ảnh để OCR.')
        if blank:
            warnings.append(f'{blank} mục trống hoặc chỉ có ảnh (ví dụ bìa) không được đưa vào lời đọc. EPUB này được lấy chữ trực tiếp, không OCR ảnh bên trong.')
        note = 'EPUB chia theo mục nội dung, không phải số trang của bản in.'
        if warnings:
            note += ' ' + ' '.join(dict.fromkeys(warnings))
        for unit in units:
            unit.update(total=len(units), chapters=chapters, bookTitle=title, format='epub', unitLabel='mục')
        units[0]['warning'] = note
        return units
    finally:
        package.close()

if __name__ == '__main__':
    try:
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        for page in extract(sys.argv[1])[start:]:
            print(json.dumps(page, ensure_ascii=False), flush=True)
    except Exception as error:
        print(json.dumps({'error':str(error)}, ensure_ascii=False), flush=True)
        sys.exit(1)
