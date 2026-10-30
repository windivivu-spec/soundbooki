import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library,signature
from model_manager import profile,voices,manifest
from exporting import portable_page

class LanguageTests(unittest.TestCase):
    def test_book_language_defaults_and_original_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'english.txt';source.write_text('Original text. Nội dung gốc.')
            library=Library(root/'library')
            english=library.create([source],language='en')
            self.assertEqual((english['model'],english['voice'],english['language']),('kitten','Jasper','en'))
            text=source.read_text();library.add_page(english,0,dict(page=0,text=text,method='text',warning=''))
            self.assertEqual(''.join(s['originalText'] for s in english['segments']),text)
            self.assertEqual(library.load(english['id'])['language'],'en')
            vietnamese=library.create([source]);self.assertEqual((vietnamese['model'],vietnamese['language']),('nano','vi'))
            with self.assertRaises(ValueError):library.create([source],language='xx')

    def test_small_english_profile_and_isolated_cache(self):
        self.assertLess(sum(f['size'] for f in manifest('kitten')['files']),100_000_000)
        self.assertEqual(profile('kitten')['languages'],['en'])
        self.assertEqual(profile('kitten')['sampleRate'],24000)
        self.assertEqual(len(voices('kitten')),8)
        self.assertNotEqual(signature('Hello','Jasper','kitten'),signature('Hello','Jasper','nano'))

    def test_english_portable_player_preserves_user_content(self):
        text='Tốc độ <script>alert("never execute")</script> English source.'
        files=portable_page('Tốc độ',[dict(text=text,page=0,index=0)],[4.0],'Page','en')
        self.assertIn('lang="en"',files['index.html']);self.assertIn('<title>Tốc độ</title>',files['index.html'])
        self.assertIn('Speed',files['index.html']);self.assertIn('Listen here',files['index.html'])
        data=json.loads(files['book.json']);self.assertEqual(data['segments'][0]['text'],text)
        self.assertEqual(data['segments'][0]['title'],'Page 1 · Segment 1')
        self.assertEqual(data['language'],'en');self.assertNotIn('<script>alert',files['book.js'])

if __name__=='__main__':unittest.main()
