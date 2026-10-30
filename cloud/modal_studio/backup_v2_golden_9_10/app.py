"""Windi Studio Cloud TTS: Qwen2.5-7B Context Director + Dynamic Reference F5-TTS."""

import base64
import io
import json
import os
import pathlib
import re
import time
from typing import Dict, List, Optional
import modal
from pydantic import BaseModel

app = modal.App("windi-studio-tts")


def download_models():
    """Cache Qwen2.5-7B-Instruct in the container image at build time via HF Hub."""
    from huggingface_hub import snapshot_download
    qwen_id = "Qwen/Qwen2.5-7B-Instruct"
    print(f"Downloading {qwen_id} for container image cache...")
    snapshot_download(repo_id=qwen_id)
    print(f"{qwen_id} cached successfully.")


studio_image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
    .apt_install("ffmpeg", "git")
    .pip_install(
        "torch>=2.4.0,<2.6.0",
        "torchaudio>=2.4.0,<2.6.0",
        "transformers>=4.45.0,<4.49.0",
        "accelerate>=0.34.0",
        "soundfile>=0.12.1",
        "librosa>=0.10.2",
        "pydub>=0.25.1",
        "vocos>=0.1.0",
        "f5-tts>=0.1.2",
        "fastapi>=0.115.0",
        "pydantic>=2.9.0",
        "huggingface_hub>=0.25.0",
    )
    .run_function(download_models)
)

voices_vol = modal.Volume.from_name("windi-studio-voices")

ALIGNED_REF_TEXTS = {
    "hàng họ bán chạy quá chủ tiệm nói với cậu sau khi người khách kia đi khỏi.":
        "hàng họ bán chạy quá, chủ tiệm nói với cậu, sau khi người khách kia đi khỏi.",
    "sau đó thái sư trần thủ độ ra mắt năm hai không mười ba với ba mươi tư tập.":
        "sau đó, thái sư trần thủ độ ra mắt năm hai không mười ba, với ba mươi tư tập.",
    "tôi cố bình tĩnh vẫn vui như thường, thấy thế trủi cũng hơi yên lòng.":
        "tôi cố bình tĩnh vẫn vui như thường, thấy thế, trủi cũng hơi yên lòng.",
    "trong đầu lão lúc này chỉ toàn là những con số và sính lễ sang trọng.":
        "trong đầu lão lúc này, chỉ toàn là những con số và sính lễ sang trọng.",
    "kinh nghiệm và trải nghiệm với thiết bị đủ lâu, đủ nhiều.":
        "kinh nghiệm, và trải nghiệm, với thiết bị đủ lâu, đủ nhiều.",
    "sau này có gì phát sinh thì có cái lôi ra mà cãi thứ năm là kiểu bịp số điện nước.":
        "sau này có gì phát sinh thì có cái lôi ra mà cãi, thứ năm là kiểu bịp số điện nước.",
    "chị gái bốn mươi ngắt máy rồi bình thản nói, có con rồi là thế đấy.":
        "chị gái bốn mươi ngắt máy, rồi bình thản nói, có con rồi là thế đấy.",
    "nguyên thức thứ ba, đó là xây dựng quan hệ bằng thứ mà mình kiểm soát được.":
        "nguyên thức thứ ba, đó là xây dựng quan hệ, bằng thứ mà mình kiểm soát được.",
}

# Continuous reference slices without internal pause (>100ms) for continuous breath groups
CONTINUOUS_REF_SLICES = {
    "voice-002": {
        "text": "sau đó thái sư trần thủ độ ra mắt năm hai không mười ba.",
        "end_sec": 3.24,
    },
    "voice-003": {
        "text": "tôi cố bình tĩnh vẫn vui như thường.",
        "end_sec": 1.83,
    },
    "voice-006": {
        "text": "sau này có gì phát sinh thì có cái lôi ra mà cãi.",
        "end_sec": 2.40,
    },
    "voice-007": {
        "text": "chị gái bốn mươi ngắt máy rồi bình thản nói.",
        "end_sec": 2.45,
    },
    "voice-008": {
        "text": "đó là xây dựng quan hệ bằng thứ mà mình kiểm soát được.",
        "end_sec": 2.80,
    },
}

DASHES = "-‐‑‒–—−"
SYNTACTIC_PIVOTS = (
    "thay vì", "chứ không phải", "không những", "mà còn",
    "nhưng lại", "cho nên", "vì vậy", "do đó", "để rồi"
)


def _prepare_studio_text(text: str, preserve_clauses: bool = False) -> str:
    import unicodedata
    line = unicodedata.normalize("NFC", text).strip().lower()
    line = line.replace("…", ".").replace(";", ",").replace(":", ",")
    line = re.sub(r"(?<!\w)[−-]\s*(?=\d)", "âm ", line)
    line = re.sub(r"\s+[" + re.escape(DASHES) + r"]+\s+", ", ", line)
    line = re.sub("[" + re.escape(DASHES) + "]", " ", line)
    line = re.sub(r"\(\s*([^)]+?)\s*\)", r", \1, ", line)
    line = re.sub(r'["“”‘’«»•‣◦▪*_`#()]', " ", line)
    line = re.sub(r"\s*,\s*,+\s*", ", ", line)
    line = re.sub(r"\s+", " ", line).strip(" ,")
    if line and not preserve_clauses:
        clauses = line.split(",")
        out = []
        for cl in clauses:
            words = cl.strip().split()
            if len(words) >= 24:
                mid_str = " " + " ".join(words[6:-6]) + " "
                for pv in SYNTACTIC_PIVOTS:
                    if f" {pv} " in mid_str:
                        cl = re.sub(rf"\b({re.escape(pv)})\b", r", \1", cl, count=1)
                        break
            out.append(cl.strip())
        line = ", ".join(out)
    if line and line[-1] not in ".?!":
        line += "."
    return line


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "voice-003"
    steps: int = 32
    cfg_strength: float = 2.2
    sway_sampling_coef: float = -1.0
    use_ai_director: bool = True
    speed_factor: float = 1.0
    author_comma: Optional[bool] = None
    continuous_breath: Optional[bool] = None


class SynthesizeResponse(BaseModel):
    status: str
    voice_id: str
    audio_b64: str
    sample_rate: int
    duration_seconds: float
    sha256: str
    ai_director: Optional[dict] = None
    inference_time: float


def _trim_and_shape(audio, sr=24000, thresh_db=-42.0, pad_ms=28, fade_ms=18):
    import numpy as np
    if len(audio) == 0:
        return audio
    win = int(0.01 * sr)
    if len(audio) > win * 2:
        thresh = 10 ** (thresh_db / 20.0)
        n_wins = (len(audio) - win) // win
        if n_wins > 0:
            frames = audio[:n_wins * win].reshape(n_wins, win)
            rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
            active = np.where(rms > thresh)[0]
            if len(active) > 0:
                pad = int(pad_ms * sr / 1000)
                start = max(0, int(active[0]) * win - pad)
                end = min(len(audio), (int(active[-1]) + 1) * win + pad)
                audio = audio[start:end].copy()
    fade = min(int(fade_ms * sr / 1000), len(audio) // 4)
    if fade > 0:
        ramp = (np.sin(np.linspace(0, np.pi / 2, fade, dtype=np.float32)) ** 2)
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
    return audio


@app.cls(
    gpu=["A10G", "L4"],
    image=studio_image,
    volumes={"/voices": voices_vol},
    scaledown_window=300,
    min_containers=0,
)
class WindiStudioEngine:
    @modal.enter()
    def setup(self):
        import torch
        from vocos import Vocos
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Initializing Windi Studio Engine on NVIDIA GPU...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16

        # 1. Load Vocos Vocoder
        vocos_path = pathlib.Path("/voices/vocos")
        print("Loading Vocos vocoder on CUDA...")
        self.vocoder = Vocos.from_hparams(str(vocos_path / "config.yaml"))
        self.vocoder.load_state_dict(
            torch.load(str(vocos_path / "pytorch_model.bin"), map_location="cpu", weights_only=True)
        )
        self.vocoder.eval().to(self.device)

        # 2. Load Qwen2.5-7B-Instruct for AI Context Director
        print("Loading Qwen2.5-7B-Instruct Context Director...")
        qwen_id = "Qwen/Qwen2.5-7B-Instruct"
        self.qwen_tokenizer = AutoTokenizer.from_pretrained(qwen_id)
        self.qwen_model = AutoModelForCausalLM.from_pretrained(
            qwen_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
        ).eval()

        # Cache for loaded F5 voice models & conditions
        self.loaded_models: Dict[str, dict] = {}
        print("Windi Studio Engine successfully initialized with Qwen2.5-7B Director!")

    def analyze_context(self, text: str, voice_persona: str) -> dict:
        """Qwen2.5-7B analyzes sentence context and returns emotion, pace, and breath guidance."""
        import torch

        system_prompt = (
            "Bạn là Đạo diễn Giọng đọc Sách nói tiếng Việt chuyên nghiệp (Audiobook Director).\n"
            "Hãy phân tích câu thoại sau và trả về DUY NHẤT một chuỗi JSON có cấu trúc chính xác như sau:\n"
            "{\n"
            '  "emotion": "neutral" | "inspiring" | "warm" | "pensive" | "inquisitive" | "dramatic",\n'
            '  "pace_factor": float từ 0.96 đến 1.08 (1.0 là bình thường, >1.0 là chậm rãi/suy tư, <1.0 là nhanh nhẹn/hào sảng),\n'
            '  "pause_ms": số nguyên từ 250 đến 650 (mili-giây nghỉ sau câu),\n'
            '  "cfg_delta": float từ -0.2 đến 0.3 (câu dõng dạc/cảm thán thì 0.2-0.3, câu hỏi thì 0.1, câu bình thường thì 0.0),\n'
            '  "continuous_breath": true | false (true nếu câu là một luồng suy nghĩ liền mạch, cần đọc trơn tru không ngắt giữa câu; false nếu câu có ngắt nghỉ rõ rệt)\n'
            "}"
        )
        user_prompt = f"Giọng đọc: {voice_persona}\nCâu văn: \"{text}\"\nJSON:"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt_text = self.qwen_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.qwen_tokenizer([prompt_text], return_tensors="pt").to(self.device)

        with torch.inference_mode():
            outputs = self.qwen_model.generate(
                **inputs,
                max_new_tokens=60,
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.qwen_tokenizer.eos_token_id,
            )
        response = self.qwen_tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        try:
            match = re.search(r"\{.*?\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return {
                    "emotion": str(data.get("emotion", "neutral")),
                    "pace_factor": float(data.get("pace_factor", 1.0)),
                    "pause_ms": int(data.get("pause_ms", 350)),
                    "cfg_delta": float(data.get("cfg_delta", 0.0)),
                    "continuous_breath": bool(data.get("continuous_breath", False)),
                }
        except Exception:
            pass

        return {
            "emotion": "neutral",
            "pace_factor": 1.0,
            "pause_ms": 350,
            "cfg_delta": 0.0,
            "continuous_breath": False
        }

    def _load_voice(self, voice_id: str) -> dict:
        if voice_id in self.loaded_models:
            return self.loaded_models[voice_id]

        import numpy as np
        import soundfile as sf
        import torch
        from pydub import AudioSegment, silence
        from f5_tts.model import CFM, DiT
        from f5_tts.model.utils import get_tokenizer

        vdir = pathlib.Path(f"/voices/{voice_id}")
        if not (vdir / "model.pt").exists():
            raise ValueError(f"Voice {voice_id} not found on Modal Volume.")

        print(f"Loading weights for {voice_id}...")
        vocab, size = get_tokenizer(str(vdir / "vocab.txt"), "custom")

        transformer = DiT(
            dim=1024, depth=22, heads=16, ff_mult=2,
            text_dim=512, conv_layers=4, text_mask_padding=False,
            pe_attn_head=1, attn_backend="torch", attn_mask_enabled=False,
            text_num_embeds=size, mel_dim=100
        ).half().to(self.device)

        model = CFM(
            transformer=transformer,
            mel_spec_kwargs=dict(
                n_fft=1024, hop_length=256, win_length=1024,
                n_mel_channels=100, target_sample_rate=24000, mel_spec_type="vocos"
            ),
            odeint_kwargs=dict(method="euler"),
            vocab_char_map=vocab
        )

        checkpoint = torch.load(str(vdir / "model.pt"), map_location="cpu", weights_only=True)
        state = {k.removeprefix("ema_model."): v for k, v in checkpoint["ema_model_state_dict"].items()
                 if k not in ("initted", "step")}
        for key in ("mel_spec.mel_stft.mel_scale.fb", "mel_spec.mel_stft.spectrogram.window"):
            state.pop(key, None)
        model.load_state_dict(state)
        del state, checkpoint

        model.transformer = model.transformer.eval().to(self.device, dtype=self.dtype)
        model.mel_spec = model.mel_spec.to(self.device, dtype=self.dtype)

        # 1. Full Reference Audio and Text
        raw, rate = sf.read(str(vdir / "ref_audio.wav"), dtype="float32")
        aseg = AudioSegment(
            data=(np.clip(raw, -1, 1) * 32767).astype("<i2").tobytes(),
            sample_width=2, frame_rate=24000, channels=1
        )
        start = silence.detect_leading_silence(aseg, silence_threshold=-42)
        end = silence.detect_leading_silence(aseg.reverse(), silence_threshold=-42)
        aseg = aseg[start:len(aseg) - end if end else len(aseg)] + AudioSegment.silent(duration=50, frame_rate=24000)
        audio_full = torch.tensor(np.array(aseg.get_array_of_samples(), dtype="float32") / 32768).unsqueeze(0)
        rms = audio_full.square().mean().sqrt().item()
        gain = min(rms / 0.1, 1.0)
        if rms < 0.1:
            audio_full = audio_full * 0.1 / rms
        ref_frames_full = audio_full.shape[-1] // 256

        with torch.inference_mode():
            cond_full = model.mel_spec(audio_full.to(self.device, dtype=self.dtype)).permute(0, 2, 1)

        raw_ref = (vdir / "ref_text.txt").read_text(encoding="utf-8").strip()
        raw_ref = ALIGNED_REF_TEXTS.get(raw_ref, raw_ref)
        if not raw_ref.endswith("."):
            raw_ref += "."
        ref_text_full = raw_ref + " "

        # 2. Dynamic Continuous Reference Slice (Unbroken stream without internal pause)
        cont_slice = CONTINUOUS_REF_SLICES.get(voice_id)
        if cont_slice:
            cut_ms = int(cont_slice["end_sec"] * 1000)
            aseg_cont = aseg[:min(len(aseg), cut_ms)] + AudioSegment.silent(duration=40, frame_rate=24000)
            audio_cont = torch.tensor(np.array(aseg_cont.get_array_of_samples(), dtype="float32") / 32768).unsqueeze(0)
            if rms < 0.1:
                audio_cont = audio_cont * 0.1 / rms
            ref_frames_cont = audio_cont.shape[-1] // 256
            with torch.inference_mode():
                cond_cont = model.mel_spec(audio_cont.to(self.device, dtype=self.dtype)).permute(0, 2, 1)
            ref_text_cont = cont_slice["text"]
            if not ref_text_cont.endswith("."):
                ref_text_cont += "."
            ref_text_cont += " "
        else:
            cond_cont = cond_full
            ref_text_cont = ref_text_full
            ref_frames_cont = ref_frames_full

        manifest = {}
        if (vdir / "voice_manifest.json").exists():
            try:
                manifest = json.loads((vdir / "voice_manifest.json").read_text(encoding="utf-8"))
            except Exception:
                pass

        item = {
            "model": model,
            "cond_full": cond_full,
            "ref_text_full": ref_text_full,
            "ref_frames_full": ref_frames_full,
            "cond_cont": cond_cont,
            "ref_text_cont": ref_text_cont,
            "ref_frames_cont": ref_frames_cont,
            "gain": gain,
            "manifest": manifest,
        }
        self.loaded_models[voice_id] = item
        return item

    @modal.fastapi_endpoint(method="POST")
    def synthesize(self, req: SynthesizeRequest) -> SynthesizeResponse:
        import hashlib
        import numpy as np
        import soundfile as sf
        import torch
        from f5_tts.model.utils import convert_char_to_pinyin

        t0 = time.time()
        vinfo = self._load_voice(req.voice_id)
        model = vinfo["model"]
        voice_label = vinfo["manifest"].get("label", req.voice_id)

        # 1. AI Context Director via Qwen2.5-7B
        director_meta = None
        cfg = req.cfg_strength
        pace = req.speed_factor
        if req.use_ai_director:
            director_meta = self.analyze_context(req.text, voice_label)
            cfg += director_meta["cfg_delta"]
            pace *= max(0.95, min(1.06, director_meta["pace_factor"]))

        # 2. Reference Conditioning (Full acoustic reference for 100% stable timbre)
        raw_clean = req.text.strip().replace("…", ".").replace(";", ",").replace(":", ",")
        has_author_comma = req.author_comma if req.author_comma is not None else ("," in raw_clean[:-1])

        # Use full rich acoustic fingerprint to keep vocal timbre stable across all units
        cond = vinfo["cond_full"]
        ref_text = vinfo["ref_text_full"]
        ref_frames = vinfo["ref_frames_full"]

        # 3. Text Normalization (Preserve clauses if author has no commas)
        gen_text = _prepare_studio_text(req.text, preserve_clauses=not has_author_comma)
        full_text = ref_text + gen_text
        final_text_list = convert_char_to_pinyin([full_text])

        ref_bytes = len(ref_text.encode("utf-8"))
        gen_bytes = len(gen_text.encode("utf-8"))
        internal_commas = gen_text[:-1].count(",")
        effective_pace = 0.35 if gen_bytes < 12 else (0.78 if gen_bytes < 28 else 0.96 * pace)
        gen_frames = int(ref_frames / ref_bytes * gen_bytes / effective_pace) + internal_commas * 18 + 12
        duration = ref_frames + gen_frames

        # 4. Flow Matching Diffusion on Cloud GPU
        with torch.inference_mode():
            gen_mel, _ = model.sample(
                cond=cond,
                text=final_text_list,
                duration=duration,
                steps=req.steps,
                cfg_strength=cfg,
                sway_sampling_coef=req.sway_sampling_coef,
                seed=42,
            )
            # Remove reference prefix frames
            speech_mel = gen_mel[:, ref_frames:, :].permute(0, 2, 1)
            audio_out = self.vocoder.decode(speech_mel.float())
            audio_np = audio_out.squeeze().cpu().numpy() * vinfo["gain"]

        # 5. Silence trimming and mid-sentence continuity shaping
        audio_np = _trim_and_shape(audio_np, sr=24000)
        if not has_author_comma and len(audio_np) > 12000:
            win = 240  # 10ms at 24kHz
            n_wins = len(audio_np) // win
            frames = audio_np[:n_wins * win].reshape(n_wins, win)
            rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
            is_silent = rms < (10 ** (-38.0 / 20.0))
            xfade = 240
            out_parts = []
            cur_idx = 0
            i = 0
            while i < n_wins:
                if is_silent[i]:
                    j = i
                    while j < n_wins and is_silent[j]:
                        j += 1
                    if i > 4 and j < n_wins - 4 and (j - i) >= 16:
                        cut_start = i * win + 4 * win
                        cut_end = j * win - 4 * win
                        if cut_end > cut_start:
                            seg = audio_np[cur_idx:cut_start].copy()
                            if len(seg) > xfade:
                                seg[-xfade:] *= np.linspace(1.0, 0.0, xfade, dtype=np.float32)
                            out_parts.append(seg)
                            cur_idx = cut_end
                    i = j
                else:
                    i += 1
            tail = audio_np[cur_idx:].copy()
            if out_parts and len(tail) > xfade:
                tail[:xfade] *= np.linspace(0.0, 1.0, xfade, dtype=np.float32)
            out_parts.append(tail)
            audio_np = np.concatenate(out_parts)

        audio_bytes_io = io.BytesIO()
        sf.write(audio_bytes_io, audio_np, 24000, format="WAV", subtype="PCM_16")
        wav_data = audio_bytes_io.getvalue()

        elapsed = time.time() - t0
        sha = hashlib.sha256(wav_data).hexdigest()
        dur_sec = len(audio_np) / 24000.0

        return SynthesizeResponse(
            status="success",
            voice_id=req.voice_id,
            audio_b64=base64.b64encode(wav_data).decode("ascii"),
            sample_rate=24000,
            duration_seconds=round(dur_sec, 2),
            sha256=sha,
            ai_director=director_meta,
            inference_time=round(elapsed, 3),
        )
