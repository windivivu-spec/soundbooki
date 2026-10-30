import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch
import wave

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from worker import Worker
from nano_session import NanoSession

class ListeningTests(unittest.TestCase):
    def test_model_reused_and_error_reply_drained_before_next_request(self):
        p=Mock();p.poll.return_value=None;p.stdin=io.StringIO()
        p.stdout=io.StringIO('\n'.join(json.dumps(e) for e in [dict(error='fixture'),dict(requestDone=True),dict(segment='next'),dict(requestDone=True)])+'\n')
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp,patch('nano_session.subprocess.Popen',return_value=p) as launch:
            session=NanoSession(ROOT,Path(tmp)/'log')
            request=dict(model='nano',models='pinned',voice='voice',segments=[])
            with self.assertRaisesRegex(ValueError,'fixture'):list(session.stream(request,dict(cancel=threading.Event())))
            self.assertEqual(list(session.stream(request,dict(cancel=threading.Event()))),[dict(segment='next')])
            self.assertEqual(launch.call_count,1)
            self.assertEqual(len(p.stdin.getvalue().splitlines()),2)
            session.close()

    def exercise(self,change_voice=False):
        tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);source=root/'source.txt';source.write_text('fixture')
        worker=Worker(root/'library');self.addCleanup(worker.nano.close)
        b=worker.lib.create([source])
        for page in range(16):worker.lib.add_page(b,0,dict(page=page,text=f'Trang {page}. Giữ nguyên dấu tiếng Việt.',method='text',warning=''))
        b['status']='ready';worker.lib.save(b)
        calls=[];events=[];finished=threading.Event()
        def stream(request,job):
            calls.append(request)
            item=request['segments'][0];p=Path(item['path'])
            with wave.open(str(p),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x01\x00'*2400)
            if change_voice:
                current=worker.lib.load(b['id']);current['voice']='Mỹ Duyên';worker.lib.save(current)
                finished.set()
            yield dict(segment=item['id'],duration=.1)
        def emit(**event):
            events.append(event)
            if event['event']=='listeningBuffer':finished.set()
        with patch.object(worker.nano,'stream',side_effect=stream),patch('worker.emit',side_effect=emit),patch('worker.models.ready',return_value=True),patch('worker.models.verified_location',return_value=root):
            worker.prepare_listening(b['id'],0,{'type':'range','fromPage':3,'toPage':16},180,'fixture')
            self.assertTrue(finished.wait(3))
            # Ensure the worker has finished its stale-output check, too.
            for _ in range(100):
                if worker.listening is None:break
                threading.Event().wait(.01)
        return b,worker,calls,events

    def test_prefetch_is_bounded_selected_and_does_not_create_takes(self):
        b,worker,calls,events=self.exercise()
        ready=[e for e in events if e['event']=='listeningReady']
        self.assertEqual([e['index'] for e in ready],list(range(2,14)))
        self.assertEqual(len(calls),12)
        self.assertFalse(worker.lib.load(b['id']).get('audiobooks'))
        self.assertTrue(all(e['token']=='fixture' for e in ready))

    def test_changed_voice_never_receives_old_buffer(self):
        b,worker,calls,events=self.exercise(change_voice=True)
        self.assertEqual(len(calls),1)
        self.assertFalse(any(e['event']=='listeningReady' for e in events))
        self.assertEqual(worker.lib.public(worker.lib.load(b['id']))['readyCount'],0)
