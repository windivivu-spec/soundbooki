import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('pilot', ROOT/'pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotTranscriptTests(unittest.TestCase):
    def test_punctuation_case_and_unicode_form_can_agree(self):
        self.assertEqual(pilot.normalized_words('“SÁCH NÓI”, Việt Nam!'),
                         pilot.normalized_words('sách nói Việt Nam'))

    def test_vietnamese_accent_error_is_rejected(self):
        self.assertNotEqual(pilot.normalized_words('Tôi đọc sách.'),
                            pilot.normalized_words('Tôi độc sách.'))

    def test_missing_word_is_rejected(self):
        self.assertNotEqual(pilot.normalized_words('Tôi đang đọc sách.'),
                            pilot.normalized_words('Tôi đọc sách.'))

    def test_boundary_requires_pause_and_no_previous_overlap(self):
        clips = [dict(start=0, end=3), dict(start=3.5, end=6), dict(start=6.5, end=8)]
        self.assertTrue(pilot.resolvable_boundary(clips, 1))
        clips[2]['start'] = 6.1
        self.assertFalse(pilot.resolvable_boundary(clips, 1))
        clips[2]['start'] = 6.5
        clips[0]['end'] = 3.6
        self.assertFalse(pilot.resolvable_boundary(clips, 1))
        self.assertFalse(pilot.resolvable_boundary(clips, 2))


if __name__ == '__main__':
    unittest.main()
