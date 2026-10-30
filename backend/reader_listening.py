"""On-device Lite sentence streaming, independent of production voice/scope."""
import threading
import wave
import model_manager as models
from core import valid_audio
from cleanup import narratable
from ebook_reader import assemble,content_key
from reading import page_data

def prepare(worker,bid,voice,cue_id,token,emit):
    if voice not in {v['id'] for v in models.voices('nano')}:raise ValueError('Chọn một giọng Lite có sẵn.')
    if not models.ready('nano'):raise ValueError('Lite chưa sẵn sàng. Tải gói giọng local trước khi đọc.')
    book=worker.lib.load(bid)
    if book['status']!='ready':raise ValueError('Chờ xử lý sách xong để nghe.')
    # Sentence input starts exactly at the chosen cue, never seeks by an estimate.
    cues=[c for c in assemble(book)['sentences'] if narratable(c['text'])]
    start=next((i for i,c in enumerate(cues) if c['id']==cue_id),None)
    if start is None:raise ValueError('Câu không còn trong nội dung sách. Mở lại trang đọc.')
    snapshot=content_key(book);worker.cancel_listening()
    job=dict(id=bid,cancel=threading.Event(),process=None,token=token,reader=True)
    with worker.jobs_lock:worker.listening=job
    local=dict(book,model='nano',voice=voice)
    def run():
        try:
            model_path=str(models.verified_location('nano'));buffered=0
            for at,cue in enumerate(cues[start:start+16]):
                if job['cancel'].is_set():return
                with worker.jobs_lock:
                    if 'audio' in worker.jobs or 'preview' in worker.jobs:raise ValueError('Đợi hoặc hủy lần tạo giọng đang chạy để nghe Lite.')
                path=worker.lib.audio_path(local,cue)
                if not valid_audio(path):
                    request=dict(model='nano',models=model_path,revision=models.revision('nano'),voice=voice,
                                 segments=[dict(id=cue['id'],text=cue['text'],path=str(path))])
                    request.update(bilingual=book.get('bilingual',False),englishVoice=book.get('englishVoice','Jasper'))
                    for _ in worker.engine_results(request,job,worker.lib.directory(bid)/'engine.log'):pass
                if job['cancel'].is_set():return
                if content_key(worker.lib.load(bid))!=snapshot:return
                if not valid_audio(path):raise ValueError('Lite chưa tạo xong câu này. Bấm Play để thử lại.')
                with wave.open(str(path),'rb') as wav:duration=wav.getnframes()/wav.getframerate()
                buffered+=duration
                emit(event='readerAudioReady',bookId=bid,token=token,voice=voice,cueId=cue['id'],text=cue['text'],path=str(path),duration=duration)
                if at>=3 and buffered>=65:break
            if not job['cancel'].is_set():emit(event='readerBuffer',bookId=bid,token=token,state='ready')
        except Exception as error:
            if not job['cancel'].is_set():emit(event='readerBuffer',bookId=bid,token=token,state='error',message=str(error))
        finally:
            with worker.jobs_lock:
                if worker.listening is job:worker.listening=None
    threading.Thread(target=run,daemon=True).start()
