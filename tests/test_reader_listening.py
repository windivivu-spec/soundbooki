import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import wave
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from worker import Worker
from reader_listening import prepare
from ebook_reader import assemble

class ReaderListeningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.root=Path(self.tmp.name);source=self.root/'book.pdf';source.write_bytes(b'fixture')
  self.worker=Worker(self.root/'library');self.book=self.worker.lib.create([source]);self.worker.lib.add_page(self.book,0,dict(page=0,text='Câu đầu phải bỏ qua. Câu thứ hai được chọn. Câu cuối đọc tiếp.',method='text',warning=''))
  self.book.update(status='ready',model='pro-cloud',voice='Giọng Pro',generationScope=dict(type='pages',fromPage=1,toPage=1));self.worker.lib.save(self.book);self.cues=assemble(self.book)['sentences']
 def tearDown(self):self.tmp.cleanup()
 def test_click_starts_at_exact_sentence_and_reads_on_using_only_lite(self):
  done=threading.Event();events=[];inputs=[]
  class Nano:
   def stream(_,request,job):
    self.assertEqual(request['model'],'nano');self.assertEqual(request['voice'],'Lite A')
    for s in request['segments']:
     inputs.append(s['text'])
     with wave.open(s['path'],'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*24000)
    yield dict(done=True)
  self.worker.nano=Nano()
  def event(**e):
   events.append(e)
   if e['event']=='readerBuffer':done.set()
  with patch('model_manager.voices',return_value=[dict(id='Lite A')]),patch('model_manager.ready',return_value=True),patch('model_manager.verified_location',return_value=self.root),patch('model_manager.revision',return_value='fixture-local'):
   prepare(self.worker,self.book['id'],'Lite A',self.cues[1]['id'],'selected',event);self.assertTrue(done.wait(2))
  self.assertEqual(inputs,[c['text'] for c in self.cues[1:]])
  self.assertEqual([e['cueId'] for e in events if e['event']=='readerAudioReady'],[c['id'] for c in self.cues[1:]])
  current=self.worker.lib.load(self.book['id']);self.assertEqual(current['model'],'pro-cloud');self.assertEqual(current['voice'],'Giọng Pro');self.assertEqual(current['segments'],self.book['segments']);self.assertFalse(current.get('audiobooks',[]))
 def test_reading_rejects_non_lite_voice_and_missing_cue(self):
  with patch('model_manager.voices',return_value=[dict(id='Lite A')]),patch('model_manager.ready',return_value=True):
   with self.assertRaisesRegex(ValueError,'Lite'):prepare(self.worker,self.book['id'],'Cloud voice',self.cues[0]['id'],'token',lambda **e:None)
   with self.assertRaisesRegex(ValueError,'Câu'):prepare(self.worker,self.book['id'],'Lite A','stale-cue','token',lambda **e:None)

if __name__=='__main__':unittest.main()
