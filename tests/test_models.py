import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import model_manager as models
from core import signature,Library

class Response(io.BytesIO):
    def __init__(self,data,status=200,headers=None):
        super().__init__(data);self.status=status;self.headers=headers or {}

class ModelTests(unittest.TestCase):
    def setUp(self):
        turbo=patch.object(models.features,'TURBO_ENABLED',True);turbo.start();self.addCleanup(turbo.stop)
        # A consumer release.json must never redirect fixtures to user resources.
        resources=patch.object(models,'resource_root',side_effect=lambda:models.ROOT/'.resources')
        resources.start();self.addCleanup(resources.stop)

    def fixture(self,root):
        payload=b'verified-model-resource'
        item=dict(file='model.bin',size=len(payload),sha256=hashlib.sha256(payload).hexdigest(),url='https://example.invalid/model',revision='fixture')
        (root/'backend').mkdir()
        data=dict(revision='fixture',files=[item])
        for name in ('models.json','models-turbo.json'):(root/'backend'/name).write_text(json.dumps(data))
        return payload,item

    def test_resume_and_atomic_install(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(models,'ROOT',Path(tmp)):
            root=Path(tmp);payload,item=self.fixture(root)
            folder=root/'.resources/tts-turbo';folder.mkdir(parents=True)
            partial=folder/'model.bin.download';partial.write_bytes(payload[:5])
            events=[]
            def fetch(request,timeout):
                self.assertEqual(request.get_header('Range'),'bytes=5-')
                return Response(payload[5:],206,{'Content-Range':f'bytes 5-{len(payload)-1}/{len(payload)}'})
            with patch('urllib.request.urlopen',fetch):models.install('turbo',lambda **e:events.append(e))
            self.assertEqual((folder/'model.bin').read_bytes(),payload)
            self.assertFalse(partial.exists());self.assertTrue(models.ready('turbo'))
            self.assertEqual(models.verified_location('turbo'),folder)
            self.assertEqual(events[-1]['phase'],'ready')
            self.assertEqual(json.loads((root/'.resources/config.json').read_text())['profiles']['turbo'],str(folder))
            # Same-size corruption must hide "ready" and offer a repair download.
            (folder/'model.bin').write_bytes(b'x'*len(payload))
            self.assertFalse(models.ready('turbo'))
            with self.assertRaisesRegex(ValueError,'bị lỗi'):models.verified_location('turbo')
            with patch('urllib.request.urlopen',return_value=Response(payload)):models.install('turbo')
            self.assertTrue(models.ready('turbo'))

    def test_server_ignores_range_and_corrupt_file_never_ready(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(models,'ROOT',Path(tmp)):
            root=Path(tmp);payload,item=self.fixture(root)
            folder=root/'.resources/tts-turbo';folder.mkdir(parents=True)
            (folder/'model.bin.download').write_bytes(payload[:4])
            with patch('urllib.request.urlopen',return_value=Response(payload)):models.install('turbo')
            self.assertEqual((folder/'model.bin').read_bytes(),payload)
            (folder/'model.bin').unlink()
            with patch('urllib.request.urlopen',return_value=Response(b'x'*len(payload))):
                with self.assertRaisesRegex(ValueError,'bị lỗi'):models.install('turbo')
            self.assertFalse(models.ready('turbo'))
            self.assertFalse((folder/'model.bin.download').exists())
            self.assertFalse((folder/'model.bin').exists())

    def test_profile_cache_compatibility_and_voice_mapping(self):
        text='Giữ nguyên giọng đọc.';voice='Minh Quân'
        legacy=hashlib.sha256(json.dumps(['vieneu-3.8.1-nano-aba295eb-16steps-v1',voice,text],ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(signature(text,voice),legacy)
        self.assertNotEqual(signature(text,voice,'turbo'),legacy)
        self.assertEqual(models.resolve_voice('turbo','Minh Quân'),'Minh Quân Pro')
        self.assertEqual(models.resolve_voice('nano','Minh Quân Pro'),'Đức Trí')
        with self.assertRaises(ValueError):models.profile('../escape')

    def test_hardware_recommendation_is_not_speed_claim(self):
        with patch.object(models,'hardware',return_value=dict(memoryGB=16,cores=10,architecture='arm64')):
            self.assertTrue(all(m['supported'] for m in models.catalog()['models']))
        with patch.object(models,'hardware',return_value=dict(memoryGB=8,cores=8,architecture='arm64')):
            turbo=models.catalog()['models'][1]
            self.assertTrue(turbo['supported']);self.assertIn('16 GB',turbo['hardwareNote'])
        with patch.object(models,'hardware',return_value=dict(memoryGB=4,cores=2,architecture='arm64')):
            self.assertFalse(models.catalog()['models'][1]['supported'])
        with patch.object(models,'hardware',return_value=dict(memoryGB=16,cores=8,architecture='x86_64')):
            self.assertFalse(models.catalog()['models'][1]['supported'])

if __name__=='__main__':unittest.main()
