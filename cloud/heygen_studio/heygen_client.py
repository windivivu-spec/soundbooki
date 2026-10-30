#!/usr/bin/env python3
"""HeyGen Cloud Text-to-Speech (TTS) Client for Windi Studio.

Implements official HeyGen v3 API endpoints:
- POST https://api.heygen.com/v3/models/audio/tts (HeyGen Voice Model)
- GET https://api.heygen.com/v3/voices (List public/private voices)
- GET https://api.heygen.com/v3/users/me (Account & quota info)

Default parameters per user request:
- Model: "heygen-voice-1-turbo"
- Language: "vi"
- Expressiveness Boost: 0.4
"""

import io
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple, Any

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Official Mapping of Windi Ref Voices to HeyGen Voice IDs
HEYGEN_REF_VOICES = {
    "Đình Mạnh": {
        "voice_id": "3414fd7fdaa64e619fb8b021534ce368",
        "heygen_name": "Podcast",
        "gender": "male",
        "default_boost": 0.5,
        "ref_file": "Đình Mạnh.wav",
        "description": "Giọng nam truyền cảm, phong cách podcast chiêm nghiệm",
    },
    "Đình Gia": {
        "voice_id": "3ab886ca76924521bbed407e45762540",
        "heygen_name": "Đình Gia",
        "gender": "male",
        "default_boost": 0.5,
        "ref_file": "Đình Gia.wav",
        "description": "Giọng nam trầm ấm, đĩnh đạc",
    },
    "Minh Bùi": {
        "voice_id": "eff592346cac4febbba5d5fef4621ff0",
        "heygen_name": "Minh Bùi",
        "gender": "male",
        "default_boost": 0.7,
        "ref_file": "Minh Bùi.wav",
        "description": "Giọng nam tự nhiên, mạch lạc (boost 0.7)",
    },
    "Minh Tài": {
        "voice_id": "b241299543834cd8994186e600280e25",
        "heygen_name": "Minh Tài",
        "gender": "male",
        "default_boost": 0.5,
        "ref_file": "Minh Tài.wav",
        "description": "Giọng nam ấm áp, biểu cảm",
    },
    "Kim Thoa": {
        "voice_id": "60dce6af562449f294ceeddb4130a9ee",
        "heygen_name": "Kim Thoa",
        "gender": "female",
        "default_boost": 0.5,
        "ref_file": "Kim Thoa.wav",
        "description": "Giọng nữ thanh thoát, dịu dàng",
    },
    "Ngân Quỳnh": {
        "voice_id": "6a92e2ed9d3843f2b059ef8e6809366c",
        "heygen_name": "Ngân Quỳnh",
        "gender": "female",
        "default_boost": 0.5,
        "ref_file": "Ngân Quỳnh.wav",
        "description": "Giọng nữ truyền cảm, mượt mà",
    },
    "Thanh Thảo": {
        "voice_id": "5ee4ba10bd0446ba85421ab177462aba",
        "heygen_name": "Thanh Thảo",
        "gender": "female",
        "default_boost": 0.7,
        "ref_file": "Thanh Thảo.wav",
        "description": "Giọng nữ trẻ trung, trong trẻo (boost 0.7)",
    },
}


def get_voice_expressiveness(voice_id_or_name: str) -> float:
    """Return default expressiveness boost per user specifications:
    - Thanh Thảo & Minh Bùi: 0.7
    - All other voices: 0.5
    """
    v_lower = str(voice_id_or_name).lower()
    if "thanh thảo" in v_lower or "thanh thao" in v_lower or "5ee4ba10bd0446ba85421ab177462aba" in v_lower:
        return 0.7
    if "minh bùi" in v_lower or "minh bui" in v_lower or "eff592346cac4febbba5d5fef4621ff0" in v_lower:
        return 0.7
    return 0.5


def load_env_local(env_path: Optional[pathlib.Path] = None) -> Dict[str, str]:
    """Parse .env.local file into environment variables."""
    if env_path is None:
        env_path = ROOT / ".env.local"
    env_vars: Dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            env_vars[k] = v
            # Also populate os.environ if not already present
            if k not in os.environ:
                os.environ[k] = v
    return env_vars


class HeyGenClient:
    """Client for HeyGen Audio TTS API."""

    BASE_URL = "https://api.heygen.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "heygen-voice-1-turbo-free",
        language: str = "vi",
        expressiveness_boost: Optional[float] = None,
        speed: float = 1.0,
        voice_id: Optional[str] = None,
    ):
        env_vars = load_env_local()
        self.api_key = api_key or os.environ.get("HEYGEN_API_KEY") or env_vars.get("HEYGEN_API_KEY", "")
        self.default_model = model or os.environ.get("HEYGEN_MODEL") or env_vars.get("HEYGEN_MODEL", "heygen-voice-1-turbo-free")
        self.default_language = language or os.environ.get("HEYGEN_LANGUAGE") or env_vars.get("HEYGEN_LANGUAGE", "vi")
        self.default_expressiveness = (
            float(expressiveness_boost) if expressiveness_boost is not None
            else (float(env_vars["HEYGEN_EXPRESSIVENESS_BOOST"]) if "HEYGEN_EXPRESSIVENESS_BOOST" in env_vars
                  else (float(os.environ["HEYGEN_EXPRESSIVENESS_BOOST"]) if "HEYGEN_EXPRESSIVENESS_BOOST" in os.environ
                  else None))
        )
        self.default_speed = float(
            speed if speed is not None
            else os.environ.get("HEYGEN_SPEED", env_vars.get("HEYGEN_SPEED", 1.0))
        )
        self.default_voice_id = voice_id or os.environ.get("HEYGEN_VOICE_ID") or env_vars.get("HEYGEN_VOICE_ID", "")
        self.total_chars_consumed = 0

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "Thiếu HEYGEN_API_KEY! Vui lòng thêm HEYGEN_API_KEY=... vào file .env.local "
                "hoặc set biến môi trường HEYGEN_API_KEY."
            )
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "WindiStudio-Audiobook/2.5.0",
        }

    def _request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        # The paid service owns this provider account's shared rate budget.
        # Read-only setup remains available; owner demos must not bypass dispatch.
        if method.upper() == "POST" and endpoint.startswith("/v3/models/audio/"):
            try:
                dispatch_only = json.loads((ROOT / "release.json").read_text()).get("heygenDispatchOnly", True)
            except (OSError, ValueError):
                dispatch_only = True
            if dispatch_only:
                raise RuntimeError("HeyGen đang dùng hàng đợi chung của dịch vụ sách. Tạo qua đơn đã xác thực; không chạy TTS trực tiếp ngoài dispatcher.")
        url = f"{self.BASE_URL}{endpoint}"
        payload = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url,
            data=payload,
            headers=self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"HeyGen API Error HTTP {e.code}: {e.reason} - {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"HeyGen Connection Error: {e}") from e

    def get_user_info(self) -> dict:
        """Fetch current account status, workspace details, and credit balance."""
        return self._request("GET", "/v3/users/me")

    def list_voices(
        self,
        language: str = "Vietnamese",
        voice_type: str = "public",
        limit: int = 50,
    ) -> List[dict]:
        """List available public or private voices."""
        params = {"limit": str(limit)}
        if voice_type:
            params["type"] = voice_type
        if language:
            params["language"] = language

        query = urllib.parse.urlencode(params)
        res = self._request("GET", f"/v3/voices?{query}")
        data = res.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("voices", [])
        return res.get("voices", [])

    def find_vietnamese_voice(self, target_name: str = "Đình Mạnh") -> Optional[str]:
        """Auto-detect the best available Vietnamese voice, prioritizing target_name."""
        # 0. If target_name is already a valid HeyGen voice_id, return it directly
        if target_name and len(target_name) == 32 and all(c in "0123456789abcdefABCDEF" for c in target_name):
            return target_name

        # 1. Check HEYGEN_REF_VOICES catalog first
        if target_name:
            for name, info in HEYGEN_REF_VOICES.items():
                if target_name.lower() in name.lower() or target_name.lower() in info.get("heygen_name", "").lower():
                    vid = info["voice_id"]
                    return vid

        if self.default_voice_id:
            return self.default_voice_id

        # 1. Try private clones from account
        try:
            privates = self.list_voices(language="", voice_type="private")
            for p in privates:
                p_name = (p.get("name") or "").lower()
                if target_name.lower() in p_name or "podcast" in p_name:
                    vid = p.get("voice_id")
                    print(f"✓ Sử dụng Voice Clone khớp: {p.get('name')} (ID: {vid})")
                    return vid
            if privates:
                vid = privates[0].get("voice_id")
                print(f"✓ Sử dụng Instant Voice Clone: {privates[0].get('name')} (ID: {vid})")
                return vid
        except Exception:
            pass

        # 2. Try Vietnamese public catalog
        try:
            vi_voices = self.list_voices(language="Vietnamese", voice_type="public")
            if vi_voices:
                vid = vi_voices[0].get("voice_id")
                print(f"✓ Tìm thấy giọng tiếng Việt catalog: {vi_voices[0].get('name')} (ID: {vid})")
                return vid
        except Exception:
            pass

        # 3. Fallback general voice list
        try:
            all_v = self.list_voices(language="", voice_type="public", limit=100)
            for v in all_v:
                lang = (v.get("language") or "").lower()
                if "viet" in lang or "vi" == lang:
                    return v.get("voice_id")
        except Exception:
            pass

        return None

    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        expressiveness_boost: Optional[float] = None,
        speed: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Synthesize text using HeyGen TTS API.

        Endpoint: POST /v3/models/audio/tts
        Returns dict with:
        - audio_url: Remote URL to download WAV
        - duration: Duration in seconds
        - audio_bytes: Raw downloaded audio bytes
        - char_count: Number of characters processed
        """
        target_voice = self.find_vietnamese_voice(voice_id) if voice_id else (self.default_voice_id or self.find_vietnamese_voice())
        if not target_voice:
            raise ValueError(
                "Chưa chọn được voice_id! Vui lòng set HEYGEN_VOICE_ID trong .env.local "
                "hoặc tạo Instant Voice Clone trong tài khoản HeyGen."
            )

        eff_speed = speed if speed is not None else getattr(self, "default_speed", 1.0)
        if expressiveness_boost is not None:
            eff_boost = expressiveness_boost
        elif self.default_expressiveness is not None:
            eff_boost = self.default_expressiveness
        else:
            eff_boost = get_voice_expressiveness(target_voice)

        # Guard: If text exceeds HeyGen's single-request limit (5,000 chars),
        # automatically chunk by sentence, synthesize each, and stitch seamlessly.
        # Keep every character; use the same lossless packing as the dispatcher snapshots.
        if len(text) > 5000:
            from backend.narration_text import split_text_into_safe_chunks
            sub_chunks = split_text_into_safe_chunks(text, max_chars=5000, drop_oversized=False)
            if len(sub_chunks) > 1:
                import numpy as np
                import soundfile as sf
                audio_parts = []
                total_duration = 0.0
                first_url = ""
                t0 = time.time()
                for s_idx, s_txt in enumerate(sub_chunks):
                    sub_res = self.synthesize(
                        text=s_txt,
                        voice_id=voice_id,
                        model=model,
                        language=language,
                        expressiveness_boost=expressiveness_boost,
                        speed=speed,
                    )
                    if not first_url:
                        first_url = sub_res["audio_url"]
                    total_duration += sub_res["duration"]

                    w_audio, w_sr = sf.read(io.BytesIO(sub_res["audio_bytes"]), dtype="float32")
                    if len(w_audio.shape) > 1:
                        w_audio = np.mean(w_audio, axis=1)
                    if w_sr != 24000:
                        import scipy.signal
                        num_samples = int(len(w_audio) * 24000 / w_sr)
                        w_audio = scipy.signal.resample(w_audio, num_samples)

                    # 10ms micro-fade
                    f_len = int(0.010 * 24000)
                    if len(w_audio) > f_len * 2:
                        w_audio[:f_len] *= np.linspace(0.0, 1.0, f_len, dtype=np.float32)
                        w_audio[-f_len:] *= np.linspace(1.0, 0.0, f_len, dtype=np.float32)
                    audio_parts.append(w_audio)


                full_w = np.concatenate(audio_parts) if audio_parts else np.zeros(0, dtype=np.float32)
                out_buf = io.BytesIO()
                sf.write(out_buf, full_w, 24000, format="WAV", subtype="PCM_16")
                merged_bytes = out_buf.getvalue()

                return {
                    "audio_url": first_url,
                    "duration": total_duration,
                    "audio_bytes": merged_bytes,
                    "char_count": len(text),
                    "voice_id": target_voice,
                    "model": model or self.default_model,
                    "language": language or self.default_language,
                    "expressiveness_boost": eff_boost,
                    "speed": eff_speed,
                    "elapsed_seconds": round(time.time() - t0, 3),
                }

        payload = {
            "model": model or self.default_model,
            "voice_id": target_voice,
            "text": text,
            "language": language or self.default_language,
            "expressiveness_boost": eff_boost,
        }
        if eff_speed is not None:
            payload["speed"] = eff_speed

        t0 = time.time()
        res = self._request("POST", "/v3/models/audio/tts", payload)
        elapsed = time.time() - t0

        data = res.get("data", {})
        audio_url = data.get("audio_url")
        duration = data.get("duration", 0.0)

        if not audio_url:
            raise RuntimeError(f"HeyGen API không trả về audio_url: {res}")

        # Download audio bytes
        dl_req = urllib.request.Request(
            audio_url,
            headers={"User-Agent": "WindiStudio-Audiobook/2.5.0"},
        )
        with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
            audio_bytes = dl_resp.read()

        char_len = len(text)
        self.total_chars_consumed += char_len

        return {
            "audio_url": audio_url,
            "duration": duration,
            "audio_bytes": audio_bytes,
            "char_count": char_len,
            "voice_id": target_voice,
            "model": payload["model"],
            "language": payload["language"],
            "expressiveness_boost": payload["expressiveness_boost"],
            "speed": payload.get("speed"),
            "elapsed_seconds": round(elapsed, 3),
        }
