from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
import book_cloud as cloud
from book_pricing import price,sample_segments,trial_snapshot,chapter_trial_units,snapshot,TRIAL_LIMIT,TRIAL_CHARACTERS,TRIAL_MAX_UNITS,VOICES
import model_manager as models
from worker import Worker

class BookCommerceTests(unittest.TestCase):
    def book(self,root):
        source=root/'fixture.txt';source.write_text('source')
        lib=Library(root/'library');b=lib.create([source])
        lib.add_page(b,0,dict(page=0,text='Bìa sách và lời tựa.',method='text',warning=''))
        lib.add_page(b,0,dict(page=1,text=('Tiếng Việt giữ nguyên dấu. '*240),method='text',warning=''))
        lib.add_page(b,0,dict(page=2,text='Chương tiếp theo không có trong mẫu thử.',method='text',warning=''))
        b.update(status='ready',model='pro-cloud',voice=VOICES[0]['id'],chapters=[dict(id='one',title='Chương 1',startPage=1,origin='epub'),dict(id='two',title='Chương 2',startPage=2,origin='epub')]);lib.save(b)
        return lib,b
    def test_prices_boundaries_and_no_speed_dependency(self):
        for n,amount in [(1,10000),(500,10000),(27000,10000),(27001,25000),(54000,25000),(54001,40000),(108000,40000),(108001,50000),(216000,60000),(216001,70000)]:self.assertEqual(price(n)['amountVND'],amount)
        for n in (0,-1,True,2_000_001):
            with self.assertRaises(ValueError):price(n)
    def test_trial_starts_at_real_chapter_and_preserves_text(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));original=json.dumps(b,ensure_ascii=False)
            segments=sample_segments(b);text=''.join(s['text'] for s in segments)
            self.assertEqual(text,b['pages'][1]['text'][:5000]);self.assertEqual(len(text),5000)
            self.assertEqual(json.dumps(b,ensure_ascii=False),original)
            b['chapters']=[];self.assertTrue(''.join(s['text'] for s in sample_segments(b)).startswith(b['pages'][0]['text']))
    def test_only_trial_excerpt_sent_and_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));fake=Mock();fake.post.return_value=dict(order=dict(id='11111111-1111-1111-1111-111111111111',state='queued',kind='trial'),trialsRemaining=9,trialLimit=10,trialCharacters=5000)
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'trial','a'*32,True);cloud.create_order(lib,b['id'],'trial','a'*32,True)
                a=fake.post.call_args_list[0].kwargs;c=fake.post.call_args_list[1].kwargs
                self.assertEqual(a,c);self.assertLessEqual(sum(len(s['text']) for s in a['snapshot']['segments']),5000)
                self.assertNotIn('Chương tiếp theo',str(a));self.assertEqual(lib.load(b['id'])['cloudTrialsRemaining'],9)
                with self.assertRaises(ValueError):cloud.create_order(lib,b['id'],'book','b'*32,False)
                self.assertEqual(fake.post.call_count,2)
    def test_generation_cannot_bypass_order_or_implicitly_spend(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);lib,b=self.book(root);worker=Worker(lib.root)
            with patch.object(cloud,'Client') as client:
                with self.assertRaisesRegex(ValueError,'thanh toán'):worker.generate(b['id'])
                with self.assertRaises(ValueError):worker.preview_voice(dict(model='pro-cloud'))
                cloud.local_info(b);models.catalog();client.assert_not_called()
    def test_paid_snapshot_survives_edits_and_requires_new_price(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));fake=Mock();fake.post.return_value=dict(order=dict(id='11111111-1111-1111-1111-111111111111',kind='book',state='awaiting_payment'),trialsRemaining=10,trialLimit=10,trialCharacters=5000)
            with patch.object(cloud,'Client',return_value=fake):cloud.create_order(lib,b['id'],'book','a'*32,True)
            saved=lib.load(b['id']);saved['segments'][0]['text']+=' Nội dung mới.';lib.save(saved)
            self.assertIsNone(cloud.local_info(saved)['savedOrder'])
            with patch.object(cloud,'Client') as client:
                with self.assertRaisesRegex(ValueError,'đã đổi'):cloud.create_order(lib,b['id'],'book','a'*32,True)
                client.assert_not_called()
    def test_trial_policy_upgrade_retains_already_used_allowance(self):
        self.assertEqual((TRIAL_LIMIT,TRIAL_CHARACTERS),(5,5000))
        for old_remaining in (0,1,3):
            self.assertEqual(cloud.cached_trials_remaining(dict(trialsRemaining=old_remaining)),2+old_remaining)
        self.assertEqual(cloud.cached_trials_remaining(dict(trialsRemaining=0,trialLimit=10)),0)
        for used in range(11):
            self.assertEqual(cloud.cached_trials_remaining(dict(trialsRemaining=10-used,trialLimit=10)),max(0,5-used))
            self.assertEqual(cloud.trial_state(dict(trialsRemaining=10-used,trialLimit=10)),dict(trialsRemaining=max(0,5-used),trialLimit=5))
        self.assertEqual(cloud.cached_trials_remaining({}),5)
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));b['cloudTrialsRemaining']=0
            self.assertEqual(cloud.local_info(b)['trialsRemaining'],2)
            b['cloudTrialsLimit']=10
            self.assertEqual(cloud.local_info(b)['trialsRemaining'],0)
    def test_trial_limit_counts_unicode_without_normalizing_original(self):
        b=dict(pages=[dict(text='Unicode fixture')],segments=[dict(id='a'*32,page=0,text=('a\u0301 Việt 😀. '*800))],chapters=[])
        original=b['segments'][0]['text']
        self.assertEqual(''.join(s['text'] for s in sample_segments(b)),original[:5000])
        self.assertEqual(b['segments'][0]['text'],original)
    def test_missing_service_does_not_persist_order_or_use_a_trial(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));before=lib.load(b['id'])
            with patch.object(cloud,'endpoint',return_value=''),patch.object(cloud,'credential') as credential:
                with self.assertRaisesRegex(ValueError,'chưa kết nối'):
                    cloud.create_order(lib,b['id'],'trial','f'*32,True,chapter_id='one')
                credential.assert_not_called()
            self.assertEqual(lib.load(b['id']),before)
            self.assertFalse((lib.root.parent/'book-cloud-state.json').exists())
    def test_confirmation_reuses_only_the_selected_chapter_trial(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));fake=Mock()
            trial=dict(id='11111111-1111-1111-1111-111111111111',kind='trial',state='queued')
            paid=dict(id='22222222-2222-2222-2222-222222222222',kind='book',state='awaiting_payment')
            fake.post.side_effect=[dict(order=trial,trialsRemaining=9,trialLimit=10),dict(order=paid,trialsRemaining=9,trialLimit=10)]
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'trial','e'*32,True,chapter_id='one')
                cloud.create_order(lib,b['id'],'book','d'*32,True)
            current=lib.load(b['id']);info=cloud.local_info(current,chapter_id='one')
            self.assertEqual(info['savedTrialOrder'],trial)
            self.assertEqual(info['savedOrder'],paid)
            self.assertIsNone(cloud.local_info(current,chapter_id='two')['savedTrialOrder'])
    def test_provider_44100_wav_is_verified_then_adapted_for_mac_playback(self):
        import io,wave,math
        import numpy as np
        source=io.BytesIO()
        tone=np.array([math.sin(2*math.pi*440*n/44100)*12000 for n in range(4410)],dtype='<i2')
        with wave.open(source,'wb') as w:w.setparams((1,2,44100,0,'NONE','not compressed'));w.writeframes(tone.tobytes())
        raw=source.getvalue();adapted=cloud.prepare_cloud_audio(raw,{'revision':'pro-cloud-heygen-v1'})
        with wave.open(io.BytesIO(adapted),'rb') as w:
            self.assertEqual((w.getnchannels(),w.getsampwidth(),w.getframerate()),(1,2,24000));self.assertEqual(w.getnframes(),2400)
            result=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
            self.assertLess(abs(float(np.sqrt(np.mean(result.astype(float)**2)))-12000/math.sqrt(2)),30)
        self.assertEqual(cloud.prepare_cloud_audio(raw,{'revision':'pro-cloud-modal-v1'}),raw)
        with self.assertRaises(ValueError):cloud.prepare_cloud_audio(raw[:-10],{'revision':'pro-cloud-heygen-v1'})

    def test_capability_check_is_explicit_and_never_sends_book_text(self):
        fake=Mock();fake.post.return_value=dict(trialAvailable=True,purchaseAvailable=False,trialsRemaining=4,trialLimit=5)
        with patch.object(cloud,'Client',return_value=fake):
            result=cloud.service_info()
        fake.post.assert_called_once_with('profile',timeout=8)
        self.assertTrue(result['trialAvailable']);self.assertFalse(result['purchaseAvailable'])
        self.assertEqual(result['trialsRemaining'],4);self.assertTrue(result['paymentRequired'])

    def test_cached_sample_opens_without_network_and_does_not_become_a_book_order(self):
        import wave
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));data=trial_snapshot(b,'two',1)
            order=dict(id='11111111-1111-1111-1111-111111111111',kind='trial',state='ready',total=len(data['segments']))
            b['cloudOrders']=[dict(kind='trial',snapshot=data,order=order,requestKey='a'*32)]
            folder=lib.directory(b['id'])/'cloud-trials';folder.mkdir()
            for segment in data['segments']:
                with wave.open(str(folder/(cloud.cloud_signature(segment,data)+'.wav')),'wb') as audio:
                    audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\0\0'*2400)
            with patch.object(cloud,'Client') as client:
                info=cloud.local_info(b,lib.root,chapter_id='two');client.assert_not_called()
            self.assertIsNone(info['savedOrder']);self.assertEqual(info['savedTrialOrder'],order)
            self.assertEqual(len(info['trialAudio']),order['total'])

    def test_ready_idempotent_submission_receives_audio_without_new_trial(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));fake=Mock();oid='11111111-1111-1111-1111-111111111111'
            fake.post.return_value=dict(order=dict(id=oid,kind='trial',state='ready',done=1,total=1))
            with patch.object(cloud,'Client',return_value=fake),patch.object(cloud,'sync_order',return_value={'localReady':True}) as receive:
                self.assertEqual(cloud.create_order(lib,b['id'],'trial','a'*32,True),{'localReady':True})
            self.assertEqual(fake.post.call_count,1);receive.assert_called_once_with(lib,b['id'],oid,on_progress=None)

    def test_unpaid_order_cannot_download_or_create_a_usable_take(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));data=snapshot(b);oid='11111111-1111-1111-1111-111111111111'
            b['cloudOrders']=[dict(kind='book',snapshot=data,order=dict(id=oid,state='awaiting_payment'))];lib.save(b)
            fake=Mock();fake.post.return_value=dict(order=dict(id=oid,state='awaiting_payment'),audio=[{'id':data['segments'][0]['id']}])
            with patch.object(cloud,'Client',return_value=fake):
                with self.assertRaisesRegex(ValueError,'thanh toán'):cloud.sync_order(lib,b['id'],oid)
            fake.opener.open.assert_not_called();self.assertFalse(lib.load(b['id']).get('audiobooks'))
            fake.post.return_value=dict(order=dict(id=oid,state='ready'),audio=[])
            with patch.object(cloud,'Client',return_value=fake):result=cloud.sync_order(lib,b['id'],oid)
            self.assertFalse(result['localReady']);self.assertEqual(result['receivedSegments'],0)
            self.assertEqual(lib.load(b['id'])['audiobooks'][0]['status'],'generating')

    def test_partial_trial_only_plays_contiguous_verified_prefix(self):
        import wave
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.book(Path(tmp));data=trial_snapshot(b,'one',2)
            self.assertGreater(len(data['segments']),1)
            entry=dict(snapshot=data)
            folder=lib.directory(b['id'])/'cloud-trials';folder.mkdir()
            def write(segment):
                with wave.open(str(folder/(cloud.cloud_signature(segment,data)+'.wav')),'wb') as audio:
                    audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\0\0'*2400)
            write(data['segments'][1])
            self.assertEqual(cloud.cached_trial_audio(lib.root,b,entry),[])
            write(data['segments'][0])
            self.assertEqual(len(cloud.cached_trial_audio(lib.root,b,entry)),2)

    def test_direct_provider_locations_are_explicit_and_strict(self):
        oid='11111111-1111-1111-1111-111111111111';base='https://qa.supabase.co'
        good='https://resource.heygen.ai/sample.wav?token=fixture'
        self.assertTrue(cloud.valid_audio_location(dict(url=good,delivery='provider'),base,oid))
        self.assertFalse(cloud.valid_audio_location(dict(url=good),base,oid))
        for url in ('https://127.0.0.1/a','http://resource.heygen.ai/a','https://heygen.ai.evil.test/a','https://secret@resource.heygen.ai/a','https://resource.heygen.ai:444/a'):
            self.assertFalse(cloud.valid_audio_location(dict(url=url,delivery='provider'),base,oid))

    def test_retired_voices_not_selectable(self):
        self.assertEqual(models.profile('nano')['label'],'Lite')
        self.assertTrue({'Adam','Ái Hân','Xuân Tiên','Minh Quân'}.isdisjoint(v['id'] for v in models.voices('nano')))
        self.assertEqual(models.resolve_voice('nano','Minh Quân'),'Đức Trí')



class SelectedProSampleTests(unittest.TestCase):
    def grouped_book(self,count):
        # A selected chapter and its neighbour share a page.
        texts=['Giữ nguyên 😀. '*((count//14)+1)]
        text=(texts[0]+'a'*count)[:count]
        return dict(title='Chương gộp',status='ready',model='pro-cloud',voice=VOICES[0]['id'],language='vi',pages=[{'text':'Source'}],totalPages=1,chapterModel='segments-v1',
            chapters=[dict(id='one',title='Chương 1',startPage=0),dict(id='two',title='Chương 2',startPage=0)],
            segments=[*[dict(id=str(i).zfill(32),page=0,text=text[at:at+1000],chapterId='one') for i,at in enumerate(range(0,len(text),1000))],dict(id='f'*32,page=0,text='Không lấy chữ chương sau.',chapterId='two')])

    def test_grouped_trial_cost_boundaries_and_verbatim_chapter(self):
        self.assertEqual(TRIAL_MAX_UNITS,4)
        for count,units in [(1,1),(5000,1),(5001,2),(10000,2),(10001,3),(15000,3),(15001,4),(20000,4),(24000,4)]:
            with self.subTest(characters=count):
                book=self.grouped_book(count);before=json.dumps(book,ensure_ascii=False)
                self.assertEqual(chapter_trial_units(book,'one'),units)
                single=cloud.local_info(book,chapter_id='one')
                self.assertEqual(single['trialUnits'],1)
                self.assertLessEqual(single['trialSelectedCharacters'],min(count,5000))
                self.assertGreaterEqual(single['trialSelectedCharacters'],min(count,4250))
                info=cloud.local_info(book,chapter_id='one',group_trial=True)
                self.assertEqual(info['trialUnits'],units)
                self.assertEqual(info['trialChapterCharacters'],count)
                self.assertLessEqual(info['trialSelectedCharacters'],min(count,20000))
                if count<=20000:self.assertEqual(info['trialSelectedCharacters'],count)
                self.assertEqual(info['trialCompleteChapter'],count<=20000)
                data=trial_snapshot(book,'one',units)
                text=''.join(s['text'] for s in data['segments'])
                original=''.join(s['text'] for s in book['segments'] if s['chapterId']=='one')
                self.assertEqual(text,original[:len(text)])
                if count<=20000:self.assertEqual(text,original)
                self.assertTrue(all(len(s['text'])<=5000 for s in data['segments']))
                self.assertNotIn('chương sau',text)
                self.assertEqual(data.get('trialUnits',1),units)
                self.assertEqual(json.dumps(book,ensure_ascii=False),before)
        for invalid in [0,5,True,2.5,'4',None]:
            with self.assertRaises(ValueError):trial_snapshot(self.grouped_book(6000),'one',invalid)
        with self.assertRaises(ValueError):trial_snapshot(self.grouped_book(6000),None,2)

    def test_grouped_retry_uses_one_request_and_does_not_reuse_a_short_sample(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=BookCommerceTests().book(Path(tmp));fake=Mock()
            fake.post.return_value=dict(order=dict(id='11111111-1111-1111-1111-111111111111',kind='trial',state='queued',trialUnits=2),trialsRemaining=8,trialLimit=10)
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'trial','9'*32,True,chapter_id='one',trial_units=2)
                cloud.create_order(lib,b['id'],'trial','9'*32,True,chapter_id='one',trial_units=2)
                self.assertEqual(fake.post.call_args_list[0],fake.post.call_args_list[1])
                self.assertEqual(fake.post.call_args.args,('trial-group',))
                self.assertEqual(fake.post.call_args.kwargs['snapshot']['trialUnits'],2)
            stored=lib.load(b['id'])
            self.assertEqual(len(stored['cloudOrders']),1)
            self.assertEqual(stored['cloudTrialsRemaining'],8)
            self.assertIsNotNone(cloud.local_info(stored,chapter_id='one',group_trial=True)['savedTrialOrder'])
            self.assertIsNone(cloud.local_info(stored,chapter_id='one')['savedTrialOrder'])
            short=trial_snapshot(stored,'one',1);long=trial_snapshot(stored,'one',2)
            self.assertFalse(cloud.same_trial_prefix(short,long))
            changed=json.loads(json.dumps(long));changed['segments'][-1]['text']+=' mới'
            self.assertFalse(cloud.same_trial_prefix(long,changed))

    def test_chapter_membership_stops_at_mid_page_boundary(self):
        b=dict(pages=[{'text':'Source'}],totalPages=1,chapterModel='segments-v1',
            chapters=[dict(id='one',number=1,title='Chương 1',startPage=0),dict(id='two',title='Chương 2',startPage=0),dict(id='three',title='Chương 3',startPage=0)],
            segments=[dict(id=str(i).zfill(32),page=0,text=t,chapterId=c) for i,(c,t) in enumerate([('one','Bỏ phần đầu.'),('two','Giữ nguyên dấu 😄. '*400),('three','Không được gửi phần này.')])])
        before=json.dumps(b,ensure_ascii=False)
        result=sample_segments(b,chapter_id='two')
        self.assertEqual(''.join(s['text'] for s in result),b['segments'][1]['text'][:5000])
        self.assertEqual([s['index'] for s in result],[1])
        self.assertEqual(before,json.dumps(b,ensure_ascii=False))
        b['segments'][1]['text']='Chương ngắn.'
        self.assertEqual(''.join(s['text'] for s in sample_segments(b,chapter_id='two')),'Chương ngắn.')
        with self.assertRaises(ValueError):sample_segments(b,chapter_id='missing')

    def test_uncertain_pre_upgrade_sample_retries_original_four_thousand(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=BookCommerceTests().book(Path(tmp))
            old=snapshot(b)|dict(segments=sample_segments(b,limit=4000),openingPage=0)
            b['cloudOrders']=[dict(kind='trial',requestKey='c'*32,snapshot=old,order=None)];lib.save(b)
            self.assertEqual(cloud.local_info(b)['pendingTrialKey'],'c'*32)
            fake=Mock();fake.post.return_value=dict(order=dict(id='11111111-1111-1111-1111-111111111111',kind='trial',state='queued'),trialsRemaining=7,trialLimit=10)
            with patch.object(cloud,'Client',return_value=fake):cloud.create_order(lib,b['id'],'trial','c'*32,True)
            self.assertEqual(fake.post.call_args.kwargs['snapshot'],old)
            self.assertEqual(sum(len(s['text']) for s in old['segments']),4000)

if __name__=='__main__':unittest.main()
