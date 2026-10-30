"""Fixture checks only: no inference/training quality claims."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave
from array import array
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('toolkit',Path(__file__).with_name('toolkit.py'))
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)
QA = Path(__file__).resolve().parents[2]/'.qa/training-tests'


class TrainingTests(unittest.TestCase):
    def setUp(self):
        QA.mkdir(parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=QA)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self,n=35):
        (self.root/'clips').mkdir()
        items=[]
        for i in range(n):
            path=self.root/'clips'/f'{i:03}.wav'
            with wave.open(str(path),'wb') as f:
                f.setparams((1,2,22050,0,'NONE','not compressed'))
                f.writeframes(array('h',[1000,-1000]*22050).tobytes())
            text=f'Đây là câu thứ {i}, giữ nguyên tiếng Việt: “Sách và đời”.'
            items.append(dict(id=str(i),audio=f'clips/{i:03}.wav',start=i*3,end=i*3+2,
                              duration=2,originalText=text,text=text,approved=True,flags=[]))
        data=dict(status='awaiting_review',sourceSha256='fixture',segments=items)
        kit.atomic_json(self.root/'review.json',data)
        return data

    def test_unreviewed_never_becomes_training(self):
        d=self.fixture()
        for s in d['segments']: s['approved']=False
        kit.atomic_json(self.root/'review.json',d)
        with self.assertRaisesRegex(ValueError,'tối thiểu'): kit.make_dataset(self.root)
        self.assertFalse((self.root/'dataset/metadata.csv').exists())

    def test_holdout_disjoint_and_unicode_verbatim(self):
        original=self.fixture()
        report=kit.make_dataset(self.root)
        with (self.root/'dataset/metadata.csv').open(newline='') as f:
            rows=list(csv.reader(f,delimiter='|'))
        hold=json.loads((self.root/'dataset/holdout.json').read_text())
        self.assertEqual(rows[0][1],original['segments'][0]['text'])
        self.assertFalse({r[1] for r in rows} & {s['text'] for s in hold})
        self.assertEqual(report['trainClips']+report['holdoutClips'],35)
        self.assertEqual(json.loads((self.root/'review.json').read_text()),original)

    def test_duplicate_does_not_cross_holdout(self):
        d=self.fixture()
        d['segments'][-1]['text']=d['segments'][0]['text']
        kit.atomic_json(self.root/'review.json',d)
        report=kit.make_dataset(self.root)
        self.assertEqual(report['trainClips']+report['holdoutClips'],34)

    def test_escape_rejected(self):
        d=self.fixture(); d['segments'][0]['audio']='../outside.wav'
        kit.atomic_json(self.root/'review.json',d)
        with self.assertRaisesRegex(ValueError,'vượt ngoài'): kit.make_dataset(self.root)

    def test_interrupted_preparation_cannot_train(self):
        d=self.fixture(); d['status']='preparing'
        kit.atomic_json(self.root/'review.json',d)
        with self.assertRaisesRegex(ValueError,'chưa hoàn tất'): kit.make_dataset(self.root)

    def test_empty_audio_rejected(self):
        d=self.fixture()
        with wave.open(str(self.root/d['segments'][0]['audio']),'wb') as f:
            f.setparams((1,2,22050,0,'NONE','not compressed'))
        with self.assertRaisesRegex(ValueError,'rỗng'): kit.make_dataset(self.root)

    def test_phrase_segmentation_keeps_every_word_verbatim(self):
        words=[SimpleNamespace(word=w,start=i,end=i+.9) for i,w in enumerate(
            ['Xin',' chào',' bạn',' nhé,',' tôi',' đang',' đọc',' sách.',' Giữ',' nguyên',' dấu',' nhé!'])]
        groups=list(kit.word_groups([SimpleNamespace(words=words)],max_seconds=5))
        self.assertEqual(''.join(w.word for g in groups for w in g),''.join(w.word for w in words))
        self.assertEqual(groups[0][-1].word,' nhé,')
        self.assertTrue(all(len(g)>0 for g in groups))

    def test_long_pause_is_a_boundary_without_dropping_speech(self):
        words=[SimpleNamespace(word='Lời đầu',start=0,end=3),
               SimpleNamespace(word=' Lời sau.',start=5,end=8)]
        groups=list(kit.word_groups([SimpleNamespace(words=words)]))
        self.assertEqual(groups,[[words[0]],[words[1]]])

    def test_dataset_records_actual_audio_and_profile(self):
        self.fixture()
        report=kit.make_dataset(self.root)
        self.assertFalse(report['profile']['trimSilence'])
        clip=self.root/'dataset/audio/0.wav'
        self.assertEqual(report['audioSha256']['0.wav'],kit.digest(clip))
        clip.write_bytes(b'changed after review')
        self.assertNotEqual(report['audioSha256']['0.wav'],kit.digest(clip))

    def test_notebook_is_self_contained_and_train_off(self):
        book=json.loads(Path(__file__).with_name('Windi_SachNoi_GiongNho_Piper.ipynb').read_text())
        for i,c in enumerate(book['cells']):
            if c['cell_type']=='code': compile(''.join(c['source']),f'cell-{i}','exec')
        all_code='\n'.join(''.join(c['source']) for c in book['cells'] if c['cell_type']=='code')
        self.assertIn('START_TRAINING = False',all_code)
        self.assertIn('MOUNT_DRIVE = False',all_code)
        self.assertIn('UPLOAD_RECORDING = False',all_code)


if __name__=='__main__': unittest.main()
