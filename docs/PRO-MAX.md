# Pro Max · tạm hoãn

**Tạm hoãn từ 21/10/2026:** chủ sở hữu yêu cầu ẩn tính năng vì chi phí API chưa phù hợp cho sách dài, cộng thêm công chụp tài liệu khi không có PDF. `backend/features.py` đặt `PRO_MAX_ENABLED=False`; giao diện, bridge native và các lệnh mạng đều bị chặn. Chưa triển khai hay mở bán. Phần dưới là thiết kế được lưu lại, không mô tả tính năng đang hoạt động.

Theo yêu cầu ngày 21/10/2026: không dùng tài khoản/credit web Clone Pro của khách. Khách mua credit trong app, **1 ký tự = 1 credit**, không thêm phí thuê bao Pro Max. Gói Pro local 189.000đ/năm vẫn riêng. Chưa có giá gói credit nên không có gói bán mặc định.

## Trong app

Mở **Pro Max · Mua credit** để cập nhật ví qua dịch vụ được cấu hình. Ví có một khóa ngẫu nhiên trong macOS Keychain, không cần email/tài khoản web. Không xóa mục Keychain `studio.windi.sachnoi.credits`: đó là quyền truy cập ví; cài lại app trên cùng Mac vẫn dùng mục Keychain còn giữ. Chưa có luồng chuyển/khôi phục ví sang Mac khác.

Khi dịch vụ có gói đang bán, chọn gói → tạo QR → chuyển khoản với mã `SC…`. QR được vẽ local bằng CoreImage. Mã thanh toán không cộng credit. App chỉ cập nhật số dư chủ động hoặc tối đa 30 lần/10 giây khi cửa sổ đang mở và có đơn chờ; không polling nền sau khi đóng. Sau giới hạn này, bấm cập nhật hoặc mở lại cửa sổ.

Chọn Pro Max cho sách → chọn giọng → chọn chương/trang/phạm vi → xác nhận số đoạn và credit dự kiến. Nút phát không sinh audio cloud, không preview cloud ngầm. Credit tính trên số Unicode code point sau NFC và bỏ khoảng trắng đầu/cuối **từng đoạn chưa cache**, cùng quy tắc API Windi hiện có. Sách và `originalText` giữ nguyên. Tốc độ player không đổi số credit/cache.

Audio MP3 được tải về, giải mã local thành PCM16 mono 48 kHz bằng `afconvert`, chỉ đổi tên vào cache khi WAV hợp lệ. Nghe và xuất WAV/M4A/web dùng chung phạm vi/nhạc hiện có. Audio hoàn tất giữ lại khi hủy; lượt đã gửi có thể vẫn được tính credit.

## Dịch vụ riêng

`commerce/credits/service.py` là gateway Python/SQLite độc lập, không sửa WindiStudio2 hoặc database hiện có. API merchant Windi Voice nằm **chỉ ở môi trường server** `WSN_CLONE_PRO_API_TOKEN`; không đóng gói, không lấy key từ project khác. Gateway gọi API Clone Pro 2.1 đã có trong WindiStudio2:

- `GET /api/v1/voice/voices`
- `POST /api/v1/voice/generations` với `Idempotency-Key`
- `GET /api/v1/voice/generations/{id}` và `/audio`

Khách chỉ gọi gateway bằng khóa ví app `wsn_credit_…`, không nhận token merchant. Số dư/đơn/giao dịch app nằm trong SQLite riêng, không đọc hay dùng số dư của tài khoản web khách. Merchant cần nguồn API/credit riêng để vận hành; không suy ra giá bán app từ giá upstream.

SQLite giữ reserve/refund/topup nguyên tử, ràng buộc không âm, mã yêu cầu duy nhất theo ví, mã giao dịch ngân hàng duy nhất toàn ledger. Yêu cầu cũ khác nội dung trả 409. Thiếu credit trả 402 trước khi gọi upstream. `unknown`/timeout giữ khoản reserve và tiếp tục cùng upstream idempotency key; không tự cấp lượt mới. Chỉ lỗi xác thực/validation chắc chắn chưa tạo hoặc trạng thái upstream `failed` mới hoàn credit. Không xoay token merchant khi có lượt chưa rõ kết quả mà chưa đối soát; gateway dừng tạo mới cho lượt đó.

Gateway lưu phần chữ được gửi và MP3 để phục hồi kết quả; upstream Windi cũng có lịch sử tạo giọng. Đây là lựa chọn xử lý qua mạng. Chưa có chính sách retention tự động hoặc khôi phục ví đa thiết bị. Server local này cần được vận hành với backup SQLite/audio, TLS, giới hạn request ở reverse proxy và bí mật merchant riêng trước khi mở bán.

## Cấu hình trước khi kích hoạt

Chưa triển khai dịch vụ, chưa gắn `creditsBaseURL`, chưa cấu hình token merchant, chưa mở bán, chưa gọi tạo giọng trả phí và chưa xác minh giao dịch thật.

1. Chốt giá gói. `WSN_CREDIT_PACKS` là mảng JSON các mục có `id`, `credits`, `amountVND` (số nguyên dương). Mặc định `[]` vô hiệu hóa mua credit; không có bảng giá mẫu bị hiểu là giá thật.
2. Cấu hình `WSN_CREDIT_BANK` với `name`, `bin` 6 chữ số, `account`, `holder` của ngân hàng nhận tiền; không đặt token ngân hàng ở app.
3. Cấu hình `WSN_CLONE_PRO_API_TOKEN` trên server bằng bí mật merchant được chủ sở hữu cấp, cùng `WSN_CREDIT_VOICE_IDS` là mảng UUID các giọng được chọn cho app. Gateway chỉ hiển thị/cho tạo các giọng này, không đưa toàn bộ thư viện riêng của merchant cho khách. Không sao chép token/khóa từ WindiStudio2 vào project/app.
4. Chạy `python3 commerce/credits/service.py serve --db commerce/private/credits.sqlite --port 8789` sau reverse proxy HTTPS. Mặc định bind 127.0.0.1.
5. Sau khi có đích triển khai được chọn và chấp thuận triển khai, điền `creditsBaseURL` HTTPS trong cấu hình app consumer. Không dùng domain giả làm dịch vụ đang hoạt động.

Đối soát thủ công đầu kỳ, chạy **trên server có ledger** sau khi kiểm tra tiền vào ngân hàng:

```sh
python3 commerce/credits/service.py confirm \
  --db commerce/private/credits.sqlite \
  --order ORDER_ID --transaction BANK_TRANSACTION_ID \
  --amount RECEIVED_VND --account RECEIVING_ACCOUNT \
  --paid-at ISO8601_WITH_TIMEZONE --confirm-received
```

Lệnh kiểm tra số tiền/tài khoản khớp đơn và không cấp trùng giao dịch. Không có HTTP admin cấp credit; chưa tích hợp webhook SePay cho **credit app**. Luồng SePay Pro hiện có chỉ cấp Pro, không cộng vào ví này. Không trộn hai ledger.

## Kiểm thử

Core: `.runtime/bin/python -m unittest discover -s tests -p 'test_*.py'`.

Integration dùng server API fixture và thư viện `.qa`, kiểm tra HTTP thật, debit/refund/replay, audio MP3 → WAV thật và export. UI chạy qua WKWebView native. Kết quả fixture không chứng minh provider chấp nhận, giao dịch ngân hàng thật, mọi giọng hoặc phát hành công khai. macOS sandbox có thể không truy cập codec AAC; kiểm tra audio cần quyền chạy codec hệ thống.
