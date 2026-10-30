from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('credit_service',ROOT/'commerce/credits/service.py')
svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)
PACK=dict(id='fixture-only',credits=1000,amountVND=10000)
BANK=dict(name='Fixture bank',bin='970423',account='0000000000',holder='QA ONLY')
VOICE='094e72c3-97d3-439a-9e64-39ac3d3fa897'
REMOTE='12345678-1234-4234-8234-123456789012'

class WalletTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.qa');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ledger=svc.Ledger(self.root/'credits.sqlite',[PACK],BANK)
        self.wallet=svc.digest('wallet-secret-fixture');self.ledger.wallet(self.wallet,True)
        self.provider=Mock(fingerprint='merchant-test');self.gateway=svc.Gateway(self.ledger,self.provider,self.root/'audio',[VOICE])
        self.input=dict(text='  Chữ Việt.  ',voice_id=VOICE,language='vi',speed=1)

    def funded(self):
        order=self.ledger.topup(self.wallet,PACK['id'],'topup-key')
        paid=datetime.now(timezone.utc).isoformat()
        self.ledger.confirm_receipt(order['id'],'bank-fixture',10000,BANK['account'],paid,True)
        return order,paid

    def test_prices_unset_disable_sale_and_no_payment_code_can_fund_wallet(self):
        ledger=svc.Ledger(self.root/'empty.sqlite')
        self.assertFalse(ledger.wallet(self.wallet,True)['salesReady'])
        with self.assertRaises(svc.CreditError):ledger.topup(self.wallet,PACK['id'],'key')
        order=self.ledger.topup(self.wallet,PACK['id'],'key')
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],0)
        with self.assertRaises(svc.CreditError):self.ledger.confirm_receipt(order['id'],'fake',10000,BANK['account'],datetime.now(timezone.utc).isoformat())
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],0)

    def test_receipt_checks_amount_account_and_replay_is_exactly_once(self):
        order=self.ledger.topup(self.wallet,PACK['id'],'key');paid=datetime.now(timezone.utc).isoformat()
        for amount,account in [(1,BANK['account']),(10000,'wrong-account')]:
            with self.assertRaises(svc.CreditError):self.ledger.confirm_receipt(order['id'],'bank-id',amount,account,paid,True)
        for _ in range(2):self.ledger.confirm_receipt(order['id'],'bank-id',10000,BANK['account'],paid,True)
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],1000)
        other=self.ledger.topup(self.wallet,PACK['id'],'other')
        with self.assertRaises(svc.CreditError):self.ledger.confirm_receipt(other['id'],'bank-id',10000,BANK['account'],datetime.now(timezone.utc).isoformat(),True)
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],1000)

    def test_insufficient_credit_does_not_call_provider(self):
        with self.assertRaises(svc.CreditError) as raised:self.gateway.generate(self.wallet,'key',self.input)
        self.assertEqual(raised.exception.code,402);self.provider.request.assert_not_called()

    def test_app_catalog_and_generation_only_expose_selected_voices(self):
        self.provider.request.return_value={'data':[dict(id=VOICE,name='Selected'),dict(id=REMOTE,name='Private merchant voice')],'has_more':False}
        self.assertEqual(self.gateway.voices(),{'data':[dict(id=VOICE,name='Selected')]})
        self.provider.request.reset_mock()
        with self.assertRaises(svc.CreditError) as raised:self.gateway.generate(self.wallet,'private',self.input|{'voice_id':REMOTE})
        self.assertEqual(raised.exception.code,403);self.provider.request.assert_not_called()

    def test_normalized_character_count_and_concurrent_duplicate_debit_once(self):
        self.funded();self.provider.request.side_effect=[{'id':REMOTE,'status':'ready'},b'mp3 fixture']
        with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:self.gateway.generate(self.wallet,'same',self.input),range(6)))
        self.assertEqual(len({r['id'] for r in results}),1)
        self.assertEqual(results[0]['credits'],len('Chữ Việt.'))
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],1000-len('Chữ Việt.'))
        self.assertEqual(self.provider.request.call_count,2)
        with self.assertRaises(svc.CreditError):self.gateway.generate(self.wallet,'same',self.input|{'text':'Khác chữ.'})

    def test_failed_upstream_refunds_once_and_wallets_cannot_read_other_jobs(self):
        self.funded();self.provider.request.return_value={'id':REMOTE,'status':'failed'}
        job=self.gateway.generate(self.wallet,'failed',self.input)
        self.assertEqual(job['status'],'failed')
        self.gateway.reconcile(self.wallet,job['id']);self.assertEqual(self.ledger.wallet(self.wallet)['balance'],1000)
        with self.assertRaises(svc.CreditError):self.ledger.job('another-wallet',job['id'])

    def test_unknown_post_reconciles_same_upstream_key_and_keeps_reservation(self):
        self.funded();self.provider.request.side_effect=svc.CreditError('timeout',503)
        first=self.gateway.generate(self.wallet,'unknown',self.input)
        self.assertEqual(first['status'],'unknown');balance=self.ledger.wallet(self.wallet)['balance']
        original_key=self.provider.request.call_args.kwargs['key']
        self.provider.request.side_effect=[{'id':REMOTE,'status':'ready'},b'mp3']
        ready=self.gateway.reconcile(self.wallet,first['id'])
        self.assertEqual(ready['status'],'ready');self.assertEqual(self.ledger.wallet(self.wallet)['balance'],balance)
        self.assertEqual(self.provider.request.call_args_list[1].kwargs['key'],original_key)

    def test_download_401_after_paid_generation_does_not_refund_or_regenerate(self):
        self.funded();self.provider.request.side_effect=[{'id':REMOTE,'status':'ready'},svc.CreditError('download unauthorized',401)]
        first=self.gateway.generate(self.wallet,'download',self.input)
        self.assertEqual(first['status'],'unknown');balance=self.ledger.wallet(self.wallet)['balance']
        self.provider.request.side_effect=[{'id':REMOTE,'status':'ready'},b'mp3']
        self.assertEqual(self.gateway.reconcile(self.wallet,first['id'])['status'],'ready')
        self.assertEqual(self.ledger.wallet(self.wallet)['balance'],balance)
        self.assertEqual(self.provider.request.call_args_list[2].args,('/api/v1/voice/generations/'+REMOTE,))

    def test_restart_or_merchant_rotation_never_reserves_again_for_uncertain_job(self):
        self.funded();self.provider.request.side_effect=svc.CreditError('lost',503)
        job=self.gateway.generate(self.wallet,'lost',self.input)
        reopened=svc.Ledger(self.ledger.path,[PACK],BANK)
        new_provider=Mock(fingerprint='rotated-merchant')
        gateway=svc.Gateway(reopened,new_provider,self.root/'audio',[VOICE])
        self.assertEqual(gateway.reconcile(self.wallet,job['id'])['status'],'unknown')
        new_provider.request.assert_not_called()
        self.assertEqual(reopened.wallet(self.wallet)['balance'],1000-len('Chữ Việt.'))

if __name__=='__main__':unittest.main()
