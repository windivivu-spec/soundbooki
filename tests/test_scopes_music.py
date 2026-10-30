import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import wave
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library,valid_audio
from scopes import chapters,selected_indices,mark_chapter
from exporting import mix_wav,ExportCancelled,portable_page
from music import music_settings,catalog

class ScopeMusicTests(unittest.TestCase):
    def book(self):
        return dict(pages=[{}]*5,totalPages=5,segments=[{'page':i//2,'text':f'Câu {i}.'} for i in range(10)],chapters=[])
    def test_page_range_and_chapter(self):
        b=self.book()
        self.assertEqual(selected_indices(b,{'type':'page','page':2}),[2,3])
        self.assertEqual(selected_indices(b,{'type':'range','fromPage':2,'toPage':4}),list(range(2,8)))
        self.assertEqual(selected_indices(b,{'type':'all'}),list(range(10)))
        c=mark_chapter(b,2,'Chương hai')
        self.assertEqual(chapters(b)[0]['title'],'Phần mở đầu')
        self.assertEqual(selected_indices(b,{'type':'chapter','chapterId':c['id']}),list(range(4,10)))
        mark_chapter(b,4,'Chương ba')
        self.assertEqual(selected_indices(b,{'type':'chapter','chapterId':c['id']}),list(range(4,8)))
        with self.assertRaises(ValueError):selected_indices(b,{'type':'range','fromPage':4,'toPage':2})
        with self.assertRaises(ValueError):selected_indices(b,{'type':'page','page':6})
        with self.assertRaises(ValueError):selected_indices(b,{'type':'chapter','chapterId':'missing'})
    def test_chapter_replacement_and_unimported(self):
        b=self.book();mark_chapter(b,0,'Cũ');c=mark_chapter(b,0,'Mới')
        self.assertEqual(len(b['chapters']),1)
        self.assertEqual(b['chapters'][0]['title'],'Mới')
        b['totalPages']=7
        with self.assertRaises(ValueError):selected_indices(b,{'type':'chapter','chapterId':c['id']})
    def test_mix_loops_volume_and_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'voice.wav';out=p/'mixed.wav'
            t=np.arange(24000*36)/24000;voice=(np.sin(2*np.pi*220*t)*8000).astype('<i2')
            with wave.open(str(src),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(voice.tobytes())
            bed=p/'bed.wav'
            with wave.open(str(bed),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(voice[:24000].tobytes())
            fixture=[dict(id='fixture-bed',path=str(bed),category='QA')]
            with patch('music.catalog',return_value=fixture):mix_wav([src],out,{'track':'fixture-bed','volume':.3})
            self.assertTrue(valid_audio(out))
            with wave.open(str(out),'rb') as w:mix=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
            self.assertEqual(len(mix),len(voice));self.assertGreater(np.sqrt(np.mean((mix.astype(float)-voice)**2)),100)
            with patch('music.catalog',return_value=fixture):mix_wav([src],out,{'track':'fixture-bed','volume':0})
            with wave.open(str(out),'rb') as w:self.assertEqual(w.readframes(w.getnframes()),voice.tobytes())
            with self.assertRaises(ExportCancelled):mix_wav([src],out,{'track':'none','volume':0},cancelled=lambda:True)
            with self.assertRaises(ValueError):music_settings({'track':'bad','volume':.2})
            with self.assertRaises(ValueError):music_settings({'track':'none','volume':float('nan')})
    def test_missing_music_does_not_block_opening_or_erase_saved_selection(self):
        root=Path(__file__).resolve().parents[1]/'.qa'
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            folder=Path(tmp);source=folder/'source.epub';source.write_bytes(b'fixture')
            lib=Library(folder/'library');book=lib.create([source]);saved={'track':'private-demo-not-bundled','volume':.23}
            book['music']=saved;lib.save(book)
            with patch('music.catalog',return_value=[]):
                public=lib.public(book)
                self.assertTrue(public['musicUnavailable']);self.assertEqual(public['music'],saved)
                self.assertEqual(lib.load(book['id'])['music'],saved)
                with self.assertRaises(ValueError):music_settings(saved)
    def test_safe_portable_player(self):
        files=portable_page('<script>alert(1)</script>',[{'page':0,'index':0,'text':'</script>Tiếng Việt'}],[2.5])
        self.assertNotIn('<script>alert(1)</script>',files['index.html'])
        self.assertIn('&lt;script&gt;',files['index.html'])
        self.assertEqual(json.loads(files['book.json'])['segments'][0]['text'],'</script>Tiếng Việt')
        self.assertEqual(set(files),{'index.html','player.css','player.js','book.json','book.js'})

if __name__=='__main__':unittest.main()
