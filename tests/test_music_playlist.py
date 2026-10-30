from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library,signature
from music import music_settings,music_unavailable
from exporting import MusicBed,mix_wav,export_book

ROOT=Path(__file__).resolve().parents[1]

class MusicPlaylistTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.root=Path(self.tmp.name)
        self.items=[]
        for name,value,duration in [('a',4000,1),('b',-8000,2)]:
            path=self.root/(name+'.wav')
            with wave.open(str(path),'wb') as w:
                w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(np.full(24000*duration,value,dtype='<i2').tobytes())
            self.items.append(dict(id=name,title=name,category='Jazz',path=str(path),duration=duration))
        self.mock=patch('music.catalog',return_value=self.items);self.mock.start()
    def tearDown(self):self.mock.stop();self.tmp.cleanup()
    def settings(self,loop=True):return dict(track='b',volume=.2,category='Jazz',mode='shuffle',playlist=['b','a'],loop=loop)
    def test_playlist_timeline_seek_loop_and_resampling(self):
        for rate in (24000,48000):
            bed=MusicBed(music_settings(self.settings()),rate)
            samples=bed.read(int(1.5*rate),3*rate)
            self.assertAlmostEqual(float(samples[int(.25*rate)]),-8000/32768,places=3)
            self.assertAlmostEqual(float(samples[int(.75*rate)]),4000/32768,places=3)
            self.assertAlmostEqual(float(samples[int(1.75*rate)]),-8000/32768,places=3)
            bed=MusicBed(music_settings(self.settings(False)),rate)
            self.assertTrue(np.all(bed.read(3*rate,rate)==0))
            self.assertGreater(np.max(np.abs(bed.read(int(2.5*rate),rate)[:rate//2])),0)
            self.assertTrue(np.all(bed.read(int(2.5*rate),rate)[rate//2:]==0))
    def test_invalid_order_and_missing_track_never_silently_export(self):
        for extra in ({'playlist':['b','b']},{'playlist':['a','b']},{'playlist':['b','missing']},{'category':'other'},{'loop':'false'}):
            with self.assertRaises(ValueError):music_settings(self.settings()|extra)
        saved=self.settings()|{'playlist':['b','missing']}
        self.assertTrue(music_unavailable(music_settings(saved,allow_unavailable=True)))
        with self.assertRaises(ValueError):mix_wav([],self.root/'bad.wav',saved)
    def test_saved_order_gain_loop_reopen_without_invalidating_narration(self):
        source=self.root/'source.epub';source.write_bytes(b'fixture')
        lib=Library(self.root/'library');book=lib.create([source]);lib.add_page(book,0,dict(page=0,text='Giữ nguyên giọng đọc.',method='text',warning=''))
        before=lib.audio_path(book,book['segments'][0]);book['music']=music_settings(self.settings(False));lib.save(book)
        reopened=lib.public(lib.load(book['id']))
        self.assertEqual(reopened['music'],self.settings(False));self.assertFalse(reopened['musicUnavailable'])
        self.assertEqual(lib.audio_path(reopened,reopened['segments'][0]),before)
    def test_real_exports_include_playlist_and_preserve_selection(self):
        source=self.root/'source.epub';source.write_bytes(b'fixture')
        lib=Library(self.root/'library');b=lib.create([source]);lib.add_page(b,0,dict(page=0,text='Một đoạn để kiểm tra nhạc.',method='text',warning=''))
        b['status']='ready';b['music']=music_settings(self.settings(False));lib.save(b)
        audio=lib.audio_path(b,b['segments'][0])
        with wave.open(str(audio),'wb') as w:
            w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(np.zeros(24000*5,dtype='<i2').tobytes())
        for ext in ('wav','m4a','zip'):
            dest=self.root/('mixed.'+ext);export_book(lib,b['id'],dest)
            self.assertGreater(dest.stat().st_size,100)
        with wave.open(str(self.root/'mixed.wav'),'rb') as w:out=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        self.assertLess(out[24000],-1000);self.assertGreater(out[int(2.5*24000)],500);self.assertEqual(out[4*24000],0)
        self.assertEqual(lib.load(b['id'])['music'],self.settings(False))

if __name__=='__main__':unittest.main()
