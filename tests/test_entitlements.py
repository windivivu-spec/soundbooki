import base64
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import entitlements as access
from core import Library
from worker import Worker
import model_manager as models

class EntitlementTests(unittest.TestCase):
    def test_cloud_offer_does_not_unlock_or_offer_local_private_assets(self):
        free=dict(tier='free',allowedModels=['nano','kitten','pro-cloud'],privateVoiceAvailable=False,privateVoiceIncluded=True)
        with patch.object(access,'status',return_value=free):
            catalog=models.catalog()['models']
            self.assertNotIn('f5-private',[m['id'] for m in catalog])
            pro=next(m for m in catalog if m['id']=='pro-cloud')
            self.assertTrue(pro['cloud']);self.assertFalse(pro['canDownload'])
            with self.assertRaisesRegex(ValueError,'Pro'):access.require_model('f5-private')

    @classmethod
    def setUpClass(cls):
        script="""const c=require('node:crypto');const k=c.generateKeyPairSync('ed25519');const v={schema:1,product:'windi-sach-noi-pro',orderId:'fixture-order',email:'reader@example.test',issuedAt:'2026-10-19T00:00:00Z',expiresAt:'2027-10-19T00:00:00Z'};const b=Buffer.from(JSON.stringify(v));console.log(JSON.stringify({key:k.publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('base64'),envelope:{payload:b.toString('base64'),signature:c.sign(null,b,k.privateKey).toString('base64')}}));"""
        cls.fixture=json.loads(subprocess.check_output(['node','-e',script],text=True))
    def test_native_verification_tamper_expiry(self):
        config={'channel':'consumer','licensePublicKey':self.fixture['key']}
        now=datetime(2026,10,20,tzinfo=timezone.utc)
        self.assertEqual(access.decode_license(self.fixture['envelope'],config,now)['email'],'reader@example.test')
        tampered=dict(self.fixture['envelope']);data=json.loads(base64.b64decode(tampered['payload']));data['expiresAt']='2099-01-01T00:00:00Z';tampered['payload']=base64.b64encode(json.dumps(data).encode()).decode()
        for envelope,cfg,date in [(tampered,config,now),(self.fixture['envelope'],{},now),(self.fixture['envelope'],config,datetime(2028,1,1,tzinfo=timezone.utc)),(self.fixture['envelope'],config,datetime(2025,1,1,tzinfo=timezone.utc))]:
            with self.assertRaises(ValueError):access.decode_license(envelope,cfg,date)
    def test_free_pro_private_voice_and_persistence(self):
        with tempfile.TemporaryDirectory(dir=access.ROOT/'.qa') as tmp,patch.object(access,'data_root',return_value=Path(tmp)),patch.object(access,'release',return_value={'channel':'consumer','licensePublicKey':self.fixture['key'],'privateVoiceAvailable':False}):
            self.assertEqual(access.status()['allowedModels'],['nano','kitten','clone-pro','pro-cloud'])
            with self.assertRaises(ValueError):access.require_model('turbo')
            with self.assertRaises(ValueError):access.require_model('f5-private')
            source=Path(tmp)/'valid.json';source.write_text(json.dumps(self.fixture['envelope']))
            access.install(source);self.assertEqual(access.status()['tier'],'pro');access.require_model('turbo')
            with self.assertRaises(ValueError):access.require_model('f5-private')
            saved=(Path(tmp)/'license.json').read_bytes();source.write_text('{}')
            with self.assertRaises(ValueError):access.install(source)
            self.assertEqual((Path(tmp)/'license.json').read_bytes(),saved)
    def test_worker_gate_blocks_cached_generation_preview_download_export(self):
        with tempfile.TemporaryDirectory(dir=access.ROOT/'.qa') as tmp,patch.object(access,'status',return_value={'tier':'free','allowedModels':['nano','kitten']}):
            source=Path(tmp)/'text.png';source.write_bytes(b'fixture')
            lib=Library(Path(tmp)/'library');b=lib.create([str(source)]);lib.add_page(b,0,{'page':0,'total':1,'text':'Xin chào.','method':'fixture','warning':''});b['model']='turbo';lib.save(b)
            worker=Worker(lib.root)
            for work in [lambda:worker.generate(b['id']),lambda:worker.preview_voice({'model':'turbo'}),lambda:worker.download_model('turbo'),lambda:lib.export(b['id'],str(Path(tmp)/'out.wav'))]:
                with self.assertRaisesRegex(ValueError,'Pro'):work()
            self.assertTrue(lib.public(b)['locked']);self.assertEqual(lib.public(b)['readyCount'],0)
    def test_invalid_consumer_policy_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=access.ROOT/'.qa') as tmp,patch.object(access,'ROOT',Path(tmp)):
            self.assertEqual(access.release()['channel'],'development')
            for text in ['broken','[]','{"channel":"development"}']:
                (Path(tmp)/'release.json').write_text(text);self.assertEqual(access.release()['channel'],'consumer')

    def test_device_license_is_bound_and_rejects_legacy_email_license(self):
        script="""const c=require('node:crypto');const k=c.generateKeyPairSync('ed25519');const b=Buffer.from(JSON.stringify({schema:2,product:'windi-sach-noi-pro',orderId:'fixture-bank-id',deviceCode:'SNABCDEF123456',issuedAt:'2026-10-19T00:00:00Z',expiresAt:'2027-10-19T00:00:00Z'}));console.log(JSON.stringify({key:k.publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('base64'),envelope:{payload:b.toString('base64'),signature:c.sign(null,b,k.privateKey).toString('base64')}}));"""
        fixture=json.loads(subprocess.check_output(['node','-e',script],text=True));cfg={'licenseMode':'device','licensePublicKey':fixture['key']};now=datetime(2026,10,20,tzinfo=timezone.utc)
        with patch.object(access,'device_code',return_value='SNABCDEF123456'):
            self.assertEqual(access.decode_license(fixture['envelope'],cfg,now)['deviceCode'],'SNABCDEF123456')
        with patch.object(access,'device_code',return_value='SN000000000000'):
            with self.assertRaises(ValueError):access.decode_license(fixture['envelope'],cfg,now)
        with self.assertRaises(ValueError):access.decode_license(self.fixture['envelope'],{'licenseMode':'device','licensePublicKey':self.fixture['key']},now)

    def test_native_device_code_is_stable_and_does_not_return_raw_hardware_id(self):
        command=[str(access.ROOT/'.build/windi-license'),'--device-code']
        first=json.loads(subprocess.check_output(command));second=json.loads(subprocess.check_output(command))
        self.assertEqual(first,second);self.assertRegex(first['deviceCode'],'^SN[A-F0-9]{12}$');self.assertEqual(list(first),['deviceCode'])

    def test_renewal_requires_a_verified_later_expiry_and_keeps_pending_out_of_success(self):
        script="""const c=require('node:crypto');const k=c.generateKeyPairSync('ed25519');function sign(expiresAt){const b=Buffer.from(JSON.stringify({schema:2,product:'windi-sach-noi-pro',orderId:expiresAt,deviceCode:'SNABCDEF123456',issuedAt:'2026-10-19T00:00:00Z',expiresAt}));return {payload:b.toString('base64'),signature:c.sign(null,b,k.privateKey).toString('base64')}}console.log(JSON.stringify({key:k.publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('base64'),old:sign('2027-10-19T00:00:00Z'),renewed:sign('2028-10-19T00:00:00Z')}));"""
        data=json.loads(subprocess.check_output(['node','-e',script],text=True))
        config=dict(channel='consumer',licenseMode='device',licensePublicKey=data['key'])
        with tempfile.TemporaryDirectory(dir=access.ROOT/'.qa') as tmp,patch.object(access,'data_root',return_value=Path(tmp)),patch.object(access,'release',return_value=config),patch.object(access,'device_code',return_value='SNABCDEF123456'):
            access.install_envelope(data['old']);path=Path(tmp)/'license.json';before=path.read_bytes()
            worker=Worker(Path(tmp)/'library');events=[]
            with patch('worker.emit',side_effect=lambda **e:events.append(e)),patch.object(worker,'model_event'):
                worker.handle(dict(action='installLicense',license=data['old'],afterExpiresAt='2027-10-19T00:00:00Z',requestId='old'))
                self.assertEqual(events,[dict(event='licenseCheck',requestId='old',state='pending')]);self.assertEqual(path.read_bytes(),before)
                events.clear();worker.handle(dict(action='installLicense',license=data['renewed'],afterExpiresAt='2027-10-19T00:00:00Z',requestId='new'))
                self.assertEqual(events,[dict(event='licenseImported',requestId='new')]);self.assertEqual(access.status()['expiresAt'],'2028-10-19T00:00:00Z')
                saved=path.read_bytes();bad=dict(data['renewed']);payload=json.loads(base64.b64decode(bad['payload']));payload['expiresAt']='2099-01-01T00:00:00Z';bad['payload']=base64.b64encode(json.dumps(payload).encode()).decode()
                events.clear();worker.handle(dict(action='installLicense',license=bad,afterExpiresAt='2028-10-19T00:00:00Z',requestId='tampered'))
                self.assertEqual(events[0]['state'],'error');self.assertFalse(any(e['event']=='licenseImported' for e in events));self.assertEqual(path.read_bytes(),saved)

if __name__=='__main__':unittest.main()
