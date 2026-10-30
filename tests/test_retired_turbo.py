from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import features
import model_manager as models
from worker import Worker

class RetiredTurboTests(unittest.TestCase):
    def test_not_offered_or_downloadable(self):
        self.assertFalse(features.TURBO_ENABLED)
        self.assertNotIn('turbo',[m['id'] for m in models.catalog()['models']])
        with patch('urllib.request.urlopen') as network:
            with self.assertRaisesRegex(ValueError,'ngừng cung cấp'):models.install('turbo')
            network.assert_not_called()

    def test_legacy_book_can_switch_without_rewriting_text_or_deleting_audio(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);source=root/'fixture.txt';source.write_text('Giữ bản gốc.')
            worker=Worker(root/'library');b=worker.lib.create([source])
            worker.lib.add_page(b,0,dict(page=0,text='Một câu tiếng Việt.',method='text',warning=''))
            b.update(model='turbo',status='ready');worker.lib.save(b)
            old=worker.lib.audio_path(b,b['segments'][0]);old.write_bytes(b'legacy-cache')
            for action in (lambda:worker.generate(b['id']),lambda:worker.download_model('turbo'),lambda:worker.preview_voice({'model':'turbo'}),lambda:worker.handle({'action':'settings','bookId':b['id'],'model':'turbo'})):
                with self.assertRaisesRegex(ValueError,'ngừng cung cấp'):action()
            with patch('worker.emit'):
                worker.handle({'action':'settings','bookId':b['id'],'model':'nano'})
            current=worker.lib.load(b['id'])
            self.assertEqual(current['model'],'nano')
            self.assertEqual(current['segments'][0]['text'],'Một câu tiếng Việt.')
            self.assertEqual(current['segments'][0]['originalText'],'Một câu tiếng Việt.')
            self.assertEqual(old.read_bytes(),b'legacy-cache')
