import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import clone_pro as cloud
import entitlements
import model_manager as models
from core import Library, signature, valid_audio
from worker import Worker

TOKEN='wsn_credit_'+'a'*64
VOICE='094e72c3-97d3-439a-9e64-39ac3d3fa897'
JOB='12345678-1234-4234-8234-123456789012'

def wav(path):
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(b'\x01\x01'*4800)

class CloudTests(unittest.TestCase):
    def setUp(self):
        gate=patch('features.PRO_MAX_ENABLED',True);gate.start();self.addCleanup(gate.stop)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_credit_model_is_available_to_free_without_unlocking_local_pro(self):
        with patch.object(entitlements,'release',return_value={'channel':'consumer'}),patch.object(entitlements,'data_root',return_value=self.root),patch.object(entitlements,'device_code',return_value='SN000000000000'):
            access=entitlements.status()
            self.assertEqual(access['tier'],'free');entitlements.require_model('clone-pro')
            with self.assertRaises(ValueError):entitlements.require_model('turbo')
            with patch.object(cloud,'config',return_value={}):
                m=next(m for m in models.catalog()['models'] if m['id']=='clone-pro')
                self.assertTrue(m['entitled']);self.assertFalse(m['ready']);self.assertFalse(m['canDownload'])

    def test_cache_includes_language_voice_text_and_revision(self):
        base=signature('Chữ Việt ă â ơ ư đ.',VOICE,'clone-pro','vi')
        self.assertNotEqual(base,signature('Chữ Việt ă â ơ ư đ.',VOICE,'clone-pro','en'))
        self.assertNotEqual(base,signature('Chữ Việt đã sửa.',VOICE,'clone-pro'))
        self.assertNotEqual(base,signature('Chữ Việt ă â ơ ư đ.',JOB,'clone-pro'))
        with patch.object(cloud,'REVISION','new-service-model'),patch.object(models,'revision',return_value='new-service-model'):
            self.assertNotEqual(base,signature('Chữ Việt ă â ơ ư đ.',VOICE,'clone-pro'))

    def test_generation_and_preview_require_explicit_credit_action(self):
        with patch.object(cloud,'credential') as keychain:
            with self.assertRaisesRegex(ValueError,'Xác nhận'):cloud.main({})
            keychain.assert_not_called()
        source=self.root/'s.png';source.write_bytes(b'fixture')
        worker=Worker(self.root/'library');b=worker.lib.create([source]);b.update(model='clone-pro',voice=VOICE);worker.lib.save(b)
        with self.assertRaisesRegex(ValueError,'xác nhận'):worker.generate(b['id'])
        with self.assertRaisesRegex(ValueError,'credit'):worker.preview_voice({'model':'clone-pro'})

    def test_busy_wallet_action_returns_a_finished_state_instead_of_leaving_ui_waiting(self):
        worker=Worker(self.root/'library');worker.jobs['audio']={}
        events=[]
        with patch('worker.emit',side_effect=lambda **e:events.append(e)),patch.object(cloud,'credential') as keychain:
            worker.handle(dict(action='creditWallet',voices=True))
            keychain.assert_not_called()
        self.assertEqual(events[0]['event'],'cloudConnection');self.assertFalse(events[0]['running']);self.assertFalse(events[0]['success'])

    def test_wallet_never_uses_customer_web_credentials_or_saves_wallet_secret_in_config(self):
        wallet=dict(walletId='fixture-wallet',balance=0,packs=[],orders=[],salesReady=False)
        with patch.object(cloud,'config_path',return_value=self.root/'connection.json'),patch.object(cloud,'service_url',return_value='https://credits.example.test'),patch.object(cloud,'credential',return_value={'token':TOKEN}) as keychain,patch.object(cloud.Client,'list_voices',return_value=[dict(id=VOICE,label='Minh Dự',default=True)]),patch.object(cloud.Client,'request',return_value=wallet):
            cloud.refresh_wallet();keychain.assert_called_once_with('create')
            self.assertNotIn(TOKEN,(self.root/'connection.json').read_text())
        with self.assertRaises(ValueError):cloud.Client('windi_voice_'+'a'*64,api='https://credits.example.test')
        with patch.object(cloud,'credential') as keychain,patch.object(cloud,'service_url',side_effect=ValueError('not configured')):
            with self.assertRaises(ValueError):cloud.refresh_wallet()
            keychain.assert_not_called()

    def test_signed_audio_redirect_drops_authorization_and_rejects_http(self):
        client=cloud.Client(TOKEN,api='https://credits.example.test')
        def redirect(url):return urllib.error.HTTPError(client.api+'/audio',307,'redirect',{'Location':url},None)
        client.opener=Mock();client.opener.open.side_effect=[redirect('https://storage.example.test/signed.mp3'),io.BytesIO(b'mp3')]
        self.assertEqual(client.request('/audio',audio=True),b'mp3')
        self.assertIsNone(client.opener.open.call_args_list[1].args[0].get_header('Authorization'))
        client.opener.open.side_effect=redirect('http://unsafe.example.test/audio')
        with self.assertRaisesRegex(ValueError,'không hợp lệ'):client.request('/audio',audio=True)

    def test_lost_post_response_reuses_key_and_unknown_never_creates_new_job(self):
        client=Mock(token=TOKEN);segment=dict(path=str(self.root/'cached.wav'),text='Giữ nguyên chữ Việt.',id='s')
        client.request.side_effect=ValueError('network lost')
        for _ in range(2):
            with self.assertRaises(ValueError):cloud.generate_segment(client,segment,VOICE,'vi')
        keys=[c.kwargs['key'] for c in client.request.call_args_list]
        self.assertEqual(keys[0],keys[1]);self.assertFalse(valid_audio(segment['path']))
        journal=Path(segment['path']).with_suffix('.remote.json');state=json.loads(journal.read_text());state['id']=JOB;journal.write_text(json.dumps(state))
        client.request.reset_mock();client.request.side_effect=None;client.request.return_value={'id':JOB,'status':'unknown'}
        with self.assertRaisesRegex(ValueError,'không tạo lượt mới'):cloud.generate_segment(client,segment,VOICE,'vi')
        client.request.assert_called_once_with('/api/v1/voice/generations/'+JOB)

    def test_token_rotation_during_uncertain_post_cannot_create_duplicate(self):
        client=Mock(token=TOKEN);client.request.side_effect=ValueError('lost');s=dict(path=str(self.root/'cache.wav'),text='Xin chào.',id='s')
        with self.assertRaises(ValueError):cloud.generate_segment(client,s,VOICE,'vi')
        client.token='wsn_credit_'+'b'*64;client.request.reset_mock()
        with self.assertRaisesRegex(ValueError,'ví credit trước'):cloud.generate_segment(client,s,VOICE,'vi')
        client.request.assert_not_called()

    def test_bad_download_is_not_usable_then_ready_job_downloads_without_post(self):
        client=Mock(token=TOKEN);client.request.side_effect=[{'id':JOB,'status':'ready'},b'bad audio']
        s=dict(path=str(self.root/'cache.wav'),text='Xin chào.',id='s')
        with patch.object(cloud.subprocess,'run'):
            with self.assertRaisesRegex(ValueError,'chưa hợp lệ'):cloud.generate_segment(client,s,VOICE,'vi')
        self.assertFalse(valid_audio(s['path']))
        client.request.reset_mock();client.request.side_effect=[{'id':JOB,'status':'ready'},b'valid fixture']
        def convert(args,**kwargs):wav(Path(args[-1]))
        with patch.object(cloud.subprocess,'run',side_effect=convert):cloud.generate_segment(client,s,VOICE,'vi')
        self.assertTrue(valid_audio(s['path']));self.assertTrue(all(not c.kwargs.get('body') and len(c.args)==1 for c in client.request.call_args_list))
        client.request.reset_mock();cloud.generate_segment(client,s,VOICE,'vi');client.request.assert_not_called()

    def test_known_refunded_failure_can_retry_with_new_explicit_request(self):
        client=Mock(token=TOKEN);client.request.return_value={'id':JOB,'status':'failed'}
        s=dict(path=str(self.root/'retry.wav'),text='Tạo lại sau khi hoàn credit.',id='s')
        with self.assertRaises(ValueError):cloud.generate_segment(client,s,VOICE,'vi')
        first_key=client.request.call_args.kwargs['key']
        client.request.return_value={'id':JOB,'status':'failed'}
        with self.assertRaises(ValueError):cloud.generate_segment(client,s,VOICE,'vi')
        self.assertNotEqual(first_key,client.request.call_args.kwargs['key'])

if __name__=='__main__':unittest.main()
