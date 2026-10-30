"""Isolated training tools. Never imported by the audiobook runtime."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave
from array import array

PROFILE = dict(id='capcut-clean-narration-v1', sampleRate=22050,
               trimSilence=False, learningRate=3e-5, pilotSteps=300,
               effects=[], preserveOriginal=True, target='speaker-and-reading-style')


def word_groups(segments, max_seconds=18):
    """Keep all ASR words in order; prefer punctuation and natural pause boundaries."""
    pending = []
    for segment in segments:
        for word in segment.words or []:
            if pending and word.start - pending[-1].end > .65:
                yield pending
                pending = []
            if pending and word.end - pending[0].start > max_seconds:
                # Prefer a completed clause to cutting inside the next phrase.
                cuts = [i+1 for i,w in enumerate(pending)
                        if w.word.rstrip().endswith((',', ';', ':', '.', '?', '!', '…'))
                        and w.end-pending[0].start >= 3]
                cut = cuts[-1] if cuts else len(pending)
                yield pending[:cut]
                pending = pending[cut:]
                if pending and word.end-pending[0].start > max_seconds:
                    yield pending
                    pending = []
            pending.append(word)
            if word.word.rstrip().endswith(('.', '?', '!', '…')) and word.end-pending[0].start >= 2:
                yield pending
                pending = []
    if pending:
        yield pending


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.partial')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Đường dẫn vượt ngoài thư mục dữ liệu.')
    return path


def audio_info(path):
    with wave.open(str(path), 'rb') as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2 or f.getframerate() != 22050:
            raise ValueError('Clip phải là WAV PCM16 mono 22050 Hz.')
        duration = f.getnframes() / f.getframerate()
        samples = array('h', f.readframes(f.getnframes()))
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples:
        raise ValueError('Clip rỗng.')
    rms = math.sqrt(sum(x*x for x in samples) / len(samples)) / 32768
    clipped = sum(abs(x) >= 32760 for x in samples) / len(samples)
    return dict(duration=duration, rms=rms, clippedFraction=clipped)


def prepare(source, root, model='small', device='cpu'):
    """ASR runs where this script runs. No upload/API and no automatic approval."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = Path(source).resolve()
    source_sha = digest(source)
    manifest_path = root / 'review.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if previous['sourceSha256'] != source_sha:
            raise ValueError('Thư mục đã chứa một bản thu khác. Chọn thư mục mới.')
        if previous.get('status') == 'awaiting_review':
            print('Đã tách xong; giữ nguyên các sửa lời và lựa chọn duyệt.')
            return
    originals = root / 'originals'
    originals.mkdir(exist_ok=True)
    original = originals / ('recording' + source.suffix.lower())
    if not original.exists():
        partial_original = original.with_name(original.name + '.partial')
        shutil.copy2(source, partial_original)
        if digest(partial_original) != source_sha:
            raise ValueError('Bản sao file gốc chưa hoàn tất.')
        partial_original.replace(original)
    if digest(original) != source_sha:
        raise ValueError('Bản gốc không khớp checksum.')
    normalized = root / 'recording-22050.wav'
    if not normalized.exists():
        partial = root / 'recording-22050.partial.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(original),
                        '-vn', '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', str(partial)], check=True)
        partial.replace(normalized)
    from faster_whisper import WhisperModel
    engine = WhisperModel(model, device=device, compute_type='int8' if device == 'cpu' else 'float16')
    segments, _ = engine.transcribe(str(normalized), language='vi', beam_size=5,
                                    vad_filter=True, word_timestamps=True,
                                    condition_on_previous_text=False)
    # Commit after every completed clip. Resume deterministically without erasing edits.
    record = json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(
        schema=1, sourceSha256=source_sha, originalFile=str(original.relative_to(root)),
        status='preparing', profile=PROFILE, segments=[])
    known = {s['id']: s for s in record['segments']}
    clips = root / 'clips'
    clips.mkdir(exist_ok=True)
    def flush(words):
        if not words:
            return
        start = max(0, words[0].start - .08)
        end = words[-1].end + .12
        text = ''.join(w.word for w in words)
        sid = f'{round(start*1000):09d}-{round(end*1000):09d}'
        if sid in known:
            return
        path = clips / (sid + '.wav')
        if not path.exists():
            partial = path.with_suffix('.partial.wav')
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', str(start),
                            '-i', str(normalized), '-t', str(end-start), '-ac', '1',
                            '-ar', '22050', '-c:a', 'pcm_s16le', str(partial)], check=True)
            partial.replace(path)
        info = audio_info(path)
        flags = []
        if not 2 <= info['duration'] <= 20:
            flags.append('duration')
        if info['rms'] < .003:
            flags.append('quiet')
        if info['clippedFraction'] > .01:
            flags.append('clipping')
        if any(getattr(w, 'probability', 1) < .5 for w in words):
            flags.append('uncertain_transcript')
        if not text.rstrip().endswith(('.', '?', '!', '…', ',', ';', ':')):
            flags.append('check_phrase_boundary')
        item = dict(id=sid, audio=str(path.relative_to(root)), start=start, end=end,
                    originalText=text, text=text, approved=False, flags=flags, **info)
        record['segments'].append(item)
        known[sid] = item
        atomic_json(manifest_path, record)
        if len(record['segments']) % 25 == 0:
            print(f"PREPARE clips={len(record['segments'])} position={end:.1f}s", flush=True)

    for words in word_groups(segments):
        flush(words)
    record['status'] = 'awaiting_review'
    atomic_json(manifest_path, record)
    print(f"Đã tách {len(record['segments'])} clip. Nghe, sửa lời và duyệt trước khi train.")


def make_dataset(root, minimum=30):
    root = Path(root).resolve()
    record = json.loads((root / 'review.json').read_text())
    if record.get('status') != 'awaiting_review':
        raise ValueError('Tách audio chưa hoàn tất.')
    items = [s for s in record['segments'] if s.get('approved') is True]
    if len(items) < minimum:
        raise ValueError(f'Cần tối thiểu {minimum} clip đã nghe và duyệt.')
    seen = set()
    unique = []
    for s in sorted(items, key=lambda x: x['start']):
        if not s['text'].strip() or any(c in s['text'] for c in '\r\n\0'):
            raise ValueError('Lời đọc trống hoặc có ký tự xuống dòng/NUL.')
        info = audio_info(safe_path(root, s['audio']))
        if not 2 <= info['duration'] <= 20 or info['rms'] < .003 or info['clippedFraction'] > .01:
            raise ValueError(f"Clip {s['id']} chưa đạt kiểm tra audio.")
        s = dict(s, **info)
        key = s['text'].strip().casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    if len(unique) < minimum:
        raise ValueError('Không đủ câu khác nhau sau loại trùng.')
    # Last 10% in time forms an untouched listening holdout. Never train on it.
    count = max(3, math.ceil(len(unique) * .1))
    train, holdout = unique[:-count], unique[-count:]
    dataset = root / 'dataset'
    (dataset / 'audio').mkdir(parents=True, exist_ok=True)
    rows = []
    for s in train:
        filename = s['id'] + '.wav'
        shutil.copy2(safe_path(root, s['audio']), dataset / 'audio' / filename)
        rows.append((filename, s['text']))
    temp = dataset / 'metadata.csv.partial'
    with temp.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='|')
        writer.writerows(rows)
    temp.replace(dataset / 'metadata.csv')
    atomic_json(dataset / 'holdout.json', holdout)
    report = dict(trainClips=len(train), holdoutClips=len(holdout),
                  trainMinutes=sum(s['duration'] for s in train)/60,
                  sourceSha256=record['sourceSha256'], reviewedManifestSha256=digest(root/'review.json'),
                  metadataSha256=digest(dataset/'metadata.csv'), profile=PROFILE,
                  audioSha256={name:digest(dataset/'audio'/name) for name,_ in rows})
    atomic_json(dataset / 'report.json', report)
    print(json.dumps({k:v for k,v in report.items() if k != 'audioSha256'}, ensure_ascii=False, indent=2))
    return report


def review_ui(root):
    import ipywidgets as w
    from IPython.display import Audio, display, clear_output
    root = Path(root)
    path = root/'review.json'
    data = json.loads(path.read_text())
    if data.get('status') != 'awaiting_review' or not data['segments']:
        raise ValueError('Chưa có clip sẵn sàng để duyệt.')
    idx = w.BoundedIntText(value=0, min=0, max=len(data['segments'])-1, description='Đoạn:')
    text = w.Textarea(layout=w.Layout(width='95%', height='100px'))
    approved = w.Checkbox(description='Đã nghe, lời khớp và chỉ một người nói')
    save = w.Button(description='Lưu và tiếp tục', button_style='success')
    out = w.Output()
    def show(*_):
        s = data['segments'][idx.value]
        text.value = s['text']
        approved.value = s['approved']
        with out:
            clear_output(wait=True)
            print(f"{idx.value+1}/{len(data['segments'])} | {s['duration']:.1f}s | Cờ: {s['flags']}")
            print('Bản chép gốc:', s['originalText'])
            display(Audio(filename=str(safe_path(root, s['audio']))))
    def commit(_):
        s = data['segments'][idx.value]
        s['text'], s['approved'] = text.value, approved.value
        atomic_json(path, data)
        if idx.value < idx.max:
            idx.value += 1
    idx.observe(show, names='value')
    save.on_click(commit)
    display(idx, out, text, approved, save)
    show()


def train(root, base_checkpoint, output, max_steps=300, resume=None):
    """Fresh fine-tune uses warmstart, never resumes epoch 4769 from base."""
    import torch
    from lightning.pytorch import Trainer, seed_everything
    from lightning.pytorch.callbacks import ModelCheckpoint
    from piper.train.vits.dataset import VitsDataModule
    from piper.train.vits.lightning import VitsModel
    if not torch.cuda.is_available():
        raise ValueError('Chưa có GPU CUDA; không bắt đầu train.')
    root, output = Path(root), Path(output)
    if digest(base_checkpoint) != 'c3879268594a85b5133146e6a4709a5cc2f3014ef0eabf9280f67289054ba2bc':
        raise ValueError('Checkpoint nền chưa đúng checksum đã khóa.')
    report = json.loads((root/'dataset/report.json').read_text())
    if report['metadataSha256'] != digest(root/'dataset/metadata.csv'):
        raise ValueError('Dataset đã thay đổi. Tạo lại dataset trước khi train.')
    if report['reviewedManifestSha256'] != digest(root/'review.json'):
        raise ValueError('Lời hoặc trạng thái duyệt đã đổi. Chốt lại dataset trước khi train.')
    if report.get('profile') != PROFILE:
        raise ValueError('Dataset chưa được chốt theo cấu hình giữ giọng gốc.')
    for name, sha in report.get('audioSha256', {}).items():
        if digest(safe_path(root/'dataset/audio', name)) != sha:
            raise ValueError('Audio đã thay đổi sau khi duyệt. Chốt lại dataset.')
    output.mkdir(parents=True, exist_ok=True)
    seed_everything(42, workers=True)
    # Official checkpoint only; hash is verified by the notebook before this call.
    checkpoint = torch.load(base_checkpoint, map_location='cpu', weights_only=False)
    hp = checkpoint['hyper_parameters']
    architecture = ['resblock','resblock_kernel_sizes','resblock_dilation_sizes',
                    'upsample_rates','upsample_initial_channel','upsample_kernel_sizes',
                    'filter_length','hop_length','win_length','mel_channels','mel_fmin','mel_fmax',
                    'inter_channels','hidden_channels','filter_channels','n_heads','n_layers',
                    'kernel_size','p_dropout','n_layers_q','use_spectral_norm','gin_channels',
                    'use_sdp','segment_size','num_symbols']
    options = {k: hp[k] for k in architecture if k in hp}
    model = VitsModel(**options, batch_size=4, sample_rate=22050, num_speakers=1,
                      learning_rate=PROFILE['learningRate'], learning_rate_d=PROFILE['learningRate'], mos_metric=None)
    # Strict load catches architectural mismatch instead of silently training random layers.
    model.load_state_dict(checkpoint['state_dict'], strict=True)
    del checkpoint
    dm = VitsDataModule(csv_path=root/'dataset/metadata.csv', audio_dir=root/'dataset/audio',
                       voice_name='windi_vi_narrator', espeak_voice='vi',
                       cache_dir=root/('piper-cache-'+PROFILE['id']), config_path=output/'voice.onnx.json',
                       sample_rate=22050, batch_size=4, num_workers=2,
                       validation_split=.1, num_test_examples=0, trim_silence=PROFILE['trimSilence'],
                       **{k:options[k] for k in ['num_symbols','filter_length','hop_length','win_length','segment_size'] if k in options})
    latest = ModelCheckpoint(dirpath=output/'checkpoints', filename='step-{step}',
                             every_n_train_steps=100, save_last=True, save_top_k=1,
                             enable_version_counter=False)
    best = ModelCheckpoint(dirpath=output/'best', monitor='val_mel', mode='min', save_top_k=2,
                           filename='epoch-{epoch}-mel-{val_mel:.3f}', auto_insert_metric_name=False)
    atomic_json(output/'run.json', dict(dataset=report,maxSteps=max_steps,seed=42,
                                       runtime='piper-tts==1.8.0',status='running',profile=PROFILE))
    trainer = Trainer(accelerator='gpu', devices=1, precision='32-true', max_steps=max_steps,
                      max_epochs=-1, default_root_dir=output, callbacks=[latest,best],
                      log_every_n_steps=10, num_sanity_val_steps=1, deterministic=False)
    try:
        trainer.fit(model, datamodule=dm, ckpt_path=resume)
    finally:
        # Lightning writes normal periodic checkpoints; retain an explicit interruption point too.
        if trainer.global_step > 0:
            partial = output/'interrupted.partial.ckpt'
            trainer.save_checkpoint(partial)
            partial.replace(output/'interrupted.ckpt')


def listening_pack(root, model, output, count=5):
    """Private A/B references only. Never include these recordings in public exports."""
    from piper import PiperVoice
    root, model, output = Path(root), Path(model), Path(output)
    holdout = json.loads((root/'dataset/holdout.json').read_text())
    if len(holdout) < 1:
        raise ValueError('Chưa có phần nghe đối chiếu giữ riêng.')
    # Reject changed/non-matching references instead of comparing against stale text/audio.
    report = json.loads((root/'dataset/report.json').read_text())
    if report['reviewedManifestSha256'] != digest(root/'review.json'):
        raise ValueError('Phần đối chiếu đã thay đổi; chốt lại dataset.')
    output.mkdir(parents=True, exist_ok=True)
    total = min(count, len(holdout))
    indices = sorted({round(i*(len(holdout)-1)/max(1,total-1)) for i in range(total)})
    voice = PiperVoice.load(model)
    results = []
    for index in indices:
        s = holdout[index]
        reference = output/(s['id']+'-original.wav')
        generated = output/(s['id']+'-generated.wav')
        temp = generated.with_suffix('.partial.wav')
        with wave.open(str(temp),'wb') as wav:
            voice.synthesize_wav(s['text'],wav)
        info = audio_info(temp)
        if info['rms'] < .003:
            raise ValueError('Bản tạo ra chưa có tiếng hợp lệ.')
        temp.replace(generated)
        shutil.copy2(safe_path(root,s['audio']),reference)
        results.append(dict(text=s['text'],original=reference.name,generated=generated.name,
                            originalDuration=s['duration'],generatedDuration=info['duration'],
                            sourceSha256=report['sourceSha256'],modelSha256=digest(model),
                            sameVoice=None,pronunciationCorrect=None,rhythmNatural=None,
                            notes='',status='needs_listening'))
        atomic_json(output/'comparison.json',results)
    print('Đã tạo bộ nghe riêng: bản gốc và bản tạo cùng lời. Chưa chấm độ giống giọng.')
    return results


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('source'); prep.add_argument('--root',required=True)
    prep.add_argument('--model',default='small'); prep.add_argument('--device',default='cpu')
    ds = sub.add_parser('dataset'); ds.add_argument('--root',required=True)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.source,args.root,args.model,args.device)
    else:
        make_dataset(args.root)


if __name__ == '__main__':
    main()
