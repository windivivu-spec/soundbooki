"""Build an isolated, synthetic book for verify_music_ui.swift."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from core import Library
from music import catalog
import model_manager

root=ROOT/'.qa/music-ui';root.mkdir(parents=True,exist_ok=True)
source=root/'source.epub';source.write_bytes(b'fixture')
lib=Library(root/'library');book=lib.create([source]);book['title']='Một khoảng lặng giữa những trang sách'
lib.add_page(book,0,dict(page=0,text='Một buổi sáng yên tĩnh, mở sách và lắng nghe câu chuyện của bạn.',method='text',warning=''))
book['status']='ready';lib.save(book)
fixture=dict(init=dict(event='init',books=[x for x in lib.summaries() if x['id']==book['id']],voices=model_manager.voices(),ready=True,music=catalog()),models=dict(event='models',**model_manager.catalog()),book=dict(event='book',book=lib.public(book)))
(root/'fixture.json').write_text(json.dumps(fixture,ensure_ascii=False))
print('Isolated music UI fixture ready')
