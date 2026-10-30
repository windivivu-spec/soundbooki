"""One cancellable local TTS job. stdout is JSON-lines only."""
import contextlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from core import atomic_json, signature, valid_audio


def offline_guard():
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                      DO_NOT_TRACK='1', ORT_DISABLE_TELEMETRY='1', GRADIO_ANALYTICS_ENABLED='False')
    def deny(*args, **kwargs): raise OSError('Windi Sách Nói: kết nối mạng bị tắt khi đọc sách.')
    socket.socket.connect=deny
    socket.socket.connect_ex=deny
    socket.create_connection=deny
    socket.getaddrinfo=deny


def emit(value):
    sys.__stdout__.write(json.dumps(value,ensure_ascii=False)+'\n'); sys.__stdout__.flush()


def main(request, cached=None):
    offline_guard()
    with contextlib.redirect_stdout(sys.stderr):
        import numpy as np
        import soundfile as sf
        from model_manager import profile
        start=time.monotonic()
        model_id=request.get('model','nano');rate=profile(model_id)['sampleRate']
        if cached is not None:
            model=cached
        elif model_id=='f5-private':
            from f5_engine import F5Engine
            model=F5Engine(request['models'])
        elif model_id=='kitten':
            from kitten_engine import KittenEngine
            model=KittenEngine(request['models'])
        elif model_id=='turbo':
            from vieneu import Vieneu
            # SDK 3.8.1 does not forward codec_dir through Vieneu. Supply the
            # local codec at its ONNX constructor boundary; never patch the SDK on disk.
            from vieneu._v3_turbo_engine import onnx_runtime_lite
            original=onnx_runtime_lite.OnnxV3LiteEngine
            class LocalCodecEngine(original):
                def __init__(self,**kwargs):
                    super().__init__(codec_dir=str(Path(request['models'])/'codec'),**kwargs)
            onnx_runtime_lite.OnnxV3LiteEngine=LocalCodecEngine
            try:
                model=Vieneu(mode='v3turbo',backend='onnx',device='cpu',precision='fp32',backbone_repo=str(Path(request['models'])/'onnx'),onnx_dir=str(Path(request['models'])/'onnx'),threads=4)
            finally:onnx_runtime_lite.OnnxV3LiteEngine=original
        else:
            from vieneu import Vieneu
            model=Vieneu(mode='v3nano', onnx_dir=request['models'], threads=4)
        load=time.monotonic()-start
        voices={v for _,v in model.list_preset_voices()}
        if request['voice'] not in voices: raise ValueError('Chọn lại giọng trong danh sách.')
        emit({'loadedSeconds':load, **({'device':model.device} if model_id=='f5-private' else {})})
        for s in request['segments']:
            emit({'processingSegment':s['id']})
            target=Path(s['path']); start=time.monotonic()
            if not valid_audio(target):
                options=dict(steps=16,seed=42) if model_id=='nano' else dict(temperature=.8,batch_size=1)
                audio=np.asarray(model.infer(s['text'], voice=request['voice'],**options)).reshape(-1)
                if not audio.size or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 0.0001:
                    raise ValueError('Đoạn này chưa tạo được tiếng hợp lệ. Hãy kiểm tra chữ rồi thử lại.')
                temp=target.with_suffix('.partial.wav')
                sf.write(temp,audio,rate,subtype='PCM_16')
                if not valid_audio(temp): raise ValueError('Audio không hợp lệ.')
                temp.replace(target)
            info=sf.info(target)
            meta=dict(segment=s['id'], path=str(target), duration=info.duration,
                      computeSeconds=time.monotonic()-start, model=model_id,sampleRate=rate,signature=signature(s['text'],request['voice'],model_id))
            if model_id=='f5-private':meta.update(device=model.device,precision=getattr(model,'precision','fp16'),nfe=getattr(model,'nfe',24))
            atomic_json(target.with_suffix('.json'),meta)
            emit(meta)
        return model

def serve_nano():
    # One process/model for local listening and explicit Nano generation.
    cached=None
    for line in sys.stdin:
        try:
            request=json.loads(line)
            if request.get('model','nano')!='nano':raise ValueError('Bộ đọc giữ ấm chỉ nhận Nano.')
            cached=main(request,cached)
            emit({'requestDone':True})
        except Exception as error:
            emit({'error':str(error)})
            emit({'requestDone':True})

if __name__=='__main__':
    if '--serve-nano' in sys.argv:serve_nano()
    else:
        try: main(json.load(sys.stdin))
        except Exception as e:
            emit({'error':str(e)}); sys.exit(1)
