import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from epub import extract, copy_directory, resource
from core import Library
from scopes import selected_indices

CONTAINER = '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>'
OPF = '''<package><metadata><title>Sách tiếng Việt</title></metadata><manifest>
<item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>
<item id="body" href="body.xhtml" media-type="application/xhtml+xml"/>
<item id="last" href="last.xhtml" media-type="application/xhtml+xml"/>
</manifest><spine><itemref idref="body"/><itemref idref="last"/></spine></package>'''
NAV = '''<html><body><nav epub:type="toc"><ol><li><a href="body.xhtml#intro">Lời mở đầu</a></li>
<li><a href="body.xhtml#one">Chương một</a></li><li><a href="last.xhtml">Lời kết</a></li></ol></nav></body></html>'''
BODY = '''<html><head><style>Không đọc CSS</style></head><body><section id="intro"><h1>Lời mở đầu</h1>
<p>Sách có dấu &amp; nội dung <em>nguyên bản</em>.</p><script>Không chạy mã</script>
<p hidden>Không đọc chữ ẩn</p></section><section id="one"><h1>Chương một</h1>
<p>Ví dụ: 3.14, 1.000 đồng.<br/>Dòng mới.</p></section></body></html>'''

class EPUBTests(unittest.TestCase):
    def fixture(self, root, body=BODY, opf=OPF):
        files = {'META-INF/container.xml':CONTAINER, 'mimetype':'application/epub+zip',
                 'OPS/book.opf':opf, 'OPS/nav.xhtml':NAV, 'OPS/body.xhtml':body,
                 'OPS/last.xhtml':'<html><body><h1>Lời kết</h1><p>Hẹn gặp lại.</p></body></html>'}
        for name, data in files.items():
            path = root / name;path.parent.mkdir(parents=True, exist_ok=True);path.write_text(data)
        return files

    def test_directory_zip_order_fragments_and_verbatim_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'demo.epub';self.fixture(folder)
            units=extract(folder)
            self.assertEqual([u['title'] for u in units], ['Lời mở đầu','Chương một','Lời kết'])
            self.assertIn('Sách có dấu & nội dung nguyên bản.',units[0]['text'])
            self.assertNotIn('Không', ''.join(u['text'] for u in units))
            self.assertIn('3.14, 1.000 đồng.',units[1]['text'])
            self.assertNotIn('Chương một',units[0]['text'])
            archive=Path(tmp)/'compressed.epub'
            copy_directory(folder,archive)
            self.assertEqual(extract(archive),units)
            # Physical ZIP order differs from declared reading order.
            with zipfile.ZipFile(archive,'w') as z:
                for path in sorted(folder.rglob('*'),reverse=True):
                    if path.is_file():z.write(path,path.relative_to(folder).as_posix())
            self.assertEqual(extract(archive),units)
            lib=Library(Path(tmp)/'library');book=lib.create([folder])
            self.assertTrue((lib.directory(book['id'])/book['sources'][0]['file']).is_file())
            book['chapters']=units[0]['chapters']
            for unit in units:lib.add_page(book,0,unit)
            selected=selected_indices(book,{'type':'chapter','chapterId':'epub-1'})
            self.assertEqual(''.join(book['segments'][i]['text'] for i in selected),units[1]['text'])
            self.assertEqual(book['pages'][1]['href'],'OPS/body.xhtml#one')

    def test_no_toc_uses_explicit_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'demo.epub';self.fixture(folder,opf=OPF.replace('properties="nav"',''))
            units=extract(folder)
            self.assertEqual(units[0]['chapters'][0]['origin'],'epub-heading')
            self.assertEqual(units[0]['title'],'Lời mở đầu')

    def test_images_only_and_missing_anchor_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'demo.epub';self.fixture(folder,body='<html><body><img src="cover.png"/></body></html>')
            units=extract(folder)
            self.assertEqual(len(units),1)
            self.assertIn('chỉ có ảnh',units[0]['warning'])
            (folder/'OPS/last.xhtml').write_text('<html><body><img src="x"/></body></html>')
            with self.assertRaisesRegex(ValueError,'không có chữ'):extract(folder)
            (folder/'OPS/body.xhtml').write_text(BODY.replace('id="one"','id="other"'))
            self.assertIn('mốc mục lục',extract(folder)[0]['warning'])

    def test_reject_unsafe_and_encrypted_resources(self):
        for href in ('../../outside','https://example.com/book','%2fetc/passwd','..%2f..%2foutside','file:///etc/passwd'):
            with self.assertRaises(ValueError):resource('OPS/book.opf',href)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'demo.epub';self.fixture(folder)
            (folder/'OPS/link.xhtml').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError,'symbolic'):extract(folder)
            (folder/'OPS/link.xhtml').unlink()
            (folder/'META-INF/encryption.xml').write_text('<encryption><CipherReference URI="OPS/body.xhtml"/></encryption>')
            with self.assertRaisesRegex(ValueError,'DRM'):extract(folder)
            (folder/'META-INF/encryption.xml').unlink()
            archive=Path(tmp)/'bad.epub'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside','bad')
            with self.assertRaisesRegex(ValueError,'ngoài sách'):extract(archive)

if __name__=='__main__':unittest.main()
