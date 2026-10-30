from pathlib import Path
import sys,json,wave
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library,atomic_json
from book_cloud import local_info
from model_manager import catalog
from book_pricing import VOICES
from launch_offer import policy
folder=ROOT/'.qa/book-ui';folder.mkdir(parents=True,exist_ok=True)
source=folder/'fixture.txt';source.write_text('Nguồn thử nghiệm riêng cho QA.')
lib=Library(folder/'library');b=lib.create([source]);lib.add_page(b,0,dict(page=0,text='Lời tựa sách thử nghiệm.',method='fixture',warning=''))
lib.add_page(b,0,dict(page=1,text='Chương 1. '+('Sách mở ra những thế giới mới. Tiếng Việt cần giữ nguyên dấu và nội dung. '*80),method='fixture',warning=''))
b.update(status='ready',model='pro-cloud',voice=VOICES[0]['id'],chapters=[dict(id='one',title='Chương 1',startPage=1,origin='epub')]);lib.save(b)
with wave.open(str(folder/'trial.wav'),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*2400)
model=catalog();model['event']='models'
info=local_info(b)|dict(configured=True,serviceCheckPending=False,trialsRemaining=5,trialLimit=5,trialCharacters=5000)
group_info=local_info(b,chapter_id='one',group_trial=True)|dict(configured=True,serviceCheckPending=False,trialsRemaining=5,trialLimit=5,trialCharacters=5000)
launch=dict(offer=policy(),bundle=None,order=None,bank=dict(bin="970423",name="QA BANK",account="0000000000",holder="QA ONLY"),configured=True,available=True)
atomic_json(folder/'fixture.json',dict(models=model,book=dict(event='book',book=lib.public(b)),init=dict(event='init',books=lib.summaries(),voices=[],ready=True,music=[]),info=info,groupInfo=group_info,launch=launch))
