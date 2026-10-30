> **Local 0.2.7 · versionCode 10:** M4B có chương/bìa, đọc Việt–Anh bằng Lite + giọng Anh offline hệ thống, tìm nội dung, tô đoạn/ghi chú/sổ tay và dán văn bản. APK: `../dist/android/Soundbooki-0.2.7-arm64-test.apk`. Xem [cách dùng/giới hạn/QA](../docs/READING-TOOLS.md).

> Bản local **0.2.6**: lật giấy theo vuốt / trượt / tắt hiệu ứng, sáu nền đọc, nhiều dấu trang kèm ghi chú, giãn dòng/lề/độ sáng và giữ vị trí khi xoay máy. APK: `../dist/android/Soundbooki-0.2.6-arm64-test.apk`, versionCode 9, cùng signer test để cài đè. Xem [hướng dẫn reader](READER-FEATURES.md). Các bản bên dưới là lịch sử.

> Bản local **0.2.5**: tối ưu màn đọc PDF/EPUB bằng dàn trang theo khối trên worker, cache bốn bố cục và giữ đúng offset khi đổi cỡ chữ/ẩn điều khiển. APK: `../dist/android/Soundbooki-0.2.5-arm64-test.apk`, versionCode 8, cùng package/signer test để cài đè. Xem [hiệu năng reader](READER-PERFORMANCE.md).

> Bản local **0.2.4**: tổng **5 lượt Pro miễn phí trọn đời/thiết bị**, giữ số đã dùng. Mặc định **Tạo thử · 1 lượt** (5.000 ký tự); tùy chọn **Tạo chương · Tối đa 4 lượt** tính đúng số lượt cần thiết và giới hạn 20.000 ký tự. Gateway mới cần SQL/RPC quota 5; chưa bật dịch vụ Pro thật. Các phiên bản bên dưới là lịch sử.

> Bản local **0.2.3**: tự tính/gộp 1–4 lượt Pro miễn phí theo chương (5.000 ký tự/lượt, tối đa 20.000 mỗi yêu cầu), xác nhận rõ số lượt; retry giữ request key, không coi mẫu cũ ngắn là chương đầy đủ. Tổng vẫn 10 lượt/thiết bị. Cần gateway/RPC gộp mới; chưa bật dịch vụ Pro thật.

> Cập nhật 23/10/2026: bản **0.2.2** thêm **Hồ sơ** ở Trang chủ/Cài đặt, tên local, mã máy, quota có trạng thái xác minh, kiểm tra quota theo hành động và đường vào combo. Chi tiết sách có **Tạo thử chương này · Pro**, xem trước đúng chương, tối đa 5.000 ký tự, không lấy tiếp chương sau. Combo Android hiện là màn thông tin, chưa mở mua. Owner chốt thiết bị độc lập, không Google login/sync; Play Billing chưa triển khai. Xem [thanh toán/queue](../docs/DEVICE-PAYMENTS-AND-QUEUE.md). Không coi profile local là tài khoản đăng nhập.

# Soundbooki Android — bản thử 0.2.6

APK: `../dist/android/Soundbooki-0.2.6-arm64-test.apk`.

Bản cài thử riêng cho Android 13+ (API 33), ARM64. Hai máy người dùng chọn là Pixel 8 Pro và Redmi Note 13; chưa có bằng chứng chạy trên hai máy thật này. Đây không phải bản phát hành Google Play.


## Tạo sách nói có thể nghỉ và tiếp tục

- Bắt đầu phát sau khi tạo được khoảng 500 ký tự đầu của chương (hoặc phần còn lại nếu ngắn hơn); tiến độ tạo vẫn được lưu theo từng đoạn.
- **Tạm dừng tạo**: hoàn tất đoạn đang xử lý rồi lưu và nhả model khỏi RAM. **Tiếp tục tạo** dùng lại WAV hợp lệ; không phải tạo từ đầu. Tạm dừng nghe là điều khiển riêng.
- Tiến độ lưu riêng trên thiết bị. Sau khi mở lại app, chọn **Tiếp tục tạo sách nói** ở Home hoặc **Tiếp tục tạo** trong màn nghe. Audio chưa tự phát khi khôi phục; bấm Nghe khi sẵn sàng.
- Bấm Home/rời app/khóa màn hình vẫn tạo chương hiện tại. Nút Dừng hoặc buộc dừng app sẽ dừng; Android không bảo đảm service sống sau khi hệ thống kết thúc process. Mở lại để tiếp tục bằng cache. Giới hạn xử lý nền và tiết kiệm pin của điện thoại vẫn áp dụng.
- Giữ 16 bước Nano, một producer, mặc định 2 CPU threads; ưu tiên vùng sắp nghe và tái dùng cache. Không có số đo tốc độ/pin mới trên điện thoại vật lý.

## Tủ sách và trình nghe (0.2.1)

Thanh dưới có Trang chủ / Thư viện / Tạo sách / Đang nghe / Cài đặt. Tủ sách hiển thị sách đã nhập thật; bìa lấy từ EPUB/PDF hoặc dùng bìa chữ nếu nguồn không có ảnh. Có tìm kiếm, đánh dấu sách, danh sách chương và tab các bản sách nói hoàn tất.

Màn hình nghe riêng có timeline chương, tua ±15 giây, chương tiếp, tốc độ, hẹn giờ ngủ và văn bản của đoạn đang phát. Timeline chỉ cho kéo khi đủ audio chương; lúc đang tạo chỉ hiển thị thời lượng đã có. Thay đổi tốc độ là thiết lập player, giữ cache. Trình nghe và chi tiết sách dùng toàn màn hình với nút back; các trang chính giữ nav và mini player khi đang phát.

**Nghe thử giọng Pro** có ngay trên Home, Cài đặt và phần chọn giọng, đồng thời ở popup Pro theo sách. Bảy mẫu owner-local được đóng gói và phát offline; nghe mẫu không gửi sách/không tạo đơn. Nút Thử với sách này chỉ mở luồng Pro cũ, vẫn cần gateway và đồng ý gửi chữ. Bản thử không kích hoạt dịch vụ trả phí hay quyền xuất bản recording.

Xem `DESIGN.md` cho luồng/bố cục và `QA.md` cho bằng chứng cùng giới hạn.

## Cài và thử

1. Chép APK sang điện thoại rồi mở file để cài. Android có thể yêu cầu cho phép ứng dụng quản lý file cài APK từ nguồn này.
2. Mở Soundbooki Test. Model Nano, bộ phát âm và bảy giọng tiếng Việt công khai đã ở trong APK. Lần nghe đầu, app sao chép/kiểm checksum tài nguyên vào vùng riêng; không tải model qua mạng.
3. Dán chữ, hoặc chọn **Thêm sách** để nhập EPUB, PDF có lớp chữ, TXT UTF-8/UTF-16 có BOM. PDF scan chưa có OCR trong bản thử. File nguồn và chữ gốc được giữ riêng.
4. Chọn chương/giọng, bấm **Nghe**. App tạo khoảng 500 ký tự đầu rồi tự phát, đồng thời tiếp tục tạo phần còn lại trong nền. Nếu chương ngắn hơn, app phát khi đã tạo xong chương. Khi hoàn tất, chương được ghép thành một WAV và đưa vào **Sách nói của bạn**. Chọn “Toàn bộ sách” để tiếp tục lần lượt qua các chương. Nhấn giữ Nghe để nghe từ đầu; nhấn bình thường để nghe tiếp vị trí đã lưu. Có Tạm dừng, Dừng và điều khiển thông báo khi ở nền.
5. Vào Tạo sách / Sửa nội dung để chỉnh chữ; thay đổi được tự lưu. Đổi chữ/giọng dừng bản đọc đang chạy và dùng cache đúng nội dung mới. Tốc độ phát không làm mất cache. Xuất WAV nhận toàn bộ sách sau khi đủ audio, không xuất một phần rồi gọi là đầy đủ.
6. Trong Cài đặt, thử 2 hoặc 4 luồng CPU. Muốn so tốc độ tạo mới, dùng đoạn chữ/giọng chưa có cache. Dòng “Âm thanh đầu” đo thời gian tới lần phát đầu; lần đầu còn gồm chuẩn bị tài nguyên/model. Audio có sẵn được ghi là cache.

Khi import bị ngắt, mỗi trang PDF hoặc mục spine EPUB đã hoàn tất có checkpoint nguyên tử. Mở lại sách trong Thư viện và chọn **Tiếp tục nhập các trang còn lại**. Không tự viết lại chữ hoặc đoán chương từ văn xuôi. Mốc EPUB lấy từ heading có trong nguồn. PDF ưu tiên outline; nếu không có thì nhận chuỗi số/tiêu đề lớn đã xác minh từ typography (kể cả số và tên ở hai trang kế tiếp). Sách cũ được đọc lại mốc từ file gốc ở nền, giữ nguyên chữ đang sửa. Nếu nguồn không có mốc rõ, dùng **Đặt mốc chương tại con trỏ**. Khi sửa nội dung, tọa độ nguồn cũ không được dùng để chọn mẫu Cloud.


## Đọc và nghe theo chương (23/10/2026)

- View đọc là trang vừa màn hình, vuốt ngang hoặc bấm ‹ / › để lật; chạm giữa trang để ẩn/hiện điều khiển. Có mục lục, đổi phông/cỡ chữ, đánh dấu trang, kéo thanh vị trí và mở lại đúng vị trí theo bản chữ. Số trang đọc thay đổi theo màn hình/cỡ chữ, không phải số trang PDF gốc.
- “Dọn nội dung” chạy trên worker, chỉ dựng tối đa 100 dòng xem trước. Đã bỏ cờ regex Java không hỗ trợ trên Android gây crash khi mở. Chương từ nguồn được bảo vệ và remap sau khi dọn; `originalText` không đổi.
- Chọn chương giới hạn cả tạo/nghe và xuất WAV theo chính phần chữ của chương, kể cả chương bắt đầu giữa trang nguồn. App đệm khoảng 500 ký tự đầu (hoặc phần còn lại nếu ngắn hơn) trước khi phát; đây là ngưỡng đệm, không đảm bảo không đứt tiếng trên mọi điện thoại.
- Audio từng đoạn chỉ là cache/checkpoint nội bộ. Thư viện đọc manifest nhỏ và dùng danh sách tái sử dụng view; chỉ chương hoàn tất mới xuất hiện. Dừng giữa chừng giữ đoạn hoàn tất để tiếp tục; chương chưa xong không được coi là bản sách nói đầy đủ. Các take đã hoàn tất giữ giọng và bản chữ cũ sau khi chỉnh sửa.
- APK mặc định có model thật. Bản 0.1.1 bỏ tone giả lập khi thiếu model và đổi revision cache để không dùng nhầm tone từ bản UI trước. Có thể chủ động đặt `INCLUDE_NANO_MODELS=0` để build UI-only; bản đó báo thiếu model khi nghe.

## Lite local

- Java + ONNX Runtime Android 1.24.3, CPU. Không đóng gói Python/PyTorch.
- VieNeu v3 Nano, model revision `aba295eb96a6fa6003ebe417cc1f2802a7adc1dc`, CFG 3, 16 Euler steps, 24 kHz.
- Bảy giọng theo bản Mac hiện tại; mặc định Đức Trí. Không có model tiếng Anh, Turbo, Clone Pro/Pro Max, private F5 hoặc dữ liệu train.
- SEA-G2P 0.10.0, source commit `dae5ca83ea45f356c43bdb70a1bcd42e8729ff16`, C ABI + JNI. Từ điển public đi kèm; phát âm số/ngày chỉ diễn ra trong synthesis, không sửa chữ đã lưu.
- Audio ghi `.partial`, fsync rồi đổi tên nguyên tử; đoạn chưa hoàn tất không được coi là audio dùng được. Cache theo chữ + giọng + revision engine. Stop giữ các file hoàn tất.
- Không analytics. Tắt telemetry ORT. Manifest không có quyền đọc toàn bộ bộ nhớ; nhập/xuất qua system document picker.

## Pro Cloud

Client có sẵn bảy giọng HeyGen theo `backend/book_pricing.py`, tạo mẫu mở đầu/chương đã chọn tối đa 5.000 ký tự, báo giá sách, QR VietQR sinh local từ báo giá server, lịch sử đơn, kiểm tra/nhận WAV đã xác minh SHA-256, nghe và xuất audio của đúng snapshot đã mua. Mẫu thử không có nút xuất.

**Chưa có endpoint Cloud trong APK.** Vào Cài đặt, nhập URL HTTPS gateway được owner cung cấp. Đây là đúng trạng thái chờ kích hoạt của bản Mac trong `docs/BOOK-COMMERCE.md`: gateway/migration/dispatcher HeyGen chưa được triển khai. Build Android này không deploy, không bật bán và không chạy inference trả phí.

Mở popup/đổi giọng không gửi chữ. Tạo mẫu hoặc gửi toàn bộ chữ để báo giá đòi hỏi đồng ý rõ ràng. Request key và snapshot được lưu trước khi POST; retry sau timeout dùng lại yêu cầu đó. Báo giá, quota, trạng thái trả tiền do server quyết định; mã thanh toán không tự xác nhận tiền. Không có merchant/proxy/service-role key trong app. Có mã thiết bị hash từ Android ID theo app + một bearer ngẫu nhiên riêng, mã hóa bằng Android Keystore, tách theo endpoint. App không cần tài khoản/email. Android là thiết bị thử riêng, không chuyển đơn hoặc dùng danh tính/Keychain của Mac.

Polling chỉ khi popup còn mở và app ở foreground, tối đa 30 lần cách 10 giây. Đóng popup/tắt màn hình dừng lịch kiểm tra. Một HTTP đã gửi có thể hoàn tất; không tự mở popup lại. Signed audio chỉ tải đúng origin gateway và đúng bucket/order, không gửi bearer thiết bị tới storage. Thiếu/khác hash không thay thế file hoàn tất. Đơn cũ giữ snapshot và endpoint riêng sau khi sửa sách/đổi giọng.

Combo ra mắt hiện dành cho Mac; bản thử Android này không tự mở rộng combo hoặc annual subscription sang điện thoại. Không có luồng mua credit/Pro Max cũ.

## Build local

```sh
./scripts/build.sh --android
```

Script dùng JDK 17, SDK 36, Build Tools 36.0.0, NDK 27.1.12297006, CMake 3.22.1; Gradle 8.13 + AGP 8.12.0. Mặc định SDK có sẵn tại `~/Library/Android/sdk`, Java Homebrew 17. Có thể đặt `JAVA_HOME`, `ANDROID_HOME`, `NANO_MODELS_ROOT` để dùng đường khác. `prepare_assets.py` chỉ đọc/copy các file Nano khớp SHA-256 trong manifest, cùng preset public và từ điển; không lấy runtime/key/dữ liệu người dùng từ Windi Dubbing.

Rust được cài trong `android/.tooling/cargo`, `RUSTUP_HOME=android/.tooling/rustup`, profile minimal, target `aarch64-linux-android`. Không sửa cấu hình shell toàn cục. Lệnh cross-build có trong `scripts/build-android.sh`. Source SEA-G2P và Cargo.lock được vendored theo commit ở trên. Có thể dùng rustup chính thức với `--no-modify-path` và hai biến thư mục này khi dựng máy mới.

Gradle wrapper có SHA-256 distribution đã khóa. Build cache, Android user home và khóa ký test đều nằm dưới `android/.tooling`, không đóng gói vào APK. Giữ `preview.keystore` local để cài đè bản thử sau mà không đổi signer. Không dùng khóa này để phát hành. Model/runtime binary lớn được stage khi build và nằm trong `.gitignore`.

Đầu ra có checksum `dist/android/SHA256SUMS.txt`, chữ ký test được kiểm tra bằng apksigner và ZIP alignment 16 KB. Đây không phải chứng nhận đã chạy trên máy cấu hình page size 16 KB.

## Kiểm tra

Bộ Android instrumentation nằm trong `app/src/androidTest`, dùng thư viện riêng trên AOSP emulator API 35 ARM64. Đường local được chạy khi Wi-Fi và dữ liệu di động của emulator tắt. Kiểm tra Cloud dùng transport fixture nội bộ, không gọi gateway/provider/thanh toán thật. Xem `QA.md` để biết bằng chứng và giới hạn.
