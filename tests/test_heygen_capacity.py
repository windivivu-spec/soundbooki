from pathlib import Path
import sys
import unittest
import tempfile,json
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'commerce'))
from heygen_capacity import estimate


class HeyGenCapacityTests(unittest.TestCase):
    def test_owner_demo_cannot_bypass_the_live_shared_dispatcher(self):
        import importlib.util
        source=Path(__file__).resolve().parents[1]/'cloud/heygen_studio/heygen_client.py'
        spec=importlib.util.spec_from_file_location('guarded_heygen_client',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'release.json').write_text(json.dumps({'heygenDispatchOnly':True}))
            with patch.object(module,'ROOT',root),patch.object(module.urllib.request,'urlopen') as network:
                client=module.HeyGenClient(api_key='qa-only')
                with self.assertRaisesRegex(RuntimeError,'hàng đợi chung'):client._request('POST','/v3/models/audio/tts',{'text':'QA only'})
                network.assert_not_called()

    def test_each_book_keeps_its_own_tail_request(self):
        self.assertEqual(estimate(4001,100)['idealRequests'],200)

    def test_free_campaign_is_not_ten_whole_books(self):
        result=estimate(4000,100*10)
        self.assertEqual(result['idealRequests'],1000)
        self.assertEqual(result['workBudgetMinutes'],40)

    def test_latency_can_dominate_rate_limit(self):
        result=estimate(216000,latency_seconds=30)
        self.assertEqual(result['effectiveAttemptRPM'],12)
        self.assertEqual(result['workBudgetMinutes'],4.5)

    def test_retries_consume_the_same_provider_capacity(self):
        self.assertEqual(estimate(216000,rpm=20,retry_ratio=.1)['workBudgetMinutes'],2.97)

    def test_reject_invalid_or_unsupported_limits(self):
        for kwargs in ({'rpm':31},{'chunk':5001},{'concurrency':0},
                       {'latency_seconds':float('nan')},{'retry_ratio':-1}):
            with self.assertRaises(ValueError):estimate(4000,**kwargs)


if __name__=='__main__':unittest.main()
