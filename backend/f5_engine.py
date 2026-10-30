"""Private F5 adapter. All weights/reference text are local and verified by the worker.

Inference follows SWivid/F5-TTS's MIT-licensed infer/utils_infer.py at
2f866649b779881af8bd644e76b9a6d95053da29, using sequential bounded chunks.
No external reference pool or online processing at runtime.
"""
import os
from pathlib import Path
from narration_text import plan_f5_prosody, prepare_f5_text

os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')

ALIGNED_REF_TEXTS = {
    'hàng họ bán chạy quá chủ tiệm nói với cậu sau khi người khách kia đi khỏi.':
        'hàng họ bán chạy quá, chủ tiệm nói với cậu, sau khi người khách kia đi khỏi.',
    'sau đó thái sư trần thủ độ ra mắt năm hai không mười ba với ba mươi tư tập.':
        'sau đó, thái sư trần thủ độ ra mắt năm hai không mười ba, với ba mươi tư tập.',
    'tôi cố bình tĩnh vẫn vui như thường, thấy thế trủi cũng hơi yên lòng.':
        'tôi cố bình tĩnh vẫn vui như thường, thấy thế, trủi cũng hơi yên lòng.',
    'trong đầu lão lúc này chỉ toàn là những con số và sính lễ sang trọng.':
        'trong đầu lão lúc này, chỉ toàn là những con số và sính lễ sang trọng.',
    'kinh nghiệm và trải nghiệm với thiết bị đủ lâu, đủ nhiều.':
        'kinh nghiệm, và trải nghiệm, với thiết bị đủ lâu, đủ nhiều.',
    'sau này có gì phát sinh thì có cái lôi ra mà cãi thứ năm là kiểu bịp số điện nước.':
        'sau này có gì phát sinh thì có cái lôi ra mà cãi, thứ năm là kiểu bịp số điện nước.',
    'chị gái bốn mươi ngắt máy rồi bình thản nói, có con rồi là thế đấy.':
        'chị gái bốn mươi ngắt máy, rồi bình thản nói, có con rồi là thế đấy.',
    'nguyên thức thứ ba, đó là xây dựng quan hệ bằng thứ mà mình kiểm soát được.':
        'nguyên thức thứ ba, đó là xây dựng quan hệ, bằng thứ mà mình kiểm soát được.',
}


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


def _tighten_mid_sentence_silences(audio, keep_ms=85, min_detect_ms=180, sr=24000):
    import numpy as np
    win = int(0.01 * sr)
    n_wins = len(audio) // win
    if n_wins < 10:
        return audio
    frames = audio[:n_wins * win].reshape(n_wins, win)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    is_silent = rms < (10 ** (-38.0 / 20.0))
    min_wins = min_detect_ms // 10
    keep_wins = keep_ms // 10
    xfade = int(0.010 * sr)
    out_parts = []
    cur_idx = 0
    i = 0
    while i < n_wins:
        if is_silent[i]:
            j = i
            while j < n_wins and is_silent[j]:
                j += 1
            if i > 4 and j < n_wins - 4 and (j - i) >= min_wins:
                left_keep = (keep_wins // 2) * win
                right_keep = (keep_wins - keep_wins // 2) * win
                cut_start = i * win + left_keep
                cut_end = j * win - right_keep
                if cut_end > cut_start:
                    seg = audio[cur_idx:cut_start].copy()
                    if xfade > 0 and len(seg) > xfade:
                        seg[-xfade:] *= np.linspace(1.0, 0.0, xfade, dtype=np.float32)
                    out_parts.append(seg)
                    cur_idx = cut_end
            i = j
        else:
            i += 1
    tail = audio[cur_idx:].copy()
    if out_parts and xfade > 0 and len(tail) > xfade:
        tail[:xfade] *= np.linspace(0.0, 1.0, xfade, dtype=np.float32)
    out_parts.append(tail)
    return np.concatenate(out_parts)


def export_mp3(audio, output_path, sr=24000, bitrate='192k'):
    """Export float32 waveform [-1, 1] directly to `.mp3` at `192k` bitrate using pydub."""
    import numpy as np
    from pydub import AudioSegment

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pcm16 = (np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0) * 32767.0).astype('<i2').tobytes()
    seg = AudioSegment(data=pcm16, sample_width=2, frame_rate=sr, channels=1).set_frame_rate(44100)
    tmp_path = out_path.with_name(out_path.stem + '.partial.mp3')
    seg.export(str(tmp_path), format='mp3', bitrate=bitrate)
    tmp_path.replace(out_path)
    return out_path


class F5Engine:
    def __init__(self, root):
        import torch
        import f5_tts.model.cfm as cfm
        from vocos import Vocos

        self.root = Path(root)
        torch.set_num_threads(min(8, os.cpu_count() or 4))
        self.device = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')
        self.dtype = torch.float16 if self.device in ('mps', 'cuda') else torch.float32
        self.precision = 'fp16' if self.dtype == torch.float16 else 'fp32'
        self.nfe = 24
        if not getattr(cfm, '_windi_fp32_epss', False):
            orig_epss = cfm.get_epss_timesteps
            cfm.get_epss_timesteps = lambda n, device, dtype: orig_epss(n, device, torch.float32).to(dtype)
            cfm._windi_fp32_epss = True
        self.vocoder = Vocos.from_hparams(str(self.root / 'vocos/config.yaml'))
        self.vocoder.load_state_dict(torch.load(self.root / 'vocos/pytorch_model.bin', map_location='cpu', weights_only=True))
        self.vocoder.eval()
        self.loaded_voice = None
        available = self.list_preset_voices()
        if not available:
            raise ValueError('Gói giọng riêng chưa sẵn sàng. Hãy cài lại gói giọng Pro.')
        self._load_voice(available[0][1])

    def _voice_dir(self, voice):
        if voice == 'voice-001' and (self.root / 'model.pt').is_file():
            return self.root
        cand = self.root / 'voices' / voice
        if (cand / 'model.pt').is_file():
            return cand
        if voice == 'voice-002' and (self.root / 'model_v2.pt').is_file():
            return self.root
        raise ValueError('Giọng riêng không hợp lệ.')

    def _load_voice(self, voice):
        if self.loaded_voice == voice:
            return
        import numpy as np
        import soundfile as sf
        import torch
        import torch.nn.functional as F
        from f5_tts.model import CFM, DiT
        from f5_tts.model.utils import get_tokenizer
        from pydub import AudioSegment, silence

        vdir = self._voice_dir(voice)
        vocab, size = get_tokenizer(str(vdir / 'vocab.txt'), 'custom')
        with torch.device('cpu'):
            transformer = DiT(dim=1024, depth=22, heads=16, ff_mult=2,
                              text_dim=512, conv_layers=4, text_mask_padding=False,
                              pe_attn_head=1, attn_backend='torch', attn_mask_enabled=False,
                              text_num_embeds=size, mel_dim=100)
            if self.dtype == torch.float16:
                transformer = transformer.half()
            model = CFM(
                transformer=transformer,
                mel_spec_kwargs=dict(n_fft=1024, hop_length=256, win_length=1024,
                                     n_mel_channels=100, target_sample_rate=24000, mel_spec_type='vocos'),
                odeint_kwargs=dict(method='euler'), vocab_char_map=vocab)
        checkpoint = torch.load(vdir / 'model.pt', map_location='cpu', weights_only=True)
        state = {k.removeprefix('ema_model.'): v for k, v in checkpoint['ema_model_state_dict'].items()
                 if k not in ('initted', 'step')}
        for key in ('mel_spec.mel_stft.mel_scale.fb', 'mel_spec.mel_stft.spectrogram.window'):
            state.pop(key, None)
        model.load_state_dict(state)
        del state, checkpoint
        if self.dtype == torch.float16:
            scale_qk = 64 ** -0.25
            for block in model.transformer.transformer_blocks:
                attn = block.attn
                qkv = torch.nn.Linear(attn.dim, attn.inner_dim * 3, dtype=torch.float16)
                qkv.weight.data.copy_(torch.cat([attn.to_q.weight.data * scale_qk, attn.to_k.weight.data * scale_qk, attn.to_v.weight.data], dim=0))
                qkv.bias.data.copy_(torch.cat([attn.to_q.bias.data * scale_qk, attn.to_k.bias.data * scale_qk, attn.to_v.bias.data], dim=0))
                attn.to_qkv = qkv
                del attn.to_q, attn.to_k, attn.to_v
        model.transformer = model.transformer.eval().to(self.device, dtype=self.dtype)
        model.mel_spec.cpu()
        if self.dtype == torch.float16:
            rope_cache = {}
            orig_rope = model.transformer.rotary_embed.forward_from_seq_len
            def cached_rope(seq_len):
                if seq_len not in rope_cache:
                    freqs, _ = orig_rope(seq_len)
                    f = freqs.to(dtype=torch.float16)
                    rope_cache[seq_len] = (f.cos().unsqueeze(0).unsqueeze(0), f.sin().unsqueeze(0).unsqueeze(0))
                return rope_cache[seq_len]
            model.transformer.rotary_embed.forward_from_seq_len = cached_rope
            orig_sdpa = F.scaled_dot_product_attention
            def fast_attn_call(proc_self, attn, x, mask=None, rope=None):
                B, N, _ = x.shape
                qkv = attn.to_qkv(x).view(B, N, 3, attn.heads, 64)
                query, key, value = qkv[:, :, 0].transpose(1, 2), qkv[:, :, 1].transpose(1, 2), qkv[:, :, 2].transpose(1, 2)
                if rope is not None:
                    cos, sin = rope
                    q0 = query[:, :1]
                    query[:, :1] = q0 * cos + torch.stack((-q0[..., 1::2], q0[..., ::2]), dim=-1).reshape_as(q0) * sin
                    k0 = key[:, :1]
                    key[:, :1] = k0 * cos + torch.stack((-k0[..., 1::2], k0[..., ::2]), dim=-1).reshape_as(k0) * sin
                out = orig_sdpa(query, key, value, dropout_p=0.0, is_causal=False, scale=1.0)
                return attn.to_out[0](out.transpose(1, 2).reshape(B, N, attn.inner_dim))
            for block in model.transformer.transformer_blocks:
                block.attn.processor = fast_attn_call.__get__(block.attn.processor, type(block.attn.processor))
        self.model = model
        raw, rate = sf.read(vdir / 'ref_audio.wav', dtype='float32')
        if rate != 24000 or raw.ndim != 1:
            raise ValueError('Gói giọng riêng bị lỗi định dạng. Hãy cài lại gói giọng Pro.')
        aseg = AudioSegment(data=(np.clip(raw, -1, 1) * 32767).astype('<i2').tobytes(), sample_width=2, frame_rate=24000, channels=1)
        start = silence.detect_leading_silence(aseg, silence_threshold=-42)
        end = silence.detect_leading_silence(aseg.reverse(), silence_threshold=-42)
        aseg = aseg[start:len(aseg) - end if end else len(aseg)] + AudioSegment.silent(duration=50, frame_rate=24000)
        audio = torch.tensor(np.array(aseg.get_array_of_samples(), dtype='float32') / 32768).unsqueeze(0)
        rms = audio.square().mean().sqrt().item()
        if rms < 1e-5:
            raise ValueError('Gói giọng riêng bị thiếu mẫu đọc. Hãy cài lại gói giọng Pro.')
        self.gain = min(rms / 0.1, 1.0)
        if rms < 0.1:
            audio = audio * 0.1 / rms
        self.ref_frames = audio.shape[-1] // 256
        with torch.inference_mode():
            self.cond = self.model.mel_spec(audio).permute(0, 2, 1).to(self.device, dtype=self.dtype)
        raw_ref = (vdir / 'ref_text.txt').read_text(encoding='utf-8').strip()
        if not raw_ref:
            raise ValueError('Gói giọng riêng chưa đầy đủ. Hãy cài lại gói giọng Pro.')
        raw_ref = ALIGNED_REF_TEXTS.get(raw_ref, raw_ref)
        self.ref_text = raw_ref if raw_ref.endswith('.') else raw_ref + '.'
        self.ref_text += ' '
        self.loaded_voice = voice

    def list_preset_voices(self):
        from model_manager import voices
        return [(v['label'], v['id']) for v in voices('f5-private', root=self.root)]

    def infer(self, text, voice, **kwargs):
        import numpy as np
        import torch
        from f5_tts.model.utils import convert_char_to_pinyin

        valid = {v for _, v in self.list_preset_voices()}
        if voice not in valid:
            raise ValueError('Giọng riêng không hợp lệ.')
        self._load_voice(voice)

        units = plan_f5_prosody(text)
        if not units:
            fallback = prepare_f5_text(text)
            if fallback:
                units = [dict(text=fallback, pause=0.45, pace=0.96, author_comma=(',' in fallback[:-1]))]

        output = []
        ref_bytes = len(self.ref_text.encode('utf-8'))
        steps = int(kwargs.get('steps', self.nfe))

        for idx, u in enumerate(units):
            chunk = u['text'].strip()
            if not chunk:
                continue
            c_bytes = len(chunk.encode('utf-8'))
            internal_commas = chunk[:-1].count(',')
            pace = 0.35 if c_bytes < 12 else (0.78 if c_bytes < 28 else u.get('pace', 0.96))
            gen_frames = int(self.ref_frames / ref_bytes * c_bytes / pace) + internal_commas * 18 + 12
            duration = self.ref_frames + gen_frames

            with torch.inference_mode():
                mel, trajectory = self.model.sample(
                    cond=self.cond,
                    text=convert_char_to_pinyin([self.ref_text + chunk]),
                    duration=duration,
                    steps=steps,
                    cfg_strength=2.0,
                    sway_sampling_coef=-1.0,
                    seed=42,
                )
                del trajectory
                wave = self.vocoder.decode(mel[:, self.ref_frames:, :].permute(0, 2, 1).float().cpu())
                audio = _trim_and_shape(wave.squeeze().numpy() * self.gain, sr=24000)
                if not u.get('author_comma', False):
                    audio = _tighten_mid_sentence_silences(audio, keep_ms=85, min_detect_ms=180, sr=24000)

            if len(audio):
                output.append(audio)
                pause_s = u.get('pause', 0.46) if idx < len(units) - 1 else 0.14
                if pause_s > 0:
                    output.append(np.zeros(int(pause_s * 24000), dtype='float32'))

        return np.concatenate(output) if output else np.array([], dtype='float32')

    def synthesize_to_mp3(self, text, voice, output_mp3_path, bitrate='192k', **kwargs):
        """Synthesize and export directly to `.mp3` (`192k`)."""
        audio = self.infer(text, voice=voice, **kwargs)
        return export_mp3(audio, output_mp3_path, sr=24000, bitrate=bitrate)
