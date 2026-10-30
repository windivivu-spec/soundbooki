import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import model_manager as models
from core import Library, signature
from narration_text import plan_f5_prosody, prepare_f5_text


class PrivateVoiceTests(unittest.TestCase):
    def test_retired_voices_stay_hidden_even_with_old_files(self):
        from f5_engine import F5Engine
        with tempfile.TemporaryDirectory() as tmp,patch.object(models,'ROOT',Path(tmp)):
            root=Path(tmp);(root/'backend').mkdir()
            folder=root/'.resources/tts-f5-private';folder.mkdir(parents=True)
            files=[]
            for name in ['model.pt','voices/voice-002/model.pt','voices/voice-005/model.pt','voices/voice-006/model.pt']:
                p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
                if 'voice-002' in name or 'voice-006' in name:
                    files.append(dict(file=name,size=7,sha256=hashlib.sha256(b'fixture').hexdigest()))
            (root/'backend/models-f5-private.json').write_text(json.dumps(dict(files=files,defaultVoice='voice-002',excludedVoices=['voice-001','voice-005'])))
            available=models.voices('f5-private',root=folder)
            self.assertEqual([v['id'] for v in available],['voice-002','voice-006'])
            self.assertEqual([v['id'] for v in available if v['default']],['voice-002'])
            engine=F5Engine.__new__(F5Engine);engine.root=folder
            self.assertEqual([vid for label,vid in engine.list_preset_voices()],['voice-002','voice-006'])

    def test_curating_voices_keeps_remaining_audio_cache(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(models,'ROOT',Path(tmp)):
            root=Path(tmp);(root/'backend').mkdir();p=root/'backend/models-f5-private.json'
            data=dict(revision='eight-voices',inferenceRevision='same-checkpoints',files=[])
            p.write_text(json.dumps(data));models.revision.cache_clear()
            before=signature('Giữ bản đã tạo.','voice-002','f5-private')
            data['revision']='six-voices';p.write_text(json.dumps(data));models.revision.cache_clear()
            self.assertEqual(signature('Giữ bản đã tạo.','voice-002','f5-private'),before)
            data['inferenceRevision']='new-checkpoints';p.write_text(json.dumps(data));models.revision.cache_clear()
            self.assertNotEqual(signature('Giữ bản đã tạo.','voice-002','f5-private'),before)
        models.revision.cache_clear()

    def test_book_heading_and_author_are_synthesis_only(self):
        source='NHỮNG CƠ HỘI TUYỆT VỜI\n\n“Cơ hội đến với bạn!”\n-Khuyết Danh-'
        spoken=prepare_f5_text(source)
        self.assertEqual(spoken,'những cơ hội tuyệt vời.\n\ncơ hội đến với bạn!\nkhuyết danh.')
        self.assertEqual(prepare_f5_text('– Khuyết danh –'),'khuyết danh.')
        self.assertEqual(prepare_f5_text('— CHÀO BẠN —'),'chào bạn.')
        self.assertEqual(prepare_f5_text('---\n***\n• Nội dung.'),'nội dung.')
        self.assertEqual(prepare_f5_text('Giá trị -5; bản 1.5.'),'giá trị âm 5, bản 1.5.')
        self.assertEqual(prepare_f5_text('Tỉ lệ 5%, A+B.'),'tỉ lệ 5%, a+b.')
        self.assertEqual(prepare_f5_text('CƠ HỘI'),'cơ hội.')
        units=plan_f5_prosody('GIỚI THIỆU\n\nCuốn sách giúp bạn:\n\n• Tư duy thông minh hơn\n\n• Giá trị -5; bản 1.5.')
        self.assertEqual([u['text'] for u in units],[
            'giới thiệu.',
            'cuốn sách giúp bạn.',
            'tư duy thông minh hơn.',
            'giá trị âm 5.',
            'bản 1.5.',
        ])
        self.assertGreaterEqual(units[0]['pause'],0.68)
        self.assertGreaterEqual(units[2]['pause'],0.55)

    def test_private_assets_fail_closed_without_network(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(models,'ROOT',Path(tmp)):
            root=Path(tmp);(root/'backend').mkdir()
            folder=root/'.resources/tts-f5-private';folder.mkdir(parents=True)
            (root/'.runtime-f5/bin').mkdir(parents=True);(root/'.runtime-f5/bin/python').touch()
            files=[]
            for name in ['model.pt','vocab.txt','ref_audio.wav','ref_text.txt','vocos/config.yaml','vocos/pytorch_model.bin']:
                path=folder/name;path.parent.mkdir(exist_ok=True)
                payload=name.encode();path.write_bytes(payload)
                files.append(dict(file=name,size=len(payload),sha256=hashlib.sha256(payload).hexdigest()))
            (root/'backend/models-f5-private.json').write_text(json.dumps(dict(revision='test',files=files)))
            with patch('urllib.request.urlopen',side_effect=AssertionError('No private download')):
                self.assertTrue(models.ready('f5-private'))
                (folder/'ref_text.txt').write_bytes(b'x'*len(b'ref_text.txt'))
                self.assertFalse(models.ready('f5-private'))
                with self.assertRaisesRegex(ValueError,'bị lỗi'):models.verified_location('f5-private')
                with self.assertRaisesRegex(ValueError,'Gói giọng riêng'):models.install('f5-private')

    def test_new_voice_cache_and_speed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.txt';source.write_text('Sách tiếng Việt.')
            lib=Library(root/'lib');b=lib.create([source]);lib.add_page(b,0,dict(page=0,text='Sách tiếng Việt.',method='text',warning=''))
            s=b['segments'][0];old=lib.audio_path(b,s)
            b.update(model='f5-private',voice='voice-001');new=lib.audio_path(b,s)
            self.assertNotEqual(old,new)
            b['speed']=1.5;self.assertEqual(new,lib.audio_path(b,s))
            s['text']+=' Mới.';self.assertNotEqual(new,lib.audio_path(b,s))
            self.assertEqual(s['originalText'],'Sách tiếng Việt.')
            with patch.object(models,'voices',return_value=[dict(id='voice-002',aliases=['legacy-voice'],default=True)]):
                self.assertEqual(models.resolve_voice('f5-private','legacy-voice'),'voice-002')
            self.assertNotEqual(signature('Một câu.','voice-001','f5-private'),signature('Một câu.','Minh Quân','nano'))


if __name__=='__main__':unittest.main()
