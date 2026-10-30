"""Real Nano lookahead in a fresh QA library; no network, fixture text only."""
import json,os,queue,subprocess,sys,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
import model_manager as models
folder=ROOT/'.qa/listening'/uuid.uuid4().hex;folder.mkdir(parents=True)
(folder/'resources').mkdir();(folder/'resources/config.json').write_text(json.dumps({'profiles':{'nano':str(models.verified_location('nano'))}}))
source=folder/'source.txt';source.write_text('Sách QA tổng hợp.')
lib=Library(folder/'library');b=lib.create([source]);b['title']='Nghe Nano liền mạch'
for page in range(16):lib.add_page(b,0,dict(page=page,text=f'Trang {page+1}. Sách mở ra một thế giới mới. Mỗi ngày, hãy dành chút thời gian để lắng nghe và khám phá.',method='text',warning=''))
b.update(status='ready',audiobooks=[]);lib.save(b);bid=b['id'];q=queue.Queue();log=(folder/'worker.log').open('w')
p=subprocess.Popen([str(ROOT/'.runtime/bin/python'),'-B',str(ROOT/'backend/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,env=os.environ|{'WINDI_SACH_HOME':str(folder/'library')})
def reader():
 for line in p.stdout:q.put((time.monotonic(),json.loads(line)))
threading.Thread(target=reader,daemon=True).start()
def send(**r):p.stdin.write(json.dumps(r,ensure_ascii=False)+'\n');p.stdin.flush()
def wait(fn):
 end=time.monotonic()+180
 while time.monotonic()<end:
  try:t,e=q.get(timeout=1)
  except queue.Empty:continue
  if e.get('event')=='error' or (e.get('event')=='listeningBuffer' and e.get('state')=='error'):raise AssertionError(e)
  if fn(e):return t,e
 raise TimeoutError('worker')
report={'fixtureOnly':True,'folder':str(folder),'bookId':bid}
try:
 start=time.monotonic();send(action='prepareListening',bookId=bid,start=0,scope={'type':'range','fromPage':1,'toPage':12},seconds=180,token='cold')
 ready=[]
 while True:
  t,e=wait(lambda e:e.get('event') in ('listeningReady','listeningBuffer'))
  if e['event']=='listeningBuffer':break
  ready.append({'index':e['index'],'readySeconds':t-start,'duration':e['duration'],'path':e['path']})
 assert len(ready)==12 and ready[0]['index']==0
 report['coldFirstAudioSeconds']=round(ready[0]['readySeconds'],3)
 # Once the first segment starts, later segments should be ready before their
 # deadlines even at 2x. This measures generation headroom, not speaker output.
 deadline=ready[0]['readySeconds'];headroom=[]
 for item in ready:
  headroom.append(deadline-item['readySeconds']);deadline+=item['duration']/2
 assert min(headroom[1:])>0
 report['minimumHeadroomAt2xSeconds']=round(min(headroom[1:]),3)
 report['bufferedSegments']=len(ready);report['audioSeconds']=round(sum(x['duration'] for x in ready),3)
 assert not lib.load(bid)['audiobooks']
 # Refill a fresh page through the same resident process and retain 16-step cache.
 warm=time.monotonic();send(action='prepareListening',bookId=bid,start=12,scope={'type':'page','page':13},seconds=30,token='warm')
 t,next_item=wait(lambda e:e.get('event')=='listeningReady' and e['token']=='warm')
 report['warmNextAudioSeconds']=round(t-warm,3);report['paths']=[x['path'] for x in ready]
 wait(lambda e:e.get('event')=='listeningBuffer' and e['token']=='warm')
 assert all(not lib.audio_path(b,s).exists() for s in b['segments'][13:])
 before=[Path(x['path']).stat().st_mtime_ns for x in ready]
 send(action='prepareListening',bookId=bid,start=0,scope={'type':'range','fromPage':1,'toPage':12},seconds=180,token='cached')
 wait(lambda e:e.get('event')=='listeningBuffer' and e['token']=='cached')
 assert before==[Path(x['path']).stat().st_mtime_ns for x in ready]
 send(action='settings',bookId=bid,voice='Mỹ Duyên')
 _,changed=wait(lambda e:e.get('event')=='book' and e['book']['voice']=='Mỹ Duyên')
 assert changed['book']['readyCount']==0
 report.update(cacheReusedWithoutWrites=True,voiceInvalidates=True,unselectedPagesUntouched=True,passed=True)
finally:
 send(action='shutdown');p.stdin.close();p.wait(timeout=15);log.close()
 (ROOT/'.qa/listening/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
