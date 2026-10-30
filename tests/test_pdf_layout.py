import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from core import split_text
from pdf_layout import process_book,plain,reflow,source_chunks
from chapters import public_sections,edit_chapter
from scopes import selected_indices,mark_chapter,remove_chapter
from book_pricing import sample_segments

def page(lines):
    text='';layout=[]
    for value,width,size in lines:
        layout.append(dict(text=value,w=width,size=size,h=15,y=len(layout)*20,startUTF16=len(text.encode('utf-16-le'))//2))
        text+=value+'\n'
    return dict(text=text,layout=layout,method='text',warning='')

def fixture():
    pages=[page([('🙂 những người Ronald Read những người Ronald Read',400,14),('Đối',20,14),('với',20,14),('nhữn',28,14),('g',7,14),('ngườ',28,14),('i biết',28,14),('Ron',25,14),('ald Read',40,14),('Kết thúc mở đầu.',200,14),('1',15,28),('CHƯƠNG ĐẦU',250,28),('Nội dung chương một.',400,14)]),
           page([('Cuối chương một.',400,14),('2',15,28),('CHƯƠNG SAU',250,28),('Nội dung chương hai.',400,14)])]
    return dict(pages=pages,chapters=[],segments=[dict(id=str(i)+'-'+str(j),page=i,text=t,originalText=t) for i,p in enumerate(pages) for j,t in enumerate(split_text(p['text']))],status='ready')

class PDFLayoutTests(unittest.TestCase):
    def test_default_import_cleanup_keeps_original_and_leaves_page_numbers(self):
        texts=['Chủ đề lặp\nNội dung trang một.\n..............\n1\n',
               'Chủ đề lặp\nNội dung trang hai.\n..............\n2\n',
               'Chủ đề lặp\nNội dung trang ba.\n..............\n3\n']
        pages=[dict(text=value,layout=[],method='text',warning='') for value in texts]
        b=dict(format='epub',pages=pages,chapters=[],segments=[dict(id=f'{i}-{j}',page=i,text=chunk,originalText=chunk)
            for i,value in enumerate(texts) for j,chunk in enumerate(split_text(value))],status='ready')
        self.assertTrue(process_book(b))
        self.assertEqual([p['text'] for p in b['pages']],texts)
        self.assertEqual(b['autoCleanup']['removedLines'],6)
        self.assertTrue(all('Chủ đề lặp' not in p['narrationText'] and '............' not in p['narrationText'] for p in b['pages']))
        self.assertEqual([p['narrationText'].splitlines()[-1] for p in b['pages']],['1','2','3'])
        self.assertEqual(''.join(s['originalText'] for s in b['segments']),''.join(texts))
        for i,p in enumerate(b['pages']):
            self.assertEqual(''.join(s['text'] for s in b['segments'] if s['page']==i),p['narrationText'])

    def test_default_reflow_removes_a_proven_line_wrap_hyphen(self):
        raw='Một doanh-\nnhân thành đạt.\n'
        line_rows=[dict(text='Một doanh-',w=300,size=12,h=15,y=0,start=0),
                   dict(text='nhân thành đạt.',w=300,size=12,h=15,y=20,start=len('Một doanh-\n'))]
        value,changes,uncertain=reflow(raw,line_rows,{})
        self.assertEqual(value,'Một doanh nhân thành đạt.')
        self.assertEqual(len(changes),1);self.assertEqual(uncertain,0)
        self.assertEqual(''.join(source_chunks(raw,split_text(value))),raw)

    def test_default_ocr_cleanup_joins_continuation_and_preserves_source(self):
        raw='Đây là dòng\ntiếp tục.\nTừ được ngắt doanh-\nnhân.\nCâu mới.\nTiếp theo.'
        p=dict(text=raw,layout=[],method='ocr',warning='')
        b=dict(format='pdf',pages=[p],chapters=[],segments=[dict(id='ocr-1',page=0,text=raw,originalText=raw)],status='ready')
        self.assertTrue(process_book(b))
        self.assertEqual(p['text'],raw)
        self.assertEqual(p['narrationText'],'Đây là dòng tiếp tục.\nTừ được ngắt doanh nhân.\nCâu mới.\nTiếp theo.')
        self.assertEqual(''.join(s['originalText'] for s in b['segments']),raw)

    def test_source_partition_and_midpage_chapters(self):
        b=fixture();raw=copy.deepcopy(b['pages']);process_book(b)
        self.assertEqual([p['text'] for p in raw],[p['text'] for p in b['pages']])
        self.assertTrue(all(plain(p['text']).casefold()==plain(p['narrationText']).casefold() for p in b['pages']))
        self.assertIn('Đối với những người biết Ronald Read',b['pages'][0]['narrationText'])
        sections=public_sections(b);self.assertEqual(len(sections),3)
        self.assertEqual(b['layoutProcessing']['chapterCount'],2)
        self.assertNotIn('Kết thúc mở đầu',sections[1]['text']);self.assertIn('Cuối chương một.',sections[1]['text'])
        self.assertNotIn('Chương sau',sections[1]['text']);self.assertTrue(sections[2]['text'].startswith('2'))
        ids=[i for c in sections for i in selected_indices(b,dict(type='chapter',chapterId=c['id']))]
        self.assertEqual(ids,list(range(len(b['segments']))))
        self.assertEqual(''.join(c['originalText'] for c in sections),''.join(p['text'] for p in raw))
        self.assertEqual(''.join(s['originalText'] for s in b['segments']),''.join(p['text'] for p in raw))
        self.assertTrue(sample_segments(b)[0]['text'].startswith('1'))
    def test_edit_shared_page_and_empty_chapter_does_not_touch_neighbor(self):
        b=fixture();process_book(b);c=public_sections(b)[1];neighbor=public_sections(b)[2]['text'];raw=copy.deepcopy(b['pages'])
        edit_chapter(b,c['id'],'Sửa chương đầu.',expected=c['text'])
        self.assertEqual(public_sections(b)[2]['text'],neighbor)
        self.assertEqual(public_sections(b)[1]['text'],'Sửa chương đầu.')
        edit_chapter(b,c['id'],'');self.assertEqual(public_sections(b)[1]['text'],'')
        edit_chapter(b,c['id'],'Đọc lại.');self.assertEqual(public_sections(b)[1]['text'],'Đọc lại.')
        self.assertEqual(public_sections(b)[2]['text'],neighbor)
        self.assertEqual([p['text'] for p in raw],[p['text'] for p in b['pages']])
    def test_cancel_checkpoints_and_resume(self):
        b=fixture();states=[]
        self.assertFalse(process_book(b,save=lambda:states.append(copy.deepcopy(b)),cancel=lambda:len(states)>=1))
        self.assertEqual(states[-1]['processing']['done'],1)
        self.assertTrue(any(s['page']==1 for s in b['segments']))
        self.assertTrue(process_book(b));self.assertEqual(len(b['chapters']),3)
        first=copy.deepcopy(b['segments']);process_book(b);self.assertEqual(first,b['segments'])
    def test_uncertain_spellings_and_numbers_are_not_invented(self):
        b=fixture();b['pages'][0]=page([('Nhữx',20,14),('g',10,14),('1',10,28),('HÌNH MINH HỌA',200,28)])
        process_book(b);self.assertIn('Nhữx g',b['pages'][0]['narrationText']);self.assertEqual(len(b['chapters']),1)
    def test_manual_marker_and_removal_preserve_sources(self):
        b=fixture();process_book(b);source=''.join(p['text'] for p in b['pages']);before=''.join(s['text'] for s in b['segments'])
        c=mark_chapter(b,1,'Mốc tay');self.assertEqual(''.join(x['originalText'] for x in b['chapters']),source)
        remove_chapter(b,c['id']);self.assertEqual(''.join(s['text'] for s in b['segments']),before)
        self.assertEqual(''.join(x['originalText'] for x in b['chapters']),source)

if __name__=='__main__':unittest.main()
