from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
import launch_offer as launch
import book_cloud as cloud
from book_pricing import VOICES

class LaunchOfferTests(unittest.TestCase):
    def library(self,root):
        source=root/'source.txt';source.write_text('Nguồn QA')
        lib=Library(root/'library');book=lib.create([source]);lib.add_page(book,0,dict(page=0,text='Nội dung sách giữ nguyên.',method='fixture',warning=''))
        book.update(status='ready',model='pro-cloud',voice=VOICES[0]['id']);lib.save(book);return lib,book
    def test_deadline_is_end_of_november_first_in_vietnam(self):
        self.assertTrue(launch.policy(datetime.fromisoformat('2026-11-01T16:59:59+00:00'))['active'])
        self.assertFalse(launch.policy(datetime.fromisoformat('2026-11-01T17:00:00+00:00'))['active'])
        self.assertEqual((launch.policy()['amountVND'],launch.policy()['books']),(50000,5))
    def test_local_display_never_contacts_cloud_or_grants_rights(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.library(Path(tmp))
            with patch.object(cloud,'Client') as client:
                self.assertIsNone(launch.local_info(lib)['bundle']);cloud.local_info(b,lib.root);client.assert_not_called()
    def test_quote_persists_retry_key_before_network_and_sends_no_book(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.library(Path(tmp));key='a'*32
            def response(route,**kwargs):
                self.assertEqual(launch.cached(lib)['requestKey'],key)
                self.assertEqual((route,kwargs),('bundle-quote',{'requestKey':key}))
                return dict(order={'id':'quote'},bundle=None,offer=launch.policy())
            fake=Mock();fake.post.side_effect=response
            with patch.object(cloud,'Client',return_value=fake):launch.quote(lib,key);launch.quote(lib,key)
            self.assertEqual(fake.post.call_count,2)
    def test_combo_redemption_uses_book_snapshot_and_separate_transport(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.library(Path(tmp));fake=Mock();fake.post.return_value=dict(order={'id':'order','kind':'book','state':'queued','fundingBundleId':'bundle'},bundle=dict(remaining=4,used=1),trialsRemaining=10,trialLimit=10)
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'combo','b'*32,True);cloud.create_order(lib,b['id'],'combo','b'*32,True)
                self.assertEqual(fake.post.call_args.args,('bundle-redeem',))
                self.assertEqual(fake.post.call_args.kwargs['snapshot']['voice'],VOICES[0]['id'])
                self.assertEqual(fake.post.call_args_list[0],fake.post.call_args_list[1])
            self.assertEqual(launch.cached(lib)['bundle']['remaining'],4)
            self.assertEqual(len(lib.load(b['id'])['cloudOrders']),1)
            self.assertEqual(lib.load(b['id'])['cloudOrders'][0]['purchaseMode'],'combo')
            self.assertEqual(cloud.local_info(lib.load(b['id']),lib.root)['launchBundle']['remaining'],4)
    def test_late_status_cannot_restore_a_consumed_display_slot(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.library(Path(tmp))
            launch.save(lib,dict(bundle=dict(id='bundle',used=2,remaining=3)))
            result=launch.save(lib,dict(bundle=dict(id='bundle',used=1,remaining=4)))
            self.assertEqual(result['bundle']['remaining'],3)
            self.assertEqual(launch.cached(lib)['bundle']['remaining'],3)
    def test_retry_key_cannot_switch_between_regular_and_combo(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib,b=self.library(Path(tmp));fake=Mock();fake.post.return_value=dict(order={'id':'order','kind':'book','state':'queued'},trialsRemaining=10,trialLimit=10)
            with patch.object(cloud,'Client',return_value=fake):
                cloud.create_order(lib,b['id'],'combo','c'*32,True)
                with self.assertRaisesRegex(ValueError,'đã đổi'):cloud.create_order(lib,b['id'],'book','c'*32,True)
                self.assertEqual(fake.post.call_count,1)

if __name__=='__main__':unittest.main()
