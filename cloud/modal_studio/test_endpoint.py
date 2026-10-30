#!/usr/bin/env python3
"""Test script for Windi Studio TTS on Modal (NVIDIA L4)."""

import argparse
import base64
import json
import pathlib
import sys
import time
import urllib.request

TEST_SAMPLE = (
    "Thị trường tài chính luôn vận động không ngừng. "
    "Nếu bạn không làm chủ cảm xúc của mình, bạn sẽ trở thành nạn nhân của lòng tham và nỗi sợ hãi."
)

def test_rest(endpoint_url: str, text: str = TEST_SAMPLE, voice_id: str = "voice-008", out_path: str = "sample_test.wav"):
    payload = {
        "text": text,
        "voice_id": voice_id,
        "steps": 32,
        "cfg_strength": 2.2,
        "use_ai_director": True,
        "speed_factor": 1.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print(f"\n[REST] Sending POST request to: {endpoint_url}")
    print(f"[REST] Voice: {voice_id} | Steps: 32 | AI Director: True")
    print(f"[REST] Text: \"{text}\"")
    t0 = time.time()

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    roundtrip = time.time() - t0
    print(f"\n[REST] Response received in {roundtrip:.2f}s:")
    print(f" - Status: {body.get('status')}")
    print(f" - Server Inference Time: {body.get('inference_time')}s")
    print(f" - Audio Duration: {body.get('duration_seconds')}s")
    print(f" - Sample Rate: {body.get('sample_rate')} Hz")
    print(f" - SHA256: {body.get('sha256')[:16]}...")
    if body.get("ai_director"):
        print(f" - AI Context Director Analysis:")
        for k, v in body["ai_director"].items():
            print(f"     * {k}: {v}")

    wav_bytes = base64.b64decode(body["audio_b64"])
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(wav_bytes)
    print(f" - Saved audio to: {p.resolve()} ({len(wav_bytes)/1024:.1f} KB)\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Modal endpoint URL")
    parser.add_argument("--voice", default="voice-008", help="Voice ID (e.g. voice-008, voice-007)")
    parser.add_argument("--text", default=TEST_SAMPLE, help="Vietnamese text to synthesize")
    parser.add_argument("--out", default="training/f5/artifacts/sample_modal_l4.wav", help="Output WAV path")
    args = parser.parse_args()

    test_rest(args.url, text=args.text, voice_id=args.voice, out_path=args.out)
