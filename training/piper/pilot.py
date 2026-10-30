"""Private, bounded Colab pilot. Automatic transcript checks are not human review."""
from pathlib import Path
import argparse
import gc
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile

import toolkit as kit


def normalized_words(text):
    # Keep Vietnamese accents; ignore only punctuation/case/whitespace.
    return re.findall(r'[^\W_]+', unicodedata.normalize('NFC', text).casefold())


def resolvable_boundary(items, index):
    """Missing punctuation can be checked using an estimated >=650ms speech gap.

    Stored clips pad 80ms before and 120ms after speech. Require non-overlap at
    the beginning too. Never resolve a hard cut directly into the next word.
    """
    item = items[index]
    if index + 1 >= len(items):
        return False
    if index and item['start'] < items[index-1]['end']:
        return False
    return items[index+1]['start'] - item['end'] >= .45


def verify_transcripts(root, maximum=180):
    from faster_whisper import WhisperModel
    engine = WhisperModel('large-v2', device='cuda', compute_type='float16')
    path = root/'review.json'
    record = json.loads(path.read_text())
    accepted = 0
    for index, item in enumerate(record['segments']):
        item['approved'] = False
        flags = set(item['flags']) - {'uncertain_transcript'}
        if 'check_phrase_boundary' in flags and resolvable_boundary(record['segments'], index):
            item['boundaryCheck'] = dict(method='ASR-word-times-natural-pause',
                estimatedSpeechGapSeconds=record['segments'][index+1]['start']-item['end']+.2,
                paddingDoesNotOverlapPreviousClip=True, humanListened=False)
            flags.remove('check_phrase_boundary')
        # The second strong recognizer may resolve a low first-pass probability.
        # Bad audio, a hard cut, and unresolved boundaries still block acceptance.
        if flags or accepted >= maximum:
            continue
        cached = item.get('automaticCheck', {})
        if cached.get('model') == 'large-v2':
            agreement = cached['exactAccentedWordAgreement']
            confident = cached['confidencePassed']
        else:
            segments, _ = engine.transcribe(str(kit.safe_path(root, item['audio'])),
                language='vi', beam_size=5, vad_filter=False,
                condition_on_previous_text=False)
            segments = list(segments)
            second = ''.join(s.text for s in segments)
            agreement = normalized_words(second) == normalized_words(item['text'])
            confident = bool(segments) and all(s.avg_logprob >= -.65 and s.no_speech_prob < .25 for s in segments)
            item['automaticCheck'] = dict(model='large-v2', text=second,
                exactAccentedWordAgreement=agreement, confidencePassed=confident,
                humanListened=False)
        if agreement and confident:
            item['approved'] = True
            item['approvalMethod'] = 'pilot-only-two-ASR-agreement-not-human-review'
            accepted += 1
        kit.atomic_json(path, record)
        if index % 15 == 0:
            print(f'CHECK {index+1}/{len(record["segments"])} accepted={accepted}', flush=True)
    del engine
    gc.collect()
    record['reviewPolicy'] = 'Bounded pilot: large-v3 and large-v2 agree on every accented word; not human listening.'
    kit.atomic_json(path, record)
    if accepted < 30:
        raise RuntimeError(f'Only {accepted} reliable clips; need 30. Keep files for review, do not train.')
    print(f'Accepted {accepted} clips for pilot only.', flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--source', required=True)
    args = p.parse_args()
    work, base, source = Path(args.work), Path(args.base), Path(args.source)
    work.mkdir(parents=True, exist_ok=True)
    root = work/'pilot-first-30m'
    run = root/'run'
    status = work/'pilot-status.json'
    provenance = json.loads(source.with_name('pilot-source.json').read_text())
    if kit.digest(source) != provenance['pilotSha256']:
        raise ValueError('Uploaded source checksum mismatch')
    kit.atomic_json(work/'pilot-source.json', provenance)
    try:
        kit.atomic_json(status, dict(stage='transcribing', provenance=provenance))
        print('PREPARE large-v3, first 30 minutes, no audio effects.', flush=True)
        kit.prepare(source, root, model='large-v3', device='cuda')
        gc.collect()
        kit.atomic_json(status, dict(stage='checking-transcripts'))
        verify_transcripts(root)
        report = kit.make_dataset(root, minimum=30)
        kit.atomic_json(status, dict(stage='training', dataset=report))
        print('TRAIN max_steps=300, fresh optimizer, donor strict load.', flush=True)
        kit.train(root, base/'vais1000-medium.ckpt', run, max_steps=300)
        import torch
        selected = run/'interrupted.ckpt'
        checkpoint = torch.load(selected, map_location='cpu', weights_only=False)
        step = checkpoint['global_step']
        del checkpoint
        if step < 300:
            raise RuntimeError(f'Training incomplete: global_step={step}')
        out = root/'export'
        out.mkdir(exist_ok=True)
        kit.atomic_json(status, dict(stage='exporting', globalStep=step, dataset=report))
        temp = out/'voice.partial.onnx'
        subprocess.run([sys.executable, '-m', 'piper.train.export_onnx',
            '--checkpoint', str(selected), '--output-file', str(temp)], check=True)
        import onnx
        onnx.checker.check_model(str(temp))
        temp.replace(out/'voice.onnx')
        shutil.copy2(run/'voice.onnx.json', out/'voice.onnx.json')
        shutil.copy2(base/'MODEL_CARD', out/'DONOR_MODEL_CARD.txt')
        with (out/'environment-lock.txt').open('w') as f:
            subprocess.run([sys.executable, '-m', 'pip', 'freeze'], check=True, stdout=f)
        (out/'ATTRIBUTION.txt').write_text(
            'Piper: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0)\n'
            'Donor: rhasspy/piper-checkpoints vi_VN/vais1000/medium.\n'
            'Dataset license: see donor model card (CC BY 4.0).\n'
            'Private experimental voice; source recordings excluded.\n')
        evidence = dict(stage='complete-pilot-needs-listening', globalStep=step,
            modelSha256=kit.digest(out/'voice.onnx'), modelBytes=(out/'voice.onnx').stat().st_size,
            dataset=report, source=provenance, similarityVerified=False,
            reviewPolicy='two-ASR exact accented words, not human listening')
        kit.atomic_json(out/'pilot-result.json', evidence)
        kit.listening_pack(root, out/'voice.onnx', root/'private-comparison')
        shutil.make_archive(str(work/'windi-voice-001-pilot'), 'zip', out)
        with zipfile.ZipFile(work/'windi-voice-001-private-preview.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for f in (root/'private-comparison').iterdir():
                z.write(f, f.name)
        kit.atomic_json(status, evidence)
        print('PILOT COMPLETE', json.dumps(evidence, ensure_ascii=False), flush=True)
    except BaseException as e:
        kit.atomic_json(status, dict(stage='interrupted-or-failed', error=repr(e)))
        raise


if __name__ == '__main__':
    main()
