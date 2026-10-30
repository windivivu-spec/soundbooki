# Local QA — 2026-10-17

Host: Mac Apple Silicon arm64, macOS 26.5.2, Swift 6.1.2 with macOS 15.5 SDK, Python 3.12.13. All test documents are synthetic Vietnamese fixtures created by `tests/Fixtures.swift`; no personal book was read.

## Passed processing evidence

Raw report: `.qa/integration-results.json`.

| Check | Observed result |
|---|---|
| Native PDF text | 3/3 pages, correct Vietnamese diacritics, about 0.10 s |
| Native image OCR | Correct sample text including `ă â ê ô ơ ư đ`, about 0.57 s |
| Native scan-PDF OCR | 2/2 pages, correct sample text, about 0.49 s |
| Import cancel/resume | Cancel after page 1, resume to 10 pages with sourcePage 0…9 and no duplicates |
| Actual local Nano inference | 3 segments, 23.048 s total audio, first audio in 7.06 s on cold job |
| Per-segment compute | 3.63 / 1.87 / 1.87 s in this sample run; these include per-segment work and are not a general benchmark |
| Audio cancel/resume/cache | Completed first WAV kept; resume completes; repeated generation leaves cached WAV mtime unchanged |
| Position persistence | Segment 1 / 3.25 s survives worker restart |
| Edit safety | Edited segment loses current audio, originalText retained |
| Voice safety | New voice selects a different signature; existing audio does not count for it |
| Export | Real PCM16 mono 24 kHz WAV, 23.048 s, 1,106,348 bytes |
| Core tests | 5 tests pass: verbatim splitting, unbroken-text limit, cache signatures, state/export and network denial |

OS-level offline proof: `sandbox-exec -p '(version 1)(allow default)(deny network*)'` successfully ran both native OCR and the real TTS engine. `.qa/offline-ocr.jsonl` contains the correct Vietnamese text; `.qa/offline-tts.jsonl` contains a 3.74 s WAV, model load about 1.08 s and compute about 1.02 s. `.qa/offline-proof.wav` passed WAV validation. These prove the tested extraction/inference paths run with network denied; they are not a security audit of every installed library.

An initial restricted terminal invocation of Vision failed with a generic Foundation error. Retesting outside the agent terminal sandbox passed, as did the OS network-denied process. This is an environment permission difference, not evidence of OCR cloud dependency.

## Native UI evidence

The initial UI imported the 3-page PDF through NSOpenPanel, generated actual audio and advanced through segments. During QA, blocking dialog handling was replaced with native asynchronous sheets, and standard Cut/Copy/Paste/Select All menu items were added.

After Liquid Glass redesign: app built and ran with a dedicated `.qa/ui-library`; native AX/screenshot showed the complete dark and light workspaces, Vietnamese text, voice/speed controls, library and floating player. Selecting segment 1 updated both content and segment count. Actual native playback showed `Đang nghe`, 0:00 / 0:07; pausing showed `Tạm dừng`, 0:03 / 0:07 and a persisted position. The appearance panel changed from system to light and exposed reduced motion. Additional final UI checks are recorded below as they complete.

JavaScript syntax check and the existing 5 core tests passed after redesign. Visual changes preserve JSON-lines processing contracts. Font and SVG assets are local; no UI network requests are needed.

## Limits of proof

No full-book/multi-hour stress test, all-voice listening evaluation, real camera photograph, handwriting/multi-column accuracy evaluation, macOS 15/Intel/Windows run, notarization, portable installer, deployment or public release. OCR warnings are intentionally shown even when the synthetic sample was recognized correctly. Audio waveform/format and native playback have been tested; perceptual pronunciation quality has not been scored.

## Final glass UI checks

Native UI confirmed library search with a nonmatching query (visible empty-result message) and clearing it restored the book. Editing a segment and saving reduced readyCount from 3 to 2 and disabled export; restoring the original text returned readyCount to 3 via the original cache. Command-comma opened appearance settings. Light appearance and reduced-motion selections both survived app restart, and native playback position was displayed as 0:03 / 0:07 after reopening. Motion was returned to system preference after the test.

Content entrance animation was narrowed to the document surface and animation classes are removed on completion/preference changes. This avoids a WebKit accessibility-tree issue observed when changing reduced motion on a whole-section opacity animation. The final AX tree retained document controls after switching motion preferences.

The build now includes a local vector-drawn ICNS app icon, transparent native title bar, draggable title area, file/edit/application menus, Command-O/Command-F/Command-comma and native asynchronous file sheets. Build and ad-hoc codesign verification passed. `iconutil` required running outside the agent terminal sandbox; the ordinary Mac build script completed there.

Final integration rerun: PASS; first audio 3.13 s, total 23.048 s, 3 segments. The earlier measurements above are retained as a separate initial run.

## 0.2 — scoped narration, background music, portable exports

`tests/enhanced_integration.py` passed using real native PDF outline extraction and local Nano inference. Native chapter boundaries were page 1–2 and page 3. Creating page 2 alone produced exactly one WAV; creating chapter 1 then produced only its missing page 1 and retained the page 2 cache timestamp. Manual chapter insertion and persisted background-music settings passed.

A real 7.694-second page export with music was tested as PCM WAV (369,356 bytes), AAC M4A (65,945 bytes) and web ZIP (65,654 bytes in that run). WAV samples differ from dry narration, the M4A decodes back to 7.694 seconds, and ZIP contains the player, text manifest/data script and mixed audio. AAC 96 kbps was rejected by CoreAudio for this mono 24 kHz source; the verified production path uses 64 kbps and no unsupported optional metadata flags.

Nine unit tests pass, including page/range/chapter bounds, replacement/manual chapter boundaries, missing-page refusal, a 36-second mix that wraps the original 32-second loop, zero-volume byte identity, cancellation, invalid gain/track rejection and safe HTML/JS serialization. Existing real PDF/OCR/TTS/cancel/resume/position/export integration passed again.

Native UI showed the scoped-generation pane and the PDF chapter picker (`Chương 1 · trang 1–2`), local music selection, preview start/stop and a real slider change from 25% to 16% with persistence. Dynamic tab panes are reinserted when activated to refresh WebKit accessibility; opacity animation was removed from these semantic control containers.

The portable web player actually played M4A with music and selected page 2. A plain Python development server ignored Range and produced seekable [0,0] in WebKit, so that environment could not restore seeking. With `tests/range_server.py` (127.0.0.1 only, HTTP 206 byte ranges), pause at 11.584279 seconds followed by reload restored exactly 11.584279 seconds and displayed `Nghe tiếp từ 0:11.`. These are localhost tests, not a cloud upload, public hosting or physical phone test.

## User-provided Warm Reflections demos

Two distinct MP3 files were read only from the user-provided Downloads paths. Source hashes are retained in `assets/music/demo-catalog.json`. Converted playback durations are 182.8135 seconds and 179.8935 seconds. Both local PCM assets are mono 24 kHz, peak normalized to 0.5 and have short outer fades; original MP3s are unchanged.

`tests/demo_music.py` exported both with the same narration and 12% bed gain. Outputs: `output/demo/warm-reflections-ban-1.m4a` (129,850 bytes) and `output/demo/warm-reflections-ban-2.m4a` (128,523 bytes). Both were parsed as AAC by afinfo. The web ZIP was re-exported with the first user demo. No music, book or generated sample was uploaded or published; pricing/online accounts are deferred.

Final native verification: both `Warm Reflections · Bản 1` and `Warm Reflections · Bản 2` appeared in the music catalog. Selecting Bản 2 updated the displayed source duration and retained 12% gain. Switching to the download tab exposed all controls in the native AX tree. NSSavePanel saved `.qa/fixtures-data/native-warm-demo.m4a`; the app displayed the completed download path. Dynamic pane reparenting resolved the tab-switch accessibility issue.

## EPUB + giữ VieNeu — 2026-10-17

- 13 unit tests PASS: EPUB ZIP/thư mục, spine khác thứ tự ZIP, fragment nhiều chương trong một XHTML, Unicode/inline text, lời mở đầu/lời kết, heading fallback, scope đúng chương và phân đoạn nguyên văn; từ chối traversal/symlink/DRM; thông báo mục chỉ có ảnh/mốc thiếu. Core/cache/music tests cũ vẫn pass.
- File demo người dùng `Tư Duy Phản Biện.epub` là thư mục: nhập thật trong 0,38 giây ở QA, 10 mục, 371 đoạn, mọi mục lấy chữ trực tiếp; đầu tiên GIỚI THIỆU, cuối có LỜI KẾT/THAM KHẢO. Không OCR hoặc thêm model. Bìa chỉ có ảnh được báo rõ.
- Checkpoint 3 mục → resume đủ 10 mục, không trùng chữ/chương.
- VieNeu Nano giọng Minh Quân tạo riêng 5 đoạn Giới thiệu trong 26,66 giây; các chương còn lại không tạo. Đây là thời gian trên máy hiện tại khi có test hồi quy chạy cùng, không phải benchmark chung.
- Warm Reflections Bản 1 ở 12% được lưu và xuất M4A/ZIP; M4A 877.779 bytes, giải mã lại được 105,788 giây. Gói web có 5 đoạn, nhãn Mục 1. Metadata scope/nhạc/audio đọc lại từ đĩa thành công. Báo cáo `.qa/epub-results.json`.
- Hồi quy extraction/inference thật PASS (`.qa/integration-results.json`): PDF lớp chữ, Vision OCR ảnh/PDF scan tiếng Việt, hủy/tiếp tục 10 trang, cache, sửa chữ/đổi giọng, vị trí sau restart và WAV.
- Native picker nhập chính thư mục EPUB demo vào thư viện người dùng; UI hiển thị 10 mục / 371 đoạn và đủ 10 tên mục. Chuyển tới Lời kết đúng Mục 9 / Đoạn 362 rồi quay lại Giới thiệu. Bộ chọn phạm vi hiển thị Mục đang đọc/Khoảng mục/Theo chương.
- Chạy CoreAudio/Vision ngoài sandbox terminal: test trong sandbox từng báo codec AAC không khả dụng; cùng lệnh ngoài sandbox và app native dùng được. Không thay đổi codec hay dùng cloud để xử lý.

- Native UI tạo thực 5 đoạn Giới thiệu trong thư viện người dùng, hiển thị 5 đoạn có audio; đã chọn Warm Reflections Bản 1 ở 12% và xác nhận player chuyển sang Đang nghe/Tạm dừng. Không tạo toàn bộ sách.

## Model options, English and completion audit — 2026-10-17

- VieNeu Turbo FP32: nine pinned SHA-256 resources (520,281,804 bytes) downloaded and verified. Real inference PASS on Apple M1 Pro / 16 GB RAM with ONNX/CPU and no torch. Nano remains available; switching models and back reuses the correct cache. Turbo WAV/M4A retains 48 kHz; background music is resampled/mixed at 48 kHz. `.qa/turbo-results.json` and `.qa/enhanced-results.json` contain the runs. A short Turbo sample generated 6.72 seconds of audio in 4.54 seconds including load; this is one local example, not a hardware benchmark.
- English lightweight choice: KittenTTS Mini 80M, pinned revision c02725660cea441db4c383af69f1f26f5cd00947, three files totalling 81,547,388 bytes. Eight presets exposed; Jasper and Bella were tested. No Kitten SDK, spaCy, misaki, torch or GPU installed. Existing ONNX/NumPy reused; four small packages added and pinned (phonemizer, espeakng-loader, attrs, dlinfo).
- English real pipeline PASS: PDF text, Vision en-US OCR on a generated image, English book defaulting to Kitten/Jasper, voice change/cache, source/original text preservation, 24 kHz PCM audio, WAV/M4A/web ZIP with Warm Reflections at 12%, English web labels, restart retaining model/language/voice/audio/position. Jasper: 7.24 seconds of audio, 0.65 seconds compute, 2.34 seconds whole job; Bella: 10.29 seconds audio, 0.87 seconds compute, 2.23 seconds whole job. These are short local examples, not proof of quality on arbitrary books or every voice. `.qa/english-results.json` records the run.
- 20 unit tests PASS. Real Vietnamese regression rerun PASS: PDF text, Vision image/scanned PDF, import cancellation/resume without duplicate pages, cancelled/completed audio cache, text/voice invalidation, saved position/restart and WAV export. Real enhanced regression rerun covers PDF outlines/manual chapters, page/chapter-only generation, music persistence and WAV/M4A/web ZIP.
- Native UI verified in English: File/Edit menus, library/search, model and book-language controls, voice descriptions, scopes, music and player text. Existing Vietnamese book title, chapter labels and editor text remained Vietnamese and unchanged. Model panel reparenting restored the native accessibility subtree after translation. English QA library shows Kitten first, Jasper as selected voice, 24 kHz, one cached segment; playback reached Playing/Pause.
- A stale end-of-playback status was found during the audit and fixed: the final segment now resets to Ready/Play with position zero and marks the completed book, rather than leaving Playing visible. Scope completion also resets its position and status; no new audio is generated for this UI fix.
- Fish Drama 3 weights were never downloaded. An official web demo generated a self-written English sample (6.5 s); browser download was denied by the user and was not retried or worked around. The user then requested a lightweight English model, so Drama 3 was not integrated. No user book/audio was uploaded.

Remaining scope: cloud upload, multi-device account sync and billing are not implemented; the ZIP is a static player package. This is still a source-linked local development app, not a portable signed/notarized installer. OCR/layout quality and pronunciation of an arbitrary full book need user review; two English presets and short fixture/user-demo passages have been tested, not every voice or hours-long books. Licensing/notice review is required before redistributing the bundled eSpeak/phonemizer runtime.

Native completion follow-up: end-of-book was observed as Ready/Play, 0:00, and Finished in the QA library. The native persistence routine now skips writes when no AVAudioPlayer exists, so quitting after completion cannot overwrite the final completion flag with a stale stopped-player state.

Final close verification: the QA process exited normally and its book JSON retained `finished: true` and position `{segment: 0, seconds: 0}`. The final 0.5.0 native build passed. The user's default library retains the Vietnamese EPUB and its Turbo/Mạnh Dũng selection; English fixtures stay in `.qa`.

Outstanding native follow-up: after a UI-language switch, the reader/player remained visibly correct in a screenshot but were omitted by the WebKit accessibility snapshot. A full assistive-technology check is still needed. A later reopen stalled in WebKit's file sandbox-extension request. Computer Use then explicitly reported that the Mac was locked and could not be automatically unlocked. Final reopening/locale accessibility verification is therefore pending manual unlock, not recorded as a pass. A temporary custom-scheme loader experiment was reverted; the final build retains the original file loader, CSP and navigation allowlist.
# Private F5 integration — 2026-10-18

Added `f5-private` / `voice-001` as an optional independent runtime. Model, vocab,
reference WAV/text and local Vocos total 728,964,734 bytes; resource manifest pins
all SHA-256 hashes. `.runtime-f5` is about 1.1 GiB on this development Mac. It uses
PyTorch 2.6.0, 16 NFE and an adapter revision included in cache keys. Runtime
denies network sockets before importing F5; no reference ASR or lazy model fetch.

Real inference on this Apple Silicon Mac produced a 24.244-second 24 kHz mono
PCM16 WAV from the first existing book segment. Initial Metal test: 8.812 seconds
loading + 47.821 seconds generation while a CPU probe was also running. Separate
worker integration: 28.072 seconds generation for the same 24.244-second excerpt.
These are short-segment observations, not throughput promises for whole books.

`tests/f5_integration.py` runs the actual worker and private engine against an
isolated `.qa/f5-library`. It verifies a newly generated WAV, preserved exact
source text/originalText, correct voice/model persistence, reuse after switching
away/back, speed not invalidating cache, and WAV/M4A/web export for the same page.
Results: `.qa/f5-integration/integration-results.json`; no real library is used by
that test. Core suite: 28 tests passed. `./scripts/build.sh` succeeded outside the
terminal sandbox (sandbox iconutil could not create a valid iconset).

F5 weights derive from a CC BY-NC-SA 4.0 model: private non-commercial test only.
No publishing, installer or portable/notarized distribution was performed.

Native UI verification: the existing `Tư Duy Phản Biện` book successfully switched
to `Giọng của tôi · F5` / `voice-001`. A new take of the selected 403-character
chapter completed, the UI showed 1/1 audio ready, and AVAudioPlayer playback
advanced to 10.3 seconds of approximately 25 seconds. Earlier Turbo takes remain
in the book's take list. A local copy is `output/demo/voice-001-tu-duy-phan-bien.wav`.

# F5 uppercase / ornamental dash correction — 2026-10-18

Synthesis-only text preparation now follows the private training's lowercase and
simple punctuation convention: uppercase headings gain lowercase text plus a
sentence stop, ornamental dashes/quotes are removed, dash-wrapped attributions
gain a stop. Exact source text and originalText remain in book state. F5 revision
v2 invalidates earlier narration cache; earlier immutable takes stay available.

29 core tests passed. Real inference with the offline guard enabled confirmed
`device=mps`, FP32, 16 NFE for the exact title and `-Khuyết Danh-`, and a combined
passage: respectively 1.525 s / 0.661 s / 10.357 s of 24 kHz PCM16 audio. Generation
took 4.244 s / 4.112 s / 11.743 s after 7.145 s loading on this Mac. These are
runtime/format observations, not human transcription or a guarantee of every
proper noun's pronunciation. Inputs and events: `.qa/f5-text-v2/results.json`.

The native app was restarted after confirming no active generation/unsaved edit.
The user's currently edited 519-character chapter was regenerated: 2/2 segments,
33.684 seconds total narration, 42.548 seconds generation excluding load; both
segments report `device=mps`. Uppercase title and dash-wrapped author remain in
source text. The selected take was copied into an isolated QA library for export
to `output/demo/voice-001-co-hoi-text-v2.wav`; music settings are included through
the normal export path. Earlier immutable takes retain their earlier audio.


# Nano buffered listening — 2026-10-21

73 core tests passed after adding the resident Nano session and lookahead. Focused tests cover one-process reuse, draining an error response before the next request, the 12-segment/scope bound, no automatic take creation, and rejection of an old voice buffer. `tests/listening_integration.py` ran real local Nano on generated Vietnamese text: 12 segments / 63.34 s narration, first uncached file 2.314 s, next fresh file with the resident model 1.193 s. Every subsequent file was available before its simulated 2× deadline; minimum generation headroom after the first was 1.49 s. Cached requests preserved file mtimes, a voice change invalidated audio, and pages outside the selected range remained untouched. Artifacts: `.qa/listening/report.json`.

A native integration harness compiled the actual AppDelegate (only replacing the main entry point) and loaded the actual WKWebView UI/worker in `.qa/native-listening/library`. Cached Play → native playing event was 0.083 s; starting without cached audio was 2.147 s. Both selected four-segment runs at 2× produced three native advancement events and zero fallback ended/restart events before segment 4. Test playback was muted in the final run. This confirms the tested scheduling/buffering path, not acoustic transcription quality or arbitrary books/devices. Artifact: `.qa/native-listening/report.json`.

`tests/verify_narration_queue.swift` exercised 0.7 s synthetic silent WAVs: all four transitions, pause hold, seek, and rescheduling at 2× passed. Scheduled starts were exactly 0.35 s apart to within 0.001 s. AVAudioPlayer delegates arrived roughly 0.25–0.30 s after a queued segment's render start on this Mac, so the implementation schedules all contiguous ready files before those callbacks instead of relying on callback timing to open the next file. Artifact: `.qa/narration-native/report.json`. A short initial segment gets a small safety reserve when its successor is missing; fully prepared audio starts without that wait.

Nano uses the same 16 steps, seed 42 and audio signature revision. Local-only operation remains enforced by the inference process's offline guard. Results do not establish zero waiting on a never-generated book or when generation is slower than listening. No paid services, user books or public release were used.

## Soundbooki logo / macOS icon — 22/10/2026

- `./scripts/build.sh` completed; ad-hoc signature verification passed. The ICNS contains 11 validated representations at 16–1024 px, using the owner's `media-kit/logo` sources. All three original source hashes stayed unchanged.
- Existing `verify_walkthrough_ui.swift` passed in native WebKit with light/dark, compact layout, reduced motion, keyboard and focus checks. No processing or inference contract changed.
- Isolated native fixture captures under `.qa/brand-preview/` show the sidebar and app-info lockups in light/dark at 1180×800 and 860×660. Reviewed icon master and rendered screenshots visually. These are local UI checks, not public distribution proof or direct Dock cache verification. The Mac was locked during the attempted live-app restart.
# Hồ sơ / Pro / device-payment review — 2026-10-23

- Mac `./scripts/build.sh`: PASS, development app 0.8.2 / Build 18.
- Android `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest`: PASS, APK 0.2.2 / versionCode 5. Local test signer, not a Play release.
- Python core: 127 PASS, including selected mid-page chapter membership, Unicode cap, old pending 4k immutable retry. M4A test needs macOS audio access; full rerun outside sandbox PASS.
- Edge/gateway: 11 PASS, including authenticated read-only profile and wrong credential rejection.
- PGlite: trial-10x5000 SQL draft PASS after historical schemas; old 3 used trials, 500-character historical sample, receipts/licenses retained; 7 additional 5k trials accepted, 11th rejected; pricing/snapshot/claim/receipt/RLS regression PASS. One connection only, not concurrency/load evidence.
- HTTPS localhost integration PASS: 5k excerpt only, retry/cache, corrupted download retention, stale text/voice invalidation, purchased snapshot receive and WAV export. No provider inference.
- Native Mac WebKit fixture PASS: profile/name/cache 7/10, combo entry, light/dark at 1000x720; sample chapter selection resets consent; 5k sample, playback, 25k QR scan, focus, polling stops. Primary Pro actions remain outside the scroll area.
- Android emulator instrumented tests: ProProfileTest + CloudTransportTest, 3 PASS on final APK. Selected chapter 5k code points / no adjacent prose / full-book quote unchanged / old 4k prefix compatibility / profile save / disabled actions without gateway / audio hash and origin checks. Physical Pixel/Redmi not tested.
- Read-only HeyGen account check: HTTP 200; filtered response did not establish RPM/limits/free-model expiry. No TTS, payment, deployment, publication or OAuth/IAP setup.

Artifacts: `.qa/profile-*.log`, `.qa/profile-db-report.json`, `.qa/profile-heygen-readonly.json`, `.qa/book-ui/profile-*.png`, `.qa/book-ui/pro-chapter-dark.png`, `.qa/profile-android/`.

Independent device purchases, automatic payment adapters and the HeyGen production dispatcher are specified in `docs/DEVICE-PAYMENTS-AND-QUEUE.md`, not implemented. Existing Mac combo terms are retained. Android combo screen is informational while per-device store payments await activation.

Supabase CLI help was rejected by automatic approval review because the CLI attempts persistent telemetry writes outside the project; it was not rerun via a workaround. New SQL remains a reviewable draft at `commerce/manual/trial-10x5000.sql`, not a generated/applied migration.

Owner revised the platform choice later on 23/10/2026: devices remain independent; shared account/OAuth/sync planning was removed before any implementation. Current contract is `docs/DEVICE-PAYMENTS-AND-QUEUE.md`; profile/offer copy and the final APK follow this decision. No backend account migration or shared storage was created.


## Mac: xác nhận tạo Pro theo chương — 23/10/2026

Đổi đường tạo Pro của chương/nút nghe khi chưa có audio/Hồ sơ sang popup ngắn đúng chapter ID và voice đã lưu. Xác nhận là một hành động consent; không thêm checkbox hoặc hiển thị lại chữ sách/bảng giá trong luồng này. Mẫu vẫn chỉ tối đa 5.000 ký tự, không đổi thành tạo toàn chương miễn phí. Giá/đơn sách đã mua giữ đường vào cũ. Thiếu endpoint hoặc không mở được Keychain không ghi thêm cloudOrders local.

- 129 Python core tests PASS, gồm thiếu endpoint không tạo đơn/không đổi quota, retry 4.000 ký tự cũ và tách saved trial khỏi order sách.
- Native WebKit `tests/verify_pro_confirmation.swift` PASS ở 1000×720: dark/light, đúng chương/giọng, 1 lần bấm xác nhận, chặn bấm hai lần, queued → ready → nghe, tái dùng mẫu cũ khi quota bằng 0; không submit khi mở popup hoặc khi service chưa cấu hình. Ảnh `.qa/book-ui/pro-confirm-ready.png` và `pro-confirm-unavailable.png`.
- Native hồi quy bảng mua sách cũ PASS: consent, nhận/nghe mẫu, QR fixture 25.000đ quét được, focus và ngừng polling khi đóng (`.qa/pro-confirm-commerce-ui.log`). HTTPS localhost PASS: cache thử riêng, tải dở giữ phần xong, retry/cache, text/voice mới không phát audio cũ, bản đã mua xuất WAV (`.qa/pro-confirm-integration.log`).
- Build Mac bằng `./scripts/build.sh` PASS. Source-linked development app, chưa phải installer/notarized release.

Kiểm tra live chỉ dùng POST `{}` không chữ sách/danh tính: function `wsn-books/profile` trên dự án Supabase license trả HTTP 404 NOT_FOUND. Cấu hình consumer hiện không có booksBaseURL. Chưa gọi HeyGen TTS, deploy, áp migration hay bật trả tiền; các test fixture không chứng minh tạo Pro thật hoạt động.


## Gộp tối đa 4 lượt miễn phí theo chương — 23/10/2026

- Quy tắc: ceil(số ký tự thực/5.000), tối đa 4 đơn vị/20.000 ký tự trong một order trial, tổng lifetime vẫn 10 đơn vị/thiết bị. App tự tính số lượt để xác nhận trọn chương khi đủ trần; không gọi toàn chương khi chỉ có 20.000/25.000 ký tự. Không lấy chữ chương sau.
- 131 Python core tests PASS; boundary 1/5.000/5.001/10.000/10.001/15.000/15.001/20.000/24.000, Unicode, source verbatim, grouped snapshot/route, pending retry và mẫu cũ không bị nhận nhầm là chương đầy đủ.
- 15 gateway tests PASS: route/RPC riêng trial-group, không nhận số lượt giả, không fallback single nếu database chưa nâng cấp, thiếu quota trả lỗi, giữ các luồng giá/receipt cũ.
- PGlite một connection PASS (`tests/book_grouped_trials_db.mjs`, `.qa/grouped-trials-db-report.json`): không reset used counter/payload/hash cũ, trừ 4 rồi 3 đúng, thiếu 2 khi còn 1 rollback cả order/counter, retry không trừ lại, cost bất biến, grants/RLS và paid receipt/pricing/claim hồi quy. Không chứng minh concurrency đa worker hoặc migration live.
- HTTPS localhost PASS (`.qa/grouped-trials-integration.log`): gửi 1 snapshot chương gộp, retry cùng key dùng cùng order/cost, nhận đủ audio chương; cache thử riêng, bản mua bất biến, tải dở giữ phần đã xong và export cũ.
- Native WebKit Mac 1000×720 PASS (`.qa/grouped-trials-ui.log`): xác nhận 2 lượt/trọn chương, cap 4 lượt hiển thị phần còn thiếu, thiếu quota, không gửi khi mở popup, double-click và nhận lại mẫu khi quota=0. Ảnh `.qa/book-ui/pro-confirm-ready.png` và `pro-confirm-four-unit-cap.png`. Bảng giá/QR cả cuốn vẫn là luồng riêng.
- Mac build PASS bằng `./scripts/build.sh`; Android 0.2.3 build/unit tests PASS, 4 emulator tests PASS (ProProfile + CloudTransport): Unicode/gộp/trần chương, UI không gửi khi chưa cấu hình, đường nhận audio an toàn. Không có test máy Android vật lý.

SQL gộp nằm trong `commerce/manual/trial-group-up-to-four.sql`, chuẩn bị local sau draft 10×5.000; chưa áp dụng live. Không deploy, gọi TTS thật, reset quota, đổi offer hoặc mở bán. Gateway/dispatcher Pro thật vẫn là phần activation còn thiếu như lần chẩn đoán trước.

## Quota 5 lượt, lựa chọn trái–phải và nút đóng tròn — 23/10/2026

- Mặc định tạo thử 1 lượt; tùy chọn tạo chương tính chi phí thực 1–4 lượt, tối đa 20.000 Unicode code point. Tổng trọn đời 5, giữ nguyên số đã dùng (thiết bị cũ dùng 6–10 vẫn lưu counter và còn 0).
- 131 core tests PASS (`.qa/five-core-tests.log`); 15 gateway tests PASS (`.qa/five-gateway-tests.log`). PGlite PASS nâng cấp lịch sử 500/4.000/5.000, payload/hash, grouped cost, cap 5, 1+4=5, thiếu quota rollback, retry cũ ở quota 0, grants service_role, ledger giá/receipt/claim trước upgrade (`.qa/grouped-trials-db-report.json`). Đây là một connection, không phải bằng chứng concurrency/deployment thật.
- HTTPS localhost integration PASS submit, retry, grouped debit, download hỏng/gián đoạn, cache và bản đã mua (`.qa/five-cloud-integration.log`), không gọi provider.
- Native WebKit PASS mặc định 1 lượt và chuyển bằng radio sang chương 2 lượt, thiếu quota, chương dài cap 4/20.000, gửi một lần, resume đơn cũ ở quota 0 (`.qa/five-confirmation-ui.log`). Hai lựa chọn nằm cùng hàng trái–phải. Hộp xác nhận gọn, không hiện form mua sách/nội dung dài. Kiểm tra Hồ sơ quota 2/5 và luồng mua/QR 25.000đ hiện tại PASS (`.qa/five-profile-ui.log`, `.qa/five-commerce-ui.log`).
- QA hình học WebKit trên 14 nút X: 14/14 là 40×40, radius 50%, không co thành ellipse khi tiêu đề dài (`.qa/popup-geometry.json`). Ảnh sáng/tối ở `.qa/book-ui/pro-confirm-*.png` và `profile-*.png`.
- `./scripts/build.sh` PASS app Mac local (`.qa/five-mac-build.log`). Android build/unit tests/signature/16KB ZIP alignment PASS (`.qa/five-android-build.log`); APK `dist/android/Soundbooki-0.2.4-arm64-test.apk`, SHA256 `448d46ac1b50450091a4140e1cf5dadc204fe3e2a081d18ef01bc2bc6c9edf09`. Emulator 5 instrumentation tests PASS: selected chapter/Unicode, explicit choice 1↔group, old cache used0..10 preserved under cap5, bounded groups, fake HTTPS transport (`.qa/five-android-instrumentation.log`). Ảnh `.qa/five-android-pro-chapter.png`; chưa kiểm tra thiết bị thật.
- SQL mới `commerce/manual/trial-five-unit-policy.sql` nằm sau bản gộp, không xóa/reset counter. Gateway mới gọi RPC `wsn_book_create_trial_v2` cho cả single/group, không fallback quota10. Không sửa database live, không deploy gateway/dispatcher, không chi quota inference, không kích hoạt mua thật hoặc phát hành installer/store. Bản Mac consumer vẫn chưa có booksBaseURL/gateway; tạo Pro thật còn bị chặn bởi activation scope riêng.

## Gateway/worker trial live trên Mac — 23/10/2026

Đã triển khai đúng hai Edge Functions mới và schema quota5/dispatcher. Supabase ACTIVE_HEALTHY. 27 gateway/worker tests, PGlite dispatcher, 132 core tests, HTTPS localhost integration và Mac build PASS. Mẫu thật Đình Mạnh dài 6,39 giây đã qua HeyGen → private bucket → signed download → SoXR 44,1→24 kHz → cache Mac; nhận lại không tạo TTS lần nữa. Thiết bị QA dùng 1 lượt riêng, Mac owner vẫn 5/5. Các row legacy giữ 2 receipt/1 license. Advisors chỉ INFO cho bảng private; không có RPC mới public execute. Không bật paid/public hoặc nhận tiền. Chi tiết/bằng chứng ở [CLOUD-TRIAL-DEPLOYMENT.md](CLOUD-TRIAL-DEPLOYMENT.md).

### 23/10/2026 — Banner bằng code, Mac + Android

- Mac: 5 bìa DOM độc lập + cảnh SVG inline, không còn ảnh raster trong banner. WebKit QA đạt ở 860×660, 1180×800, 1600×900 và bản component 375px; kiểm tra bìa/nút nằm trong banner, giao diện sáng/tối và luồng combo fixture sẵn có đều đạt. Ảnh trong `.qa/banner-code-*.png`.
- `./scripts/build.sh` hoàn tất cả ký app và đăng ký Launch Services khi chạy với quyền hệ thống phù hợp. App local đã mở thành công; quan sát native AX xác nhận banner, giá và nút combo. Không phải bản cài portable/notarized.
- Android: `ReadingBanner` dùng native text/button và `BannerBooksView` Canvas; APK ARM64 test build thành công, signer/zipalign đạt. Đã xem trực tiếp trên emulator API 35 ở màn hình dọc tối, 360dp sáng với font scale 1.3 và màn hình ngang; không phải kiểm tra thiết bị vật lý. Không kích hoạt combo Android, gọi provider hay thanh toán thật.

- Banner compact follow-up: kiểm tra lại chiều cao <=150px ở viewport desktop 860–1600px, <=180px ở component 375px, và tỷ lệ computed width/height của từng bìa là 2:3. Tất cả đạt trong WebKit. Mac/Android đã build lại thành công; app Mac được khởi động lại và quan sát trực tiếp. Android dọc nay dùng dải ngang gọn, cảnh và chữ trên bìa scale đồng đều, không kéo riêng hai trục. Ảnh `.qa/banner-compact-*.png` và `.qa/banner-android-compact.png`.

### Đọc PDF mượt hơn · 23/10/2026

- 22 core/reading/ebook/listening unit tests đạt. `tests/verify_reader_performance.swift` chạy worker/WebKit thật, xác nhận thay chữ làm mới chữ ký, đổi ngôn ngữ UI hoạt động và chữ sách không bị dịch/đổi.
- `tests/verify_flipbook_ui.swift` dùng fixture mới: PASS curved geometry giữ ở 42%, kéo ngược/hủy, queue/fallback, font/theme/TOC/bookmark, ảnh PDF, PDF gốc/highlight và nhập EPUB. Bộ QA chủ động chọn sách sau init để phù hợp màn hình Trang chủ hiện tại.
- Cache Vision đã thử với một PDF scan local: 13 highlight được giữ qua cache; câu đã sửa không khớp không nhận anchor cũ. Bitmap cache theo nguồn + mtime/size + trang; OCR thêm ngôn ngữ; kết quả request lỗi thời bị bỏ.
- `./scripts/build.sh` hoàn tất. App local được khởi động lại. Không gọi cloud/inference/payment; chưa phải bằng chứng cho mọi PDF, thiết bị hoặc bản phân phối.
# 25/10/2026 — chuẩn hóa HOA / La Mã khi import

Import mặc định nay chuẩn hóa dòng hoàn toàn viết HOA thành dòng chỉ viết hoa chữ đầu, giữ viết tắt đã biết (AI, USD, TP.HCM, GS.TS. …), số và các dòng vốn viết đúng. Áp dụng trên cả trang trước khi phân phối lại vào segment để không viết hoa lại mỗi 420 ký tự. Bản nguồn và `originalText` vẫn giữ nguyên.

Số La Mã chuẩn được đổi sang số thập phân trong ngữ cảnh chương/phần/mục/tập/thế kỷ, tiêu đề và mục đánh số. Ví dụ `CHƯƠNG IV` → `Chương 4`, `Thế kỷ XXI` → `Thế kỷ 21`, `IV.` → `4.`. Dòng `I` độc lập được xử lý theo ngôn ngữ sách; giữ đại từ `I` trong sách tiếng Anh. Không thay các chuỗi La Mã sai quy tắc hoặc từ viết tắt lẫn trong văn xuôi. Mapping có tính thay đổi chiều dài của chữ số để giữ đúng phân vùng nguồn và không mất chữ.

Đã bỏ nút, bảng xem trước, event và CSS dọn thủ công khỏi workspace; dán văn bản cũng chạy cùng bước dọn tự động. Không thay snapshot/đơn đã chốt hoặc tự sửa lại sách đã import trước nâng cấp.

QA: test uppercase/viết tắt/số La Mã, Unicode, dòng dài qua nhiều segment, idempotency và giữ nguyên source; native PDF + EPUB import thật trong `.qa/import-case/` xác nhận nội dung chuẩn hóa đi vào snapshot Pro mà không gọi TTS. Native WebKit PASS sửa/hủy sửa/nút lưu, xóa hoàn toàn UI dọn, light/dark và phát take. Build local PASS với `WINDI_SKIP_REGISTRATION=1`. Đây là fixture QA, không phải bằng chứng mọi tài liệu hoặc bản phát hành installer.

