import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from cleanup import normalize_all_caps_lines, normalize_import_text, roman_number
from core import split_text
from pdf_layout import process_book

class ImportCaseTests(unittest.TestCase):
    def test_structural_roman_numerals_and_ambiguous_prose(self):
        cases={
            'CHƯƠNG IV: AI VÀ TƯ DUY':'Chương 4: AI và tư duy',
            'Phần II, mục IX; Thế kỷ XXI.':'Phần 2, mục 9; Thế kỷ 21.',
            'I. MỞ ĐẦU\nIV) NỘI DUNG\nXX — KẾT THÚC':'1. Mở đầu\n4) Nội dung\n20 — Kết thúc',
            'IV\nNỘI DUNG':'4\nNội dung',
            'I am reading. NASA makes a MIX. Vitamin D and vitamin C.':'I am reading. NASA makes a MIX. Vitamin D and vitamin C.',
            'I\nMỞ ĐẦU':'1\nMở đầu',
            'Chương IIII và phần IC không hợp lệ.':'Chương IIII và phần IC không hợp lệ.',
            'Chapter XIV: Introduction':'Chapter 14: Introduction',
        }
        for raw,expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_import_text(raw)[0],expected)
                self.assertEqual(normalize_import_text(expected)[0],expected)
        for raw,number in [('I',1),('IV',4),('IX',9),('XL',40),('XC',90),('CD',400),('CM',900),('MMXXVI',2026)]:
            self.assertEqual(roman_number(raw),number)
        self.assertEqual(normalize_import_text('I\nam reading',language='en')[0],'I\nam reading')

    def test_roman_length_changes_keep_source_partition_across_reader_chunks(self):
        raw='CHƯƠNG XIV: '+('NỘI DUNG GIỮ NGUYÊN VÀ AI. '*80)+'\nPHẦN XXIX\n'
        b=dict(format='epub',pages=[dict(text=raw,method='text',layout=[],warning='')],chapters=[],status='ready',
               segments=[dict(id=f'{i:032x}',page=0,text=c,originalText=c) for i,c in enumerate(split_text(raw))])
        process_book(b);expected=normalize_import_text(raw)[0]
        self.assertEqual(''.join(s['text'] for s in b['segments']),expected)
        self.assertTrue(expected.startswith('Chương 14:'))
        self.assertIn('Phần 29',expected)
        self.assertEqual(''.join(s['originalText'] for s in b['segments']),raw)
        first=copy.deepcopy(b['segments']);process_book(b);self.assertEqual(b['segments'],first)

    def test_pasted_text_uses_same_automatic_import_rules(self):
        import tempfile
        from core import Library
        from reading_tools import import_text
        with tempfile.TemporaryDirectory(dir=ROOT/'.qa') as tmp:
            lib=Library(Path(tmp)/'library')
            raw='CHƯƠNG IV: ĐỌC SÁCH VỚI AI\nTên Nguyễn Văn An.\n........\n'
            b=import_text(lib,'QA',raw)
            self.assertEqual(b['pages'][0]['text'],raw)
            self.assertEqual(''.join(s['originalText'] for s in b['segments']),raw)
            self.assertEqual(''.join(s['text'] for s in b['segments']),'Chương 4: đọc sách với AI\nTên Nguyễn Văn An.\n')

    def test_uppercase_only_lines_preserve_acronyms_spacing_numbers_and_diacritics(self):
        cases={
            'TƯ DUY PHẢN BIỆN':'Tư duy phản biện',
            '  “ĐỌC SÁCH VỀ AI Ở TP.HCM NĂM 2026!”\r\n':'  “Đọc sách về AI ở TP.HCM năm 2026!”\r\n',
            'CHƯƠNG IV: GDP VÀ USD':'Chương IV: GDP và USD',
            'AI NASA PDF':'AI NASA PDF',
            'Tên Nguyễn Văn An và AI giữ nguyên.':'Tên Nguyễn Văn An và AI giữ nguyên.',
            'PHẦN ĐẦU\nPHẦN SAU':'Phần đầu\nPhần sau',
            'ĐOẠN NÀY. ĐOẠN KẾ.':'Đoạn này. đoạn kế.',
            '1. GIỚI THIỆU\n\n***':'1. Giới thiệu\n\n***',
        }
        for raw,expected in cases.items():
            with self.subTest(raw=raw):
                value=normalize_all_caps_lines(raw)
                self.assertEqual(value,expected)
                self.assertEqual(len(value),len(raw))
                self.assertEqual(normalize_all_caps_lines(value),value)

    def test_import_normalizes_whole_lines_across_segments_and_retains_every_source_character(self):
        raw=('ĐÂY LÀ DÒNG DÀI GIỮ NGUYÊN NỘI DUNG VÀ AI. '*100)+'\nTên Nguyễn Văn An giữ nguyên.\n........\n'
        for fmt in ('epub','pdf'):
            b=dict(format=fmt,pages=[dict(text=raw,method='text',layout=[],warning='')],chapters=[],status='ready',
                   segments=[dict(id=f'{i:032x}',page=0,text=c,originalText=c) for i,c in enumerate(split_text(raw))])
            self.assertTrue(process_book(b))
            text=''.join(s['text'] for s in b['segments'])
            self.assertTrue(text.startswith('Đây là dòng dài'))
            self.assertEqual(text.count('Đây'),1)
            self.assertEqual(text.count('AI.'),100)
            self.assertIn('Tên Nguyễn Văn An giữ nguyên.',text)
            self.assertNotIn('........',text)
            self.assertEqual(''.join(s['originalText'] for s in b['segments']),raw)
            self.assertEqual(b['pages'][0]['text'],raw)
            before=copy.deepcopy(b['segments']);process_book(b)
            self.assertEqual(b['segments'],before)
