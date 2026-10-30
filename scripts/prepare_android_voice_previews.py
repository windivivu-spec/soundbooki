#!/usr/bin/env python3
"""Cut the first minute of each supplied Pro reference recording for Android."""
from __future__ import annotations

import hashlib
import array
import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "Đình Mạnh.wav",
    "Đình Gia.wav",
    "Minh Bùi.wav",
    "Minh Tài.wav",
    "Kim Thoa.wav",
    "Ngân Quỳnh.wav",
    "Thanh Thảo.wav",
]
NAMES = ["Đình Mạnh", "Đình Gia", "Minh Bùi", "Minh Tài", "Kim Thoa", "Ngân Quỳnh", "Thanh Thảo"]
OUT = ROOT / "android/app/src/debug/assets/voice-previews"
MAX_SECONDS = 60
RATE = 24_000
BAR_SECONDS = 0.5


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required to prepare Android voice previews")
    catalog = []
    with tempfile.TemporaryDirectory(prefix="soundbooki-pro-preview-") as temp:
        for index, (source_name, name) in enumerate(zip(SOURCES, NAMES)):
            source = ROOT / "ref voice" / source_name
            if not source.is_file():
                raise SystemExit(f"Missing source recording: {source}")
            filename = f"pro-{index}.wav"
            staged = Path(temp) / filename
            subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                 "-t", str(MAX_SECONDS), "-ac", "1", "-ar", str(RATE),
                 "-c:a", "pcm_s16le", str(staged)],
                check=True,
            )
            raw = staged.read_bytes()
            with wave.open(str(staged), "rb") as audio:
                frame_rate = audio.getframerate()
                samples = audio.readframes(audio.getnframes())
                duration_ms = round(audio.getnframes() * 1000 / frame_rate)
            values = array.array("h")
            values.frombytes(samples)
            if values.itemsize != 2:
                raise SystemExit("Expected 16-bit PCM preview")
            samples_per_bar = max(1, round(frame_rate * BAR_SECONDS))
            rms = []
            for start in range(0, len(values), samples_per_bar):
                chunk = values[start:start + samples_per_bar]
                rms.append((sum(sample * sample for sample in chunk) / len(chunk)) ** 0.5)
            peak = max(rms, default=1) or 1
            bars = [round(min(0.95, value / peak), 4) for value in rms]
            (OUT / filename).write_bytes(raw)
            catalog.append({
                "name": name,
                "file": filename,
                "durationMs": duration_ms,
                "waveform": bars,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "usage": "owner-local-demo",
                "source": source_name,
            })
    (OUT / "pro.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    for item in catalog:
        print(f"{item['name']}: {item['durationMs'] / 1000:.2f}s · {item['sha256']}")


if __name__ == "__main__":
    main()
