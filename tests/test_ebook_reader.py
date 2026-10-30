import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
from ebook_reader import prepare,content_key
import audiobooks

class EbookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.root=Path(self.tmp.name)
        source=self.root/'fixture.pdf';source.write_bytes(b'%PDF-independent-original')
        self.lib=Library(self.root/'library');self.b=self.lib.create([source])
        for at,text in enumerate(['CHƯƠNG 1\n\n🙂 Sách tiếng Việt. Giữ tên & số 3.14.\n\n','Trang sau <script>chỉ là chữ</script>.\n']):self.lib.add_page(self.b,0,dict(page=at,text=text,method='text',warning=''))
        self.b['status']='ready';self.b['chapters']=[dict(id='chapter-1',title='CHƯƠNG 1',startPage=0,origin='manual')];self.lib.save(self.b)
    def tearDown(self):self.tmp.cleanup()
    def test_valid_epub_preserves_text_source_anchors_and_escapes_markup(self):
        before=copy.deepcopy(self.b);data,path=prepare(self.lib,self.b,with_images=False)
        self.assertEqual(self.b,before);self.assertEqual(''.join(c['text'] for c in data['sentences']),''.join(s['text'] for s in self.b['segments']))
        self.assertEqual([p['page'] for p in data['pages']],[0,1]);self.assertEqual(data['timing'],'estimated')
        with zipfile.ZipFile(path) as z:
            self.assertEqual(z.infolist()[0].filename,'mimetype');self.assertEqual(z.getinfo('mimetype').compress_type,zipfile.ZIP_STORED)
            for name in ['META-INF/container.xml','EPUB/package.opf','EPUB/book.xhtml','EPUB/nav.xhtml']:ET.fromstring(z.read(name))
            text=ET.fromstring(z.read('EPUB/book.xhtml'));self.assertFalse(any(n.tag.endswith('script') for n in text.iter()))
            self.assertIn('<script>chỉ là chữ</script>',''.join(text.itertext()));self.assertIn('data-source-page="1"',z.read('EPUB/book.xhtml').decode())
            self.assertIn(data['chapters'][0]['cue'],z.read('EPUB/nav.xhtml').decode())
    def test_cache_reuse_and_edit_creates_derived_book_without_invalidating_audio(self):
        data,path=prepare(self.lib,self.b,with_images=False);stamp=path.stat().st_mtime_ns
        with patch('ebook_reader.source_figures',side_effect=AssertionError('Do not reprocess unchanged book')):again,same=prepare(self.lib,self.b)
        self.assertEqual(same,path);self.assertEqual(path.stat().st_mtime_ns,stamp);self.assertEqual(again['contentKey'],data['contentKey'])
        key=content_key(self.b);self.b['speed']=1.5;self.b['voice']='another';self.assertEqual(content_key(self.b),key)
        self.b['segments'][0]['text']='Nội dung đã sửa.';edited,new=prepare(self.lib,self.b,with_images=False)
        self.assertNotEqual(new,path);self.assertTrue(path.is_file());self.assertNotEqual(edited['contentKey'],key)
    def test_image_requests_are_lazy_and_cannot_escape_book(self):
        from ebook_reader import image
        from PIL import Image
        data,path=prepare(self.lib,self.b,with_images=False,include_images=False)
        self.assertTrue(all('image' not in f for f in data['figures']))
        target=path.parent/'images'/'p0-0.jpg';Image.new('RGB',(4,4),'red').save(target)
        self.assertTrue(image(self.lib,self.b['id'],data['contentKey'],'p0-0.jpg').startswith('data:image/jpeg;base64,'))
        for key,file in [(data['contentKey'],'../book.json'),('../escape','p0-0.jpg'),('a'*64,'https://outside.test/image.jpg')]:
            with self.assertRaises(ValueError):image(self.lib,self.b['id'],key,file)
        target.unlink();outside=self.root/'outside.jpg';Image.new('RGB',(4,4),'blue').save(outside);target.symlink_to(outside)
        with self.assertRaises(ValueError):image(self.lib,self.b['id'],data['contentKey'],'p0-0.jpg')

    def test_saved_take_content_is_immutable_in_epub(self):
        take=audiobooks.create(self.b,[0],'Bản đã lưu',dict(type='all'));original=self.b['segments'][0]['text'];self.b['segments'][0]['text']='Đã thay chữ.'
        data,path=prepare(self.lib,self.b,take['id'],with_images=False)
        self.assertEqual(''.join(c['text'] for c in data['sentences']),original)
        self.assertNotIn('Đã thay chữ.',path.read_bytes().decode(errors='ignore'))
    def test_failed_build_is_atomic_and_rejects_unready_or_symlink(self):
        self.b['status']='importing'
        with self.assertRaises(ValueError):prepare(self.lib,self.b,with_images=False)
        self.b['status']='ready'
        with patch('ebook_reader.write_epub',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):prepare(self.lib,self.b,with_images=False)
        self.assertEqual(list((self.lib.directory(self.b['id'])/'reader').iterdir()),[])
        (self.lib.directory(self.b['id'])/'reader').rmdir();outside=self.root/'outside';outside.mkdir();(self.lib.directory(self.b['id'])/'reader').symlink_to(outside)
        with self.assertRaises(ValueError):prepare(self.lib,self.b,with_images=False)
        self.assertEqual(list(outside.iterdir()),[])

    def test_reader_background_remains_responsive_and_blocks_deletion_until_atomic_finish(self):
        import threading
        import time
        from worker import Worker
        worker=Worker(self.lib.root);entered=threading.Event();release=threading.Event();finished=threading.Event();events=[]
        def blocked(*args,**kwargs):
            entered.set();release.wait(2);return dict(contentKey='fixture'),self.root/'fixture.epub'
        def event(**value):
            events.append(value)
            if value['event']=='readerBook':finished.set()
        with patch('ebook_reader.prepare',side_effect=blocked),patch('worker.emit',side_effect=event):
            started=time.monotonic();worker.handle(dict(action='readerBook',bookId=self.b['id'],token='selected'))
            self.assertLess(time.monotonic()-started,.3);self.assertTrue(entered.wait(1))
            with self.assertRaisesRegex(ValueError,'ebook'):worker.handle(dict(action='deleteBook',bookId=self.b['id']))
            release.set();self.assertTrue(finished.wait(1))
        self.assertEqual(events[0]['token'],'selected');self.assertTrue((self.lib.directory(self.b['id'])/'book.json').is_file())

    def test_simultaneous_requests_share_one_completed_derived_book(self):
        from concurrent.futures import ThreadPoolExecutor
        import ebook_reader
        original=ebook_reader.write_epub
        with patch('ebook_reader.write_epub',wraps=original) as writer:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures=[executor.submit(prepare,self.lib,self.b,None,False) for _ in range(2)]
                paths=[f.result()[1] for f in futures]
            self.assertEqual(writer.call_count,1);self.assertEqual(paths[0],paths[1])
        self.assertFalse(list(paths[0].parent.parent.glob('.preparing-*')))

if __name__=='__main__':unittest.main()
