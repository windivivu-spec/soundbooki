# Android QA — reader ebook 0.2.6 (24/10/2026)

APK đầy đủ model Lite, versionCode 9 / `0.2.6-test`, cùng package/signer preview. Hướng dẫn: [READER-FEATURES.md](READER-FEATURES.md).

- `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest --offline`: PASS. 5 unit Java PASS; apksigner và ZIP alignment 16 KB PASS.
- Native trên AOSP API 35 ARM64 emulator, cùng APK cuối:

| Cấu hình | Kết quả |
| --- | --- |
| 1080×2400 · density 420 · dark · font hệ thống 100% | 11 tests PASS · 29.447 giây |
| 720×1600 · density 320 · light · font hệ thống 130% | 10 tests PASS · 24.314 giây |
| 1280×720 · density 320 · dark · font hệ thống 150% | 10 tests PASS · 19.614 giây |
| 1080×2400 · dark · tắt animation hệ thống | 6 tests PASS · 11.459 giây |

Bao gồm: đổi nền/typography/lề và khôi phục; nền đổi không chạy paginator; độ sáng/keep-awake giới hạn ở cửa sổ reader; legacy bookmark migration; nhiều dấu + ghi chú + phân biệt bản chữ; vuốt có snapshot, hủy giữ offset, nhả tay xác nhận giữ offset qua reflow; tự bỏ snapshot khi animation hệ thống tắt; đóng/mở lại và Activity recreation; nhiều lần mở danh sách không giữ cây view; hướng dẫn dấu trang không bị cắt khi chữ lớn. Đã xem ảnh native của nền đọc, menu cài đặt, danh sách dấu trang và fold đang kéo ở portrait/landscape.

Trên bản chữ QA PDF 203 trang (312.297 đơn vị UTF-16), tất cả trang cỡ chữ 30 được đo bằng TextView thực để kiểm tra mép ngang/dưới, cùng phân hoạch nguyên văn và giữ offset. Kiểm tra chữ hệ thống 130% ban đầu phát hiện một trang ngắt thành 9 dòng khi đứng riêng dù khối lớn đo 8 dòng. Đã thêm bước đo ứng viên độc lập và chỉ rebase khối khi cần; sau sửa toàn bộ trang qua trên ba cấu hình. Vẫn dùng worker, hủy task và cache bốn bộ ranh giới; không dựng bitmap cả sách.

Lần đo portrait cuối: mở reader 635 ms, đổi cỡ 30 là 512 ms, quay về cỡ 19 là 135 ms; 596/1.292 trang ở cỡ 19/30. Có overhead polling của test; không phải FPS, import, OCR, inference hoặc benchmark máy vật lý. Không chạy synthesis, upload hay thanh toán trong QA reader.

APK: `dist/android/Soundbooki-0.2.6-arm64-test.apk` · 436,654,740 bytes · SHA-256 `82b750a86920b8eaa740f94b23f65a7ef08f0b7321dbc763a1b917ed78400940`.

Raw evidence local: `.qa/android-ebook/build.log`, `native-{portrait,small,landscape,reduced}.log`, ảnh `ebook-*.png` và `reader-*.json`. Thư viện fixture tách `.qa/reader-features`, `.qa/reader-performance`, `.qa/reader-chapters` trong vùng riêng emulator.

Chưa có QA mới trên Pixel 8 Pro/Redmi Note 13 thật, pin/nhiệt, kernel 16 KB hoặc mọi phiên bản Android/font. Đây là APK thử local Android 13+ ARM64; chưa phát hành Google Play, không kích hoạt Android paid flow.

---

# Android QA — reader 0.2.5 (23/10/2026)

- `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest --offline`: PASS; 5 unit tests Java, apksigner và ZIP alignment 16 KB PASS. APK đủ bốn graph Nano, cùng package/signer test, versionCode 8.
- AOSP API 35 ARM64 emulator: 5 kiểm tra native reader qua ở dark 1080×2400/density 420 (4 + 1 run riêng), 5 qua ở light 720×1280/density 320, 5 qua ở dark 1280×720/density 320. Có ảnh native cỡ chữ 30 cho cả ba bố cục.
- Bao gồm: mọi range nối lại nguyên văn; không cắt surrogate/chương; trang với emoji/combining marks; đo TextView của toàn bộ trang cỡ 30; hủy worker không xuất kết quả thiếu; đổi typography liên tục; ẩn/hiện controls; anchor chính xác qua dàn lại/đóng/mở; reader regression đã có.
- Cùng 312.297 đơn vị UTF-16 từ PDF QA 203 trang: mở reader 1.821 → 582 ms; đổi cỡ 30: 3.309 → 285 ms; về cỡ 19: 1.483 → 346 ms. Đây là thời gian frontend sau khi sách đã nhập và activity đã sẵn sàng, có chi phí test polling, không phải FPS/import/OCR/TTS hay benchmark máy thật.
- Thư viện `.qa/reader-performance` / `.qa/reader-chapters` của emulator; không chạy cloud/provider/synthesis. Xem [READER-PERFORMANCE.md](READER-PERFORMANCE.md) cho nguyên nhân, cách sửa và giới hạn.

APK: `dist/android/Soundbooki-0.2.5-arm64-test.apk` · 436,584,376 bytes · SHA-256 `35049e1f3c76b53b831309e917ee30e0395bfe727c0a43f40b3fa796d687a8db`.

Raw evidence: `.qa/android-reader/` trong project. Chưa có QA mới trên Pixel 8 Pro / Redmi Note 13 vật lý, pin/nhiệt hay mọi font/system font scale. Đây là APK thử local.

---

# Android QA — 0.2.1 (23/10/2026)

Package `studio.windi.soundbooki.preview`, versionCode 4, Android 13+, ARM64. Bản local cùng signer; có model Lite thật. Kiểm tra dưới đây dùng emulator AOSP API 35 ARM64 offline, không phải đo tốc độ/pin/nhiệt trên Pixel 8 Pro / Redmi Note 13 vật lý.

- Official `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest`: PASS; 5 unit Java PASS, apksigner + ZIP alignment 16 KB PASS.
- Core Python/Mac: 122 tests PASS trong 3,980 giây. Không thay code Mac/backend trong lượt này.
- Android 1080×2400, density 420, dark: 21 tests PASS trong 145,004 giây. Bổ sung ràng buộc hash ranh giới chương sau vòng này; cùng layout/producer. Vòng APK cuối và test force-stop ghi bên dưới.
- Ngưỡng 5% được kiểm tra với cache fixture trống: first playback >=5% và <30%, producer vẫn tiếp tục. Đã rời Activity, gửi phím Sleep, xác nhận màn hình tắt và chờ thêm >=2 audio segments; foreground notification còn tồn tại. Đây là bằng chứng emulator, không bảo đảm mọi firmware giữ service sống.
- Dừng tạo hoàn tất đoạn đang chạy rồi park worker. Ready không tăng trong lúc nghỉ; player tạm dừng; vùng **Wake Locks đang giữ** của `dumpsys power` không còn `soundbooki:narration` (không nhầm lịch sử acquire/release là lock đang giữ). Tiếp tục cùng worker tạo thêm được rồi dừng lại lần hai; `generation.json` state/selection được lưu.
- Khôi phục dùng checkpoint riêng và xác minh WAV thật. Fixture cố ý cắt ngắn một WAV đã có: phần hỏng được tạo lại, các WAV hợp lệ giữ nguyên mtime + SHA. Chỉ ghi một chương hoàn tất vào manifest; chữ gốc không đổi, không phát audio bất ngờ khi chỉ chọn tiếp tục tạo. Đổi chữ/giọng hoặc ranh giới chương không dùng lại checkpoint cũ.
- Resume yêu cầu phát liên tục bắt đầu ở chương đang lưu, không nhảy lại chương đầu đã chọn. Có thể dừng tạo các chương kế tiếp khi hiện tại đã đủ. Không chạy model/chương tiếp theo khi còn dừng nghe tại chương hiện tại.
- Tua +15 giây qua nhiều WAV, -15 giây và chặn ở đầu/cuối chương, seek khi pause và sleep timer PASS bằng WAV fixture xác định. Hai icon mới và loading/pause được xem trên ảnh native. Tone fixture không phải bằng chứng TTS; các phép thử Nano/JNI thật chạy riêng.
- Giữ một producer, mặc định 2 threads, 16 steps CFG=3. Ưu tiên suffix sắp nghe; cache hợp lệ không ghi lại. Đóng ONNX sessions khi nghỉ/hoàn tất, nhả wakelock khi không còn tạo/phát, gộp thông báo trùng, không fsync lặp cho cache đã bền vững. Chưa có benchmark thời gian tạo cả sách hoặc pin/nhiệt máy thật.
- Service khai báo processing phù hợp và xử lý Android timeout; `START_NOT_STICKY`, không tự hồi sinh sau force-stop/khởi động máy. [Android foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types), [hành vi người dùng dừng app](https://developer.android.com/develop/background-work/services/fgs/handle-user-stopping).

- APK cuối: màn hình nhỏ 720×1280, density 320, light: **21 tests PASS · 130,752 giây**; gồm ràng buộc hash ranh giới chương. SHA APK không đổi sau lần build bổ sung assertion PID chỉ trong test APK.
- Hai instrumentation runs độc lập: save/pause **PASS · 25,619 giây**, `adb shell am force-stop` ở giữa, resume với `requireProcessRestart=true` **PASS · 40,542 giây**. Assertion xác nhận PID Android khác, checkpoint/voice/chương còn đúng, WAV tốt giữ mtime/SHA, WAV cố ý hỏng được tạo lại và chương hoàn tất được lưu.
- Đã xem ảnh native loading/paused ở dark 1080×2400 và light 720×1280. Màn nhỏ vẫn có thể cuộn tới phần văn bản; nút dừng/tiếp tục nằm sau tiến độ, không bị lớp điều khiển che.

APK cuối: `dist/android/Soundbooki-0.2.1-arm64-test.apk` · 419,740,642 bytes · SHA-256 `366da4b7477a676c306ee6ef5274b2c666ad79b523fdc7ace8d8ad6d109ca5af`.

Bằng chứng raw local (ignored): `generation-build.log`, `generation-core-tests.log`, `generation-final-dark-tests.txt`, `generation-final-small-light-tests.txt`, `generation-paused-dark.png`, `generation-loading-dark.png`, `generation-paused-small-light.png`, `generation-loading-small-light.png`, `generation-restart-save.txt`, `generation-restart-resume.txt`. Không có cloud/provider/payment/upload/publication trong QA; Pro Max và paid deployment vẫn giữ hoãn.

---

## Lịch sử 0.2.0

# Android QA — 0.2.0 (23/10/2026)

Package `studio.windi.soundbooki.preview`, versionCode 3, Android 13+, ARM64. APK local có model Lite thật. Bằng chứng dưới đây là emulator AOSP API 35 ARM64; chưa có phép thử mới trên Pixel 8 Pro / Redmi Note 13 vật lý.

| Bộ kiểm tra | Kết quả |
| --- | --- |
| Build, apksigner, ZIP alignment 16 KB | PASS |
| Unit Java | 5 tests PASS |
| Core Python/Mac | 122 tests PASS · 2,881 giây |
| Android 1080×2400, density 420, dark | 16 tests PASS · 61,326 giây |
| Android 720×1280, density 320, light | 16 tests PASS · 58,731 giây |
| Android 1280×720, density 320, dark · APK cuối | 16 tests PASS · 57,555 giây |

## Bằng chứng chức năng

- Home khởi động bằng tủ sách, có sách mở gần đây, shelf ngang, empty state. Thư viện tìm/lọc sách từ dữ liệu local thật. Bìa PDF/EPUB lấy từ nguồn; fallback là typography Canvas. Không thêm sách danh mục, lượt nghe hay tác giả giả vào sản phẩm. Các screenshot dùng bốn sách tự viết trong thư viện fixture `.qa/shelf-*`, không phải catalog bán sách.
- Navigation Home → Library → Detail → back → Create → Settings được kiểm tra native. Editor cũ giữ chữ gốc. Detail/player là màn hình sâu có back; trang chính có nav và mini player khi phát. Đã xem trực tiếp ảnh native portrait dark/light và landscape dark. Nội dung dài tiếp tục cuộn, không ép mọi thành phần lên một màn hình.
- 7 mẫu Pro đều mở/phát offline; SHA-256 của WAV trong APK khớp catalog. Mỗi mẫu dài 8,5 giây, waveform đo 72 bins từ PCM thật. Chuyển giọng/dismiss/background dừng đúng player. Không tạo trial/quote/order khi chỉ nghe mẫu. Mẫu là recording owner-local được yêu cầu dùng cho bản thử, không phải xác nhận quyền phát hành public.
- Timeline/tua ±15 giây qua đoạn, pause/seek và hẹn giờ ngủ được kiểm tra với WAV fixture có thời lượng xác định. Vị trí tua 9.500 ms được giữ khi pause, tua lùi không sang chương trước. Deadline ngủ mô phỏng bằng monotonic clock làm pause đúng. Không dùng tone fixture làm bằng chứng giọng TTS thật.
- Inference Nano/JNI thật và hủy được kiểm tra riêng trong bộ Android hiện có, cùng luồng đệm 30%, tạo tiếp và chỉ lưu chương hoàn tất. Partitions, checkpoint import EPUB/PDF, cleanup sách dài, phân trang, restore offset, chữ/voice/revision cache và snapshot Cloud cũ vẫn qua regression. Cloud transport chỉ dùng fixture `example.invalid`, không gọi gateway/provider/thanh toán thật.
- Văn bản theo audio lấy đúng segment; archived take cũ không khớp text hiện tại bị chặn mở theo dõi sang bản mới. Tốc độ là player setting. Chưa cam kết word-level highlight hay không đứt tiếng trên mọi máy.
- APK chứa bốn ONNX Nano và bảy sample Pro trong whitelist. ZIP không có `.env`, keystore, private F5, training dataset hoặc file sách 203 trang. Source/cover/cache sách chỉ ở vùng riêng của app/fixture.
- Không thay backend, giá, quota, payments/ledgers hay deployment. `PRO_MAX_ENABLED=False` và phạm vi paid/gateway/HeyGen dispatcher/publication vẫn giữ nguyên.

## Artifact và giới hạn

- APK: `dist/android/Soundbooki-0.2.0-arm64-test.apk` · 419,711,066 bytes.
- SHA-256: `98ecb3ef582e9a729ec8f9841fba0bb543c4a34285f77c19cf1f54b1bff9c82b`.
- Bản preview dùng cùng package/signer local; không phát hành Google Play hay dùng khóa production. Chưa kiểm tra kernel 16 KB, pin/nhiệt, Android 13/16 trên máy thật, toàn bộ sách dài/mọi giọng hoặc ngân hàng/provider thật.
- Raw evidence (ignored): `android/qa/shelf-build.log`, `shelf-core-tests.log`, `shelf-all-tests.txt`, `shelf-small-light-tests.txt`, `shelf-landscape-dark-tests.txt`, các ảnh `shelf-*.png`.

---

## Lịch sử 0.1.1

# Android QA — 0.1.1 (23/10/2026)

Bản local Android 13+, ARM64, package `studio.windi.soundbooki.preview`, versionCode 2. Emulator AOSP API 35 ARM64; chưa có kiểm tra mới trên Pixel 8 Pro/Redmi Note 13 thật.

- `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest`: PASS. 5 unit tests PASS; bao gồm giữ số chương/remap offset qua cleanup và partition Unicode dài có emoji/khoảng trắng.
- 13 instrumentation tests PASS trên emulator offline. Lần toàn bộ ở cấu hình gốc: 58,789 giây; lần toàn bộ ở màn hình nhỏ 720×1280, density 320, light: 46,006 giây. Bộ thử có Nano/JNI thật, hủy inference, nhập EPUB/PDF/checkpoint, cleanup sách dài, phân trang, khôi phục vị trí, đệm chương 30%, tạo tiếp khi phát, chỉ lưu chương đủ audio, giữ cache khi dừng và Cloud transport fixture. Cloud fixture không gọi dịch vụ/thanh toán thật.
- Sau chỉnh bố cục popup cleanup để toàn bộ tùy chọn cuộn được, 2 test reader/cleanup cuối PASS ở landscape 1280×720, density 320, dark: 8,075 giây. Đã xem trực tiếp ảnh native light portrait/dark landscape và thư viện chương.
- Tái hiện đúng cờ gây crash trước đây: Android ném `IllegalArgumentException: UNICODE_CHARACTER_CLASS flag not supported`. Mã mới không dùng cờ đó. Preview cleanup chạy worker; UI dựng tối đa 100 dòng thay đổi. Fixture 8.000 khối lặp (~400.000 ký tự) mở và áp dụng thành công; không sửa `originalText`.
- File local “Tâm lý học về tiền” 203 trang từ thư viện Mac được **sao chép chỉ vào fixture QA local**, không upload/đóng gói. Nguồn Android nhận 20 heading số/tiêu đề lớn + phần mở đầu = 21 phần. Extraction + reflow + mapping + lưu fixture đo 3.708 giây trên emulator trong lần ghi kết quả; không phải benchmark máy thật, OCR hay tạo giọng cả sách.
- Partition chương/trang giữ đủ ký tự theo thứ tự. Typography nguồn hỗ trợ số và tên chương ở trang kế tiếp; source outline/EPUB heading và mốc thủ công có offset riêng. Sách thiếu bằng chứng vẫn là một phần, không bịa chương từ văn xuôi.
- Player bắt đầu ở ngưỡng >=30% ký tự chương/phần còn lại, producer tiếp tục và ghép WAV nguyên tử trước khi ghi manifest. Fixture dừng khi chưa đủ 30% không phát và không xuất hiện trong thư viện; cache hoàn tất vẫn dùng được. Fixture chọn chương 2 không tạo chương 1/3. Sửa text sau đó vẫn giữ take chương cũ.
- Core Mac/Python regression: 122 tests PASS. Lần đầu sandbox chặn M4A; chạy lại với quyền codec hệ thống thì toàn bộ PASS. Không thay đổi backend Mac trong lượt này.
- APK có đúng bốn ONNX Nano + bảy preset công khai. Đã bỏ tone fallback khi thiếu model, tăng revision cache để tránh dùng nhầm tone bản UI cũ. Không có private F5, dataset, keystore hay `.env` trong ZIP.
- apksigner và ZIP alignment 16 KB: PASS trong build script. Chưa kiểm tra kernel page size 16 KB thật, độ nóng/pin/độ trễ trên hai điện thoại vật lý, hoặc toàn bộ sách với mọi giọng. Chưa phát hành Google Play/notarize/deploy hay bật trả phí.

APK: `dist/android/Soundbooki-0.1.1-arm64-test.apk` — 416.655.303 bytes. SHA-256: `087dff1f41c2a9e00a3546ec2c4b40a6eae213cf4768b208ab4c77c7a8d138c4`.

Raw evidence (ignored): `android/qa/chapter-build.log`, `chapter-all-tests.txt`, `chapter-all-small-light-tests.txt`, `landscape-dark-tests.txt`, `core-regression.log`, `selected-book-result.json`, `reader-small-light.png`, `chapter-library-small-light.png`, `reader-landscape-dark.png`, `cleanup-landscape-dark.png`.

---

## Lịch sử 0.1.0

# Android QA

22/10/2026 — AOSP API 35, ARM64, emulator trên Mac Apple Silicon. Kết quả này không phải benchmark Pixel 8 Pro/Redmi Note 13 thật.

- Pipeline Java + JNI + bốn graph ONNX đã tạo WAV PCM tiếng Việt thật trên host Mac và Android emulator.
- Lần kiểm tra emulator trước bổ sung checkpoint import: 6 instrumentation tests PASS trong 15,071 giây. Bao gồm phân đoạn nguyên văn, chữ gốc/cache/partial WAV/export, EPUB spine/PDF, suy luận Nano thật/hủy, khóa thiết bị/giới hạn mẫu/QR, player native và cloud transport fixture.
- Phép đo inference riêng: model load 0,997 giây, tổng 3,923 giây, output 5,376 giây audio, 2 CPU threads, 16 steps. Không bao gồm first-time asset install của lần này.
- Player đã phát câu đầu trong khoảng 3,27 giây ở fixture sau khi tài nguyên đã chuẩn bị; tiếp tục tạo các đoạn sau. Lần nghe lại cache có hành vi khác, không dùng nó làm số tốc độ inference.
- Cloud fixture kiểm tra request/bearer, giá do server trả, chữ giữ nguyên, chặn tải đơn chưa thanh toán, chặn host khác, từ chối WAV thiếu/hash sai, retry tải đúng và không gửi device bearer đến signed storage. Không có tiền/GPU/provider thật.

Ảnh và raw metrics ở `android/qa/` (ignored). Kết quả cuối sau checkpoint import, theme và đóng gói ghi thêm bên dưới.

## Kết quả cuối

- `./scripts/build.sh --android :app:assembleDebugAndroidTest`: BUILD SUCCESSFUL. APK có 4 graph Nano, 7 preset tiếng Việt, SEA-G2P public, bộ font local (`SFProRounded`, `SVN-Nexa`, `SVN-Georgia`) và âm thanh chào mừng (`welcome.wav`, `piano_podcast_1.mp3`); không có Kitten/English TTS, private F5, .env hay khóa ký.
- Bộ 3 unit tests (`CleanerAndReflowTest.java`): PASS (0 failures, 0 errors). Kiểm tra dọn dẹp các đường kẻ trang trí, số trang đứng riêng, tiêu đề lặp, mục lục dot leader, sửa lỗi quét OCR tiếng Việt (`1àm` -> `làm`, `kh0ng` -> `không`), gỡ gạch nối ngắt từ (`truyền-\nthống`), nối dòng ngắt đoạn PDF và chia chuỗi chương.
- Bản APK kiểm thử UI nhẹ: 128 MB (tạm lược bỏ ONNX models để người dùng test giao diện mượt mà và cài đặt nhanh; `NanoEngine` hỗ trợ chế độ tone giả lập hoạt động trơn tru; khi người dùng duyệt xong UI sẽ thêm lại model đầy đủ).
- Bổ sung các tính năng đồng bộ với Mac:
  1. Cuộn văn bản mượt mà, gỡ bỏ giới hạn cố định `maxLines`.
  2. Phân đoạn chương (`chapterSpinner`) và phát âm thanh từ chương được chọn.
  3. Dọn nội dung (`CleanupDialog`) xem trước các thay đổi và áp dụng an toàn.
  4. Sắp xếp lại bố cục PDF (`PdfReflow`) tự động căn chỉnh các đoạn bị ngắt dòng.
  5. View đọc sách (`ReaderDialog`) giao diện toàn màn hình với tùy chọn Serif/Sans và cỡ chữ A−/A+.
  6. Thư viện audio đã tạo (`AudioLibraryDialog`) nghe lại và chia sẻ file WAV.
  7. Nhạc nền khi nghe (`PlaybackService`) looping êm ái với các bài Piano, Mưa nhẹ, Late night cùng 4 mức âm lượng.
  8. Hiệu chỉnh âm thanh Walkthrough: BGM fade-in trước, voice phát sau 0,8s với âm lượng đầy đủ không bị nuốt chữ đầu.
  9. Quản lý sách chuyển gọn gàng vào Cài đặt; tạm ẩn panel hero trên cùng.
- Bộ 7 instrumentation tests trên APK cuối: PASS trong 19,820 giây, kiểm tra đầy đủ phân đoạn nguyên văn, resume EPUB từ checkpoint, suy luận Nano thật, Walkthrough 5 bước kèm âm thanh chào mừng + bật/tắt âm, player native và cloud transport fixture.
- Phép thử native dark mode đã cập nhật để chọn đúng thư viện fixture theo Activity class: PASS trong 13,285 giây. Xác nhận mở Walkthrough 5 bước, bấm Nghe trên đúng văn bản, audio tiếp tục khi Activity xuống nền, pause lưu vị trí > 0, mở popup Cloud local, stop giữ cache. Ảnh sáng/tối (`home`, `walkthrough-1`, `walkthrough-5`, `playing`, `cloud-unconfigured`) đã xem trực tiếp.
- apksigner verification PASS; ZIP alignment 16 KB PASS. Tất cả LOAD segment của 4 thư viện ARM64 có alignment >= 0x4000; JNI chỉ phụ thuộc tên `libsea_g2p_rs.so`, không còn đường dẫn máy build. Chưa chạy trên cấu hình kernel 16 KB thật.
- APK: 382,56 MiB (~401 MB), `studio.windi.soundbooki.preview`, version `0.1.0-test`, minSdk 33, targetSdk 36, chỉ arm64-v8a.
- SHA-256: `226d86b434c00c50314363668a3990c63d5451452a37be18b39d91b9b810b7ee`.
- Wi-Fi và data emulator được tắt trong kiểm tra local. Phần Cloud chỉ có bằng chứng fixture; không kích hoạt gateway, chi tiêu GPU, chuyển tiền hoặc upload sách cá nhân.
- Chưa cài APK lên Pixel 8 Pro hoặc Redmi Note 13 vật lý. Chưa khẳng định độ trễ, pin, nhiệt máy hoặc độ liền mạch đọc sách dài trên hai máy đó.
