# Android 0.2.7 — gói Play (28/10/2026)

Gói upload: `dist/android/Soundbooki-0.2.7-play-fixed.aab`, package `windi.soundbooki`, versionCode 10. Đã build release, kiểm tra chữ ký, chạy bundletool validate và build-apks; chưa được Play Console chấp nhận hoặc kiểm tra cài đặt từ Google Play. Build lại bằng `zsh scripts/package-android-play.sh`.

Khóa upload và mật khẩu nằm trong `android/.tooling/play-upload/`, cần sao lưu riêng và giữ bí mật. Bảy bản ghi mẫu Pro và bản chào owner-local chỉ được chuẩn bị vào assets của bản debug; nghe thử các mẫu và giọng chào trong walkthrough không khả dụng trong gói Play.

---

# Android 0.2.7-test — đổi package ID (28/10/2026)

Package ID: `windi.soundbooki`. APK local: `dist/android/Soundbooki-0.2.7-arm64-test.apk`, versionCode 10. Bản ARM64, Android 13+; ký bằng khóa preview local, chỉ dùng để cài thử, không tải lên Google Play Console.

---

# Android 0.2.6 — trải nghiệm đọc ebook (24/10/2026)

APK local: `dist/android/Soundbooki-0.2.6-arm64-test.apk`, versionCode 9. Cùng package/signer test, cài đè giữ thư viện. Hướng dẫn và bằng chứng: [READER-FEATURES.md](READER-FEATURES.md).

- Lật giấy theo ngón tay, trượt nhẹ hoặc tắt hiệu ứng. Vuốt chưa hoàn tất/hủy không làm mất vị trí. Tôn trọng giảm chuyển động và TalkBack; chỉ giữ tối đa hai ảnh viewport rồi nhả khi kết thúc.
- Bảy nền local, cỡ chữ, phông, giãn dòng, lề, độ sáng riêng màn đọc và giữ màn hình sáng; lưu riêng từng sách. Nền **Đen** là `#000000`, chỉ áp dụng cho trang đọc; palette xanh đậm của app không đổi. Đổi nền không dàn trang lại.
- Có thể chọn PDF/EPUB từ app khác bằng **Mở bằng** hoặc **Chia sẻ** vào Soundbooki. Cả hai dùng chung importer, nhận loại file từ phần mở rộng hoặc MIME, rồi giữ file nguồn và `originalText` như luồng chọn file trong app.
- Nhiều dấu trang có ghi chú, danh sách chạm để quay lại, nhấn giữ sửa/xóa. Di chuyển dấu cũ vào danh sách; giữ đúng offset theo hash bản chữ, không gắn dấu cũ sang nội dung đã sửa.
- Giữ reader/vị trí/nền khi Android tạo lại Activity; lề được đo từ vùng chữ thực. Kiểm tra lại trang độc lập trước khi dùng ranh giới từ khối chữ để tránh cắt dòng ở font hệ thống lớn.

---

# Android 0.2.5 — tối ưu màn đọc (23/10/2026)

Bản hiện tại: `dist/android/Soundbooki-0.2.5-arm64-test.apk`, versionCode 8. Cùng package/signer test; cài đè giữ dữ liệu trên thiết bị.

- `ReaderPaginator` đo từng khối chữ một lần rồi dùng các dòng đã đo cho nhiều trang. Chỉ mang trang cuối chưa đủ sang khối kế; giữ ranh giới chương và phân hoạch UTF-16 nguyên văn. Vẫn dùng native TextView và gắn đúng một trang.
- `ReaderDialog` gộp yêu cầu dàn lại 40 ms, hủy tác vụ cũ, giữ bốn bộ ranh giới trang theo viewport/phông/cỡ chữ. Anchor nguồn tồn tại chính xác qua đổi cỡ chữ, ẩn/hiện điều khiển và mở lại; tác vụ đã hủy không trả về UI. Trạng thái nghe chỉ đổi nhãn khi cần, không tạo layout lại mỗi tick.
- Đã build APK đầy đủ model Lite. Phép đo trên emulator với chữ từ PDF 203 trang: mở 1.821 → 582 ms; đổi cỡ 30: 3.309 → 285 ms. Không phải số đo máy thật. Chi tiết/giới hạn: `READER-PERFORMANCE.md`, `QA.md`.

---

# Android 0.2.1 — tạo Nano có thể dừng/tiếp tục (23/10/2026)

Bản hiện tại: `dist/android/Soundbooki-0.2.1-arm64-test.apk`, versionCode 4. Cùng package/signer test; cài đè giữ thư viện. Các mốc bên dưới là lịch sử.

- Ngưỡng bắt đầu phát hiện là khoảng 500 ký tự đầu chương (hoặc phần còn lại nếu chương ngắn hơn); giao diện không hiển thị quy tắc đệm. Hai icon tua 15 giây được vẽ lại; điều khiển vẫn đi qua WAV đã sẵn sàng.
- **Tạm dừng nghe** và **Tạm dừng tạo** độc lập. Dừng tạo hoàn tất một đoạn đang xử lý, lưu WAV/checkpoint nguyên tử rồi đóng ONNX sessions và nhả CPU nếu không phát audio. Tiếp tục trong cùng service đánh thức worker; mở lại app có nút tiếp tục trên Home/màn nghe và giữ audio ở trạng thái tạm dừng.
- `GenerationProgress` lưu yêu cầu chương/continuous, hash chữ+giọng+engine và ranh giới chương, phần trăm và đoạn hoàn tất ở `library/<book>/generation.json`. File riêng tránh editor cũ ghi đè. Cache WAV được kiểm tra RIFF trước khi dùng; checkpoint counter không xác nhận audio. Đổi text/voice/revision không cho resume snapshot cũ. `.partial`/WAV hỏng phải tạo lại. Dừng/buộc dừng không làm mất đoạn hoàn tất.
- Producer ưu tiên phần còn lại từ vị trí nghe, rồi mới bổ sung prefix còn thiếu để ghép chương theo đúng thứ tự. Cache hợp lệ không ghi lại; chỉ checkpoint mới hoàn tất mới fsync từng đoạn, cache đã bền vững không fsync lặp. Giữ 16 bước CFG=3, một producer, mặc định 2 CPU threads, ONNX spinning tắt. Không đổi chất lượng model để đổi lấy tốc độ.
- Rời activity/bấm Home/khóa màn hình: foreground service tiếp tục chương hiện tại, có partial wakelock được nhả khi hết việc. Android 15+ khai báo `mediaProcessing` khi đang tạo; Android 13–14 dùng local-file `dataSync`, playback vẫn là `mediaPlayback`. Bỏ processing type khi nghỉ. `onTimeout` giữ tiến độ và dừng; không tự khởi động sau force-stop hoặc khởi động máy. Android áp hạn mức background processing; mở app và chọn tiếp tục nếu bị ngắt. Không tự tạo các chương tiếp theo khi đang dừng nghe ở cuối chương hiện tại.
- Không gọi cloud/paid, upload, analytics, hay đóng gói private model. QA và giới hạn máy thật ở `QA.md`.

---

# Android 0.2.0 — redesign tủ sách (23/10/2026)

Bản hiện tại: `dist/android/Soundbooki-0.2.0-arm64-test.apk`, versionCode 3. Cùng package/signer test để cài đè; giữ thư viện, thanh toán/đơn cũ và các thiết lập.

- `AppShell` thêm Home dạng kệ, Library có tìm/lọc/lưu sách, chi tiết chương, Create bọc workspace cũ, player riêng và Settings. Giữ palette/font local hiện có; không có số lượt nghe/catalog giả. Player toàn màn hình; màn khác có mini player. Tải metadata/cover ở worker, không render lại toàn thư viện theo progress tick.
- `BookArtwork` dùng bìa trong file nguồn; fallback là jacket chữ Canvas. `VoicePreview` có bảy mẫu Pro owner-local, waveform thật, quản lý focus và dừng khi app xuống nền/đóng popup. Build stage theo whitelist và ignore khỏi Git; không gọi provider, không phát hành public recordings.
- Player thêm duration/position thật theo WAV, tua ±15s và kéo timeline đủ chương, giữ vị trí khi pause, hẹn giờ ngủ monotonic và scope continuous tùy chọn. Văn bản theo đúng segment; chặn theo dõi take cũ sang text mới.
- Import/dọn/chương/reader/Cloud workflow hiện có vẫn được MainActivity sở hữu. Mẫu Pro offline khác với tạo thử chữ sách; gateway/paid/dispatcher/publication vẫn hoãn.
- Xem `DESIGN.md`, `QA.md` cho luồng, kiểm thử và giới hạn. Chưa có QA mới trên Pixel 8 Pro / Redmi Note 13 thật.

---

# Android 0.1.1 — cập nhật 23/10/2026

Mốc 0.1.0 bên dưới là lịch sử. Bản hiện tại: `dist/android/Soundbooki-0.1.1-arm64-test.apk`, versionCode 2, có đủ model Lite thật.

- Đã sửa crash Dọn nội dung do `Pattern.UNICODE_CHARACTER_CLASS` không hỗ trợ trên Android; preview chạy worker và giới hạn 100 dòng UI.
- `BookChapters.java` là nguồn phạm vi dùng chung cho reader/player/export. `PdfChapterSource.java` đọc typography/outline một lượt, xác minh chuỗi số; heading EPUB và mốc thủ công được giữ. Anchor source chỉ tái dùng khi chữ khớp, cho phép whitespace/wrap-hyphen của reflow cũ. Text sửa khác không dùng tọa độ cũ. Cleanup bảo vệ dòng đầu chương và remap offset sau khi bỏ dòng.
- Player đệm 30% chương, tạo tiếp đến hết chương. Chỉ chạy producer trong chương hiện tại, không tạo cả sách trong lúc pause. `ChapterAudio.java` ghép WAV nguyên tử rồi ghi manifest hoàn tất; thư viện dùng các manifest, không quét/render hàng nghìn đoạn. Take cũ không đổi theo text/voice mới.
- Reader phân trang bằng StaticLayout trên worker, gắn đúng một trang lên UI. Có vuốt, nút trang, mục lục, cỡ chữ/phông, bookmark, khôi phục offset theo hash bản chữ, chế độ đọc ẩn điều khiển và bố cục gọn cho landscape.
- Đã bỏ silent mock-tone fallback và tăng cache revision `nano-aba295eb-java-cfg3-16-v2-real`. Build mặc định có model; không dùng cache tone của bản UI cũ.
- Kiểm thử/giới hạn hiện tại: xem `QA.md`. Chưa có bằng chứng mới trên Pixel 8 Pro/Redmi Note 13 thật. Cloud/deployment/paid vẫn tách riêng.

---

# Mốc lưu Android để tối ưu sau

Ngày 22/10/2026: người dùng xác nhận tính năng tạm ổn và yêu cầu lưu Graphify. Giữ bản thử hiện tại làm mốc; các mục dưới đây là việc còn lại, chưa phải thay đổi đã thực hiện.

## Bản đang lưu

- Soundbooki Test `0.1.0-test`, `studio.windi.soundbooki.preview`, Android 13+, ARM64.
- APK: [`Soundbooki-0.1.0-arm64-test.apk`](../dist/android/Soundbooki-0.1.0-arm64-test.apk), bản nhẹ phục vụ kiểm thử UI (khoảng 128 MB, tạm bỏ graph ONNX theo yêu cầu để build và test UI nhanh; `NanoEngine` hỗ trợ mock tone khi vắng model).
- Giao diện đồng bộ với bản Mac (`UiTheme.java`): font local `SF Pro Rounded` + `SVN Nexa` + `SVN Georgia`, nền glassmorphism/radial glow, icon vector riêng, nút lớn dễ thao tác (`48dp–54dp`).
- Cuộn nội dung mượt mà: gỡ bỏ giới hạn cố định `maxLines` trong ô soạn thảo, tắt `nestedScrollingEnabled` để kéo cuộn toàn bộ tài liệu dài trên điện thoại không bị kẹt cảm ứng.
- Phân đoạn và chọn chương (`chapterSpinner`): tự động nhận diện danh sách chương từ sách (`PdfReflow.extractChapters`), cho phép chuyển nhanh con trỏ đến từng chương và phát audio trực tiếp từ chương đã chọn.
- View đọc sách toàn màn hình (`ReaderDialog.java`): giao diện giấy đọc phân tâm tối thiểu, chuyển đổi font Serif / Sans-Serif, nút tăng giảm cỡ chữ A− / A+, chọn chương và dock mini player đồng bộ.
- Dọn dẹp nội dung (`CleanupDialog.java`, `ContentCleaner.java`): port đầy đủ 5 tiêu chuẩn dọn dẹp bảo toàn từ Mac (đường kẻ trang trí, số trang đứng riêng, tiêu đề lặp, mục lục dot-leader và sửa lỗi gõ/quét OCR tiếng Việt mà không đổi câu chữ).
- Sắp xếp bố cục PDF (`PdfReflow.java`): tự động nối các dòng bị ngắt giữa chừng do chia cột, gỡ gạch nối ngắt từ qua dòng (`truyền-\nthống` -> `truyền thống`), phát hiện chuỗi chương đánh số.
- Thư viện audio đã tạo (`AudioLibraryDialog.java`): quản lý và nghe lại toàn bộ các đoạn/bản đọc đã xuất, chia sẻ file WAV qua `FileProvider`.
- Nhạc nền khi nghe (`PlaybackService.java`): hỗ trợ chọn nhạc nền looping (`Piano podcast`, `Whitenoise mưa nhẹ`, `Late night`) với mức âm lượng tùy chỉnh (10%, 18%, 25%, 35%) tự động đồng bộ theo nhịp phát/dừng của giọng đọc.
- Walkthrough 5 bước trên điện thoại (`WalkthroughDialog.java`, `WelcomeAudioPlayer.java`): hiệu chỉnh thời gian phát âm thanh: nhạc nền fade-in trước, giọng chào `welcome.wav` bắt đầu sau 0,8s ở mức âm lượng trọn vẹn (không fade voice) giúp nghe rõ ràng từng từ đầu tiên.
- Quản lý sách trong Cài đặt: chuyển "Thêm sách mới" và "Thư viện trên máy" vào hộp thoại Cài đặt; tạm ẩn panel hero card trên cùng để tập trung bề mặt đọc & chỉnh sửa.
- Nhập EPUB/PDF có lớp chữ/TXT → xem và sửa → nghe; giữ chữ gốc, checkpoint nhập, cache đúng chữ/giọng/revision, phát nền, lưu vị trí và xuất WAV khi đủ audio.
- Client Pro Cloud có mẫu thử, báo giá, QR, lịch sử và nhận audio theo snapshot. APK chưa cấu hình endpoint; gateway/dispatcher HeyGen và kích hoạt trả phí vẫn hoãn. Không coi fixture là bằng chứng thanh toán hoặc provider thật.

## Bằng chứng của mốc này

Xem [`QA.md`](QA.md) cho kết quả đầy đủ: 7 instrumentation tests PASS trên AOSP API 35 ARM64 emulator; phép thử dark mode/phát nền riêng PASS; inference Nano tạo WAV thật khi mạng emulator tắt; apksigner và ZIP alignment 16 KB PASS. Chưa kiểm tra kernel 16 KB thật.

Phép đo emulator riêng: load model 0,997 giây, tổng inference 3,923 giây cho 5,376 giây audio, 2 CPU threads / 16 steps, không gồm sao chép tài nguyên lần đầu. Đây không phải benchmark điện thoại thật.

## Khi tiếp tục tối ưu

1. Cài đúng APK/checksum trên **Pixel 8 Pro và Redmi Note 13**. Ghi Android version, biến thể chip/RAM của Redmi, trạng thái máy và đoạn chữ/giọng; hiện chưa có kết quả từ hai máy thật.
2. Đo riêng lần mở mới, sao chép tài nguyên lần đầu, nạp model, thời gian có âm thanh đầu và nghe lại cache. Đọc dài để đo thời gian tạo audio so với độ dài audio, khoảng đứt tiếng, RAM cao nhất, nhiệt và pin.
3. So 2/4 CPU threads trên cùng fixture chưa có cache. Chỉ đổi chunk/prefetch/khởi động model khi có số đo; giữ phân đoạn nguyên văn, giới hạn bộ đệm, khả năng hủy và cache hợp lệ. Nếu đổi thuật toán synthesis, tăng engine revision.
4. Khảo sát giảm dung lượng APK và chi phí sao chép tài nguyên; chỉ thay model/quantization khi đã nghe so sánh chất lượng tiếng Việt và kiểm tương thích. Hiện tài nguyên được đóng gói sẵn, không tự tải qua mạng.
5. Kiểm tra đọc liên tục, khóa màn hình, tiến trình bị dừng rồi mở lại, import bị ngắt và xuất sách dài trên máy thật. PDF scan/OCR chưa thuộc khả năng bản thử này.
6. Cloud là việc kích hoạt riêng: cần xác nhận phạm vi deployment/paid trước khi triển khai hoặc dùng quota. Không đặt merchant/proxy key trong APK, không mở rộng combo Mac sang Android.

## Điểm bắt đầu trong mã

- UI & Walkthrough: `app/src/main/java/studio/windi/soundbooki/MainActivity.java`, `UiTheme.java`, `WalkthroughDialog.java`, `WelcomeAudioPlayer.java`.
- Suy luận/phát âm/tài nguyên: `NanoEngine.java`, `Phonemizer.java`, `ModelAssets.java` trong cùng thư mục Java.
- Nhập/lưu/phân đoạn: `BookImporter.java`, `BookStore.java`, `TextChunks.java`.
- Phát/cache/xuất: `PlaybackService.java`, `AudioFiles.java`.
- Cloud: `CloudClient.java`, `CloudIdentity.java`, `PaymentQR.java`.
- Build: `../scripts/build-android.sh`, `scripts/prepare_assets.py`; hướng dẫn [`README.md`](README.md).
- Graphify: [`GRAPH_REPORT.md`](../graphify-out/GRAPH_REPORT.md), [`graph.json`](../graphify-out/graph.json), [`graph.html`](../graphify-out/graph.html). Sinh lại bằng `.runtime/bin/python scripts/generate_graphify.py` ở thư mục gốc; không sửa riêng file sinh ra.

Build lại khi cần: `./scripts/build.sh --android`. Không cần build/suy luận lại chỉ để cập nhật ghi chú Graphify.
