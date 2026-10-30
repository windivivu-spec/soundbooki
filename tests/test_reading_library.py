import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
from reading import page_data,sentences,folded
from chapters import edit_chapter
from worker import Worker
import audiobooks

class ReadingLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.root=Path(self.temp.name)
        self.source=self.root/'source.pdf';self.source.write_bytes(b'%PDF-original-source')
        self.lib=Library(self.root/'library');self.b=self.lib.create([self.source])
        for i,text in enumerate(['🙂 Xin chào\nViệt Nam. Một câu nữa!\n','Trang hai. Câu cuối sách.']):self.lib.add_page(self.b,0,dict(page=i,text=text,method='text',warning=''))
        self.b.update(status='ready',chapters=[]);self.lib.save(self.b)
    def tearDown(self):self.temp.cleanup()
    def test_sentence_partition_and_utf16_anchors(self):
        raw=self.b['pages'][0]['text'];data=page_data(self.b,0)
        self.assertEqual(''.join(c['text'] for c in data['sentences']),raw)
        self.assertEqual(data['timing'],'estimated')
        for cue in data['sentences']:
            r=cue['sourceRange'];value=raw.encode('utf-16-le')[r['location']*2:(r['location']+r['length'])*2].decode('utf-16-le')
            self.assertEqual(folded(value),folded(cue['text']))
        self.assertEqual(data['sentences'][0]['startFraction'],0);self.assertEqual(data['sentences'][-1]['endFraction'],1)
        self.assertEqual(len(sentences('Giá 3.14 đồng. Đọc tiếp!')),2)
    def test_reflow_uses_original_offsets_and_edited_text_never_false_matches(self):
        self.b['segments'][0]['text']=self.b['segments'][0]['text'].replace('\n',' ')
        self.assertTrue(all(c['sourceRange'] for c in page_data(self.b,0)['sentences']))
        self.b['segments'][0]['text']='Câu đã sửa hoàn toàn. Một câu nữa!'
        cues=page_data(self.b,0)['sentences'];self.assertIsNone(cues[0]['sourceRange']);self.assertIsNotNone(cues[1]['sourceRange'])
        self.b['pages'][0]['text']='Lặp lại. Lặp lại.';self.b['segments'][0]['text']='Lặp lại.'
        self.assertIsNone(page_data(self.b,0)['sentences'][0]['sourceRange'])
    def test_saved_take_reads_its_own_text_after_edit(self):
        take=audiobooks.create(self.b,[0],'Bản đã lưu',dict(type='all'))
        self.b['segments'][0]['text']='Thay nội dung sau khi tạo.'
        old=page_data(self.b,0,take['id']);current=page_data(self.b,0)
        self.assertIn('Xin chào',old['sentences'][0]['text']);self.assertNotEqual(old['contentKey'],current['contentKey'])
    def test_trash_restore_preserves_original_cache_and_purchase_metadata(self):
        b=self.b;b['cloudOrders']=[dict(order=dict(id='saved-paid-order'),snapshot=dict(text='Paid snapshot'))];self.lib.save(b)
        audio=self.lib.directory(b['id'])/'audio'/'fixture.wav';audio.write_bytes(b'completed cached audio')
        saved=(self.lib.directory(b['id'])/'book.json').read_bytes();token=self.lib.trash(b['id'])
        reopened=Library(self.lib.root);self.assertEqual(reopened.last_deleted()['undoToken'],token)
        self.assertEqual(self.lib.summaries(),[]);self.assertEqual(self.source.read_bytes(),b'%PDF-original-source')
        self.assertEqual(self.lib.restore(token),b['id']);self.assertEqual((self.lib.directory(b['id'])/'book.json').read_bytes(),saved)
        self.assertEqual(audio.read_bytes(),b'completed cached audio')
        self.assertIsNone(self.lib.last_deleted())
        for invalid in ('../escape',b['id']+'/../../escape',None):
            with self.assertRaises(ValueError):self.lib.restore(invalid)
    def test_worker_does_not_delete_busy_book_and_reader_settings_do_not_change_voice_cache(self):
        worker=Worker(self.lib.root);before=self.lib.audio_path(self.b,self.b['segments'][0])
        worker.jobs['audio']=dict(id=self.b['id'],cancel=threading.Event(),process=None)
        with self.assertRaisesRegex(ValueError,'xong'):worker.handle(dict(action='deleteBook',bookId=self.b['id']))
        self.assertTrue(self.lib.directory(self.b['id']).exists());worker.jobs.clear()
        worker.handle(dict(action='readerSettings',bookId=self.b['id'],reader=dict(mode='read',variant='text',page=1,fontSize=25,follow=False)))
        b=self.lib.load(self.b['id']);self.assertEqual(b['reader']['page'],1);self.assertEqual(before,self.lib.audio_path(b,b['segments'][0]))
        events=[]
        with patch('worker.emit',side_effect=lambda **e:events.append(e)):
            worker.handle(dict(action='deleteBook',bookId=b['id']));worker.handle(dict(action='restoreBook',undoToken=events[0]['undoToken']))
        self.assertEqual([e['event'] for e in events],['bookDeleted','bookRestored'])
    def test_path_validation_and_missing_pages(self):
        for page in (-1,True,2,'1'):
            with self.assertRaises(ValueError):page_data(self.b,page)
        linked='a'*32;(self.lib.root/linked).symlink_to(self.lib.directory(self.b['id']),target_is_directory=True)
        with self.assertRaises(ValueError):self.lib.trash(linked)

    def test_reading_does_not_block_cancel_or_lose_preferences_during_processing(self):
        worker=Worker(self.lib.root);held=threading.Event();release=threading.Event();stale=self.lib.load(self.b['id'])
        def processing():
            with worker.lib.lock:held.set();release.wait(2)
        thread=threading.Thread(target=processing);thread.start();held.wait(1)
        started=time.monotonic();events=[]
        try:
            with patch('worker.emit',side_effect=lambda **e:events.append(e)):
                worker.handle(dict(action='readerSettings',bookId=self.b['id'],reader=dict(mode='read',page=1)))
                worker.handle(dict(action='readerPage',bookId=self.b['id'],page=1,token='reader'))
            self.assertLess(time.monotonic()-started,.5);self.assertEqual(events[0]['page'],1)
        finally:release.set();thread.join()
        # A processing checkpoint made from an older book snapshot cannot undo
        # the reader's page/mode preference.
        self.lib.save(stale);self.assertEqual(self.lib.load(self.b['id'])['reader'],dict(mode='read',page=1))

    def test_multiple_deleted_books_can_be_recovered_after_reopening(self):
        first=self.lib.trash(self.b['id']);other=self.lib.create([self.source]);second=self.lib.trash(other['id'])
        reopened=Library(self.lib.root);self.assertEqual(reopened.last_deleted()['undoToken'],second)
        reopened.restore(second);self.assertEqual(reopened.last_deleted()['undoToken'],first)
        reopened.restore(first);self.assertIsNone(reopened.last_deleted());self.assertEqual(len(reopened.summaries()),2)

if __name__=='__main__':unittest.main()
