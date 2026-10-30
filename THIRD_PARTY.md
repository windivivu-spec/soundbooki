# Third-party components

This project is a local development MVP. Do not redistribute its environment/model without preserving component notices and checking the final installer contents.

| Component | Version / revision | License / source |
|---|---|---|
| VieNeu SDK | 3.8.1 | Apache-2.0, [upstream](https://github.com/pnnbao97/VieNeu-TTS), license in `licenses/VieNeu-APACHE-2.0.txt` |
| VieNeu v3 Nano, preset-only | aba295eb96a6fa6003ebe417cc1f2802a7adc1dc | Apache-2.0, [model card](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Nano); six asset hashes in `backend/models.json` |
| VieNeu v3 Turbo FP32, preset-only | 61b85e3d937fbbacb387714180e8182823512523 | Apache-2.0, [model card](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo); hashes in `backend/models-turbo.json` |
| OpenMOSS Nano ONNX codec decoder | ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae | Apache-2.0, [upstream package](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX); only decoder graphs/weights |
| soxr | 1.1.0 | LGPL-2.1-or-later, package notices retained; used for background music resampling |
| KittenTTS Mini 80M + voices | c02725660cea441db4c383af69f1f26f5cd00947 | Apache-2.0, [model](https://huggingface.co/KittenML/kitten-tts-mini-0.8); `backend/models-kitten.json` |
| Local Kitten ONNX adapter | based on upstream 0.8.1 | Apache-2.0; notice `licenses/KittenTTS-LICENSE.txt`; no SDK or lazy model download |
| phonemizer | 3.4.0 | GPL-3.0; full notice in installed dist-info |
| espeakng-loader / bundled eSpeak NG | 0.2.4 | Loader license is not declared in the installed wheel metadata; bundled eSpeak NG is GPL-3.0; confirm notices/source obligations before redistribution |
| sea-g2p | 0.10.0 | Apache-2.0; installed dist-info retains license |
| ONNX Runtime | 1.31.0 | MIT; installed dist-info retains license |
| NumPy | 2.5.4 | BSD-3-Clause plus bundled-library notices; installed dist-info retains licenses |
| SoundFile / libsndfile | 0.14.0 / wheel-bundled | SoundFile BSD-3-Clause; libsndfile LGPL notices retained in wheel |
| Python | 3.12.13 | PSF and bundled-library notices, from uv-managed Python on the development machine |
| AppKit, WebKit, Vision, PDFKit, AVFoundation | macOS system frameworks | Apple platform SDK/runtime terms; not separately copied |

Base Python dependency versions are pinned in `requirements.lock.txt`. Their dist-info notices remain in `.runtime`. The SDK installs web/audio-analysis dependencies that are not launched by this app. No Tencent translation model, Whisper or video pipeline is installed. Optional F5 uses the separate runtime below.

## Private F5 voice (optional local setup)

- F5-TTS 1.1.22 source revision `2f866649b779881af8bd644e76b9a6d95053da29`: MIT, notice in `licenses/F5-TTS-MIT.txt`. The local inference adapter follows upstream inference preparation/sampling, with sequential chunks and CPU FFT/vocoder for Metal compatibility.
- Private voice-001 fine-tune uses `hynt/F5-TTS-Vietnamese-ViVoice` revision `5c14cdd4e3f62b69e75140558bea2b2e293ee8f1`, CC BY-NC-SA 4.0, **non-commercial**. It does not inherit the permissive license of the F5 code. Private recordings/reference are local-only user assets and are not authorized for publication.
- Vocos mel-24khz: `charactr/vocos-mel-24khz` revision `0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21`; upstream Vocos code/model MIT. Resource hashes in `backend/models-f5-private.json`.
- PyTorch/torchaudio 2.6.0, Vocos 0.1.0 and transitive packages are isolated in `.runtime-f5`; versions in `requirements-f5.lock.txt`, license notices retained in dist-info. Training-related imports in upstream do not launch trainers, telemetry or downloads; the engine sets offline environment and denies socket connections before importing dependencies.

The current SDK/model Nano API and model card differ on some preset-count/cloning details across revisions. This app obtains the voice catalog from the installed SDK's preset file and uses only its available presets; it exposes no cloning or lazy cloning downloads. The model is preview quality, not an accuracy guarantee.

## User-provided music demos

`Warm Reflections.mp3` and `Warm Reflections (1).mp3` were explicitly supplied by the user for local background-music demos. Their converted local assets are described in `assets/music/demo-catalog.json`; original source SHA-256 values are retained there. No general redistribution license is inferred. They are not published or uploaded, and their generated assets/sample exports are ignored by Git. The three procedural loops are created by `scripts/music.py` without third-party recordings.

Turbo preset catalog is read from the pinned installed SDK 3.8.1: 25 presets on this machine (the upstream model card may document an older count). Turbo requires 520,281,804 bytes for the nine preset-only ONNX/codec resources. These are optional, separate downloads; Nano remains available.

## Previous flat page-turn component (Build 17, inactive)

- [rayhankhilji/flipbook](https://github.com/rayhankhilji/flipbook), commit `94c8724245e768e9f597c3b1859a300ef061797e`, MIT © 2026 Rayhan Khilji. Full notice: `licenses/Flipbook-MIT.txt`.
- `native/PageTurn/FlipbookTurnView.swift` adapts the upstream `Flipbook/Features/Reader/PageTurn/PageTurnNSView.swift`: two-sided transform layer, spine hinge, front/back self-shading, cast shadow, and spring constants (mass 1, damping 32, stiffness 260).
- This historical source is excluded from the build. Only its page-turn component was adapted; no PDF session, design system, storage or AI/provider code was imported.

## GulLabs curved page turn (Build 18)

- [gul-labs/flipbook](https://github.com/gul-labs/flipbook), core 3.2.2 at commit `3fb7192c02ecca559d67192d15a1479fd7cf3af8`, MPL-2.0. Upstream StPageFlip/react-pageflip MIT notices are preserved.
- Unmodified source: `ui/vendor/gul-flipbook/source/`; generated standalone HTML engine and CSS alongside it. The adapter in `ui/flipbook-turn.js` calls the public API only. No React runtime is included.
- Full license, notice and upstream copyrights: `licenses/GulLabs-Flipbook/`. The local app also includes these and the corresponding engine source under Resources/Licenses/GulLabs-Flipbook. Recipients can obtain the source there or at the pinned GitHub revision above, under MPL-2.0.
- This replaces the active flat Core Animation turn from Build 17. `native/PageTurn/FlipbookTurnView.swift` is retained as historical source, excluded from the build; its MIT notice remains. No engine source has been modified.
