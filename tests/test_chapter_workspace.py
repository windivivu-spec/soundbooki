import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library
from chapters import edit_chapter,public_sections,text_and_spans
from cleanup import clean_text,narratable
from scopes import selected_indices
import audiobooks

class ChapterWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        source=self.root/'fixture.txt';source.write_text('source')
        self.lib=Library(self.root/'library');self.book=self.lib.create([source])
        for i,text in enumerate(['Lời mở đầu.\n...............\n','Trang tiếp theo, vẫn giữ dấu.\n','Chương hai có 1.5 và 42.']):
            self.lib.add_page(self.book,0,dict(page=i,text=text,method='text',warning=''))
        self.book.update(status='ready',chapters=[dict(id='a',title='Mở đầu',startPage=0),dict(id='b',title='Hai',startPage=2)])
        self.lib.save(self.book)
    def tearDown(self):self.temp.cleanup()
    def audio(self,segment):
        p=self.lib.audio_path(self.book,segment)
        with wave.open(str(p),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x10\x00'*2400)
        return p
    def test_conservative_cleanup_preview(self):
        text='Tiếng Việt… vẫn giữ!\n.............\n***\n42\nChương 1... 12\n1.5 là số thập phân.\n'
        result=clean_text(text)
        self.assertEqual(result['count'],2);self.assertIn('42\n',result['text']);self.assertIn('Chương 1... 12',result['text'])
        self.assertIn('Tiếng Việt… vẫn giữ!',result['text']);self.assertEqual(clean_text(result['text'])['count'],0)
        self.assertFalse(narratable('… ··· ***'));self.assertTrue(narratable('42 là câu trả lời.'))
    def test_explicit_toc_and_numbers(self):
        text='Mục lục\nMở đầu ........ 1\nChương Một ........ 3\nChương Hai ........ 12\n\nNội dung cần giữ.\n42\n'
        self.assertEqual(clean_text(text)['text'],text)
        result=clean_text(text,dict(toc=True,pageNumbers=True))
        self.assertNotIn('Mục lục',result['text']);self.assertIn('Nội dung cần giữ.',result['text'])
        self.assertNotIn('42',result['text'])
    def test_chapter_edit_provenance_and_restore(self):
        b=self.book;original=json.loads(json.dumps(b['pages']));other=b['segments'][-1]['id']
        before=text_and_spans(b,public_sections(b)[0])[0]
        edited=before.replace('...............\n','').replace('Trang tiếp theo','Nội dung mới')
        edit_chapter(b,'a',edited,expected=before)
        self.assertEqual(public_sections(b)[0]['text'],edited)
        self.assertEqual(''.join(s['text'] for s in b['segments'] if s['page']<2),edited)
        self.assertEqual([p['text'] for p in b['pages']],[p['text'] for p in original])
        self.assertTrue(b['sourceSegments']);self.assertEqual(b['segments'][-1]['id'],other)
        self.assertIn('Nội dung mới',''.join(b['segments'][i]['text'] for i in selected_indices(b,{'type':'page','page':2})))
        with self.assertRaises(ValueError):edit_chapter(b,'a','lost change',expected=before)
        edit_chapter(b,'a',public_sections(b)[0]['originalText'])
        self.assertEqual(public_sections(b)[0]['text'],before)
    def test_empty_chapter_and_long_text(self):
        edit_chapter(self.book,'a','')
        self.assertEqual(public_sections(self.book)[0]['text'],'')
        self.assertEqual(selected_indices(self.book,{'type':'chapter','chapterId':'a'}),[])
        value=('Chữ Việt còn nguyên.\n'*1500)+'Kết thúc.'
        edit_chapter(self.book,'a',value)
        self.assertEqual(public_sections(self.book)[0]['text'],value)
        self.assertTrue(all(len(s['text'])<=420 for s in self.book['segments']))
    def test_saved_take_survives_edits_voice_change_and_restart(self):
        b=self.book;indices=selected_indices(b,{'type':'chapter','chapterId':'a'})
        for i in indices:self.audio(b['segments'][i])
        take=audiobooks.create(b,indices,'Mở đầu',{'type':'chapter','chapterId':'a'});take['status']='ready';self.lib.save(b)
        saved_text=[s['text'] for s in take['segments']]
        edit_chapter(b,'a','Đã sửa hoàn toàn.');b['voice']='Mỹ Duyên';self.lib.save(b)
        reopened=self.lib.load(b['id']);saved=audiobooks.public(self.lib,b['id'],audiobooks.find(reopened,take['id']))
        self.assertEqual(saved['status'],'ready');self.assertEqual([s['text'] for s in saved['segments']],saved_text)
        self.assertEqual(saved['voice'],'Đức Trí')
        out=self.root/'saved.wav';self.lib.export(b['id'],out,take_id=take['id'])
        self.assertTrue(out.is_file())
        with self.assertRaises(ValueError):audiobooks.path(self.lib,b['id'],{'file':'../../escape.wav'})
    def test_legacy_cache_migration_and_noise_skip(self):
        b=self.book
        self.audio(b['segments'][0]);audiobooks.archive_existing(self.lib,b)
        self.assertEqual(len(b['audiobooks']),1)
        audiobooks.archive_existing(self.lib,b);self.assertEqual(len(b['audiobooks']),1)
        edit_chapter(b,'a','…\n..........\n***')
        self.assertEqual(selected_indices(b,{'type':'chapter','chapterId':'a'}),[])

if __name__=='__main__':unittest.main()
