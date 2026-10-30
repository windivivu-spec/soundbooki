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


def call_modal_batch(batch_url: str, units: list, voice_id: str, steps: int = 28):
    batch_units = [
        {
            "id": i + 1,
            "text": u["text"],
            "pause_after": u.get("pause", 0.4),
            "author_comma": u.get("author_comma", False)
        }
        for i, u in enumerate(units)
    ]
    payload = {
        "units": batch_units,
        "voice_id": voice_id,
        "steps": steps,
        "cfg_strength": 2.2,
        "use_ai_director": True,
        "speed_factor": 1.0,
    }
    req = urllib.request.Request(
        batch_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    roundtrip = time.time() - t0

    wav_bytes = base64.b64decode(res["audio_b64"])
    audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    return audio, sr, res, roundtrip


def synthesize_batch_passage(batch_url: str, voice_id: str, out_path: str, steps: int = 28, option_name: str = "Batch Pipeline"):
    units = segment_passage(PASSAGE_TEXT)
    print(f"\n========================================================")
    print(f"🎬 Windi Studio Turbo Synthesis [{option_name}]")
    print(f"Voice ID: {voice_id} | Steps: {steps} | Units: {len(units)}")
    print(f"Batch Endpoint: {batch_url}")
    print(f"========================================================\n")

    print(f"Submitting {len(units)} units in 1 single GPU batch call...")
    audio, sr, res, roundtrip = call_modal_batch(batch_url, units, voice_id, steps=steps)

    server_time = res.get("total_time", 0.0)
    audio_dur = res.get("duration_seconds", len(audio) / sr)
    speedup = audio_dur / roundtrip if roundtrip > 0 else 1.0

    print(f"\n⚡ Response received in {roundtrip:.2f}s (Server execution: {server_time:.2f}s)!")
    print(f"   Audio Duration: {audio_dur:.2f}s | Speed: {speedup:.2f}x Real-Time")
    
    # Print director summary
    print(f"\n🎭 AI Director Prosody Breakdown:")
    for idx, (u, meta) in enumerate(zip(units, res.get("ai_director_summary", []))):
        short = (u["text"][:45] + "...") if len(u["text"]) > 45 else u["text"]
        emo = meta.get("emotion", "neutral")
        pace = meta.get("pace_factor", 1.0)
        p_ms = meta.get("pause_ms", 350)
        dur = res.get("unit_durations", [])[idx] if idx < len(res.get("unit_durations", [])) else 0.0
        print(f"   [{idx+1:02d}] {dur:4.2f}s | {emo:11s} | pace {pace:4.2f} | pause {p_ms}ms | \"{short}\"")

    out_p = pathlib.Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_p), audio, sr, subtype="PCM_16")

    # Export MP3 192k
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
        mp3_info = "ffmpeg skipped"

    print(f"\n========================================================")
    print(f"🎉 Synthesis Complete: {option_name}!")
    print(f"Audio Duration: {audio_dur:.2f}s ({audio_dur/60:.2f} min)")
    print(f"Total Wall-Clock Time: {roundtrip:.2f}s ({speedup:.2f}x Real-Time)")
    print(f"Estimated 1-Hour Audiobook Time: {3600 / speedup / 60:.1f} minutes")
    print(f"WAV File: {out_p.resolve()} ({out_p.stat().st_size / (1024*1024):.2f} MB)")
    print(f"MP3 File: {mp3_path.resolve()} ({mp3_info})")
    print(f"========================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://windivivuco--windi-studio-tts-windistudioengine-batch.us-east.modal.run"
    )
    parser.add_argument("--voice", default="voice-003")
    parser.add_argument("--out", default="training/f5/artifacts/modal_batch_sample.wav")
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--name", default="Batch Pipeline")
    args = parser.parse_args()

    synthesize_batch_passage(args.url, args.voice, args.out, steps=args.steps, option_name=args.name)
