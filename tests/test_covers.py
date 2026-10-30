import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from core import Library
from covers import cover, epub_cover, ROOT

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5WQAAAAASUVORK5CYII=')


class CoverTests(unittest.TestCase):
    def epub(self, folder, declaration, image_href='images/cover.png'):
        path = folder / 'Bìa sách.epub'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
            archive.writestr('OPS/book.opf', '<package><metadata>' + declaration + '</metadata><manifest><item id="cover" href="' + image_href + '" properties="cover-image"/></manifest></package>')
            archive.writestr('OPS/images/cover.png', PNG)
        return path

    def test_epub_3_declared_cover_and_epub_2_metadata(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.qa') as tmp:
            folder = Path(tmp)
            path = self.epub(folder, '')
            self.assertEqual(epub_cover(path), PNG)
            with zipfile.ZipFile(path) as archive:
                files = {n: archive.read(n) for n in archive.namelist()}
            files['OPS/book.opf'] = files['OPS/book.opf'].replace(b'properties="cover-image"', b'').replace(b'<metadata>', b'<metadata><meta name="cover" content="cover"/>')
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in files.items(): archive.writestr(name, data)
            self.assertEqual(epub_cover(path), PNG)

    def test_remote_and_escaping_cover_are_ignored(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.qa') as tmp:
            for href in ('https://example.com/cover.png', '../../private.png'):
                self.assertIsNone(epub_cover(self.epub(Path(tmp), '', href)))

    def test_native_cover_cache_preserves_book_and_invalidates_source(self):
        if not (ROOT / '.build/windi-cover').is_file(): self.skipTest('Run scripts/build.sh first')
        with tempfile.TemporaryDirectory(dir=ROOT / '.qa') as tmp:
            folder = Path(tmp); source = folder / 'Ảnh.png'; source.write_bytes(PNG)
            lib = Library(folder / 'library'); book = lib.create([source]); bid = book['id']
            metadata = (lib.directory(bid) / 'book.json').read_bytes()
            image = cover(lib, bid)
            self.assertTrue(image.startswith('data:image/jpeg;base64,'))
            with patch('covers.subprocess.run', side_effect=AssertionError('must use cached thumbnail')):
                self.assertEqual(cover(lib, bid), image)
            (lib.directory(bid) / 'source-0000.png').write_bytes(b'invalid image')
            self.assertIsNone(cover(lib, bid))
            self.assertEqual((lib.directory(bid) / 'book.json').read_bytes(), metadata)
            self.assertFalse(list(lib.directory(bid).glob('.cover-*')))

    def test_pdf_and_epub_real_thumbnail(self):
        source = ROOT / '.qa/fixtures-data/text-viet.pdf'
        if not source.is_file(): self.skipTest('Generate native PDF fixtures first')
        with tempfile.TemporaryDirectory(dir=ROOT / '.qa') as tmp:
            folder = Path(tmp); lib = Library(folder / 'library')
            pdf = lib.create([source]); epub = lib.create([self.epub(folder, '')])
            for book in (pdf, epub):
                image = cover(lib, book['id'])
                self.assertTrue(base64.b64decode(image.split(',', 1)[1]).startswith(b'\xff\xd8'))
                saved = json.loads((lib.directory(book['id']) / 'cover-v1.json').read_text())
                self.assertEqual(saved['image'], image)


if __name__ == '__main__': unittest.main()
