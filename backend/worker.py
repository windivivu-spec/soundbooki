"""JSON-lines coordinator. Network only for explicit model setup and Clone Pro actions."""
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from core import Library, valid_audio
from scopes import selected_indices, mark_chapter, remove_chapter
from music import catalog as music_catalog, music_settings
import model_manager as models
import entitlements
from features import require_pro_max, require_local_model

ROOT=Path(__file__).resolve().parents[1]
HOME=Path(os.environ.get('WINDI_SACH_HOME',str(Path.home()/'Library/Application Support/Windi Sach Noi/library')))
OUTPUT=threading.Lock()

def emit(**value):
    with OUTPUT:
        sys.__stdout__.write(json.dumps(value,ensure_ascii=False)+'\n'); sys.__stdout__.flush()

class Worker:
    def __init__(self, home=HOME):
        self.lib=Library(home)
        self.jobs={}
        self.reader_tasks={}
        self.cover_lock=threading.Lock()
        self.jobs_lock=threading.RLock()
        self.extractor=Path(os.environ.get('WINDI_EXTRACTOR',str(ROOT/'.build/windi-extract')))
        from nano_session import NanoSession
        self.nano=NanoSession(ROOT,self.lib.root.parent/'nano-listening.log')
        self.listening=None

    def cancel_listening(self):
        with self.jobs_lock:
            if self.listening:self.listening['cancel'].set()

    def prepare_listening(self, bid, start=0, scope=None, seconds=60, token=''):
        """Bounded lookahead for the selected book only; never creates a take."""
        b=self.lib.load(bid)
        if b.get('status')!='ready':return
        if b.get('model','nano')!='nano':return
        entitlements.require_model('nano')
        if not models.ready('nano'):raise ValueError('Gói Nano chưa đầy đủ hoặc bị lỗi. Mở Gói giọng đọc để cài lại.')
        indices=selected_indices(b,scope or {'type':'all'})
        from cleanup import narratable
        indices=[i for i in indices if i>=start and narratable(b['segments'][i]['text'])][:12]
        if not indices:return
        self.cancel_listening()
        j=dict(id=bid,cancel=threading.Event(),process=None,token=token)
        with self.jobs_lock:self.listening=j
        voice=b['voice'];model_path=str(models.verified_location('nano'))
        target=min(180,max(30,float(seconds)))
        def run():
            import wave
            try:
                buffered=0.0
                for at,i in enumerate(indices):
                    if j['cancel'].is_set():return
                    # Explicit generation gets the model after at most one buffer segment.
                    with self.jobs_lock:
                        if 'audio' in self.jobs or 'preview' in self.jobs:return
                    s=b['segments'][i];path=self.lib.audio_path(b,s)
                    if not valid_audio(path):
                        request=dict(model='nano',models=model_path,revision=models.revision('nano'),voice=voice,
                            segments=[dict(id=s['id'],text=s['text'],path=str(path))])
                        request.update(bilingual=b.get('bilingual',False),englishVoice=b.get('englishVoice','Jasper'))
                        for result in self.engine_results(request,j,self.lib.directory(bid)/'engine.log'):pass
                    if j['cancel'].is_set():return
                    with self.lib.lock:
                        current=self.lib.load(bid)
                        if current.get('model','nano')!='nano' or current['voice']!=voice or current.get('bilingual',False)!=b.get('bilingual',False):return
                        if i>=len(current['segments']) or current['segments'][i]['id']!=s['id'] or current['segments'][i]['text']!=s['text']:return
                        if not valid_audio(path):raise ValueError('Nano chưa tạo được đoạn đọc hợp lệ.')
                        with wave.open(str(path),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
                    buffered+=duration
                    emit(event='listeningReady',bookId=bid,index=i,segmentId=s['id'],text=s['text'],voice=voice,
                         model='nano',path=str(path),duration=duration,token=token)
                    if at>=2 and buffered>=target:break
                if not j['cancel'].is_set():emit(event='listeningBuffer',bookId=bid,state='ready',token=token)
            except Exception as error:
                if not j['cancel'].is_set():emit(event='listeningBuffer',bookId=bid,state='error',message=str(error),token=token)
            finally:
                with self.jobs_lock:
                    if self.listening is j:self.listening=None
        threading.Thread(target=run,daemon=True).start()

    def engine_results(self, request, j, log):
        if request.get('bilingual') and request['model']=='nano':
            from bilingual import synthesize
            yield from synthesize(self,request,j,log)
            return
        if request['model']=='nano':
            request['revision']=models.revision('nano')
            yield from self.nano.stream(request,j)
            return
        with log.open('ab') as err:
            executable=str(ROOT/'.runtime-f5/bin/python') if request['model']=='f5-private' else sys.executable
            engine='clone_pro.py' if request['model']=='clone-pro' else 'engine.py'
            p=subprocess.Popen([executable,'-B',str(ROOT/'backend'/engine)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True)
            j['process']=p
            if j['cancel'].is_set():p.terminate();p.wait();return
            p.stdin.write(json.dumps(request,ensure_ascii=False));p.stdin.close()
            for line in p.stdout:yield json.loads(line)
            code=p.wait()
            if code!=0 and not j['cancel'].is_set():raise ValueError('Tạo giọng bị gián đoạn. Bấm nghe để thử lại đoạn chưa xong.')

    def model_event(self):
        emit(event='models',**models.catalog())

    def cloud_connection(self, pack=None, key=None, refresh_voices=False):
        require_pro_max()
        with self.jobs_lock:
            if any(k in self.jobs for k in ('audio','export','cloud')):
                emit(event='cloudConnection',running=False,success=False,message='Hãy chờ hoặc hủy tạo/xuất audio trước khi cập nhật ví credit.')
                return
            self.jobs['cloud']={'id':None,'cancel':threading.Event(),'process':None}
        emit(event='cloudConnection',running=True)
        def task():
            try:
                from clone_pro import refresh_wallet,purchase_credits
                result=purchase_credits(pack,key) if pack is not None else refresh_wallet(refresh_voices)
                self.model_event()
                emit(event='cloudConnection',running=False,success=True,wallet=result if pack is None else None,order=result if pack is not None else None,
                     message='Đã cập nhật ví credit.' if pack is None else 'Đã tạo yêu cầu mua credit. Chỉ cộng credit khi tiền vào được xác nhận.')
            except Exception as error:
                emit(event='cloudConnection',running=False,success=False,
                     message=str(error) if isinstance(error,ValueError) else 'Chưa cập nhật được ví credit. Kiểm tra mạng và thử lại.')
            finally:
                with self.jobs_lock:self.jobs.pop('cloud',None)
        threading.Thread(target=task,daemon=True).start()

    def download_model(self,model_id):
        require_local_model(model_id)
        entitlements.require_model(model_id)
        item=next((m for m in models.catalog()['models'] if m['id']==model_id),None)
        if not item:raise ValueError('Gói giọng không hợp lệ.')
        if not item['supported']:raise ValueError('Gói giọng này cần Mac Apple Silicon với ít nhất 8 GB RAM.')
        if not item['canDownload']:raise ValueError('Chưa đủ dung lượng trống để tải gói giọng.')
        with self.jobs_lock:
            if 'model' in self.jobs:raise ValueError('Một model đang được tải. Hãy chờ hoặc hủy trước.')
            j={'id':None,'cancel':threading.Event(),'process':None};self.jobs['model']=j
        emit(event='modelJob',modelId=model_id,running=True)
        def task():
            try:
                args=[sys.executable,'-B',str(ROOT/'backend/model_manager.py'),'--install',model_id]
                if model_id=='nano' and models.ready('nano'):args+=['--reuse-cache',str(models.location('nano'))]
                p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True);j['process']=p
                if j['cancel'].is_set():p.terminate()
                for line in p.stdout:
                    result=json.loads(line)
                    if 'error' in result:raise ValueError(result['error'])
                    if 'done' in result:emit(event='modelProgress',modelId=model_id,**result)
                if p.wait()!=0 and not j['cancel'].is_set():raise ValueError('Tải model bị gián đoạn. Bấm tải tiếp để giữ phần đã tải.')
            except Exception as error:
                if not j['cancel'].is_set():emit(event='error',message=str(error))
            finally:
                with self.jobs_lock:self.jobs.pop('model',None)
                self.model_event();emit(event='modelJob',modelId=model_id,running=False,cancelled=j['cancel'].is_set())
        threading.Thread(target=task,daemon=True).start()

    def book_event(self,bid,request_id=None):
        with self.lib.lock:
            b=self.lib.load(bid)
            from audiobooks import archive_existing
            if 'audiobooks' not in b:
                archive_existing(self.lib,b);b.setdefault('audiobooks',[]);self.lib.save(b)
            emit(event='book',book=self.lib.public(b),requestId=request_id)
        emit(event='library',books=self.lib.summaries())

    def launch(self,kind,bid,fn):
        with self.jobs_lock:
            if kind in self.jobs: raise ValueError('Công việc này đang chạy. Hủy hoặc chờ hoàn tất.')
            j={'id':bid,'cancel':threading.Event(),'process':None}
            self.jobs[kind]=j
        def run():
            try: fn(j)
            except Exception as e:
                with self.lib.lock:
                    b=self.lib.load(bid)
                    if kind=='import': b['status']='paused' if j['cancel'].is_set() else 'error'
                    if kind=='audio' and j.get('takeId'):
                        from audiobooks import find
                        take=find(b,j['takeId']);take['status']='cancelled' if j['cancel'].is_set() else 'error';take['error']=str(e)
                    b['error']='' if j['cancel'].is_set() else str(e)
                    self.lib.save(b)
                emit(event='error',message=str(e),bookId=bid,kind=kind) if not j['cancel'].is_set() else None
            finally:
                with self.jobs_lock: self.jobs.pop(kind,None)
                self.book_event(bid)
                emit(event='job',kind=kind,bookId=bid,running=False,cancelled=j['cancel'].is_set())
        emit(event='job',kind=kind,bookId=bid,running=True)
        threading.Thread(target=run,daemon=True).start()

    def cancel(self,kind):
        with self.jobs_lock:
            j=self.jobs.get(kind)
            if j:
                j['cancel'].set()
                if j['process'] and j['process'].poll() is None: j['process'].terminate()

    def extract(self,bid,force=False,refresh_layout=False):
        def task(j):
            started=time.monotonic();last_event=0
            def progress(**state):
                emit(event='processing',kind='import',bookId=bid,elapsedSeconds=round(time.monotonic()-started,1),**state)
            with self.lib.lock:
                b=self.lib.load(bid); b['status']='importing'; b['error']=''; b['forceOCR']=force or b.get('forceOCR',False)
                refresh=refresh_layout or b.get('refreshLayout',False)
                if refresh:b['refreshLayout']=True
                self.lib.save(b)
            for source in range(len(b['sources'])):
                with self.lib.lock:
                    b=self.lib.load(bid)
                    if source < b['importedSources'] and not refresh: continue
                    saved=[p for p in b['pages'] if p['source']==source]
                    start=next((p['sourcePage'] for p in saved if not p.get('layoutScanned')),len(saved)) if refresh else len(saved)
                    if refresh and start==len(saved):continue
                if j['cancel'].is_set(): break
                args=[str(self.extractor),str(self.lib.directory(bid)/b['sources'][source]['file']),str(start)]
                is_epub=Path(b['sources'][source]['file']).suffix.lower()=='.epub'
                if is_epub:
                    args=[sys.executable,'-B',str(ROOT/'backend/epub.py'),args[1],str(start)]
                else:
                    args+=['--language='+b.get('language','vi')]
                    if b['forceOCR']: args+=['--ocr']
                p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
                j['process']=p
                if j['cancel'].is_set(): p.terminate()
                for line in p.stdout:
                    if j['cancel'].is_set(): break
                    page=json.loads(line)
                    if 'error' in page: raise ValueError(page['error'])
                    with self.lib.lock:
                        b=self.lib.load(bid)
                        if not refresh:b['totalPages']=len(b['pages'])+page['total']-page['page']
                        if is_epub:
                            b['format']='epub';b['unitLabel']='mục';b['title']=page['bookTitle']
                        if source==0 and page.get('chapters') and not b.get('chapters'):
                            b['chapters']=page['chapters'] if is_epub else [dict(id='pdf-'+str(c['page']),title=c['title'],startPage=c['page'],origin='pdf') for c in page['chapters']]
                        if refresh:
                            target=next((p for p in b['pages'] if p['source']==source and p['sourcePage']==page['page']),None)
                            if target is None:raise ValueError('Số trang nguồn đã thay đổi. Hãy nhập thành cuốn sách mới.')
                            # Never replace the saved source or an edited narration.
                            target['layout']=page.get('layout',[]) if page['text']==target['text'] else []
                            target['layoutScanned']=True;target['pageWidth']=page.get('pageWidth',0);self.lib.save(b)
                        else:self.lib.add_page(b,source,page)
                    progress(phase='extract',done=page['page']+1 if refresh else len(b['pages']),total=page['total'] if refresh else b['totalPages'])
                    # Full chapter/source snapshots are expensive and unnecessary
                    # on every page. Page checkpoints themselves stay atomic.
                    if time.monotonic()-last_event>.8:
                        self.book_event(bid);last_event=time.monotonic()
                if j['cancel'].is_set():
                    p.terminate() if p.poll() is None else None
                    p.wait(); break
                if p.wait()!=0: raise ValueError('Không trích được tài liệu. Hãy kiểm tra EPUB/PDF/ảnh.')
                with self.lib.lock:
                    b=self.lib.load(bid); b['importedSources']=source+1; self.lib.save(b)
            if not j['cancel'].is_set():
                self.cancel_listening()
                with self.lib.lock:
                    b=self.lib.load(bid)
                    from pdf_layout import process_book
                    process_book(b,save=lambda:self.lib.save(b),progress=progress,cancel=j['cancel'].is_set)
            with self.lib.lock:
                b=self.lib.load(bid); b['status']='paused' if j['cancel'].is_set() else 'ready'; self.lib.save(b)
                if b['status']=='ready':
                    b.pop('refreshLayout',None)
                    b['processing']=dict(phase='ready',elapsedSeconds=round(time.monotonic()-started,1));self.lib.save(b)
                    progress(phase='ready',done=len(b['pages']),total=len(b['pages']))
        self.launch('import',bid,task)

    def generate(self,bid,start=0,all_segments=False,scope=None,cloud_consent=None):
        self.cancel_listening()
        model=self.lib.load(bid).get('model','nano')
        if model=='pro-cloud':raise ValueError('Mở Pro Cloud để tạo thử hoặc thanh toán đúng cuốn sách trước khi tạo.')
        require_local_model(model)
        if model=='clone-pro':require_pro_max()
        entitlements.require_model(model)
        if model=='clone-pro' and not isinstance(cloud_consent,dict):
            raise ValueError('Bấm Tạo sách nói và xác nhận gửi chữ, dùng credit Clone Pro 2.1 trước khi tạo.')
        if self.lib.load(bid).get('status')!='ready':raise ValueError('Chờ xử lý sách xong trước khi tạo giọng.')
        if 'cloud' in self.jobs:raise ValueError('Hãy chờ kết nối Clone Pro 2.1 hoàn tất.')
        def task(j):
            from audiobooks import create,find
            from cleanup import narratable
            with self.lib.lock:
                b=self.lib.load(bid); b['error']=''; self.lib.save(b)
                indices=selected_indices(b,scope) if scope else list(range(start,len(b['segments']) if all_segments else min(start+3,len(b['segments']))))
                indices=[i for i in indices if narratable(b['segments'][i]['text'])]
                segments=[b['segments'][i] for i in indices]
                if not segments:raise ValueError('Phạm vi đang chọn chưa có đoạn chữ.')
                if b.get('model')=='clone-pro':
                    expected=dict(voice=b['voice'],language=b.get('language','vi'),segments=[dict(id=s['id'],text=s['text']) for s in segments])
                    if cloud_consent!=expected:raise ValueError('Nội dung hoặc giọng đã đổi. Xác nhận lại phần sách cần tạo.')
                pending=[dict(id=s['id'],text=s['text'],path=str(self.lib.audio_path(b,s))) for s in segments if not valid_audio(self.lib.audio_path(b,s))]
                voice=b['voice']
                model_id=b.get('model','nano')
                require_local_model(model_id)
                entitlements.require_model(model_id)
                from chapters import sections
                title=next((c['title'] for c in sections(b) if (scope or {}).get('chapterId')==c['id']), 'Toàn bộ sách' if (scope or {}).get('type')=='all' else 'Phần đã chọn')
                take=create(b,indices,title,scope);take_id=take['id'];j['takeId']=take_id;self.lib.save(b)
            completed=len(segments)-len(pending)
            emit(event='progress',kind='audio',bookId=bid,done=completed,total=len(segments),phase='preparing' if pending else 'complete',title=title)
            self.book_event(bid)
            if not pending:
                with self.lib.lock:
                    b=self.lib.load(bid);find(b,take_id)['status']='ready';self.lib.save(b)
                return
            model_path='' if model_id=='clone-pro' else str(models.verified_location(model_id))
            request=dict(models=model_path,model=model_id,voice=voice,segments=pending,language=b.get('language','vi'),cloudConfirmed=model_id=='clone-pro',bilingual=b.get('bilingual',False),englishVoice=b.get('englishVoice','Jasper'))
            log=self.lib.directory(bid)/'engine.log'
            done=0
            for result in self.engine_results(request,j,log):
                if 'error' in result:raise ValueError(result['error'])
                if 'loadedSeconds' in result:
                    emit(event='progress',kind='audio',bookId=bid,done=completed,total=len(segments),phase='generating',title=title)
                if 'processingSegment' in result:
                    current=next((s for s in segments if s['id']==result['processingSegment']),None)
                    if current:emit(event='progress',kind='audio',bookId=bid,done=completed+done,total=len(segments),phase='generating',title=title,page=current['page'],index=next(i for i,s in enumerate(b['segments']) if s['id']==current['id']))
                if 'segment' in result:
                    done+=1
                    with self.lib.lock:
                        b=self.lib.load(bid);find(b,take_id)['completed']=done;self.lib.save(b)
                    self.book_event(bid)
                    emit(event='progress',kind='audio',bookId=bid,done=completed+done,total=len(segments),phase='generating',title=title)
            with self.lib.lock:
                b=self.lib.load(bid);find(b,take_id)['status']='cancelled' if j['cancel'].is_set() else 'ready';self.lib.save(b)
        self.launch('audio',bid,task)

    def preview_voice(self,r):
        model=r.get('model','')
        if not r.get('voice'):
            if model=='pro-cloud':raise ValueError('Bấm Tạo thử từ Cloud để nghe đoạn đầu sách, tối đa 5 lượt, mỗi lượt 5.000 ký tự.')
            require_local_model(model)
            if model=='clone-pro':raise ValueError('Chọn một đoạn sách và bấm Tạo sách nói để nghe giọng Clone Pro 2.1 bằng credit.')
            entitlements.require_model(model)
            raise ValueError('Chưa chọn giọng đọc.')
        voice=r['voice']
        token=str(r.get('token',''))
        if not re.fullmatch('[a-f0-9]{32}',token):raise ValueError('Mã nghe thử không hợp lệ.')
        from voice_previews import request
        text,path=request(model,voice,r.get('language','vi'))
        if valid_audio(path):emit(event='voiceDemo',token=token,path=str(path),voice=voice,model=model);return
        if model=='pro-cloud':raise ValueError('Bấm Tạo thử từ Cloud để nghe đoạn đầu sách, tối đa 5 lượt, mỗi lượt 5.000 ký tự.')
        require_local_model(model)
        if model=='clone-pro':raise ValueError('Chọn một đoạn sách và bấm Tạo sách nói để nghe giọng Clone Pro 2.1 bằng credit.')
        entitlements.require_model(model)
        with self.jobs_lock:
            if 'preview' in self.jobs or 'audio' in self.jobs:raise ValueError('Hãy chờ hoặc hủy tạo audio trước khi nghe thử giọng.')
            j={'id':None,'cancel':threading.Event(),'process':None};self.jobs['preview']=j
        emit(event='previewJob',running=True,token=token)
        def task():
            try:
                path.parent.mkdir(parents=True,exist_ok=True)
                payload=dict(models=str(models.verified_location(model)),model=model,voice=voice,segments=[dict(id=token,text=text,path=str(path))])
                for result in self.engine_results(payload,j,path.parent/'engine.log'):
                    if 'error' in result:raise ValueError(result['error'])
                if j['cancel'].is_set():return
                if not valid_audio(path):raise ValueError('Chưa tạo được mẫu giọng đọc.')
                emit(event='voiceDemo',token=token,path=str(path),voice=voice,model=model)
            except Exception as error:
                if not j['cancel'].is_set():emit(event='error',message=str(error))
            finally:
                with self.jobs_lock:self.jobs.pop('preview',None)
                emit(event='previewJob',running=False,token=token)
        threading.Thread(target=task,daemon=True).start()

    def book_cloud_action(self,r):
        from book_cloud import create_order,sync_order
        bid=r['bookId'];token=r.get('token')
        with self.jobs_lock:
            if 'bookCloud' in self.jobs:raise ValueError('Đang cập nhật đơn sách. Hãy chờ một chút.')
            self.jobs['bookCloud']={'id':bid,'cancel':threading.Event(),'process':None}
        emit(event='bookCloudBusy',bookId=bid,token=token,running=True)
        def task():
            def progress(value):emit(event='bookCloudProgress',bookId=bid,token=token,**value)
            try:
                if r['action']=='bookCloudCheck':result=sync_order(self.lib,bid,r['orderId'],on_progress=progress)
                else:result=create_order(self.lib,bid,'combo' if r['action']=='bookCloudCombo' else 'trial' if r['action']=='bookCloudTrial' else 'book',r['requestKey'],r.get('consent'),r.get('chapterId'),r.get('trialUnits',1),on_progress=progress)
                self.book_event(bid)
                emit(event='bookCloudResult',bookId=bid,token=token,success=True,**result)
            except Exception as error:
                emit(event='bookCloudResult',bookId=bid,token=token,success=False,message=str(error))
            finally:
                with self.jobs_lock:self.jobs.pop('bookCloud',None)
                emit(event='bookCloudBusy',bookId=bid,token=token,running=False)
        threading.Thread(target=task,daemon=True).start()

    def launch_action(self,r):
        from launch_offer import refresh,quote
        with self.jobs_lock:
            if 'launch' in self.jobs:raise ValueError('Đang kiểm tra combo. Hãy chờ một chút.')
            self.jobs['launch']={'id':'','cancel':threading.Event(),'process':None}
        def task():
            try:
                result=quote(self.lib,r['requestKey']) if r['action']=='launchQuote' else refresh(self.lib)
                emit(event='launchResult',token=r.get('token'),success=True,**result)
            except Exception as error:emit(event='launchResult',token=r.get('token'),success=False,message=str(error))
            finally:
                with self.jobs_lock:self.jobs.pop('launch',None)
        threading.Thread(target=task,daemon=True).start()

    def mutable(self,bid):
        self.cancel_listening()
        with self.jobs_lock:
            if self.jobs.get('import',{}).get('id')==bid:raise ValueError('Chờ hoặc hủy xử lý sách trước khi sửa nội dung.')
            if any(j['id']==bid for kind,j in self.jobs.items() if kind in ('audio','export')):
                raise ValueError('Hãy hủy tạo/xuất audio trước khi sửa chữ hoặc đổi giọng.')

    def handle(self,r):
        action=r['action']; bid=r.get('bookId')
        if action=='init':
            emit(event='init',books=self.lib.summaries(),voices=models.voices(),ready=models.ready('nano'),libraryPath=str(self.lib.root),music=music_catalog(),lastDeleted=self.lib.last_deleted())
            self.model_event()
        elif action=='license':self.model_event()
        elif action=='importLicense':
            entitlements.install(r['path']);self.model_event()
            emit(event='licenseImported')
            if bid:self.book_event(bid)
        elif action=='installLicense':
            try:
                result=entitlements.install_envelope(r['license'],r.get('afterExpiresAt'))
                if result is None:
                    emit(event='licenseCheck',requestId=r.get('requestId'),state='pending');return
                self.model_event()
                emit(event='licenseImported',requestId=r.get('requestId'))
                if bid:self.book_event(bid)
            except (ValueError,KeyError,TypeError,OSError):
                emit(event='licenseCheck',requestId=r.get('requestId'),state='error',message='Chưa xác minh được Pro cho Mac này. App sẽ thử lại sau.')
        elif action in ('profileInfo','profileSave'):
            from user_profile import info as profile_info
            with self.lib.lock:details=profile_info(self.lib,r.get('name') if action=='profileSave' else None)
            emit(event='profileInfo',token=r.get('token'),**details)
        elif action=='bookCloudInfo':
            from book_cloud import local_info
            with self.lib.lock:info=local_info(self.lib.load(bid),self.lib.root,r.get('chapterId'),r.get('groupTrial') is True)
            emit(event='bookCloudInfo',bookId=bid,token=r.get('token'),**info)
        elif action=='bookCloudAvailability':
            def availability():
                from book_cloud import service_info
                try:details=service_info()
                except Exception:details=dict(configured=True,reachable=False,trialAvailable=False,purchaseAvailable=False,message='Chưa kiểm tra được dịch vụ Pro. Kiểm tra kết nối rồi mở lại cửa sổ này; các yêu cầu đã gửi vẫn được giữ.')
                emit(event='bookCloudAvailability',bookId=bid,token=r.get('token'),**details)
            threading.Thread(target=availability,daemon=True).start()
        elif action in ('bookCloudQuote','bookCloudTrial','bookCloudCheck','bookCloudCombo'):
            self.book_cloud_action(r)
        elif action in ('launchInfo','launchQuote','launchCheck'):self.launch_action(r)
        elif action=='models':self.model_event()
        elif action=='creditWallet':self.cloud_connection(refresh_voices=r.get('voices') is True)
        elif action=='creditPurchase':self.cloud_connection(r['packId'],r['key'])
        elif action=='downloadModel':self.download_model(r['model'])
        elif action=='voicePreview':self.preview_voice(r)
        elif action=='get': self.book_event(bid,r.get('requestId'))
        elif action=='bookCover':
            self.lib.directory(bid)
            with self.jobs_lock:self.reader_tasks[bid]=self.reader_tasks.get(bid,0)+1
            def read_cover():
                image=None
                try:
                    from covers import cover
                    with self.cover_lock:image=cover(self.lib,bid)
                except Exception as error:
                    print('Bìa sách: '+str(error),file=sys.stderr)
                finally:
                    emit(event='bookCover',bookId=bid,image=image)
                    with self.jobs_lock:self.reader_tasks[bid]-=1
            threading.Thread(target=read_cover,daemon=True).start()
        elif action=='importText':
            from reading_tools import import_text
            with self.lib.lock:b=import_text(self.lib,r.get('title',''),r.get('text'),r.get('language','vi'))
            self.book_event(b['id']);emit(event='textImported',bookId=b['id'])
        elif action in ('readingSearch','readingNotes','readingAnnotation'):
            def reading_tool():
                try:
                    from reading_tools import search,edition,read_notes,annotation
                    with self.lib.lock:
                        b=self.lib.load(bid)
                        if action=='readingSearch':data=dict(results=search(b,r.get('query','')))
                        else:data=dict(notes=annotation(self.lib,bid,r) if action=='readingAnnotation' else read_notes(self.lib,bid))
                    emit(event='readingTools',bookId=bid,token=r.get('token'),edition=edition(b),**data)
                except Exception as error:emit(event='error',bookId=bid,action=action,message=str(error))
            threading.Thread(target=reading_tool,daemon=True).start()
        elif action=='readerBook':
            # Derived ebook work stays off the input loop; cancel/close stays responsive.
            b=self.lib.load(bid)
            with self.jobs_lock:self.reader_tasks[bid]=self.reader_tasks.get(bid,0)+1
            def read_book():
                try:
                    from ebook_reader import prepare
                    data,_=prepare(self.lib,b,r.get('takeId'),include_images=False)
                    emit(event='readerBook',bookId=bid,token=r.get('token'),**data)
                except Exception as error:
                    emit(event='readerBookError',bookId=bid,token=r.get('token'),message=str(error))
                finally:
                    with self.jobs_lock:self.reader_tasks[bid]-=1
            threading.Thread(target=read_book,daemon=True).start()
        elif action=='exportEbook':
            from ebook_reader import prepare
            import shutil
            import tempfile
            b=self.lib.load(bid);path=Path(r['path'])
            if path.suffix.lower()!='.epub':raise ValueError('Chọn tên file .epub.')
            _,source=prepare(self.lib,b,r.get('takeId'),include_images=False)
            if path.resolve().is_relative_to(self.lib.root.resolve()):raise ValueError('Lưu bản EPUB bên ngoài thư viện nội bộ.')
            fd,temp=tempfile.mkstemp(prefix='.ebook-',dir=path.parent);os.close(fd)
            try:shutil.copyfile(source,temp);os.replace(temp,path)
            finally:Path(temp).unlink(missing_ok=True)
            emit(event='ebookExported',bookId=bid,path=str(path))
        elif action=='readerImage':
            try:
                from ebook_reader import image
                data=image(self.lib,bid,r.get('contentKey'),r.get('file'))
                emit(event='readerImage',bookId=bid,contentKey=r.get('contentKey'),file=r.get('file'),image=data)
            except (OSError,ValueError):emit(event='readerImageError',bookId=bid,contentKey=r.get('contentKey'),file=r.get('file'))
        elif action=='readerPage':
            from reading import page_data
            try:
                # Atomic book snapshots make reading safe while extraction is
                # checkpointing. Never block cancel input on a long layout lock.
                data=page_data(self.lib.load(bid),r.get('page'),r.get('takeId'))
                emit(event='readerPage',bookId=bid,token=r.get('token'),**data)
            except (ValueError,OSError,KeyError) as error:emit(event='readerPageError',bookId=bid,token=r.get('token'),message=str(error))
        elif action=='readerSettings':
            from core import atomic_json
            b=self.lib.load(bid);state=r.get('reader',{})
            if not isinstance(state,dict):raise ValueError('Thiết lập đọc sách không hợp lệ.')
            saved=b.setdefault('reader',{})
            if state.get('mode') in ('create','read'):saved['mode']=state['mode']
            if state.get('variant') in ('original','text'):saved['variant']=state['variant']
            if type(state.get('page')) is int and 0<=state['page']<len(b['pages']):saved['page']=state['page']
            if type(state.get('fontSize')) is int:saved['fontSize']=min(34,max(14,state['fontSize']))
            if isinstance(state.get('fontFamily'),str) and len(state['fontFamily'])<=50:saved['fontFamily']=state['fontFamily']
            if type(state.get('follow')) is bool:saved['follow']=state['follow']
            if state.get('ebookVersion')==1:saved['ebookVersion']=1
            if state.get('voice') in {v['id'] for v in models.voices('nano')}:saved['voice']=state['voice']
            if type(state.get('seconds')) in (int,float) and 0<=state['seconds']<36000:saved['seconds']=state['seconds']
            if isinstance(state.get('anchor'),str) and len(state['anchor'])<=100:saved['anchor']=state['anchor']
            atomic_json(self.lib.directory(bid)/'reader.json',saved)
        elif action=='deleteBook':
            with self.jobs_lock:
                if self.reader_tasks.get(bid,0):raise ValueError('Đang chuẩn bị ebook. Thử xóa lại sau một chút.')
                if any(j.get('id')==bid for j in self.jobs.values()):raise ValueError('Hủy hoặc chờ xử lý/tạo/xuất sách xong trước khi xóa.')
                if self.listening and self.listening.get('id')==bid:
                    self.listening['cancel'].set()
                    p=self.listening.get('process')
                    if p and p.poll() is None:p.terminate()
                with self.lib.lock:token=self.lib.trash(bid)
            emit(event='bookDeleted',bookId=bid,undoToken=token,books=self.lib.summaries(),lastDeleted=self.lib.last_deleted())
        elif action=='restoreBook':
            with self.lib.lock:restored=self.lib.restore(r.get('undoToken'))
            emit(event='bookRestored',bookId=restored,books=self.lib.summaries(),lastDeleted=self.lib.last_deleted())
        elif action=='import':
            sources=r['paths']
            if not sources or len(sources)>2000: raise ValueError('Chọn từ 1 đến 2.000 ảnh hoặc một EPUB/PDF.')
            if any(Path(p).suffix.lower() not in ('.epub','.pdf','.jpg','.jpeg','.png','.heic','.tiff','.tif','.webp') for p in sources): raise ValueError('Chọn EPUB, PDF hoặc ảnh PNG/JPEG/HEIC/TIFF/WebP.')
            if len(sources)>1 and any(Path(p).suffix.lower() in ('.pdf','.epub') for p in sources): raise ValueError('Mỗi lần chọn một EPUB/PDF hoặc nhiều ảnh.')
            if any(Path(p).is_dir() and Path(p).suffix.lower()!='.epub' for p in sources):raise ValueError('Chỉ chọn thư mục sách có đuôi .epub.')
            sources=sorted(sources,key=lambda s:[int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',Path(s).name)])
            with self.jobs_lock:
                if 'import' in self.jobs: raise ValueError('Hãy chờ hoặc hủy lần nhập hiện tại.')
                b=self.lib.create(sources,r.get('language','vi'))
            self.book_event(b['id']); self.extract(b['id'],r.get('forceOCR',False))
        elif action=='resume':
            b=self.lib.load(bid)
            if b['status']=='ready': return
            self.extract(bid,b.get('forceOCR',False))
        elif action=='processPDF':
            self.mutable(bid);self.cancel_listening()
            with self.lib.lock:
                b=self.lib.load(bid)
                if b.get('format')=='epub' or any(Path(s['file']).suffix!='.pdf' for s in b['sources']):raise ValueError('Chỉ sắp xếp lại bố cục PDF.')
                if b.get('sourceSegments') or any(s['text']!=s.get('originalText',s['text']) for s in b['segments']):raise ValueError('Cuốn này đã được sửa. Nhập PDF thành bản mới để giữ nguyên phần bạn đã chỉnh.')
                from audiobooks import archive_existing
                archive_existing(self.lib,b);self.lib.save(b)
            self.extract(bid,refresh_layout=True)
        elif action=='readerListen':
            from reader_listening import prepare
            prepare(self,bid,r.get('voice'),r.get('cueId'),r.get('token'),emit)
        elif action=='prepareListening':self.prepare_listening(bid,max(0,int(r.get('start',0))),r.get('scope'),r.get('seconds',60),r.get('token',''))
        elif action=='cancelListening':self.cancel_listening()
        elif action=='generate': self.generate(bid,max(0,int(r.get('start',0))),r.get('all',False),r.get('scope'),r.get('cloudConsent'))
        elif action=='cancel': self.cancel(r['kind'])
        elif action=='edit':
            self.mutable(bid)
            with self.lib.lock:
                b=self.lib.load(bid); index=int(r['index']); text=r['text']
                if not text.strip() or len(text)>2000: raise ValueError('Mỗi đoạn cần từ 1 đến 2.000 ký tự. Chia đoạn dài hơn trước khi nhập.')
                b['segments'][index]['text']=text; b['finished']=False
                if index==b['position']['segment']: b['position']['seconds']=0
                self.lib.save(b)
            self.book_event(bid)
        elif action=='cleanChapter':
            from chapters import preview_cleanup
            with self.lib.lock:
                result=preview_cleanup(self.lib.load(bid),r['chapterId'],r['text'],r.get('options'))
            emit(event='cleanup',bookId=bid,chapterId=r['chapterId'],token=r.get('token'),**result)
        elif action=='editChapter':
            self.mutable(bid)
            from chapters import edit_chapter
            with self.lib.lock:
                b=self.lib.load(bid);edit_chapter(b,r['chapterId'],r['text'],r.get('expected'));self.lib.save(b)
            self.book_event(bid)
            emit(event='chapterSaved',bookId=bid,chapterId=r['chapterId'],token=r.get('token'))
        elif action=='settings':
            if any(k in r for k in ('voice','model','language','bilingual')):self.mutable(bid)
            if 'music' in r and self.jobs.get('export',{}).get('id')==bid:raise ValueError('Hãy chờ hoặc hủy xuất file trước khi đổi nhạc.')
            with self.lib.lock:
                b=self.lib.load(bid)
                if 'language' in r:
                    language=r['language']
                    if language not in ('vi','en'):raise ValueError('Ngôn ngữ sách không hợp lệ.')
                    if b['status']!='ready':raise ValueError('Hãy trích chữ xong trước khi đổi ngôn ngữ sách.')
                    b['language']=language
                    if language not in models.profile(b.get('model','nano'))['languages']:
                        b['model']='kitten' if language=='en' else 'nano';b['voice']=models.resolve_voice(b['model'],'')
                        b['position']['seconds']=0;b['finished']=False
                if 'model' in r:
                    model_id=r['model'];models.profile(model_id)
                    require_local_model(model_id)
                    if model_id=='clone-pro':require_pro_max()
                    entitlements.require_model(model_id)
                    if not models.ready(model_id):raise ValueError('Tải gói giọng này trước khi sử dụng.')
                    if not next(m for m in models.catalog()['models'] if m['id']==model_id)['supported']:raise ValueError('Mac này chưa đáp ứng yêu cầu của gói giọng.')
                    b['model']=model_id;b['voice']=models.resolve_voice(model_id,b['voice'])
                    if b.get('language','vi') not in models.profile(model_id)['languages']:b['language']=models.profile(model_id)['languages'][0]
                    b['position']['seconds']=0;b['finished']=False
                if 'voice' in r:
                    if b.get('model')=='clone-pro':require_pro_max()
                    entitlements.require_model(b.get('model','nano'))
                    if r['voice'] not in [v['id'] for v in models.voices(b.get('model','nano'))]:raise ValueError('Giọng này không có trong model đang chọn.')
                    b['voice']=r['voice']; b['position']['seconds']=0; b['finished']=False
                if 'bilingual' in r:
                    if type(r['bilingual']) is not bool:raise ValueError('Thiết lập Việt–Anh không hợp lệ.')
                    if r['bilingual'] and not models.ready('kitten'):raise ValueError('Tải Kitten trong Quản lý giọng trước khi bật Việt–Anh.')
                    b['bilingual']=r['bilingual'];b['position']['seconds']=0;b['finished']=False
                if 'speed' in r: b['speed']=min(2,max(.5,float(r['speed'])))
                if 'music' in r:b['music']=music_settings(r['music'])
                if 'scope' in r:
                    selected_indices(b,r['scope']);b['generationScope']=r['scope']
                self.lib.save(b)
            self.book_event(bid)
        elif action=='chapter':
            self.mutable(bid)
            with self.lib.lock:
                b=self.lib.load(bid)
                if r.get('remove'):
                    remove_chapter(b,r['remove'])
                    if b.get('generationScope',{}).get('chapterId')==r['remove']:b['generationScope']={'type':'all'}
                else:
                    chapter=mark_chapter(b,int(r['page'])-1,r['title']);b['generationScope']={'type':'chapter','chapterId':chapter['id']}
                self.lib.save(b)
            self.book_event(bid)
        elif action=='position': self.lib.position(bid,int(r['segment']),float(r['seconds']),r.get('finished',False))
        elif action=='export':
            self.mutable(bid)
            def task(j):
                def progress(done,total):
                    emit(event='progress',kind='export',bookId=bid,done=done,total=total)
                def process(p):
                    j['process']=p
                    if j['cancel'].is_set() and p.poll() is None:p.terminate()
                path=self.lib.export(bid,r['path'],r.get('scope'),take_id=r.get('takeId'),progress=progress,cancelled=j['cancel'].is_set,process=process)
                with self.lib.lock:
                    b=self.lib.load(bid)
                    if r.get('takeId'):
                        from audiobooks import find
                        take=find(b,r['takeId']);take.setdefault('exports',[]).append(dict(path=path,music=music_settings(b.get('music'))))
                        self.lib.save(b)
                emit(event='exported',path=path,bookId=bid,takeId=r.get('takeId'))
            self.launch('export',bid,task)
        elif action=='shutdown':
            self.cancel_listening()
            for kind in list(self.jobs): self.cancel(kind)
            self.nano.close()
        else: raise ValueError('Thao tác không hợp lệ.')

if __name__=='__main__':
    w=Worker()
    for line in sys.stdin:
        request={}
        try:
            request=json.loads(line)
            with contextlib.redirect_stdout(sys.stderr): w.handle(request)
        except Exception as e: emit(event='error',message=str(e),bookId=request.get('bookId') if isinstance(request,dict) else None,action=request.get('action') if isinstance(request,dict) else None)
    w.cancel_listening()
    for kind in list(w.jobs): w.cancel(kind)
    w.nano.close()
