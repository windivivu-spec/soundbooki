#!/usr/bin/env python3
"""Sync private voices to Modal Volume 'windi-studio-voices'."""

import os
import pathlib
import sys
import time
import modal

ROOT = pathlib.Path(__file__).resolve().parents[2]
VOLUME_NAME = "windi-studio-voices"

def main():
    vol = modal.Volume.from_name(VOLUME_NAME)
    print(f"Connecting to Modal Volume: {VOLUME_NAME}...")

    # 1. Upload Vocos
    vocos_dir = ROOT / ".resources/tts-f5-private/vocos"
    if vocos_dir.is_dir():
        print("Checking Vocos vocoder...")
        with vol.batch_upload(force=True) as batch:
            for item in vocos_dir.glob("*"):
                if item.is_file() and not item.name.startswith("."):
                    batch.put_file(str(item), f"/vocos/{item.name}")
        print("Vocos synced successfully.")

    # 2. Upload voices from .resources/tts-f5-private/voices
    voices_dir = ROOT / ".resources/tts-f5-private/voices"
    existing_remote = {e.path.split("/")[0] for e in vol.listdir("/")}
    
    # Priority list: upload newest 008, 007 first, then others
    vids = ["voice-008", "voice-007", "voice-006", "voice-004", "voice-003", "voice-002"]
    
    for vid in vids:
        local_vdir = voices_dir / vid
        if not local_vdir.is_dir():
            print(f"Skipping missing local directory: {local_vdir}")
            continue
        
        # Check if already present on remote
        remote_files = [e.path for e in vol.listdir(f"/{vid}")] if vid in existing_remote else []
        if f"{vid}/model.pt" in remote_files:
            print(f"[{vid}] Already uploaded on remote Volume, skipping.")
            continue

        print(f"[{vid}] Uploading files to /{vid}...")
        t0 = time.time()
        with vol.batch_upload(force=True) as batch:
            for item in local_vdir.glob("*"):
                if item.is_file() and not item.name.startswith("."):
                    batch.put_file(str(item), f"/{vid}/{item.name}")
        elapsed = time.time() - t0
        sz_mb = sum(f.stat().st_size for f in local_vdir.glob("*") if f.is_file()) / (1024*1024)
        speed = sz_mb / elapsed if elapsed > 0 else 0
        print(f"[{vid}] Uploaded {sz_mb:.1f} MB in {elapsed:.1f}s ({speed:.2f} MB/s)")

    print("\n=== VOLUME FILE LIST ===")
    for entry in vol.listdir("/"):
        print(f" - {entry.path}")

if __name__ == "__main__":
    main()
