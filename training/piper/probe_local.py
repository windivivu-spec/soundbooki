"""Run an isolated donor voice offline. This is not the user's trained voice."""
import json
import os
from pathlib import Path
import resource
import socket
import time
import wave

os.environ.update(ORT_DISABLE_TELEMETRY='1', HF_HUB_OFFLINE='1', DO_NOT_TRACK='1')


def deny(*args, **kwargs):
    raise OSError('Network disabled during local voice probe.')


socket.create_connection = deny
socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.getaddrinfo = deny

import onnxruntime as ort
ort.disable_telemetry_events()
from piper import PiperVoice

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'.qa/piper-probe'
MODEL = QA/'model/vi_VN-vais1000-medium.onnx'
OUT = QA/'sample-vietnamese.wav'
text = ('Buổi sáng, nắng nhẹ đi qua ô cửa nhỏ. Tôi mở cuốn sách và bắt đầu đọc. '
        '“Bạn có nghe thấy tiếng mưa không?” cô khẽ hỏi. '
        'Một giọng kể dễ chịu cần rõ từng chữ, giữ nhịp tự nhiên và không làm người nghe mệt mỏi.')
start = time.monotonic()
voice = PiperVoice.load(MODEL)
load = time.monotonic()-start
start = time.monotonic()
temp = OUT.with_suffix('.partial.wav')
with wave.open(str(temp),'wb') as wav:
    voice.synthesize_wav(text,wav)
seconds = time.monotonic()-start
with wave.open(str(temp),'rb') as wav:
    duration = wav.getnframes()/wav.getframerate()
    rate = wav.getframerate()
    assert wav.getnframes()>0 and wav.getsampwidth()==2 and wav.getnchannels()==1
temp.replace(OUT)
proof = dict(model='VAIS1000 medium donor; not user-trained',modelBytes=MODEL.stat().st_size,
             sampleRate=rate,durationSeconds=duration,loadSeconds=load,
             synthesisSeconds=seconds,realTimeFactor=seconds/duration,
             processPeakMemoryBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             networkBlocked=True,text=text,audio=str(OUT))
(QA/'local-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
print(json.dumps(proof,ensure_ascii=False,indent=2))
