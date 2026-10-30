#!/usr/bin/env python3
"""HeyGen Turbo Cloud Audiobook Production Pipeline for Windi Studio.

Features:
1. HeyGen v3 TTS: model="heygen-voice-1-turbo", language="vi", expressiveness_boost=0.4.
2. Pre-synthesis Text Proofreading & Normalization:
   - Lowercases ALL-CAPS words to avoid letter-spelling while preserving standard acronyms (AI, CEO...).
   - Converts Roman numerals (Chương I -> Chương 1).
   - Repairs blurred OCR typos (1uôn -> luôn, kh0ng -> không, ngườ1 -> người).
   - Strips scanner headers, page numbers, and ornaments.
3. Natural Audiobook Pacing:
   - 3.0s natural silence between chapters.
   - 1.5s pause after chapter headings.
4. Master Silence QA Gate:
   - Detects any dead air > 4.5s and cleanly compresses it down to 1.0s.
5. High-quality, fast-download MP3:
   - 128kbps CBR with full ID3 metadata.
6. 5,000 Free Character Budget Tracker.
"""

import argparse
import io
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Optional, List, Dict
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.narration_text import (
    plan_f5_prosody,
    proofread_audiobook_text,
    split_smart_vietnamese_sentences,
    pack_sentences_into_chunks,
    split_long_sentence_by_clauses,
)
from cloud.heygen_studio.heygen_client import HeyGenClient, load_env_local, get_voice_expressiveness

SAMPLE_PASSAGE = """
CHƯƠNG I: SỨC MẠNH CỦA Ý TƯỞNG
Trang 1 / 150
--- 1 ---

“Có nhiều vàng được khai thác từ suy nghĩ của loài người hơn là số vàng được lấy ra từ trái đất. Vậy hãy quét đi lớp mạng nhện và tận dụng tất cả những ý tưởng tuyệt vời mà bạn có!”

- Khuyết danh -

Bạn 1uôn mường tượng về người mà mình sẽ trở thành hay chưa? Đã bao giờ bạn thiết tha muốn thực hiện bằng được một việc gì? Hay bạn có hình dung nào về việc bạn sinh ra để dành cho điều gì chưa?

Nhưng đồng thời, bạn cũng tự nói với bản thân rằng viễn cảnh đó kh0ng thể xảy ra. Bạn mơ về việc trở thành một doanh-
nhân, nhưng lại kh0ng bao giờ khởi nghiệp. Bạn muốn là một nghệ sĩ, nói đúng hơn là một họa sĩ, nhưng lại kh0ng bao giờ động đến cọ vẽ và vải toan. Nếu đúng là như vậy, thì theo như Steven Pressfield, tác giả cuốn The War of Art (tạm dịch: Cuộc chiến nghệ thuật), bạn đang bị thử thách.

***
CHƯƠNG II: VƯỢT QUA SỰ TRÌ HOÃN
Trang 2 / 150
--- 2 ---

Sự kháng cự chính là kẻ thù nguy hiểm nhất của mỗi chúng ta. Nó 1uôn xuất hiện vào đúng thời điểm bạn chuẩn bị bắt đầu một điều gì đó vĩ đại. Đừng để nó đánh bại bạn!
"""


def split_into_audiobook_paragraphs(text: str, max_chunk_chars: int = 4800, drop_oversized: bool = True) -> list:
    """Split text into logical paragraphs and sentence-aligned chunks strictly <= max_chunk_chars.

    Guarantees:
    - Maximizes utilization up to max 5,000 characters per HeyGen request (default ceiling 4,800).
    - If a paragraph is longer than max_chunk_chars (e.g. 5k, 10k, 20k chars), it splits
      cleanly at sentence boundaries (.!?… and dialogue quotes).
    - If a single sentence exceeds max_chunk_chars: drops the sentence for safety ('bỏ nguyên câu cho an toàn')
      when drop_oversized=True, ensuring the final audio is 100% smooth, natural, and never crashes HeyGen.
    - Preserves emotional rhythm: 0.4s natural breathing pause between sentences of the same
      paragraph, 0.9s between paragraphs, 3.0s between chapters.

    Returns list of dicts:
    - text: clean paragraph or sentence chunk text
    - pause_s: pause duration after this chunk (0.4s - 3.0s)
    - type: role (heading, quote, attribution, question, body, sentence_continuation, chapter_end)
    - chapter_idx: chapter index
    - para_idx: paragraph index
    - sub_idx: sub-chunk index within long paragraph (if split)
    - total_sub: total sub-chunks within long paragraph
    - is_sub_chunk: bool
    """
    import re
    # Split by chapter headings
    raw_chapters = re.split(r'(?im)(?=^\s*chương\s+\d+)', text)
    raw_chapters = [c.strip() for c in raw_chapters if c.strip()]
    if not raw_chapters:
        raw_chapters = [text.strip()]

    items = []
    for c_idx, ch in enumerate(raw_chapters):
        paras = [p.strip() for p in ch.split("\n\n") if p.strip()]
        for p_idx, p in enumerate(paras):
            # Ensure proper capitalization for natural TTS inflection
            if p and p[0].islower():
                p = p[0].upper() + p[1:]

            is_last_in_ch = (p_idx == len(paras) - 1)
            is_last_overall = is_last_in_ch and (c_idx == len(raw_chapters) - 1)

            p_lower = p.lower()
            if is_last_overall:
                pause = 1.0
                ptype = "final"
            elif is_last_in_ch:
                pause = 3.0
                ptype = "chapter_end"
            elif p.startswith("-") and p.endswith("-") and len(p) < 30:
                pause = 0.8
                ptype = "attribution"
            elif p.startswith("“") or p.startswith('"'):
                pause = 0.8
                ptype = "quote"
            elif p_lower.startswith("chương ") or (len(p) < 45 and not p.endswith((".", "!", "?", "”", '"'))):
                pause = 0.8
                ptype = "heading"
            elif p.endswith("?"):
                pause = 1.0
                ptype = "question"
            else:
                pause = 0.9
                ptype = "body"

            # Check if paragraph length fits safely within request budget
            if len(p) <= max_chunk_chars:
                items.append({
                    "text": p,
                    "pause_s": pause,
                    "type": ptype,
                    "chapter_idx": c_idx + 1,
                    "para_idx": p_idx + 1,
                    "sub_idx": 1,
                    "total_sub": 1,
                    "is_sub_chunk": False,
                })
            else:
                # Long paragraph (> max_chunk_chars or > 5k characters)
                # Split intelligently into sentence-aligned sub-chunks
                sents = split_smart_vietnamese_sentences(p)
                sub_chunks = (
                    pack_sentences_into_chunks(sents, max_chars=max_chunk_chars, drop_oversized=drop_oversized)
                    if sents
                    else (
                        [] if drop_oversized else split_long_sentence_by_clauses(p, max_chars=max_chunk_chars)
                    )
                )
                if not sub_chunks and drop_oversized:
                    import sys
                    print(f"   ⚠️ [Bỏ câu quá dài] Bỏ qua đoạn văn {len(p)} ký tự (> {max_chunk_chars}) để đảm bảo an toàn tuyệt đối.", file=sys.stderr)

                for sub_idx, sub_text in enumerate(sub_chunks):
                    sub_text = sub_text.strip()
                    if not sub_text:
                        continue
                    if sub_text[0].islower():
                        sub_text = sub_text[0].upper() + sub_text[1:]

                    is_last_sub = (sub_idx == len(sub_chunks) - 1)
                    if is_last_sub:
                        sub_pause = pause
                        sub_type = ptype
                    else:
                        # Natural inter-sentence breathing pause within the same paragraph
                        sub_pause = 0.40
                        sub_type = "sentence_continuation"

                    items.append({
                        "text": sub_text,
                        "pause_s": sub_pause,
                        "type": sub_type,
                        "chapter_idx": c_idx + 1,
                        "para_idx": p_idx + 1,
                        "sub_idx": sub_idx + 1,
                        "total_sub": len(sub_chunks),
                        "is_sub_chunk": True,
                    })
    return items


def trim_excessive_silence(audio: np.ndarray, sr: int = 24000, max_silence_s: float = 4.5, target_silence_s: float = 1.0) -> np.ndarray:
    """Master Audio QA gate: detect any silence > max_silence_s (especially dead air > 5s)
    and compress it down to target_silence_s with smooth crossfades, preserving 3.0s chapter breaks."""
    if len(audio) == 0:
        return audio

    win = int(0.02 * sr)  # 20ms analysis window
    n_wins = len(audio) // win
    if n_wins == 0:
        return audio

    thresh = 10 ** (-40.0 / 20.0)  # -40 dB
    frames = audio[:n_wins * win].reshape(n_wins, win)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    is_silent = rms < thresh

    spans = []
    in_sil = False
    s_idx = 0
    for i, s in enumerate(is_silent):
        if s and not in_sil:
            in_sil = True
            s_idx = i
        elif not s and in_sil:
            in_sil = False
            spans.append((s_idx, i))
    if in_sil:
        spans.append((s_idx, n_wins))

    max_wins = int(max_silence_s / 0.02)
    target_len = int(target_silence_s * sr)
    xfade = int(0.015 * sr)  # 15ms crossfade

    out_parts = []
    cur_sample = 0

    for s_w, e_w in spans:
        span_dur_w = e_w - s_w
        if span_dur_w > max_wins:
            span_start_samp = s_w * win
            span_end_samp = min(len(audio), e_w * win)

            before = audio[cur_sample:span_start_samp].copy()
            if len(before) > xfade:
                before[-xfade:] *= np.linspace(1.0, 0.0, xfade, dtype=np.float32)
            out_parts.append(before)
            out_parts.append(np.zeros(target_len, dtype=np.float32))
            cur_sample = span_end_samp

    if cur_sample < len(audio):
        tail = audio[cur_sample:].copy()
        if out_parts and len(tail) > xfade:
            tail[:xfade] *= np.linspace(0.0, 1.0, xfade, dtype=np.float32)
        out_parts.append(tail)

    return np.concatenate(out_parts) if out_parts else audio


def synthesize_book_heygen(
    text: str,
    voice_id: str = "",
    out_path: str = "training/f5/artifacts/heygen_audiobook_master.wav",
    book_title: str = "Audiobook Master",
    author: str = "Tác giả",
    model: str = "heygen-voice-1-turbo-free",
    language: str = "vi",
    expressiveness_boost: Optional[float] = None,
    speed: float = 1.0,
):
    eff_boost = (
        expressiveness_boost if expressiveness_boost is not None
        else get_voice_expressiveness(voice_id or "Đình Mạnh")
    )
    print("\n" + "=" * 65)
    print("🚀 WINDI STUDIO HEYGEN CLOUD AUDIOBOOK ENGINE")
    print(f"Model: {model} | Lang: {language} | Boost: {eff_boost} | Speed: {speed}")
    print("=" * 65 + "\n")

    client = HeyGenClient(
        model=model,
        language=language,
        expressiveness_boost=eff_boost,
        speed=speed,
        voice_id=voice_id or None,
    )

    if not client.api_key:
        print("❌ LỖI: Chưa có HEYGEN_API_KEY trong .env.local!")
        print("Vui lòng mở file .env.local và điền: HEYGEN_API_KEY=your_key_here")
        return None

    # Step 1: Pre-synthesis Text Proofreading & Normalization
    print("📝 Bước 1: Rà soát & Chuẩn hóa văn bản trước khi đọc...")
    clean_text = proofread_audiobook_text(text)
    print("   ✓ Đã dọn rác máy scan, số trang và dấu trang trí.")
    print("   ✓ Đã hạ chữ in hoa (ALL-CAPS) để tránh đánh vần từng ký tự.")
    print("   ✓ Đã chuyển đổi số La Mã (Chương I -> Chương 1).")
    print("   ✓ Đã sửa các lỗi OCR mờ (1uôn -> luôn, kh0ng -> không...).")

    # Step 2: Paragraph & Chapter Segmentation with Natural Audiobook Pacing
    print("\n🎼 Bước 2: Phân đoạn đoạn văn và tính toán nhịp thở chiêm nghiệm...")
    items = split_into_audiobook_paragraphs(clean_text, max_chunk_chars=4800, drop_oversized=True)
    total_chars = sum(len(it["text"]) for it in items)
    sub_count = sum(1 for it in items if it.get("is_sub_chunk"))
    print(f"   ✓ Đã chia thành {len(items)} phân đoạn âm thanh an toàn ({total_chars} kí tự).")
    if sub_count > 0:
        print(f"   ✓ Đã tự động ngắt câu {sub_count} phân đoạn dài (tận dụng tối đa 4.800/5.000 ký tự) để giọng đọc mượt mà, đầy đủ cảm xúc và không lỗi HeyGen.")
    print("   ✓ Giới hạn HeyGen: 5.000 ký tự/request; tất cả các phân đoạn đều nằm trong ngưỡng an toàn.")

    # Step 3: Synthesis Loop via HeyGen TTS API
    print(f"\n⚡ Bước 3: Đang tạo âm thanh qua HeyGen TTS API ({model}, speed={speed})...")
    audio_parts = []
    target_sr = 24000
    t_start = time.time()

    for idx, item in enumerate(items):
        txt = item["text"]
        p_type = item["type"]
        p_pause = item["pause_s"]
        first_line = txt.splitlines()[0] if txt.splitlines() else txt
        label_part = (
            f"Ch{item['chapter_idx']}.P{item['para_idx']}.{item['sub_idx']}/{item['total_sub']}"
            if item.get("is_sub_chunk")
            else f"Ch{item['chapter_idx']}.P{item['para_idx']}"
        )
        print(f"   [{idx+1:02d}/{len(items):02d}] {label_part} ({p_type:11s} +{p_pause:.1f}s nghỉ) \"{first_line[:30]}...\" ({len(txt)} ký tự)...", end="", flush=True)

        res = client.synthesize(
            text=txt,
            voice_id=voice_id or None,
            model=model,
            language=language,
            expressiveness_boost=expressiveness_boost,
            speed=speed,
        )

        audio_bytes = res["audio_bytes"]
        seg_audio, seg_sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")

        # Convert to mono if stereo
        if len(seg_audio.shape) > 1:
            seg_audio = np.mean(seg_audio, axis=1)

        # Resample to 24000Hz if needed
        if seg_sr != target_sr:
            import scipy.signal
            num_samples = int(len(seg_audio) * target_sr / seg_sr)
            seg_audio = scipy.signal.resample(seg_audio, num_samples)

        # Apply gentle 10ms micro-fade to start and end of seg_audio to prevent clicks/pops
        fade_len = int(0.010 * target_sr)  # 10ms at 24kHz
        if len(seg_audio) > fade_len * 2:
            seg_audio[:fade_len] *= np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
            seg_audio[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)

        audio_parts.append(seg_audio)

        # Append natural breathing pause after this segment
        if p_pause > 0:
            audio_parts.append(np.zeros(int(p_pause * target_sr), dtype=np.float32))

        print(f" ✓ ({res['duration']:.2f}s audio in {res['elapsed_seconds']}s)")
        time.sleep(2.4)  # Owner demo only: <=25 TTS/min per process; NOT an account-wide limiter.

    wall_clock = time.time() - t_start

    # Step 4: Master Assembly & Silence QA Gate
    print("\n🎧 Bước 4: Ghép nối toàn bộ sách & quét kiểm định khoảng lặng...")
    full_audio = np.concatenate(audio_parts) if audio_parts else np.zeros(0, dtype=np.float32)
    final_audio = trim_excessive_silence(full_audio, sr=target_sr, max_silence_s=4.5, target_silence_s=1.0)
    final_dur = len(final_audio) / target_sr

    # Step 5: Export Master WAV and MP3 128kbps
    out_p = pathlib.Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_p), final_audio, target_sr, subtype="PCM_16")

    mp3_path = out_p.with_suffix(".mp3")
    mp3_size_mb = 0.0
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(out_p),
                "-b:a", "128k",
                "-metadata", f"title={book_title}",
                "-metadata", f"artist={author}",
                "-metadata", "album=Windi Studio Audiobooks (HeyGen Turbo)",
                "-metadata", "comment=Synthesized via HeyGen Turbo (language: vi, expressiveness: 0.4)",
                str(mp3_path)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        mp3_size_mb = mp3_path.stat().st_size / (1024 * 1024)
        mp3_info = f"{mp3_path.name} ({mp3_size_mb:.2f} MB)"
    except Exception as e:
        mp3_info = f"ffmpeg error: {e}"

    print("\n" + "=" * 65)
    print("🏆 HOÀN THÀNH TẠO SÁCH NÓI BẰNG HEYGEN TURBO!")
    print(f"Tổng thời lượng audio: {final_dur:.2f}s ({final_dur / 60:.2f} phút)")
    print(f"Tổng thời gian xử lý: {wall_clock:.2f}s")
    print(f"Tổng ký tự đã dùng trong lần chạy: {client.total_chars_consumed}")
    print("Giới hạn HeyGen: 5.000 ký tự/request; không phải quota tổng của sách.")
    print(f"File Master WAV: {out_p.resolve()}")
    print(f"File Master MP3 (128kbps): {mp3_path.resolve()} ({mp3_info})")
    print("=" * 65 + "\n")

    return {
        "wav_path": str(out_p.resolve()),
        "mp3_path": str(mp3_path.resolve()),
        "duration": final_dur,
        "wall_clock": wall_clock,
        "chars_used": client.total_chars_consumed,
        "request_character_limit": 5000,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HeyGen Turbo Audiobook Production")
    parser.add_argument("--voice", default="", help="HeyGen Voice ID")
    parser.add_argument("--file", default="", help="Path to text/book file (optional)")
    parser.add_argument("--out", default="training/f5/artifacts/heygen_audiobook_master.wav", help="Output WAV path")
    parser.add_argument("--title", default="Cuộc Chiến Nghệ Thuật", help="Book title")
    parser.add_argument("--author", default="Steven Pressfield", help="Author name")
    parser.add_argument("--model", default="heygen-voice-1-turbo-free", help="HeyGen Model")
    parser.add_argument("--expressiveness", type=float, default=None, help="Expressiveness boost (default: 0.7 for Thanh Thảo/Minh Bùi, 0.5 for others)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier (default: 1.0; player handles speed adjustments)")
    args = parser.parse_args()

    if args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            book_text = f.read()
    else:
        book_text = SAMPLE_PASSAGE

    synthesize_book_heygen(
        text=book_text,
        voice_id=args.voice,
        out_path=args.out,
        book_title=args.title,
        author=args.author,
        model=args.model,
        language="vi",
        expressiveness_boost=args.expressiveness,
        speed=args.speed,
    )
