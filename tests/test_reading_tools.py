import sys,unittest,tempfile,wave,json,subprocess,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import Library
from reading_tools import import_text,search,annotation,read_notes,edition
from bilingual import parts,language,cache_signature
from ebook_reader import assemble
from m4b import chapter_marks

class ReadingToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='reading-',dir=Path(__file__).resolve().parents[1]/'.qa')
        self.root=Path(self.tmp.name);self.lib=Library(self.root/'library')
        self.book=import_text(self.lib,'Sách thử','Chào 🌍. Đọc tiếng Việt. It is a truth universally acknowledged.\nKết thúc.')
    def tearDown(self):self.tmp.cleanup()
    def test_paste_search_preserves_original(self):
        self.assertEqual(''.join(s['text'] for s in self.book['segments']),self.book['pages'][0]['text'])
        self.assertEqual(len(search(self.book,'doc tieng viet')),1)
        self.assertTrue(search(self.book,'🌍'))
        for query in ['',' '*5,'x'*201]:self.assertEqual(search(self.book,query),[])
        self.assertEqual((self.lib.directory(self.book['id'])/'source-0000.txt').read_text(),self.book['pages'][0]['text'])
    def test_annotations_reopen_edit_remove_and_stale_edition(self):
        b=self.book;cue=assemble(b)['sentences'][0];text=cue['text'];quote='🌍';start=len(text[:text.index(quote)].encode('utf-16-le'))//2
        r=dict(edition=edition(b),cueId=cue['id'],quote=quote,start=start,end=start+2,note='Ghi chú',color='yellow')
        notes=annotation(self.lib,b['id'],r);self.assertEqual(read_notes(self.lib,b['id']),notes)
        updated=annotation(self.lib,b['id'],dict(r,id=notes[0]['id'],note='Đã sửa'));self.assertEqual(len(updated),1)
        b['segments'][0]['text']='Nội dung mới.';self.lib.save(b)
        with self.assertRaises(ValueError):annotation(self.lib,b['id'],r)
        self.assertEqual(len(read_notes(self.lib,b['id'])),1)
        self.assertEqual(annotation(self.lib,b['id'],{'remove':notes[0]['id']}),[])
    def test_multi_sentence_annotation_and_legacy_take_are_not_relabelled(self):
        b=self.book;cues=assemble(b)['sentences'][:2]
        ranges=[dict(cueId=c['id'],quote=c['text'],start=0,end=len(c['text'].encode('utf-16-le'))//2) for c in cues]
        saved=annotation(self.lib,b['id'],dict(edition=edition(b),ranges=ranges,note='Qua hai câu',color='blue'))
        self.assertEqual(saved[0]['quote'],''.join(c['text'] for c in cues));self.assertEqual(len(saved[0]['ranges']),2)
        from m4b import freeze_labels
        self.assertEqual(freeze_labels(b,[dict(id='unknown',text='old',index=0,page=0)]),{})
    def test_bilingual_partition_language_cache(self):
        for text in ['Tiếng Việt. It is a truth universally acknowledged.\nKết thúc!', '🌍\nABC', '\n\nabc','hello','a'*1000]:self.assertEqual(''.join(parts(text)),text)
        self.assertEqual(language('Sherlock Holmes'),'vi');self.assertEqual(language('Đây là tiếng Việt.'),'vi');self.assertEqual(language('It is a truth universally acknowledged.'),'en')
        b=self.book;text='Sách';old=cache_signature(b,text);b['bilingual']=True;new=cache_signature(b,text);self.assertNotEqual(old,new);b['speed']=2;self.assertEqual(new,cache_signature(b,text));b['englishVoice']='Bella';self.assertNotEqual(new,cache_signature(b,text))
    def test_m4b_snapshot_chapters_and_actual_durations(self):
        from audiobooks import create
        b=self.book;b['chapterModel']='segments-v1';b['segments']=[dict(id='one',text='A.',originalText='A.',page=0,chapterId='a'),dict(id='two',text='B.',originalText='B.',page=0,chapterId='b')];b['chapters']=[dict(id='a',title='Chương Một',startPage=0),dict(id='b',title='Chương Hai',startPage=0)]
        take=create(b,[0,1],'Cả sách',{'type':'all'});paths=[]
        for i in range(2):
            p=self.root/f'{i}.wav';paths.append(p)
            with wave.open(str(p),'wb') as out:out.setparams((1,2,24000,0,'NONE',''));out.writeframes(b'\0\0'*(24000*(i+1)))
        b['chapters'][0]['title']='Tên thay đổi'
        marks=chapter_marks(b,take['segments'],paths,take);self.assertEqual([(c['title'],c['start'],c['end']) for c in marks],[('Chương Một',0,1),('Chương Hai',1,3)])
        selected=chapter_marks(b,[take['segments'][1]],[paths[1]],take);self.assertEqual(selected[0]['start'],0);self.assertEqual(selected[0]['title'],'Chương Hai')
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
    def test_real_m4b_cover_chapters_and_cancel(self):
        from exporting import ExportCancelled
        b=self.book
        p=self.lib.audio_path(b,b['segments'][0])
        with wave.open(str(p),'wb') as out:out.setparams((1,2,24000,0,'NONE',''));out.writeframes(b'\x10\x00'*24000)
        dest=self.root/'result.m4b';self.lib.export(b['id'],dest)
        result=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_chapters','-show_streams','-show_format','-of','json',str(dest)]))
        self.assertTrue(result['chapters']);self.assertTrue(any(s.get('disposition',{}).get('attached_pic') for s in result['streams']));self.assertEqual(result['format']['tags']['title'],'Sách thử')
        original=dest.read_bytes()
        with self.assertRaises(ExportCancelled):self.lib.export(b['id'],dest,cancelled=lambda:True)
        self.assertEqual(dest.read_bytes(),original);self.assertFalse((self.root/'result.partial.m4b').exists())

if __name__=='__main__':unittest.main()
