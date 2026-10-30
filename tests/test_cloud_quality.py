import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as Obj
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
quality=module('cloud_quality','cloud/modal_studio/quality.py')
pdf=module('pdf_processing','cloud/pdf_processing.py')
sys.path.insert(0,str(ROOT/'backend'))
from book_cloud import cloud_signature
from book_pricing import REVISION,AUDIO_REVISION

class CloudQualityTests(unittest.TestCase):
    def test_source_bound_suggestions_never_rewrite(self):
        text='Đọc nhữn\ng chữ này.';p=[dict(before='nhữn\ng',after='những',reason='Ngắt dòng')]
        report=quality.review_report([text],[dict(review_checked=True,text_issues=p)])
        self.assertFalse(report['textChanged']);self.assertTrue(report['issues'][0]['requiresReview'])
        self.assertEqual(text[report['issues'][0]['start']:report['issues'][0]['end']],p[0]['before'])
        self.assertEqual(report['sourceSHA256'],hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(quality.validated_issues('một một',[dict(before='một',after='hai')]),[])
        self.assertEqual(quality.validated_issues(text,[dict(before='câu không có trong sách',after='bịa')]),[])
        with self.assertRaises(ValueError):quality.validated_issues('abcdef',[dict(before='abc',after='ab'),dict(before='bcd',after='bc')])
        with self.assertRaises(ValueError):quality.review_report([text],[dict(text_issues=[])])
    def test_audio_gate_rejects_silence_nan_truncation_and_clipping(self):
        sample=.2*np.sin(np.arange(24000)*.05)
        self.assertTrue(quality.check_audio(sample,24000,'Tiếng Việt có dấu')['passed'])
        for bad in (np.zeros(24000),np.ones(24000),np.array([float('nan')]),sample[:10]):
            with self.assertRaises(ValueError):quality.check_audio(bad,24000,'Tiếng Việt có dấu')
    def test_old_orders_keep_cache_revision(self):
        s=dict(text='Nội dung đã mua.');base=dict(voice='voice-003',language='vi',revision=REVISION)
        self.assertNotEqual(cloud_signature(s,base),cloud_signature(s,dict(base,audioRevision=AUDIO_REVISION)))
        self.assertEqual(cloud_signature(s,base),cloud_signature(s,dict(base,audioRevision=REVISION)))
    def test_cloud_layout_keeps_provenance_and_requires_human_review(self):
        bbox=Obj(l=10,t=20,r=400,b=60,coord_origin='TOPLEFT')
        items=[Obj(text='1 KHÔNG AI ĐIÊN',label=Obj(value='section_header'),prov=[Obj(page_no=1,bbox=bbox)]),Obj(text='Chữ giữ nguyên dấu.',label=Obj(value='text'),prov=[Obj(page_no=1,bbox=bbox)])]
        doc=Obj(pages={1:Obj()},iterate_items=lambda:((i,0) for i in items))
        result=pdf.pack_document(doc);self.assertTrue(result['requiresReview'])
        self.assertEqual(result['pages'][0]['text'],'1 KHÔNG AI ĐIÊN\n\nChữ giữ nguyên dấu.\n\n')
        self.assertEqual(len(result['headingCandidates']),1)
        doc.iterate_items=lambda:iter([])
        with self.assertRaises(ValueError):pdf.pack_document(doc)

if __name__=='__main__':unittest.main()
