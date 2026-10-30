#!/usr/bin/env python3
"""Graphify generator for Soundbooki Mac, Android and cloud architecture.

Generates:
1. graphify-out/graph.json (Standard GraphRAG JSON format with nodes, edges, clusters)
2. graphify-out/GRAPH_REPORT.md (Human & AI Agent comprehensive architecture report with Mermaid diagrams)
3. graphify-out/graph.html (Standalone interactive visual graph using Vis.js)
"""

import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "graphify-out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Define Nodes
NODES = [
    # Community 0: Text Ingestion & OCR Proofreading
    {
        "id": "raw_input_text",
        "label": "Raw Book / Text Input",
        "community": "Text Ingestion",
        "community_id": 0,
        "type": "data",
        "source_file": "cloud/modal_studio/synthesize_book_parallel.py",
        "doc": "Original book text from scan, PDF, EPUB, or TXT file"
    },
    {
        "id": "proofread_audiobook_text",
        "label": "proofread_audiobook_text()",
        "community": "Text Ingestion",
        "community_id": 0,
        "type": "function",
        "source_file": "backend/narration_text.py",
        "source_location": "L35",
        "doc": "Deterministic regex normalizer: all-caps lowercasing, Roman numerals conversion, OCR scan artifact & digit typo repair"
    },
    {
        "id": "qwen_proofread_endpoint",
        "label": "Qwen OCR Proofreader Endpoint (/proofread)",
        "community": "Text Ingestion",
        "community_id": 0,
        "type": "api",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L880",
        "doc": "Optional Qwen2.5-7B contextual OCR checker returning JSON typo corrections without rewriting"
    },

    # Community 1: Prosody Planning & Breath Segmentation
    {
        "id": "plan_f5_prosody",
        "label": "plan_f5_prosody()",
        "community": "Prosody Planning",
        "community_id": 1,
        "type": "function",
        "source_file": "backend/narration_text.py",
        "source_location": "L225",
        "doc": "Syntactic breath unit partitioner: inserts discourse pivots, 3.0s chapter breaks, heading and punctuation-aware pauses"
    },
    {
        "id": "chunk_units_for_workers",
        "label": "chunk_units_for_workers()",
        "community": "Prosody Planning",
        "community_id": 1,
        "type": "function",
        "source_file": "cloud/modal_studio/synthesize_book_parallel.py",
        "source_location": "L120",
        "doc": "Balances prosodic units into equal-sized batches across 3-4 concurrent GPU workers"
    },

    # Community 2: Parallel Multi-GPU Orchestration
    {
        "id": "synthesize_book_parallel",
        "label": "synthesize_book_parallel() [GOD NODE]",
        "community": "Parallel Orchestration",
        "community_id": 2,
        "type": "orchestrator",
        "source_file": "cloud/modal_studio/synthesize_book_parallel.py",
        "source_location": "L130",
        "doc": "Master audiobook production runner: dispatches concurrent threads, collects audio parts, applies QA gates"
    },
    {
        "id": "thread_pool_workers",
        "label": "ThreadPoolExecutor (3-4 Workers)",
        "community": "Parallel Orchestration",
        "community_id": 2,
        "type": "concurrency",
        "source_file": "cloud/modal_studio/synthesize_book_parallel.py",
        "source_location": "L165",
        "doc": "Dispatches HTTP batch requests concurrently to Modal serverless auto-scaling GPU containers"
    },
    {
        "id": "call_modal_batch_worker",
        "label": "call_modal_batch_worker()",
        "community": "Parallel Orchestration",
        "community_id": 2,
        "type": "network",
        "source_file": "cloud/modal_studio/synthesize_book_parallel.py",
        "source_location": "L85",
        "doc": "Worker client that submits batch payloads, receives base64 WAV, and decodes numpy audio"
    },

    # Community 3: Cloud GPU Serverless Engine (Modal)
    {
        "id": "modal_windi_studio_engine",
        "label": "WindiStudioEngine [GOD NODE]",
        "community": "Modal Cloud Engine",
        "community_id": 3,
        "type": "class",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L325",
        "doc": "Serverless GPU Container (NVIDIA A10G / L4): hosts F5-TTS, Vocos vocoder, Qwen2.5-7B, and voice weights"
    },
    {
        "id": "modal_batch_endpoint",
        "label": "FastAPI Batch Endpoint (/batch)",
        "community": "Modal Cloud Engine",
        "community_id": 3,
        "type": "api",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L750",
        "doc": "High-throughput endpoint: accepts multiple breath units, runs 1-pass Qwen AI direction, and batches DiT inference"
    },
    {
        "id": "qwen_ai_director",
        "label": "Qwen2.5-7B AI Context Director",
        "community": "Modal Cloud Engine",
        "community_id": 3,
        "type": "model",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L465",
        "doc": "Analyzes emotional tone, pace factors (0.96-1.06), and inter-unit pauses in a single forward pass (~1.5s)"
    },

    # Community 4: F5-TTS Acoustic Synthesis & Vocoding
    {
        "id": "f5_tts_dit",
        "label": "F5-TTS Diffusion Transformer (DiT)",
        "community": "Acoustic Synthesis",
        "community_id": 4,
        "type": "model",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L770",
        "doc": "Option 2 Standard: 22 sampling steps, sway_sampling_coef=-1.0, CFG 2.2, trained on Vietnamese speech"
    },
    {
        "id": "vocos_vocoder",
        "label": "Vocos 24kHz Neural Vocoder",
        "community": "Acoustic Synthesis",
        "community_id": 4,
        "type": "model",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L390",
        "doc": "High-fidelity neural vocoder converting predicted mel-spectrograms into crystal-clear 24kHz waveforms"
    },
    {
        "id": "voice_volume_manifests",
        "label": "Voice Volume (windi-studio-voices)",
        "community": "Acoustic Synthesis",
        "community_id": 4,
        "type": "storage",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L25",
        "doc": "Modal Persistent Volume storing proprietary checkpoints: voice-003, voice-007, voice-008, voice-002, voice-004, voice-006"
    },

    # Community 5: Audio Mastering & QA Gates
    {
        "id": "silence_qa_gate",
        "label": "trim_excessive_silence() (Silence Gate)",
        "community": "Audio Mastering & QA",
        "community_id": 5,
        "type": "function",
        "source_file": "cloud/modal_studio/app.py",
        "source_location": "L284",
        "doc": "Scans RMS audio energy: trims any dead air > 4.5s down to 1.0s with 15ms sine-squared crossfades, preserving 3.0s chapter breaks"
    },
    {
        "id": "master_wav_export",
        "label": "Master Studio WAV (PCM 16-bit 24kHz)",
        "community": "Audio Mastering & QA",
        "community_id": 5,
        "type": "artifact",
        "source_file": "training/f5/artifacts/modal_audiobook_parallel.wav",
        "doc": "Uncompressed archival master audio"
    },
    {
        "id": "master_mp3_128k_export",
        "label": "Customer MP3 128kbps (Lightweight)",
        "community": "Audio Mastering & QA",
        "community_id": 5,
        "type": "artifact",
        "source_file": "training/f5/artifacts/modal_audiobook_parallel.mp3",
        "doc": "Fast-download release format with ID3 tags: Title, Author, Album, Year"
    },

    # Community 6: HeyGen Turbo Cloud TTS
    {
        "id": "heygen_client",
        "label": "HeyGenClient",
        "community": "HeyGen Cloud TTS",
        "community_id": 6,
        "type": "class",
        "source_file": "cloud/heygen_studio/heygen_client.py",
        "source_location": "L45",
        "doc": "HeyGen v3 API Client: manages authentication, voice listing, and audio download"
    },
    {
        "id": "heygen_tts_endpoint",
        "label": "HeyGen TTS API (/v3/models/audio/tts)",
        "community": "HeyGen Cloud TTS",
        "community_id": 6,
        "type": "api",
        "source_file": "cloud/heygen_studio/heygen_client.py",
        "source_location": "L150",
        "doc": "HeyGen Turbo endpoint: model=heygen-voice-1-turbo, language=vi, expressiveness_boost=0.4"
    },
    {
        "id": "synthesize_book_heygen",
        "label": "synthesize_book_heygen.py",
        "community": "HeyGen Cloud TTS",
        "community_id": 6,
        "type": "orchestrator",
        "source_file": "cloud/heygen_studio/synthesize_book_heygen.py",
        "source_location": "L85",
        "doc": "HeyGen Turbo audiobook runner: handles 5,000 char budget, proofreading, silence QA, and 128k MP3 export"
    }
]

# 2. Define Edges (Relationships)
EDGES = [
    {"source": "raw_input_text", "target": "proofread_audiobook_text", "relation": "cleaned_by", "confidence": "EXTRACTED"},
    {"source": "raw_input_text", "target": "qwen_proofread_endpoint", "relation": "optional_ai_clean", "confidence": "INFERRED"},
    {"source": "proofread_audiobook_text", "target": "plan_f5_prosody", "relation": "feeds_into", "confidence": "EXTRACTED"},
    {"source": "plan_f5_prosody", "target": "chunk_units_for_workers", "relation": "partitioned_by", "confidence": "EXTRACTED"},
    {"source": "chunk_units_for_workers", "target": "synthesize_book_parallel", "relation": "scheduled_in", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_parallel", "target": "thread_pool_workers", "relation": "spawns", "confidence": "EXTRACTED"},
    {"source": "thread_pool_workers", "target": "call_modal_batch_worker", "relation": "executes", "confidence": "EXTRACTED"},
    {"source": "call_modal_batch_worker", "target": "modal_batch_endpoint", "relation": "calls_http_post", "confidence": "EXTRACTED"},
    {"source": "modal_batch_endpoint", "target": "modal_windi_studio_engine", "relation": "handled_by", "confidence": "EXTRACTED"},
    {"source": "modal_windi_studio_engine", "target": "qwen_ai_director", "relation": "analyzes_prosody_with", "confidence": "EXTRACTED"},
    {"source": "modal_windi_studio_engine", "target": "f5_tts_dit", "relation": "generates_mel_with", "confidence": "EXTRACTED"},
    {"source": "modal_windi_studio_engine", "target": "voice_volume_manifests", "relation": "loads_weights_from", "confidence": "EXTRACTED"},
    {"source": "f5_tts_dit", "target": "vocos_vocoder", "relation": "vocodes_mel_to_wave", "confidence": "EXTRACTED"},
    {"source": "vocos_vocoder", "target": "silence_qa_gate", "relation": "verified_by_level1_gate", "confidence": "EXTRACTED"},
    {"source": "silence_qa_gate", "target": "call_modal_batch_worker", "relation": "returns_batch_wave", "confidence": "EXTRACTED"},
    {"source": "call_modal_batch_worker", "target": "synthesize_book_parallel", "relation": "assembles_tracks", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_parallel", "target": "silence_qa_gate", "relation": "verified_by_master_gate", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_parallel", "target": "master_wav_export", "relation": "writes_wav", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_parallel", "target": "master_mp3_128k_export", "relation": "encodes_ffmpeg_128k", "confidence": "EXTRACTED"},
    {"source": "plan_f5_prosody", "target": "synthesize_book_heygen", "relation": "schedules_units_for", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_heygen", "target": "heygen_client", "relation": "calls", "confidence": "EXTRACTED"},
    {"source": "heygen_client", "target": "heygen_tts_endpoint", "relation": "posts_turbo_request", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_heygen", "target": "silence_qa_gate", "relation": "verified_by_gate", "confidence": "EXTRACTED"},
    {"source": "synthesize_book_heygen", "target": "master_mp3_128k_export", "relation": "exports_mp3_128k", "confidence": "EXTRACTED"}
]

# Customer-facing routes verified in source; graph navigation is not activation proof.
APP_DISCOVERY = [
    ("app_import", "Import & inspect original text", "backend/worker.py", "EPUB/PDF/image import; editable segments retain originalText."),
    ("app_reader", "Read alongside Lite narration", "ui/reader-lite.js", "Explicit local listening, source-page reading, chapter navigation and automatic saved reading position."),
    ("app_voices", "Local free voices & explicit Pro trials", "backend/book_pricing.py", "Lite Vietnamese / Kitten English local; Pro from 10000 VND/book; 10 trials per Mac, at most 4000 characters each. Cloud activation is separate."),
    ("app_export", "Music & selected-range export", "backend/core.py", "Persist music settings; selected audio WAV/M4A and web package export. Publication is separate."),
    ("app_launch", "One five-book launch combo per Mac", "backend/launch_offer.py", "50000 VND / 5 books; buy and redeem before 2026-11-02 00:00 +07. Separate server activation required."),
    ("app_welcome_audio", "Local calm welcome audio", "native/Welcome.swift", "Owner-provided greeting once at 80 percent plus Piano podcast Bài 01 at 40 percent; fixed asset paths, mute, fade and stop on close; local-only asset authorization."),
    ("app_walkthrough", "Five-page feature discovery", "ui/walkthrough.js", "Five concise illustrated benefit pages; swipe/dot pager, reduced-motion-aware entrance, first-empty-library introduction and manual reopen. Final explicit CTA opens import. Navigation never starts cloud, payment or generation.")
]
NODES.extend(dict(id=id, label=label, source_file=file, doc=doc,
                  community="Mac App Discovery", community_id=7, type="feature")
             for id, label, file, doc in APP_DISCOVERY)
EDGES.extend(dict(source="app_walkthrough", target=id, relation="introduces_verified_route", confidence="SOURCE_REVIEWED")
             for id, _, _, _ in APP_DISCOVERY if id != "app_walkthrough")

# Standalone Vietnamese landing page. Details below are source-reviewed against
# landing-page/index.html and landing-page/hero-animation.js.
NODES.append({
    "id": "landing_page",
    "label": "Soundbooki Vietnamese Landing Page",
    "community": "Mac App Discovery",
    "community_id": 7,
    "type": "website",
    "source_file": "landing-page/index.html",
    "doc": "Standalone local-first Vietnamese product site with five feature highlights, explicit Pro voice samples, Mac download information, and an audio-synchronized welcome hero. The welcome plays Piano Podcast track 01 after an explicit user action; narration starts after a 1-second lead-in at 0.95x. Twelve sparse, irregularly distributed floating score symbols follow the timed words. Piano continues to 60 seconds and fades out over 3 seconds."
})
EDGES.extend([
    {"source": "landing_page", "target": "app_walkthrough", "relation": "presents_five_app_features", "confidence": "SOURCE_REVIEWED"},
    {"source": "landing_page", "target": "app_welcome_audio", "relation": "shares_piano_podcast_track_01", "confidence": "SOURCE_REVIEWED"},
    {"source": "landing_page", "target": "app_voices", "relation": "offers_explicit_pro_voice_samples", "confidence": "SOURCE_REVIEWED"}
])
NODES.append({
    "id": "landing_loading",
    "label": "Loading: matte paper book opens to notes",
    "community": "Mac App Discovery",
    "community_id": 7,
    "type": "component",
    "source_file": "landing-page/hero-animation.js",
    "doc": "Opening uses an articulated 3D book: solid cover shells, staggered page layers and curved sheets rotate around a shared spine over 2.35 seconds. The final contour follows the original curved book; paper is warm ivory and covers are matte charcoal, with almost no specular reflection. SVG is a static fallback. Six faint notes float around the backdrop edges (four on mobile/save-data/low-core); layered radial light adds depth. Seven phrases start around 2.4 seconds with a quick, gentle visibility fade and become rising notes over 3.6-3.96-second curved flights; base upward travel is capped at 330px or 78 percent of book height and constrained to the viewport. Repeatable reload, hidden preparation/two paint frames, tab visibility pause, stable reveal layout, Skip/Escape/replay and reduced-motion bypass remain. Hero narration/cues remain separate."
})
EDGES.append({"source": "landing_page", "target": "landing_loading", "relation": "opens_with_lightweight_book_prelude", "confidence": "SOURCE_REVIEWED"})
NODES.append({
    "id": "landing_book_model", "label": "Lightweight articulated book geometry",
    "community": "Mac App Discovery", "community_id": 7, "type": "renderer",
    "source_file": "landing-page/assets/vendor/book-opening.js",
    "doc": "Self-contained WebGL book geometry: cover/page shells share a 3D spine, staggered hinges and curved surfaces. Static GPU buffers and simple lighting; render only on GSAP opening updates or resize/replay. No Three.js/model/texture download. Mobile uses fewer subdivisions, DPR <=1.2 and <=30 draws/sec; desktop DPR <=1.35. Local SVG fallback handles unavailable/lost contexts."
})
EDGES.append({"source": "landing_loading", "target": "landing_book_model", "relation": "opens_cover_and_pages_with", "confidence": "SOURCE_REVIEWED"})

# Android baseline accepted for later optimization on 2026-10-22.
# Evidence belongs in QA.md; graph edges describe code, not deployment status.
ANDROID_JAVA = "android/app/src/main/java/studio/windi/soundbooki/"
ANDROID_DISCOVERY = [
    ("android_ui", "Android: import → edit → listen", ANDROID_JAVA + "MainActivity.java", "Native Vietnamese UI synchronized with Mac design system, large >=48-54dp touch controls, hero card, sticky glass player dock; Android 13+ ARM64 test app."),
    ("android_theme", "Mac-synchronized theme, fonts & vector icons", ANDROID_JAVA + "UiTheme.java", "Shared light/dark color tokens, local SF Pro Rounded & SVN Nexa typography, custom vector icons, ambient glow canvas, 3D book hero illustration and animated equalizer art."),
    ("android_reader", "Reader themes including pure black", ANDROID_JAVA + "ReaderDialog.java", "Per-book reading palette includes system, paper, white, sepia, sage, night and pure #000000 black. The black option applies only to the reading page; app-wide dark blue surfaces remain unchanged."),
    ("android_walkthrough", "Five-step mobile walkthrough", ANDROID_JAVA + "WalkthroughDialog.java", "Phone-tailored 5-step discovery with vector scene artwork, swipe/dot pager, reduced-motion awareness, large thumb-zone CTAs and mute toggle. Never starts cloud, payment or synthesis during navigation."),
    ("android_welcome_audio", "Local welcome greeting, BGM & chime SFX", ANDROID_JAVA + "WelcomeAudioPlayer.java", "Plays owner greeting welcome.wav once at 80% + Piano podcast Bài 01 at 40% with 1.8s fade-in + synthesized harmonic chimes on step transitions; mute/fade-out on close."),
    ("android_import", "EPUB / text PDF / TXT + open, share & resume", ANDROID_JAVA + "BookImporter.java", "Imports from the system picker or Android Open with (VIEW) / Share (SEND) intents for PDF and EPUB. MIME type fallback handles providers without an extension; preserves source file and originalText with atomic PDF-page/EPUB-spine checkpoints. Source headings only; no scan OCR."),
    ("android_store", "Original text, cache & saved position", ANDROID_JAVA + "BookStore.java", "Atomic persistence; cache bound to text, voice and engine revision. Edits/voice changes stop stale playback; speed is player-only."),
    ("android_chunks", "Verbatim text partitions", ANDROID_JAVA + "TextChunks.java", "Bounded source partitions retain Vietnamese diacritics; whitespace-only parts are not synthesized."),
    ("android_player", "Foreground player & bounded prefetch", ANDROID_JAVA + "PlaybackService.java", "Background notification, pause/resume/stop/next, saved segment and milliseconds, bounded producer, first-audio/cache metrics; 2/4 CPU threads."),
    ("android_nano", "VieNeu v3 Nano · local Vietnamese", ANDROID_JAVA + "NanoEngine.java", "ONNX Runtime Android 1.24.3 CPU; four graphs; model aba295eb96a6fa6003ebe417cc1f2802a7adc1dc; CFG 3 / 16 Euler steps / 24 kHz; 7 public Vietnamese presets. Telemetry disabled; no English model or private F5."),
    ("android_models", "Bundled model checksum verification", ANDROID_JAVA + "ModelAssets.java", "First-use copy into app-private storage from bundled public assets, verified by SHA-256. No automatic model network download."),
    ("android_g2p", "SEA-G2P C ABI / JNI", ANDROID_JAVA + "Phonemizer.java", "SEA-G2P 0.10.0, pinned dae5ca83ea45f356c43bdb70a1bcd42e8729ff16, public dictionary. Synthesis normalization never rewrites stored source text."),
    ("android_jni", "ARM64 phonemizer bridge", "android/app/src/main/cpp/CMakeLists.txt", "Rust shared library linked by basename libsea_g2p_rs.so; ELF alignment >= 16 KB verified, physical 16 KB kernel not tested."),
    ("android_audio", "Atomic WAV cache & full export", ANDROID_JAVA + "AudioFiles.java", "Partial output is unusable until fsync/atomic rename; cancellation retains completed segments. Full WAV export requires all segments."),
    ("android_cloud", "Pro Cloud client · activation deferred", ANDROID_JAVA + "CloudClient.java", "Explicit consent, <=4000-character opening sample, server-priced immutable snapshots/request keys, order history, bounded visible polling, SHA-256-verified WAV receipt. No endpoint bundled; transport fixtures only."),
    ("android_identity", "Android device identity & Keystore", ANDROID_JAVA + "CloudIdentity.java", "Hashed Android ID plus separate random encrypted bearer per endpoint; no account/email or reuse of Mac credentials. Device bearer is not sent to signed audio storage."),
    ("android_qr", "Local VietQR from server quote", ANDROID_JAVA + "PaymentQR.java", "Uses authoritative receiving account, amount and payment code. A code/QR never confirms payment; Android does not extend the Mac launch combo."),
    ("android_cloud_contract", "Versioned HeyGen book contract", "docs/BOOK-COMMERCE.md", "New catalog uses pro-cloud-heygen-v1; existing authenticated Modal orders retain their path. Gateway/dispatcher deployment, paid activation and live provider/payment tests remain separate scope."),
    ("android_assets", "Stage public Nano, font & welcome assets", "android/scripts/prepare_assets.py", "Copy only checksum-matching public Nano/presets/dictionary, local UI fonts and owner-authorized welcome audio. No private F5, English runtime, training dataset, keys or user data."),
    ("android_build", "Build Android test APK", "scripts/build-android.sh", "Entry ./scripts/build.sh --android; JDK 17, SDK 36, minSdk 33, arm64-v8a. Toolchain/cache/test signer stay project-local. Current output dist/android/Soundbooki-0.2.6-arm64-test.apk."),
    ("android_qa", "Emulator QA evidence & limits", "android/QA.md", "7 instrumentation tests and separate dark/background playback + 5-step walkthrough test PASS on AOSP API 35 ARM64. Real local Nano WAV, signer and 16 KB ZIP alignment verified. No physical Pixel 8 Pro/Redmi Note 13 benchmark or live Cloud proof."),
    ("android_handoff", "Android 0.2.6 checkpoint · 24/10/2026", "android/HANDOFF.md", "Current local test APK and reader/import feature checkpoint. Physical-device QA, battery/thermal measurements, Google Play release, and Android paid activation remain separate work.")
]
NODES.extend(dict(id=id, label=label, source_file=file, doc=doc,
                  community="Android Local & Cloud Client", community_id=8, type="component")
             for id, label, file, doc in ANDROID_DISCOVERY)
ANDROID_EDGES = [
    ("android_ui", "android_theme", "styled_by"),
    ("android_ui", "android_reader", "opens_reader_with"),
    ("android_ui", "android_walkthrough", "opens_5_step_discovery"),
    ("android_walkthrough", "android_theme", "renders_scenes_with"),
    ("android_walkthrough", "android_welcome_audio", "plays_greeting_bgm_and_sfx"),
    ("android_walkthrough", "app_walkthrough", "synchronized_with_mac_tour"),
    ("android_welcome_audio", "app_welcome_audio", "shares_verified_welcome_assets"),
    ("android_ui", "android_import", "imports_and_resumes"),
    ("android_import", "android_reader", "opens_imported_book_for_reading"),
    ("android_import", "android_store", "checkpoints_original_source"),
    ("android_ui", "android_store", "edits_and_restores"),
    ("android_ui", "android_player", "controls"),
    ("android_store", "android_chunks", "partitions_verbatim"),
    ("android_player", "android_store", "uses_cache_and_saves_position"),
    ("android_player", "android_nano", "prefetches_bounded_audio"),
    ("android_chunks", "android_nano", "supplies_spoken_parts"),
    ("android_nano", "android_models", "loads_verified_graphs"),
    ("android_nano", "android_g2p", "phonemizes_without_source_edits"),
    ("android_g2p", "android_jni", "calls_native_library"),
    ("android_nano", "android_audio", "commits_completed_wav"),
    ("android_player", "android_audio", "plays_or_exports_completed_audio"),
    ("android_ui", "android_cloud", "explicit_cloud_actions"),
    ("android_cloud", "android_identity", "authenticates_per_endpoint"),
    ("android_cloud", "android_qr", "renders_server_quote"),
    ("android_cloud", "android_audio", "receives_verified_wav"),
    ("android_cloud", "android_cloud_contract", "targets_deferred_gateway_contract"),
    ("android_cloud_contract", "app_voices", "shares_versioned_catalog"),
    ("android_build", "android_assets", "stages_public_resources"),
    ("android_assets", "android_models", "provides_manifest_and_assets"),
    ("android_assets", "android_theme", "bundles_local_fonts"),
    ("android_assets", "android_welcome_audio", "bundles_welcome_audio"),
    ("android_build", "android_jni", "cross_compiles_arm64"),
    ("android_handoff", "android_build", "records_reproduction_command"),
    ("android_handoff", "android_qa", "records_evidence_and_remaining_work"),
    ("android_qa", "android_walkthrough", "tests_pager_and_welcome_audio"),
    ("android_qa", "android_import", "tests_resume_and_extraction"),
    ("android_qa", "android_nano", "tests_real_local_inference"),
    ("android_qa", "android_player", "tests_background_and_cancellation"),
    ("android_qa", "android_cloud", "tests_fixture_transport_only")
]
EDGES.extend(dict(source=source, target=target, relation=relation, confidence="SOURCE_REVIEWED")
             for source, target, relation in ANDROID_EDGES)

# 3. Community Grouping
COMMUNITIES = {
    0: {"name": "Text Ingestion & OCR Normalization", "color": "#4A90E2", "god_node": "proofread_audiobook_text"},
    1: {"name": "Prosody Planning & Breath Segmentation", "color": "#50E3C2", "god_node": "plan_f5_prosody"},
    2: {"name": "Parallel Multi-GPU Orchestration", "color": "#F5A623", "god_node": "synthesize_book_parallel"},
    3: {"name": "Modal Cloud Engine", "color": "#BD10E0", "god_node": "modal_windi_studio_engine"},
    4: {"name": "F5 Acoustic Synthesis & Vocoding", "color": "#9013FE", "god_node": "f5_tts_dit"},
    5: {"name": "Audio Mastering & QA Gates", "color": "#7ED321", "god_node": "silence_qa_gate"},
    7: {"name": "Mac App Discovery", "color": "#316fce", "god_node": "app_walkthrough"},
    6: {"name": "HeyGen Turbo Cloud TTS", "color": "#FF5964", "god_node": "synthesize_book_heygen"},
    8: {"name": "Android Local & Cloud Client", "color": "#39c9a0", "god_node": "android_ui"}
}


def build_graph_json():
    data = {
        "metadata": {
            "title": "Soundbooki Mac, Android, Website & Cloud Architecture",
            "version": "2.8.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_nodes": len(NODES),
            "total_edges": len(EDGES),
            "total_communities": len(COMMUNITIES),
            "god_nodes": [
                "synthesize_book_parallel",
                "modal_windi_studio_engine",
                "proofread_audiobook_text",
                "plan_f5_prosody",
                "android_ui"
            ]
        },
        "communities": COMMUNITIES,
        "nodes": NODES,
        "edges": EDGES
    }
    with open(OUT_DIR / "graph.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Wrote {OUT_DIR / 'graph.json'}")


def build_graph_report_md():
    android_checkpoint = (ROOT / "android/HANDOFF.md").read_text(encoding="utf-8")
    # Rebase links from android/ into graphify-out/ when embedding the checkpoint.
    android_checkpoint = android_checkpoint.replace("](QA.md)", "](../android/QA.md)").replace("](README.md)", "](../android/README.md)")
    android_checkpoint = "\n".join("##" + line if line.startswith("#") else line
                                   for line in android_checkpoint.splitlines())
    md = f"""# Soundbooki — Mac, Android, Website & Cloud (Graphify Knowledge Report)

> [!NOTE]
> Tài liệu này được tạo tự động bởi **Graphify** để phục vụ việc tra cứu, định vị kiến trúc, và điều phối hệ thống giữa lập trình viên và các AI Agents (Gemini, Claude, Cursor).
> 
> * **Tổng số Nodes (Thành phần):** {len(NODES)}
> * **Tổng số Edges (Mối quan hệ):** {len(EDGES)}
> * **Cụm kiến trúc (Communities):** {len(COMMUNITIES)}
> * **God Nodes (Điểm điều phối trung tâm):** `synthesize_book_parallel.py`, `app.py`, `narration_text.py`

## Website — landing page tiếng Việt

Tra cứu: [`landing-page/index.html`](../landing-page/index.html), [`landing-page/hero-animation.js`](../landing-page/hero-animation.js).
Màn loading (`landing_loading`) dùng mô hình sách có bìa dày, các lớp trang và mặt giấy cong, cùng mở quanh gáy trong 2.35 giây. Dáng sách cong khi mở hết bám bản cũ; giấy màu ngà, bìa xám than lì và gần như không phản chiếu bóng. Renderer nằm tại [`book-opening.js`](../landing-page/assets/vendor/book-opening.js), dùng WebGL nhẹ với buffer tĩnh, chỉ vẽ khi đang mở hoặc resize/xem lại; không tải Three.js/model/texture. Mobile giảm phân đoạn, DPR và số lần vẽ; SVG cũ là hình dự phòng tĩnh. Bảy cụm từ sau đó tan thành nốt nhạc bay lên, không ghép lại thành câu. Reload, Bỏ qua/Esc, giảm chuyển động và cơ chế giữ bố cục khi chuyển cảnh vẫn được giữ. Clip kiểm tra riêng trong `landing-page/qa/book-opening-motion.mp4`, không đưa vào web build.

Landing page giới thiệu năm nhóm tính năng của Soundbooki, có nghe thử giọng Pro và hộp thông tin tải ứng dụng Mac. Hero đồng bộ lời chào theo timestamp, chỉ phát sau thao tác rõ ràng; Piano Podcast Bài 01 vào trước, giọng đọc bắt đầu sau 1 giây ở tốc độ 0.95x. Mười hai ký hiệu nhạc bay thưa, lệch nhịp theo từng từ; nhạc nền tiếp tục đến mốc 1 phút rồi fade out trong 3 giây.

```mermaid
flowchart LR
    Site[Landing page tiếng Việt] --> Tour[5 nhóm tính năng Soundbooki]
    Site --> Loading[Loading: sách xanh cong mở đôi, chữ hóa nốt nhạc]
    Site --> Voices[Nghe thử giọng Pro]
    Site --> Download[Thông tin tải ứng dụng Mac]
    Site --> Welcome[Hero lời chào + Piano Podcast Bài 01]
    Welcome --> Timed[Chữ đồng bộ lời đọc + ký hiệu nhạc bay]
```

## Android — mốc hiện tại 24/10/2026

Tra cứu: [`android/HANDOFF.md`](../android/HANDOFF.md), [`android/README.md`](../android/README.md), [`android/QA.md`](../android/QA.md).
Graph này mô tả mã và bằng chứng đã ghi; không tự xác nhận deployment hay kích hoạt dịch vụ. Các mục Cloud/F5 lịch sử bên dưới không phải pipeline Nano trên Android; số hiệu năng/chi phí Cloud không áp dụng cho điện thoại.

```mermaid
flowchart LR
    UI[MainActivity] --> Theme[UiTheme: font SF Pro/SVN Nexa + icon vector]
    UI --> Tour[WalkthroughDialog: 5 bước trên điện thoại]
    Tour --> Welcome[WelcomeAudioPlayer: welcome.wav + Piano BGM + chime SFX]
    UI --> Import[BookImporter]
    UI --> Reader[ReaderDialog: nền Đen #000000 riêng trang đọc]
    Reader --> ReaderStyle[ReaderPreferences: theme theo từng sách]
    External[Android Open with / Share · PDF & EPUB] --> Import
    Import --> Store[BookStore: originalText + checkpoints]
    Store --> Chunks[TextChunks: nguyên văn]
    UI --> Player[PlaybackService: nền + prefetch giới hạn]
    Chunks --> Nano[VieNeu v3 Nano: 4 ONNX graphs]
    Player --> Nano
    Nano --> G2P[SEA-G2P JNI]
    Nano --> WAV[AudioFiles: atomic WAV]
    WAV --> Player
    Player --> Store
    UI --> Cloud[CloudClient: hành động rõ ràng]
    Cloud --> ID[Android Keystore identity]
    Cloud --> QR[VietQR từ báo giá server]
    Cloud -. gateway chưa kích hoạt .-> Contract[pro-cloud-heygen-v1]
```

{android_checkpoint}

---

## 1. Bản Đồ Cloud Đã Có (Existing Cloud Flow Graph)

```mermaid
flowchart TD
    Raw["Raw Book Text (Scan/PDF/EPUB)"] --> Proofread["proofread_audiobook_text()\n(Regex OCR + All-Caps Fix)"]
    Raw -.-> QwenProof["Qwen OCR Proofreader\n(/proofread - Optional)"]
    
    Proofread --> Plan["plan_f5_prosody()\n(Syntactic Breath Pivots & 3s Chapter Pauses)"]
    Plan --> Chunker["chunk_units_for_workers()\n(Batch Balancer)"]
    
    subgraph MultiGPU ["Cụm Điều Phối Song Song (Client Runner)"]
        Chunker --> Orchestrator["synthesize_book_parallel.py\n(GOD NODE)"]
        Orchestrator --> Pool["ThreadPoolExecutor\n(3-4 Concurrent Workers)"]
        Pool --> Worker1["Worker 1 (Batch A)"]
        Pool --> Worker2["Worker 2 (Batch B)"]
        Pool --> Worker3["Worker 3 (Batch C)"]
    end
    
    subgraph ModalCloud ["Serverless GPU Cloud (Modal A10G/L4)"]
        Worker1 & Worker2 & Worker3 --> API["POST /batch\n(WindiStudioEngine)"]
        API --> Director["Qwen2.5-7B AI Director\n(Single-Pass Emotion & Pace)"]
        API --> DiT["F5-TTS DiT (Option 2: 22 steps)\n(NVIDIA CUDA FP16)"]
        DiT --> Vocos["Vocos Vocoder 24kHz"]
        Vocos --> SubSilence["Local Silence Check\n(Max Silence < 4.5s)"]
    end
    
    SubSilence --> Pool
    Pool --> Assembly["Master Track Assembly"]
    Assembly --> MasterQA["trim_excessive_silence()\n(Double-Layer Master Gate)"]
    
    MasterQA --> WAV["Master WAV 24kHz\n(Lossless PCM)"]
    MasterQA --> MP3["Customer MP3 128kbps\n(Lightweight ~55MB/hr + ID3)"]
    
    classDef god fill:#ffdd99,stroke:#d48800,stroke-width:2px;
    classDef model fill:#e8d5ff,stroke:#722ed1,stroke-width:2px;
    classDef out fill:#d9f7be,stroke:#389e0d,stroke-width:2px;
    
    class Orchestrator,API,Proofread,Plan god;
    class Director,DiT,Vocos model;
    class WAV,MP3 out;
```

---

## 2. Danh Mục Các Cụm Kiến Trúc (Architectural Communities)

### Cụm 0: Tiền Xử Lý & Chuẩn Hóa Văn Bản (Text Ingestion & OCR Normalization)
* **Thành phần chính:**
  * [`proofread_audiobook_text()`](file://{ROOT}/backend/narration_text.py#L35): Hàm thuần Python, chạy mất `0.001s`. Xử lý triệt tiêu đánh vần chữ in hoa (ALL-CAPS), bảo tồn danh mục từ viết tắt chuẩn (`AI`, `CEO`, `VND`, `GDP`...), chuyển số La Mã (`Chương I` $\rightarrow$ `Chương 1`), xóa rác scan (`Trang 45 / 320`, `--- 12 ---`), sửa lỗi OCR mờ (`1àm` $\rightarrow$ `làm`, `kh0ng` $\rightarrow$ `không`, `ngườ1` $\rightarrow$ `người`).
  * Endpoint [`/proofread`](file://{ROOT}/cloud/modal_studio/app.py#L880): Tích hợp Qwen2.5-7B hỗ trợ dò lỗi ngữ cảnh cho các trang sách scan mờ nát (trả về JSON danh sách từ nghi vấn mà không viết lại câu).

### Cụm 1: Lập Kế Hoạch Ngắt Nghỉ & Nhịp Thở (Prosody Planning)
* **Thành phần chính:**
  * [`plan_f5_prosody()`](file://{ROOT}/backend/narration_text.py#L225): Chia tách văn bản thành từng nhịp thở tự nhiên theo các từ nối ngữ pháp (`nhưng lại`, `cho nên`, `bởi vì`).
  * **Quy chuẩn khoảng nghỉ:**
    * Nghỉ chuyển chương: **3.0 giây** (tự động kích hoạt khi gặp `Chương X` mới).
    * Nghỉ tiêu đề chương: **1.5 giây**.
    * Nghỉ câu hỏi/cảm thán: **0.54s – 0.68s**.
    * Nghỉ dấu phẩy/giữa câu: **0.28s – 0.35s**.

### Cụm 2: Điều Phối Song Song 3–4 GPU (Parallel Orchestration)
* **Thành phần chính:**
  * [`synthesize_book_parallel.py`](file://{ROOT}/cloud/modal_studio/synthesize_book_parallel.py): Master CLI script.
  * `ThreadPoolExecutor(max_workers=3-4)`: Chia đều các batch và gửi song song lên Modal.
  * **Hiệu năng:** Tốc độ đạt **~3.5x - 4.5x Real-Time**, hoàn thành 1 cuốn sách (1 giờ audio) trong **13 – 16 phút**. Chi phí chỉ ~$0.15 - $0.20 / cuốn.

### Cụm 3 & 4: Hạ Tầng GPU Serverless & Âm Học Studio (Modal Cloud & F5 Engine)
* **Thành phần chính:**
  * [`WindiStudioEngine`](file://{ROOT}/cloud/modal_studio/app.py#L325): Container GPU NVIDIA A10G/L4.
  * [`Qwen2.5-7B AI Director`](file://{ROOT}/cloud/modal_studio/app.py#L465): Đọc hiểu toàn bộ văn bản và sinh metadata cảm xúc/nhịp đọc trong 1 forward pass duy nhất (~1.5s).
  * `F5-TTS DiT`: Cấu hình **Option 2 (22 steps + Sway Sampling -1.0 + CFG 2.2)** cho chất lượng 9/10 tương đương 32 steps nhưng tốc độ nhanh gấp đôi.
  * `Vocos 24kHz`: Vocoder tái tạo âm thanh phòng thu trong trẻo.

### Cụm 5: Kiểm Định Chất Lượng & Xuất Bản (Audio QA & Mastering)
* **Thành phần chính:**
  * [`trim_excessive_silence()`](file://{ROOT}/cloud/modal_studio/synthesize_book_parallel.py#L40): Lưới lọc khoảng lặng 2 lớp. Giữ trọn vẹn khoảng nghỉ chuyển chương 3.0s, nhưng cắt gọt triệt để mọi khoảng lặng chết $> 4.5s$ về 1.0s mượt mà.
  * **Master MP3 128kbps:** Bitrate tối ưu cho sách nói, giảm 33% dung lượng (1 giờ ~ 55 MB), tích hợp thẻ ID3 metadata.

---

## 3. Bảng Tra Cứu Nhanh Lệnh & Đường Dẫn (Quick Retrieval Index)

| Mục Đích | Lệnh CLI / Đường Dẫn File | Ghi Chú |
| :--- | :--- | :--- |
| **Chạy tạo cả cuốn sách song song** | `.runtime/bin/python cloud/modal_studio/synthesize_book_parallel.py --file <path> --workers 4` | Option 2 (22 steps), MP3 128k |
| **Deploy lại Cloud Engine** | `.runtime/bin/python -m modal deploy cloud/modal_studio/app.py` | Cập nhật container Modal |
| **Cloud Endpoint URL (Batch)** | `https://windivivuco--windi-studio-tts-windistudioengine-batch.us-east.modal.run` | Hỗ trợ batch nhiều câu |
| **File Master MP3 vừa tạo** | [`training/f5/artifacts/modal_audiobook_parallel.mp3`](file://{ROOT}/training/f5/artifacts/modal_audiobook_parallel.mp3) | 128kbps, 74.34s, nghỉ chương 3s |
| **File Master WAV vừa tạo** | [`training/f5/artifacts/modal_audiobook_parallel.wav`](file://{ROOT}/training/f5/artifacts/modal_audiobook_parallel.wav) | PCM 16-bit 24kHz |
| **Bản lưu trữ chuẩn Golden V2** | [`cloud/modal_studio/backup_v2_golden_9_10/`](file://{ROOT}/cloud/modal_studio/backup_v2_golden_9_10/) | Bản gốc dự phòng bất khả xâm phạm |
"""
    with open(OUT_DIR / "GRAPH_REPORT.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✓ Wrote {OUT_DIR / 'GRAPH_REPORT.md'}")


def build_graph_html():
    nodes_json = json.dumps([
        {
            "id": n["id"],
            "label": n["label"],
            "group": str(n["community_id"]),
            "title": f"<b>{n['label']}</b><br>Type: {n['type']}<br>File: {n['source_file']}<br>{n['doc']}"
        }
        for n in NODES
    ], ensure_ascii=False)

    edges_json = json.dumps([
        {
            "from": e["source"],
            "to": e["target"],
            "label": e["relation"],
            "arrows": "to"
        }
        for e in EDGES
    ], ensure_ascii=False)

    groups_json = json.dumps({str(id): {"color": {"background": "#1a2634", "border": group["color"]}}
                              for id, group in COMMUNITIES.items()})
    legend_html = "\n".join(
        f'<div class="legend-item"><span class="dot" style="background: {group["color"]};"></span>{group["name"]}</div>'
        for group in COMMUNITIES.values())

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>Soundbooki Mac, Android & Cloud - Interactive Knowledge Graph</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #12141a;
      color: #e6edf3;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    header {{
      padding: 12px 24px;
      background: #1a1e29;
      border-bottom: 1px solid #2a3142;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      color: #58a6ff;
    }}
    .subtitle {{
      font-size: 13px;
      color: #8b949e;
      margin-left: 12px;
    }}
    #network {{
      flex: 1;
      width: 100%;
      height: calc(100vh - 60px);
    }}
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(26, 30, 41, 0.9);
      border: 1px solid #2a3142;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin: 4px 0;
    }}
    .dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      margin-right: 8px;
    }}
  </style>
</head>
<body>
  <header>
    <div style="display: flex; align-items: center;">
      <h1>🕸️ Soundbooki Graphify</h1>
      <span class="subtitle">Mac · Android Nano · Cloud</span>
    </div>
    <div style="font-size: 13px; color: #8b949e;">
      {len(NODES)} nodes · {len(EDGES)} edges · Android checkpoint 24/10/2026
    </div>
  </header>
  <div id="network"></div>
  <div class="legend">
    <div style="font-weight: bold; margin-bottom: 6px;">Cụm Kiến Trúc (Communities):</div>
    {legend_html}
  </div>

  <script type="text/javascript">
    const nodes = new vis.DataSet({nodes_json});
    const edges = new vis.DataSet({edges_json});

    const container = document.getElementById("network");
    const data = {{ nodes: nodes, edges: edges }};
    const options = {{
      nodes: {{
        shape: "box",
        margin: 10,
        font: {{ color: "#ffffff", size: 14 }},
        borderWidth: 2,
        shadow: true
      }},
      edges: {{
        font: {{ color: "#8b949e", size: 11, align: "middle" }},
        arrows: {{ to: {{ enabled: true, scaleFactor: 0.8 }} }},
        smooth: {{ type: "cubicBezier", roundness: 0.5 }},
        color: {{ color: "#484f58", highlight: "#58a6ff" }}
      }},
      groups: {groups_json},
      physics: {{
        solver: "forceAtlas2Based",
        forceAtlas2Based: {{
          gravitationalConstant: -70,
          centralGravity: 0.015,
          springLength: 120,
          springConstant: 0.08
        }}
      }}
    }};

    const network = new vis.Network(container, data, options);
  </script>
</body>
</html>
"""
    with open(OUT_DIR / "graph.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Wrote {OUT_DIR / 'graph.html'}")


if __name__ == "__main__":
    build_graph_json()
    build_graph_report_md()
    build_graph_html()
    print("\n🎉 Graphify generation complete! Artifacts stored in graphify-out/")
