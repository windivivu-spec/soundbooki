from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import features
import clone_pro
import model_manager
from worker import Worker


class PausedProMaxTests(unittest.TestCase):
    def test_hidden_catalog_does_not_read_wallet_or_advertise_cloud(self):
        self.assertFalse(features.PRO_MAX_ENABLED)
        with patch.object(clone_pro,'config') as saved:
            catalog=model_manager.catalog()
        self.assertNotIn('clone-pro',[m['id'] for m in catalog['models']])
        self.assertIsNone(catalog['credits']);saved.assert_not_called()
        self.assertFalse(model_manager.ready('clone-pro'))

    def test_network_and_wallet_keychain_blocked_even_if_service_configured(self):
        client=clone_pro.Client('wsn_credit_'+'a'*64,api='https://example.invalid')
        client.opener=Mock()
        with patch.object(clone_pro,'credential') as secret:
            for action in (lambda:client.request('/api/credits/wallet',{}),clone_pro.refresh_wallet,lambda:clone_pro.main({'cloudConfirmed':True})):
                with self.assertRaisesRegex(ValueError,'tạm hoãn'):action()
            secret.assert_not_called()
        client.opener.open.assert_not_called()

    def test_old_cloud_book_cannot_generate_or_buy_but_can_switch_to_local(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            root=Path(tmp);source=root/'fixture.png';source.write_bytes(b'fixture')
            worker=Worker(root/'library');book=worker.lib.create([source]);book['model']='clone-pro';worker.lib.save(book)
            for action in (lambda:worker.generate(book['id'],cloud_consent={}),lambda:worker.handle({'action':'creditWallet'}),lambda:worker.handle({'action':'creditPurchase','packId':'p','key':'a'*32}),lambda:worker.handle({'action':'settings','bookId':book['id'],'model':'clone-pro'})):
                with self.assertRaisesRegex(ValueError,'tạm hoãn'):action()
            with patch('worker.emit'):
                worker.handle({'action':'settings','bookId':book['id'],'model':'nano'})
            self.assertEqual(worker.lib.load(book['id'])['model'],'nano')


if __name__=='__main__':unittest.main()
