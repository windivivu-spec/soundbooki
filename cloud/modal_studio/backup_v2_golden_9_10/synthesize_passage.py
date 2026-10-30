#!/usr/bin/env python3
"""Batch synthesis for complete passages using Windi Studio Cloud on Modal with Qwen2.5 Director."""

import argparse
import base64
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from narration_text import plan_f5_prosody

PASSAGE_TEXT = """“Có nhiều vàng được khai thác từ suy nghĩ của loài người hơn là số vàng được lấy ra từ trái đất. Vậy hãy quét đi lớp mạng nhện và tận dụng tất cả những ý tưởng tuyệt vời mà bạn có!”

- Khuyết danh -

Bạn đã bao giờ mường tượng về người mà mình sẽ trở thành hay chưa? Đã bao giờ bạn thiết tha muốn thực hiện bằng được một việc gì? Hay bạn có hình dung nào về việc bạn sinh ra để dành cho điều gì chưa?

Nhưng đồng thời, bạn cũng tự nói với bản thân rằng viễn cảnh đó không thể xảy ra. Bạn mơ về việc trở thành một doanh nhân, nhưng lại không bao giờ khởi nghiệp. Bạn muốn là một nghệ sĩ, nói đúng hơn là một họa sĩ, nhưng lại không bao giờ động đến cọ vẽ và vải toan. Nếu đúng là như vậy, thì theo như Steven Pressfield, tác giả cuốn The War of Art (tạm dịch: Cuộc chiến nghệ thuật), bạn đang bị thử thách."""


def segment_passage(text: str):
    """Use the exact deterministic prosodic planner from backend/narration_text.py."""
    return plan_f5_prosody(text)


def call_modal(endpoint: str, text: str, voice_id: str, steps: int = 32, author_comma: bool = False):
    payload = {
        "text": text,
        "voice_id": voice_id,
        "steps": steps,
        "cfg_strength": 2.2,
        "use_ai_director": True,
        "speed_factor": 1.0,
        "author_comma": author_comma,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    wav_bytes = base64.b64decode(res["audio_b64"])
    audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    return audio, sr, res


def synthesize_passage(endpoint: str, voice_id: str, out_path: str, steps: int = 32):
    units = segment_passage(PASSAGE_TEXT)
    print(f"\n========================================================")
    print(f"🎬 Windi Studio Cloud Synthesis (Qwen2.5 + F5-TTS)")
    print(f"Voice ID: {voice_id} | Steps: {steps} | Units: {len(units)}")
    print(f"Endpoint: {endpoint}")
    print(f"========================================================\n")

    audio_chunks = []
    sr = 24000
    t_start = time.time()

    for idx, u in enumerate(units):
        chunk_text = u["text"]
        short_preview = (chunk_text[:55] + "...") if len(chunk_text) > 55 else chunk_text
        print(f"[{idx+1:02d}/{len(units):02d}] \"{short_preview}\"")
        t0 = time.time()
        audio, sr, meta = call_modal(
            endpoint,
            chunk_text,
            voice_id,
            steps,
            author_comma=u.get("author_comma", False)
        )
        elapsed = time.time() - t0

        director = meta.get("ai_director") or {}
        emo = director.get("emotion", "neutral")
        pace = director.get("pace_factor", 1.0)
        c_breath = director.get("continuous_breath", False)
        dur = len(audio) / sr
        print(f"      ↳ Inferred in {elapsed:.2f}s | Audio: {dur:.2f}s | Emotion: {emo} | Pace: {pace:.2f} | Continuous: {c_breath}")

        audio_chunks.append(audio)

        # Add pause silence
        pause_s = u.get("pause", 0.4)
        if idx < len(units) - 1 and pause_s > 0:
            silence = np.zeros(int(pause_s * sr), dtype=np.float32)
            audio_chunks.append(silence)

    full_audio = np.concatenate(audio_chunks)
    total_time = time.time() - t_start
    total_dur = len(full_audio) / sr

    out_p = pathlib.Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_p), full_audio, sr, subtype="PCM_16")

    # Export MP3 192k for easy listening
    mp3_path = out_p.with_suffix(".mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(out_p), "-b:a", "192k", str(mp3_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        mp3_size_mb = mp3_path.stat().st_size / (1024 * 1024)
        mp3_info = f"{mp3_path.name} ({mp3_size_mb:.2f} MB)"
    except Exception:
        mp3_info = "ffmpeg export skipped"

    print(f"\n========================================================")
    print(f"🎉 Synthesis Complete!")
    print(f"Total Duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes)")
    print(f"Total Cloud Time: {total_time:.2f}s ({total_dur/total_time:.2f}x Real-Time)")
    print(f"WAV File: {out_p.resolve()} ({out_p.stat().st_size / (1024*1024):.2f} MB)")
    print(f"MP3 File: {mp3_path.resolve()} ({mp3_info})")
    print(f"========================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://windivivuco--windi-studio-tts-windistudioengine-synthesize.us-east.modal.run"
    )
    parser.add_argument("--voice", default="voice-003")
    parser.add_argument("--out", default="training/f5/artifacts/modal_qwen_dynamic_ref_voice003.wav")
    parser.add_argument("--steps", type=int, default=32)
    args = parser.parse_args()

    synthesize_passage(args.url, args.voice, args.out, steps=args.steps)
