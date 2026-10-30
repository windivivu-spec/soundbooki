"""Short self-written local voice demos, cached by exact engine revision."""
from pathlib import Path
from core import signature
import model_manager as models

ROOT=Path(__file__).resolve().parents[1]
VI='Chào bạn. Hãy dành một chút thời gian, lắng nghe và khám phá thế giới qua từng trang sách.'
EN='Welcome. Take a moment to listen, and discover a new world through every page.'

def request(model,voice,language='vi'):
    if voice not in [v['id'] for v in models.voices(model)]:raise ValueError('Giọng đọc không hợp lệ.')
    language=language if language in models.profile(model)['languages'] else models.profile(model)['languages'][0]
    text=EN if language=='en' else VI
    from entitlements import release, data_root
    folder=data_root()/'voice-previews' if release().get('channel')=='consumer' else ROOT/'assets/voice-previews'
    # Owner-supplied recordings are stable demos, independent of synthesis revisions.
    if model=='pro-cloud':
        import unicodedata
        label=next(v['label'].split(' · ',1)[0] for v in models.voices(model) if v['id']==voice)
        for candidate in (folder/model).glob('*.wav'):
            if unicodedata.normalize('NFC',candidate.stem)==unicodedata.normalize('NFC',label):
                return text,candidate
    target=folder/model/(signature(text,voice,model)+'.wav')
    return text,target
