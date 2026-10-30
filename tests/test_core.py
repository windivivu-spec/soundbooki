import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library, split_text, signature, valid_audio
from engine import offline_guard

class CoreTests(unittest.TestCase):
    def test_verbatim_chunking(self):
        text=('Tiếng Việt: ă â đ. Version 1.5 vẫn giữ nguyên!\n\n' * 100)+'Kết thúc.'
        chunks=split_text(text)
        self.assertEqual(''.join(chunks),text)
        self.assertTrue(all(len(c)<=420 for c in chunks))
        self.assertTrue(all('1.' not in c[-2:] for c in chunks))
    def test_no_punctuation(self):
        text='ă'*1000
        self.assertEqual(''.join(split_text(text)),text)
        self.assertEqual(max(map(len,split_text(text))),420)
    def test_signature_invalidates(self):
        self.assertNotEqual(signature('Sách','Minh Quân'),signature('Sách mới','Minh Quân'))
        self.assertNotEqual(signature('Sách','Minh Quân'),signature('Sách','Mỹ Duyên'))
    def test_state_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); src=p/'sách.txt';src.write_text('Đọc sách')
            lib=Library(p/'library');b=lib.create([src]);lib.add_page(b,0,dict(page=0,text='Sách có dấu.',method='text',warning=''))
            self.assertEqual(b['segments'][0]['originalText'],'Sách có dấu.')
            lib.position(b['id'],0,3.25)
            reopened=Library(p/'library').load(b['id']);self.assertEqual(reopened['position']['seconds'],3.25)
            b=reopened;b['status']='ready';lib.save(b)
            with self.assertRaises(ValueError):lib.export(b['id'],p/'book.wav')
            audio=lib.audio_path(b,b['segments'][0])
            with wave.open(str(audio),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\1\0'*2400)
            self.assertTrue(valid_audio(audio));self.assertEqual(lib.public(b)['readyCount'],1)
            lib.export(b['id'],p/'book.wav');self.assertTrue(valid_audio(p/'book.wav'))
            b['segments'][0]['text']='Đã sửa';lib.save(b);self.assertEqual(lib.public(b)['readyCount'],0)
            with self.assertRaises(ValueError):lib.position(b['id'],5,0)
            with self.assertRaises(ValueError):lib.directory('../escape')
    def test_network_denied(self):
        import subprocess
        result=subprocess.run([sys.executable,'-c',"import sys,socket;sys.path.insert(0,'backend');from engine import offline_guard;offline_guard();socket.create_connection(('example.com',443))"],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('kết nối mạng bị tắt',result.stderr)

if __name__=='__main__':unittest.main()
