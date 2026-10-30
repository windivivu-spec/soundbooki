#!/usr/bin/env python3
"""Test script for HeyGen TTS API connection and Vietnamese voice synthesis."""

import argparse
import io
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cloud.heygen_studio.heygen_client import HeyGenClient, load_env_local

TEST_PHRASE = (
    "Chào mừng bạn đến với sách nói Windi Studio. "
    "Hệ thống đang chạy thử nghiệm trên mô hình HeyGen Turbo với ngôn ngữ tiếng Việt."
)


def run_test(voice_id: str = "", text: str = TEST_PHRASE):
    print("\n" + "=" * 65)
    print("🚀 KIỂM TRA KẾT NỐI HEYGEN TTS CLOUD API (TURBO MODEL)")
    print("=" * 65 + "\n")

    env_vars = load_env_local()
    api_key = os.environ.get("HEYGEN_API_KEY") or env_vars.get("HEYGEN_API_KEY", "")

    if not api_key:
        print("⚠️ CHƯA TÌM THẤY HEYGEN_API_KEY!")
        print("Vui lòng mở file .env.local và điền API key:")
        print("   HEYGEN_API_KEY=your_heygen_api_key_here\n")
        print("Lấy API key tại: https://app.heygen.com/settings?nav=API")
        print("=" * 65 + "\n")
        return False

    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
    print(f"✓ Đã nạp HEYGEN_API_KEY: {masked}")

    client = HeyGenClient()
    print(f"✓ Cấu hình mặc định:")
    print(f"   - Model: {client.default_model}")
    print(f"   - Language: {client.default_language}")
    print(f"   - Expressiveness Boost: {client.default_expressiveness}")

    # 1. Test User Info
    print("\n📡 Bước 1: Kiểm tra thông tin tài khoản HeyGen...")
    try:
        user_info = client.get_user_info()
        data = user_info.get("data", user_info)
        username = data.get("username") or data.get("email") or "User"
        print(f"   ✓ Đăng nhập thành công! Tài khoản: {username}")
    except Exception as e:
        print(f"   ⚠️ Lỗi lấy thông tin tài khoản (có thể bỏ qua nếu API key chỉ có quyền TTS): {e}")

    # 2. List Vietnamese Voices
    print("\n🎙️ Bước 2: Quét danh sách giọng đọc tiếng Việt...")
    try:
        vi_voices = client.list_voices(language="Vietnamese", voice_type="public")
        print(f"   ✓ Tìm thấy {len(vi_voices)} giọng đọc tiếng Việt công khai:")
        for idx, v in enumerate(vi_voices[:8]):
            vid = v.get("voice_id")
            name = v.get("name")
            gender = v.get("gender", "unknown")
            print(f"     [{idx+1}] {name} ({gender}) - ID: {vid}")
    except Exception as e:
        print(f"   ⚠️ Lỗi lấy danh sách giọng: {e}")
        vi_voices = []

    # 3. Check Private Cloned Voices
    try:
        privates = client.list_voices(language="", voice_type="private")
        if privates:
            print(f"   ✓ Tìm thấy {len(privates)} giọng clone riêng (Instant/Pro Voice Clones):")
            for idx, v in enumerate(privates[:5]):
                vid = v.get("voice_id")
                name = v.get("name")
                print(f"     [Private {idx+1}] {name} - ID: {vid}")
    except Exception:
        pass

    # 4. Test TTS Synthesis
    target_text = text or TEST_PHRASE
    print(f"\n⚡ Bước 3: Tạo âm thanh thử nghiệm ({len(target_text)} kí tự)...")
    print(f"   Văn bản: \"{target_text}\"")

    try:
        res = client.synthesize(
            text=target_text,
            voice_id=voice_id or None,
            model="heygen-voice-1-turbo",
            language="vi",
            expressiveness_boost=0.4,
        )

        out_wav = ROOT / "training/f5/artifacts/heygen_test_sample.wav"
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        with open(out_wav, "wb") as f:
            f.write(res["audio_bytes"])

        out_mp3 = out_wav.with_suffix(".mp3")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(out_wav),
                "-b:a", "128k",
                "-metadata", "title=HeyGen Turbo Test",
                "-metadata", "artist=HeyGen Studio",
                str(out_mp3)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        print("\n" + "=" * 65)
        print("🎉 TẠO ÂM THANH HEYGEN THÀNH CÔNG!")
        print(f"Thời gian tạo (Latency): {res['elapsed_seconds']}s")
        print(f"Thời lượng audio: {res['duration']:.2f}s")
        print(f"Số ký tự đã dùng: {res['char_count']} kí tự (Hạn mức miễn phí: 5,000 kí tự)")
        print(f"Giọng đọc đã dùng (Voice ID): {res['voice_id']}")
        print(f"File WAV: {out_wav}")
        print(f"File MP3 (128kbps): {out_mp3}")
        print("=" * 65 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ Lỗi tạo âm thanh HeyGen: {e}\n")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test HeyGen TTS API")
    parser.add_argument("--voice", default="", help="Voice ID (optional)")
    parser.add_argument("--text", default="", help="Custom text (optional)")
    args = parser.parse_args()

    run_test(voice_id=args.voice, text=args.text)
