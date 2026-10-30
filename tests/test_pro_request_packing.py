import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from cloud_chunking import chunks, source_items
from book_pricing import snapshot, trial_snapshot, VOICES
from core import Library, valid_audio
import book_cloud as cloud


class ProRequestPackingTests(unittest.TestCase):
    def book(self,text):
        return dict(title='QA Pro',status='ready',voice=VOICES[0]['id'],model='pro-cloud',language='vi',
                    pages=[dict(text=text)],totalPages=1,chapters=[],
                    segments=[dict(id=f'{i:032x}',page=0,text=text[at:at+360]) for i,at in enumerate(range(0,len(text),360))])

    def test_4977_characters_from_fourteen_reader_segments_is_one_request(self):
        text=('Tiếng Việt 😀 và dấu a\u0301 vẫn nguyên vẹn. '*150)[:4977]
        b=self.book(text);before=json.dumps(b,ensure_ascii=False)
        self.assertEqual(len(b['segments']),14)
        for data in (snapshot(b),trial_snapshot(b)):
            self.assertEqual([s['text'] for s in data['segments']],[text])
            self.assertEqual(data['chunkingVersion'],'heygen-5000-v1')
            self.assertEqual(len(source_items(data)),14)
        self.assertEqual(json.dumps(b,ensure_ascii=False),before)

    def test_over_limit_preserves_all_text_and_packs_across_paragraphs(self):
        for text in [('Câu văn tiếng Việt có dấu 😀.\n\n'*1000), ('câu rất dài, '*1000)+'.', 'ă'*12001,
                     ('a\u0301'*6001), ('Đây là đoạn bình thường. '*300)+'GS.TS. Nguyễn ở TP.HCM có 15.5 năm kinh nghiệm.']:
            with self.subTest(length=len(text)):
                parts=chunks(text)
                self.assertEqual(''.join(parts),text)
                self.assertTrue(all(0<len(p)<=5000 for p in parts))
                self.assertTrue(all(len(p)>=4250 for p in parts[:-1]))
        self.assertEqual(chunks('a'*5000),['a'*5000])
        self.assertEqual(list(map(len,chunks('a'*5001))),[5000,1])

    def test_sentence_and_abbreviation_boundaries_do_not_rewrite(self):
        text='Một câu hoàn chỉnh. '*240+'GS.TS. Nguyễn có 15.5 năm kinh nghiệm. '+('Câu tiếp theo. '*200)
        parts=chunks(text)
        self.assertEqual(''.join(parts),text)
        self.assertTrue(parts[0].rstrip().endswith('.'))
        self.assertFalse(parts[0].rstrip().endswith(('GS.','GS.TS.','15.')))
        self.assertEqual(chunks('a'*4800+'. '+('b'*300)+'.')[0],'a'*4800+'. ')

    def test_real_chapter_boundaries_and_export_labels_survive_packing(self):
        from m4b import freeze_labels
        b=self.book('Chương một. '*300+'Chương hai. '*300)
        b.update(chapterModel='segments-v1',chapters=[dict(id='one',title='Chương 1',startPage=0),dict(id='two',title='Chương 2',startPage=0)])
        for i,s in enumerate(b['segments']):s['chapterId']='one' if i<10 else 'two'
        data=snapshot(b);labels=freeze_labels(b,data['segments'])
        self.assertEqual(len(data['segments']),2)
        self.assertEqual([labels[s['id']]['chapterId'] for s in data['segments']],['one','two'])
        self.assertEqual(''.join(s['text'] for s in data['segments']),''.join(s['text'] for s in b['segments']))

    def test_legacy_paid_and_trial_retry_keep_exact_body_after_upgrade(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);source=root/'source.txt';source.write_text('QA')
            lib=Library(root/'library');b=lib.create([source]);b.update(self.book('Sách thử nghiệm. '*400));lib.save(b)
            raw=[dict(id=s['id'],page=s['page'],index=i,text=s['text']) for i,s in enumerate(b['segments'])]
            old=snapshot(b)|dict(segments=raw);old.pop('chunkingVersion')
            trial=cloud.trial_reference(b,None,1);trial.pop('chunkingVersion')
            b['cloudOrders']=[dict(kind='book',requestKey='a'*32,snapshot=old,order=None),dict(kind='trial',requestKey='b'*32,snapshot=trial,order=None)];lib.save(b)
            self.assertEqual(cloud.local_info(b)['pendingQuoteKey'],'a'*32)
            self.assertEqual(cloud.local_info(b)['pendingTrialKey'],'b'*32)
            fake=Mock();fake.post.return_value=dict(order=dict(id='11111111-1111-1111-1111-111111111111',kind='book',state='awaiting_payment'))
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'book','a'*32,True)
                self.assertEqual(fake.post.call_args.kwargs['snapshot'],old)
                fake.post.return_value=dict(order=dict(id='22222222-2222-2222-2222-222222222222',kind='trial',state='queued'))
                cloud.create_order(lib,b['id'],'trial','b'*32,True)
                self.assertEqual(fake.post.call_args.kwargs['snapshot'],trial)

    def test_cached_legacy_trial_reopens_as_one_exportable_immutable_take(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);source=root/'source.txt';source.write_text('QA')
            lib=Library(root/'library');b=lib.create([source]);b.update(self.book('Bản thử nguyên vẹn. '*200))
            data=trial_snapshot(b);order=dict(id='11111111-1111-1111-1111-111111111111',kind='trial',state='ready')
            b['cloudOrders']=[dict(kind='trial',requestKey='a'*32,snapshot=data,order=order)]
            lib.save(b);folder=lib.directory(b['id'])/'cloud-trials';folder.mkdir()
            originals=[]
            for segment in data['segments']:
                path=folder/(cloud.cloud_signature(segment,data)+'.wav')
                with wave.open(str(path),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x01\x00'*2400)
                originals.append(path.read_bytes())
            with patch.object(cloud,'Client') as client:
                first=lib.load(b['id']);second=lib.load(b['id']);client.assert_not_called()
            self.assertEqual(len(first['audiobooks']),1);self.assertEqual(first['audiobooks'],second['audiobooks'])
            take=first['audiobooks'][0];self.assertEqual(take['status'],'ready');self.assertEqual(take['cloudKind'],'trial')
            first['segments'][0]['text']='Nội dung đã sửa';first['voice']=VOICES[1]['id'];lib.save(first)
            dest=root/'trial.wav';lib.export(b['id'],dest,take_id=take['id']);self.assertTrue(valid_audio(dest))
            with wave.open(str(dest),'rb') as w:self.assertEqual(w.readframes(w.getnframes()),b'\x01\x00'*2400*len(data['segments']))
            self.assertEqual([p.read_bytes() for p in folder.glob('*.wav')],originals)
