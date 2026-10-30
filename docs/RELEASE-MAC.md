# Chuẩn bị bản Mac Free / Pro — 0.6.0 preview

Điều chỉnh sau phản hồi UI ngày 21/10/2026: Turbo đã ngừng cung cấp, chỉ dùng Nano cho lựa chọn tiếng Việt miễn phí; Kitten tiếng Anh và gói Pro gồm 6 giọng riêng F5 vẫn giữ. Không có thẻ mua hoặc nút nâng cấp trên màn hình đọc. Chọn F5 bị khóa sẽ mở chi tiết gói, nút mua nằm bên trong. Các tệp/audio Turbo cũ được giữ, không phát sinh tải/tạo Turbo mới. Phần tiến độ tạo nằm dưới thanh chọn giọng; bỏ toast bắt đầu tạo ở dưới và đưa panel phạm vi lên cạnh vùng điều khiển trên.

QA lần điều chỉnh: 70 core tests; WKWebView fixture xác minh tiến độ chuẩn bị/25%/hoàn tất, hủy và lỗi, không hiện upsell lúc mở, F5 mở chi tiết trước khi mua. Inference Nano thật trên 9 đoạn được chọn: 1 đoạn cache lúc bắt đầu, hủy giữ 2 đoạn, tiếp tục đạt 9/9, 1 đoạn ngoài chương không được tạo, lượt cuối dùng lại toàn bộ cache. Log tại `.qa/revised-ui-tests.log`, `.qa/revised-generation/report.json`, ảnh trong `.qa/revised-ui/`. Đây là fixture local, không phải giao dịch thật hoặc proof mọi sách/giọng.

Cập nhật 21/10/2026: script đóng gói luôn kèm các tệp inference Nano và Kitten được pin/checksum, không sao chép đường dẫn cache hoặc cấu hình người dùng. Bản cài mới dùng hai model Free ngay trên Mac. Các artifact cũ không tự thay đổi. Ứng viên local mới: `dist/pro-cta-free-bundled-preview/Windi Sách Nói.app`; không bật checkout và không kèm F5. UI source có nút mua ở thanh bên, cạnh bộ chọn giọng và ngay tại Turbo/F5 bị khóa; chỉ quảng bá F5 ở edition có bộ giọng này. Popup mua giữ nguyên model đang dùng cho sách.

QA cho thay đổi này: 69 core tests; AppKit/WKWebView fixture kiểm tra 5 điểm mở mua, giữ model, trả focus, ẩn lời mời mua khi đã Pro, VI/EN và sáng/tối. Payment fixture kiểm tra pending → success, gia hạn, dừng kiểm tra khi đóng popup. Portable integration dùng EPUB tổng hợp và thư viện sạch, chạy Nano/Kitten thật với guard chặn mạng, xuất WAV/M4A/web ZIP và khôi phục thiết lập sau restart. Kết quả tại `.qa/pro-ui-core-tests.log`, `.qa/pro-ui/`, `.qa/pro-bundled-integration.log`. Đây là kiểm thử local, chưa xác minh giao dịch tiền thật hoặc phát hành công khai.

Quyết định sản phẩm ngày 20/10/2026:

| Bản | Giá | Giọng đọc |
|---|---:|---|
| Free | Miễn phí | VieNeu Nano tiếng Việt; 8 giọng KittenTTS tiếng Anh |
| Pro | 189.000đ / năm | Free + VieNeu Turbo 48 kHz + 8 giọng F5 đã train |

Ngày 20/10/2026, chủ sở hữu xác nhận có đầy đủ quyền thương mại cho model F5 riêng và các giọng đã train; Pro preview vì vậy chứa checkpoint cùng tài nguyên reference cần cho suy luận. Giấy phép upstream và quyền sử dụng riêng là hai căn cứ riêng; không suy ra quyền thương mại từ giấy phép MIT của mã F5. Bản thu dùng để train, dữ liệu QA, nhạc demo và thư viện sách không được đóng gói.

Luồng mua đã chuyển sang **QR trực tiếp + mã máy + SePay/Supabase** theo yêu cầu mới. Không cần tài khoản/email khách hoặc hosting trang mua để test nội bộ. Đã tạo `wsn_payments`, `wsn_licenses` và hai Edge Functions riêng trong project WindiStudio. Token SePay mới và tài khoản TPBank đã kiểm tra đạt; cần cấu hình webhook và xác minh đồng bộ giao dịch trước khi chuyển tiền thử. Xem [setup SePay](SEPAY-SETUP.md). Người dùng chưa đăng ký Apple Developer.

## Artifact local

`dist/mac-0.6.0-preview-sepay/Windi Sách Nói.app` là ứng viên QA Free, ký ad-hoc, chưa notarize. `dist/mac-0.6.0-preview-pro-voices/Windi Sách Nói.app` là ứng viên Pro riêng, khoảng 7,1 GiB vì kèm 8 checkpoint và runtime. Chỉ dành cho Mac Apple Silicon, khai báo macOS 15 trở lên; chưa có máy macOS 15/16 hoặc máy Mac thứ hai để xác minh.

App chứa CPython riêng + dependency của project, extractor, bộ xác minh chữ ký native, UI local, Nano (~282 MB), Kitten (~82 MB) và ba nhạc nền procedural. Không dùng `.runtime` ở project khi chạy bản đóng gói. Không có `WindiProjectRoot` tuyệt đối. Tài nguyên thêm/cache/bản quyền được ghi dưới Application Support bên cạnh thư viện; không ghi vào bundle sau khi cài. Sách và audio vẫn trong thư viện local.

Không kèm Turbo để giảm dung lượng tải Free. Sau khi nhập license Pro hợp lệ, khách chủ động chọn tải Turbo; chỉ bước setup tải model dùng mạng. Bản Free không kèm F5 runtime hoặc checkpoint. Gói Pro preview có đủ 8 giọng F5 để chạy local; không kèm dữ liệu train gốc, service thanh toán, private signing key, `.env`, dữ liệu QA hoặc thư viện của người dùng.

Build lại trong project:

```sh
./scripts/build.sh
.runtime/bin/python scripts/package_macos.py \
  --output dist/mac-0.6.0-preview-next \
  --public-key-file commerce/private/license-public.txt

# Pro preview, chỉ tạo sau khi quyền thương mại của voice được xác nhận:
.runtime/bin/python scripts/package_macos.py \
  --output dist/mac-0.6.0-preview-pro-voices \
  --public-key-file commerce/private/license-public.txt \
  --include-f5
```

Thêm `--checkout-url https://<đích đã chọn>/` sau khi có backend. Script chỉ chấp nhận HTTPS và không ghi đè output cũ; không upload hoặc notarize. Luôn chạy build entry point của project. Public key phải khớp private key ở backend; không đổi key sau khi phát hành mà không có kế hoạch rotation.

## Kiểm tra local

```sh
.runtime/bin/python -m unittest discover -s tests -v
(cd 'package qr pay' && npm test)
(cd commerce && npm test)
.runtime/bin/python tests/portable_integration.py \
  --app 'dist/mac-0.6.0-preview-qr/Windi Sách Nói.app'
codesign --verify --deep --strict 'dist/mac-0.6.0-preview-qr/Windi Sách Nói.app'
```

Test portable dùng EPUB tổng hợp trong `.qa`, chạy Python từ bundle và kiểm tra import, Nano/Kitten inference thật, giữ cache khi đổi speed, nhạc nền, xuất WAV/M4A/web ZIP và mở lại. Nó không chứng minh mọi sách/giọng hoặc mọi máy Mac hoạt động. AudioToolbox/`iconutil` và kiểm thử HTTP localhost có thể cần chạy ngoài sandbox phát triển.

Giao diện native đã kiểm tra Free/Pro, giá 189.000đ/năm, trạng thái chưa mở bán, Nano/Kitten sẵn sàng và Turbo bị khóa. Trang checkout local đã kiểm tra bố cục mặc định và 390px, không tràn ngang. Không tạo tài khoản khách thật hoặc thực hiện giao dịch tiền thật.

## Điều còn thiếu trước khi gửi khách

1. Hoàn tất API token, kết nối ngân hàng và webhook theo `docs/SEPAY-SETUP.md`; thử tiền thật có chủ đích và xác minh lên Pro đúng mã máy. Chốt kênh hỗ trợ/chính sách mua. `sachnoi.windistudio.app` có thể triển khai trang mua sau; QR trực tiếp và license Supabase không phụ thuộc DNS này.
2. Hoàn thiện quyền thương mại cho giọng riêng nếu vẫn bán kèm. Free/Pro hiện chỉ cam kết các model ở bảng trên.
3. Rà soát nghĩa vụ phân phối dependency trong `THIRD_PARTY.md`: phonemizer/eSpeak NG GPL-3.0, soxr/libsndfile LGPL và license metadata chưa rõ của espeakng-loader. Bundle giữ dist-info/notices; chưa có gói corresponding source và kết luận cho phương thức phân phối cuối. Không xem kiểm thử kỹ thuật là xác nhận tuân thủ giấy phép.
4. Có Developer ID Application, ký các Mach-O/helpers và bundle với hardened runtime/entitlement phù hợp, submit bằng `xcrun notarytool`, staple ticket và kiểm tra Gatekeeper trên một máy sạch. Máy hiện tại báo **0 valid signing identities**. Ký ad-hoc trong preview không thay thế bước này. Không hướng dẫn khách bỏ qua Gatekeeper.
5. Kiểm tra trên Mac thứ hai và macOS thấp nhất hỗ trợ; thử launch từ Applications, import PDF/scan/EPUB, hủy/tiếp tục, license hết hạn/gia hạn và tạo audio offline. Chuẩn bị thông tin hỗ trợ, khôi phục tài khoản và chính sách mua/gia hạn/hoàn tiền trước khi mở bán.

Chưa có URL tải công khai, DMG/installer phát hành, Developer ID, notarization hoặc thanh toán thật. App preview chỉ phục vụ QA nội bộ. Candidate `mac-0.6.0-preview-sepay` pin QR trực tiếp và URL kiểm tra license Supabase; chỉ thử chuyển tiền sau khi các bước SePay đã hoàn tất. Candidate QR cũ giữ cấu hình tắt mua/kiểm tra online.

Nguồn: [SePay webhook](https://docs.sepay.vn/tich-hop-webhooks.html), [Apple Developer ID](https://developer.apple.com/developer-id/), [model F5 Vietnamese](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice), [Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo).

## Kết quả QA bản QR cuối

35 core tests, 32 package QR tests, 9 commerce/manual groups đã qua. Gói `mac-0.6.0-preview-qr` đã chạy Nano/Kitten thật trên EPUB tổng hợp, xuất WAV/M4A/web và khôi phục thiết lập sau restart. Native import license schema 2 QA hiển thị Pro hết hạn 20/10/2027; license sai máy bị từ chối trong test. License QA chỉ trong `.qa`, đã gỡ khỏi thư viện UI QA sau kiểm tra; không có thanh toán thật. Trang QR 390px không tràn ngang, không có ô email/mật khẩu. Bản ZIP ký ad-hoc, không notarize và chưa mở mua online.

## Candidate SePay nội bộ

`dist/mac-0.6.0-preview-sepay/Windi Sách Nói.app` dùng QR trực tiếp và `https://zpjphixcttehkkgxlmsn.supabase.co/functions/v1/wsn-license/` để kiểm tra chủ động. Đóng gói bằng `--checkout-mode qr --checkout-url <URL do commerce/qr-url.mjs tạo> --license-base-url <URL trên>`. License URL không phụ thuộc trang tĩnh. Không chứa bất kỳ server secret nào. Chưa phải bản notarized hoặc bản phát hành cho khách.

## Popup thanh toán trong app

Nút Mua mở một dialog QR trong app, không gọi NSWorkspace.open. QR vector được tạo local bằng Core Image từ payload VietQR, mã SN, tài khoản và giá cố định trong cấu hình bundle; không cần mạng để hiện QR. `checkoutURL` cũ chỉ là cấu hình ngân hàng được pin, không còn được mở trong trình duyệt. Chỉ nút kiểm tra thanh toán chủ động mới gọi license API. Kiểm tra payload/CRC bằng mẫu chính thức và quét cả PNG và bản raster từ SVG bằng Vision:

```sh
swiftc -O native/Payment.swift tests/verify_payment.swift -o .qa/payment-popup/verify-payment
.qa/payment-popup/verify-payment
```

Build native gồm `App.swift` + `Payment.swift`; app entry point dùng `@main`. Dùng `./scripts/build.sh` như trước.
