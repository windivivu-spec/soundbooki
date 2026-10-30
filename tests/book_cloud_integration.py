"""Real local HTTPS → atomic WAV download → immutable take → export. No paid provider."""
from pathlib import Path
import hashlib,io,json,ssl,subprocess,sys,threading,urllib.request,uuid,wave
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import book_cloud as cloud
from book_pricing import price,VOICES
from core import Library,valid_audio,signature,atomic_json
direct_mode=False
folder=ROOT/'.qa/book-contract'/uuid.uuid4().hex;folder.mkdir(parents=True)
subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(folder/'key.pem'),'-out',str(folder/'cert.pem'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def wav():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*2400)
    return out.getvalue()
audio=wav();orders={};objects={};calls=[];corrupt=set();requests={};used=0
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def output(self,value,status=200,mime='application/json'):
        data=value if isinstance(value,bytes) else json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_POST(self):
        global used
        assert self.headers.get('Authorization')=='Bearer wsn_book_'+'a'*64
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append((self.path,data))
        if self.path in ('/quote','/trial','/trial-group'):
            snap=data['snapshot'];kind='trial' if self.path in ('/trial','/trial-group') else 'book'
            if data['requestKey'] in requests:
                old=requests[data['requestKey']];assert old['snapshot']==snap
                self.output(dict(order=old['order'],trialsRemaining=5-used,trialLimit=5,trialCharacters=5000));return
            oid=str(uuid.uuid4())
            count=sum(len(s['text']) for s in snap['segments'])
            debit=(count+4999)//5000 if kind=='trial' else 0
            if self.path=='/trial-group':assert 2<=snap['trialUnits']<=4 and debit==snap['trialUnits']
            used+=debit
            o=dict(id=oid,kind=kind,trialUnits=debit,state='queued' if kind=='trial' else 'awaiting_payment',amountVND=0 if kind=='trial' else price(count)['amountVND'],done=0,total=len(snap['segments']))
            orders[oid]=dict(order=o,snapshot=snap,available=[]);requests[data['requestKey']]=orders[oid];self.output(dict(order=o,trialsRemaining=5-used,trialLimit=5,trialCharacters=5000));return
        entry=orders[data['orderId']];results=[]
        for s in entry['available']:
            if s['id'] not in data.get('knownSegments',[]):
                key=entry['order']['id']+'/'+s['id']+'.wav';objects[key]=audio
                results.append(dict(id=s['id'],sha256=hashlib.sha256(audio).hexdigest(),url=('https://resource.heygen.ai/'+key if direct_mode else base+'/storage/v1/object/sign/wsn-book-audio/'+key),**({'delivery':'provider'} if direct_mode else {})))
        self.output(dict(order=entry['order'],audio=results,trialsRemaining=5-used,trialLimit=5,trialCharacters=5000))
    def do_GET(self):
        assert self.headers.get('Authorization') is None
        key=self.path.split('/wsn-book-audio/')[1];self.output(b'incomplete' if key in corrupt else objects[key],mime='audio/wav')
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(folder/'cert.pem',folder/'key.pem');server.socket=ctx.wrap_socket(server.socket,server_side=True)
threading.Thread(target=server.serve_forever,daemon=True).start();base='https://localhost:'+str(server.server_address[1])
class LocalClient(cloud.Client):
    def __init__(self):
        self.base=base;self.device='SNAAAAAAAAAAAA';self.token='wsn_book_'+'a'*64
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),cloud.NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(folder/'cert.pem'))))
source=folder/'fixture.txt';source.write_text('Fixture only');lib=Library(folder/'library');b=lib.create([source])

for i in range(20):lib.add_page(b,0,dict(page=i,text=(('Trang '+str(i)+'. Tiếng Việt nguyên vẹn. ')*10),method='fixture',warning=''))
b.update(status='ready',model='pro-cloud',voice=VOICES[0]['id']);lib.save(b)
report={}
try:
 with patch.object(cloud,'Client',LocalClient):
    trial=cloud.create_order(lib,b['id'],'trial','a'*32,True)['order'];entry=orders[trial['id']]
    assert 4250<=sum(len(s['text']) for s in entry['snapshot']['segments'])<=5000
    assert len(entry['snapshot']['segments'])==1
    entry['available']=entry['snapshot']['segments'];entry['order']['state']='ready'
    progress=[]
    result=cloud.sync_order(lib,b['id'],trial['id'],on_progress=progress.append);assert result['trialAudio'];
    assert [p['receivedSegments'] for p in progress]==[0,1]
    assert not progress[0]['trialAudio'] and len(progress[1]['trialAudio'])==1
    assert valid_audio(Path(progress[1]['trialAudio'][0]['audio']))
    assert all(p['stage']=='receiving' and p['order']['id']==trial['id'] for p in progress)
    report['verifiedAudioPublishedBeforeFinalResult']=True
    assert lib.public(lib.load(b['id']))['readyCount']==0
    trial_take=lib.public(lib.load(b['id']))['audiobooks'][0];assert trial_take['cloudKind']=='trial' and trial_take['status']=='ready'
    lib.export(b['id'],folder/'trial-export.wav',take_id=trial_take['id']);assert valid_audio(folder/'trial-export.wav')
    report['trialLocallySavedAndExportable']=True
    current=lib.load(b['id']);current['chapters']=[dict(id='one',title='Chương thử',startPage=0,origin='manual')];lib.save(current)
    from book_pricing import chapter_trial_units
    units=chapter_trial_units(current,'one');assert units==2
    group=cloud.create_order(lib,b['id'],'trial','c'*32,True,chapter_id='one',trial_units=units)['order']
    assert group['trialUnits']==2 and calls[-1][0]=='/trial-group'
    repeat=cloud.create_order(lib,b['id'],'trial','c'*32,True,chapter_id='one',trial_units=units)['order']
    assert repeat['id']==group['id'] and used==3
    group_entry=orders[group['id']];group_entry['available']=group_entry['snapshot']['segments'];group_entry['order']['state']='ready'
    complete=cloud.sync_order(lib,b['id'],group['id']);assert len(complete['trialAudio'])==len(group_entry['snapshot']['segments'])
    assert ''.join(s['text'] for s in group_entry['snapshot']['segments'])==''.join(s['text'] for s in current['segments'])
    report['groupedChapterAndIdempotentDebit']=True
    current=lib.load(b['id']);current['voice']=VOICES[1]['id'];lib.save(current)
    quote=cloud.create_order(lib,b['id'],'book','b'*32,True)['order'];entry=orders[quote['id']]
    cloud.sync_order(lib,b['id'],quote['id']);assert not any(t.get('cloudOrderId')==quote['id'] for t in lib.load(b['id']).get('audiobooks',[]))
    entry['available']=entry['snapshot']['segments'][:1];entry['order']['state']='processing';cloud.sync_order(lib,b['id'],quote['id'])
    current=lib.load(b['id']);first=lib.directory(b['id'])/'audio'/(cloud.cloud_signature(entry['snapshot']['segments'][0],entry['snapshot'])+'.wav');assert valid_audio(first);mtime=first.stat().st_mtime_ns
    current['segments'][0]['text']+=' Nội dung mới.';current['voice']=VOICES[2]['id'];lib.save(current)
    entry['available']=entry['snapshot']['segments'];entry['order']['state']='ready'
    corrupt.add(quote['id']+'/'+entry['available'][1]['id']+'.wav')
    partial_progress=[]
    try:cloud.sync_order(lib,b['id'],quote['id'],on_progress=partial_progress.append);raise AssertionError('Accepted corrupt download')
    except ValueError:pass
    assert first.stat().st_mtime_ns==mtime
    assert partial_progress and partial_progress[0]['receivedSegments']>=1
    corrupt.clear();cloud.sync_order(lib,b['id'],quote['id']);current=lib.load(b['id']);public=lib.public(current)
    assert public['readyCount']==0;take=next(t for t in public['audiobooks'] if t.get('cloudOrderId')==quote['id']);assert take['status']=='ready'
    assert take['voice']==VOICES[1]['id'];assert all('Nội dung mới.' not in s['text'] for s in take['segments'])
    destination=folder/'paid-take.wav';lib.export(b['id'],destination,take_id=take['id']);assert valid_audio(destination)
    direct_mode=True
    direct=cloud.create_order(lib,b['id'],'trial','d'*32,True,chapter_id='one',trial_units=1)['order']
    direct_entry=orders[direct['id']];direct_entry['available']=direct_entry['snapshot']['segments'];direct_entry['order']['state']='ready'
    class DirectClient(LocalClient):
        def __init__(self):
            super().__init__();opener=self.opener
            class Transport:
                def open(self,url,**kwargs):
                    if isinstance(url,str) and url.startswith('https://resource.heygen.ai/'):
                        url=base+'/storage/v1/object/sign/wsn-book-audio/'+url.split('https://resource.heygen.ai/',1)[1]
                    return opener.open(url,**kwargs)
            self.opener=Transport()
    with patch.object(cloud,'Client',DirectClient):
        direct_result=cloud.sync_order(lib,b['id'],direct['id'])
        assert direct_result['localReady'] and direct_result['trialAudio']
        assert direct_result['audio'][0]['delivery']=='provider'
        calls_before=len(calls);cloud.sync_order(lib,b['id'],direct['id'])
        assert len(calls)==calls_before+1 and not calls[-1][1]['knownSegments']==[]
    report['directProviderLinkViaTLSAndCacheRetry']=True
    report.update(interruptedDownloadRetainsCompletedAudio=True,retryReusesCache=True,editedBookDoesNotPlayStaleAudio=True,paidTakeRetainsPurchasedTextAndVoice=True,paidTakeWavExport=True,passed=True)
finally:server.shutdown();server.server_close()
atomic_json(ROOT/'.qa/book-contract/report.json',report);print(json.dumps(report,indent=2))
