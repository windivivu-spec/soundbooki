# Backend tài khoản cũ — không dùng cho consumer mode device

# Windi Sách Nói — mua Pro

**Luồng hiện tại: [QR + mã máy + SePay/Supabase](../docs/SEPAY-SETUP.md).** Hai bảng và hai Edge Functions riêng đã triển khai; API token mới và TPBank đã kiểm tra đạt; cần cấu hình webhook trước khi thử tiền thật. Không có tài khoản/email khách. Nội dung bên dưới mô tả backend tài khoản SQLite cũ, không deploy và không dùng cho app consumer gắn máy. License email schema 1 của backend cũ không được consumer mode `device` chấp nhận.

Backend riêng cho bản Mac. **189.000 VND / một năm**, gia hạn thủ công. Không nhận sách, bản thu hay audio của khách. Không có thanh toán hoặc dịch vụ thật nào được kích hoạt bởi việc chạy test.

Đã có `.env.local` ở thư mục gốc project để điền token. `npm start` từ `commerce/` đọc `.env`, sau đó `../.env.local`, cuối cùng `commerce/.env.local` nếu có; biến môi trường đã đặt khi chạy vẫn được ưu tiên. Đường dẫn dữ liệu/key trong file mẫu tính từ thư mục `commerce/`. File local được bỏ qua trong Git và không nằm trong gói Mac/trang QR.

`SEPAY_API_TOKEN` là token API Access để backend truy vấn giao dịch bằng Bearer; hiện chỉ chuẩn bị chỗ điền, chưa có tác vụ truy vấn SePay bằng token này. `SEPAY_WEBHOOK_API_KEY` là khóa khác để kiểm tra webhook bằng `Authorization: Apikey ...`; backend tùy chọn hiện dùng khóa này. Không dùng API token làm khóa webhook hoặc đưa token/private key vào Mac app, HTML hay biến public. Chỉ tạo QR không cần hai khóa này. Điền token không tự biến luồng cấp quyền thủ công thành tự động.

Free: Nano tiếng Việt + KittenTTS tiếng Anh. Pro: thêm Turbo. Giọng F5 riêng đang dùng model CC BY-NC-SA 4.0 nên không được đưa vào gói thương mại hiện tại.

## Chạy backend trên một máy có ổ đĩa bền vững

Yêu cầu Node 22.13+ (đã test trên Node 24.11.1). Chạy từ `commerce/`:

```sh
node keys.mjs private
cp env.example .env
```

Nếu key đã tồn tại, `keys.mjs` dừng, không ghi đè. Project này đã tạo cặp key local trong `commerce/private/`. Sao lưu private key và cả DB trước khi dùng thương mại; mất key hoặc đổi key sẽ khiến app đã phát hành không xác minh được bản quyền mới. Chỉ public key được đưa vào app. Không gửi private key qua chat, không commit `.env`, `private/` hay `data/`.

Điền `.env`:

- `WSN_PUBLIC_ORIGIN`: origin HTTPS đã chọn, không có dấu `/` cuối. HTTP chỉ cho localhost QA.
- `WSN_SIGNING_KEY_FILE`: tệp PEM Ed25519 của backend; `WSN_DATA_DIR`: ổ bền vững chứa `accounts.sqlite`, `payments.sqlite` và WAL/SHM.
- `QR_API_KEY`: khóa ngẫu nhiên riêng, ít nhất 32 ký tự. Khóa này chỉ phục vụ module QR ở backend, không gửi cho browser/app.
- `SEPAY_WEBHOOK_API_KEY`: khóa khác, ít nhất 16 ký tự. Cấu hình cùng khóa ở SePay, xác thực `Authorization: Apikey ...`.
- `VOICE_BANK_BIN=TPB`, `VOICE_BANK_ACCOUNT=55111685555`, `VOICE_BANK_NAME=BUI QUOC HUNG` đã điền đúng yêu cầu trong env mẫu; module tự ánh xạ sang `QR_BANK_*`.
- `WSN_SALES_ENABLED=false` mặc định. Chỉ mở sau khi cấu hình đích, kiểm tra webhook/đối soát và hoàn tất phần phát hành.

```sh
npm test
npm start
```

Service mặc định bind `127.0.0.1:8789`. Đặt sau reverse proxy HTTPS và hạn chế tần suất `/api/register`, `/api/login`, `/api/recover`, `/api/orders`, giới hạn body và timeout tại proxy. Service có giới hạn in-memory theo địa chỉ socket; sau proxy, giới hạn này được dùng chung cho khách sau proxy. Chưa tin `X-Forwarded-For`. Không tự bật CORS. Cookie HttpOnly, Secure ở HTTPS, SameSite=Strict. Mutation JSON phải có Origin khớp cấu hình. Mật khẩu dùng scrypt với salt riêng; session token và mã khôi phục chỉ lưu dạng hash.

Đây là **một backend với SQLite trên ổ bền vững**. Tùy chọn `QR_DATABASE_URL` chỉ chuyển phần thanh toán sang Postgres, không chuyển tài khoản/giấy phép. Không chạy bản này trên filesystem tạm, serverless hoặc nhiều replica. Module dùng trực tiếp từ `../package qr pay/src/`, và `pg` đã có trong package. Nếu sao chép backend sang VPS, giữ `commerce/` và `package qr pay/` cạnh nhau cùng dependency của package.

## SePay và cấp quyền

Webhook: `POST https://<origin đã chọn>/api/payments/webhook`. Chọn giao dịch tiền vào của đúng tài khoản; nếu dùng bộ lọc mã SePay, tiền tố `WSN`, hậu tố 10 chữ số. Không dùng cùng tiền tố này cho project khác nhận cùng tài khoản.

Module QR kiểm tra auth, đúng tài khoản, đúng một mã, đúng số tiền nguyên 189.000 VND, ngày giao dịch và thời hạn. Chỉ `paid` từ API backend tin cậy mới được cấp quyền; client không quyết định giá hay trạng thái. Không có nút “tôi đã chuyển” để tự mở Pro. Chuyển thiếu/dư, sai mã hoặc ngoài hạn cần đối soát riêng; không tự hoàn tiền.

Khi khách đăng nhập và kiểm tra đơn paid, backend tạo bản quyền Ed25519, unique theo order ID. Polling và tải lại không cộng thêm thời hạn. Gia hạn thêm một năm lịch tính từ thời điểm muộn hơn giữa ngày trả tiền và hạn hiện có. Ngày 29/2 được chuyển sang 28/2 năm sau. Webhook đến muộn vẫn có thể xác nhận giao dịch ngân hàng xảy ra đúng hạn. Khách có thể kiểm tra lại đơn expired.

Browser poll mỗi 3 giây khi pending; dừng khi paid/expired. Khách tải `.windilicense`, vào app → **Free / Pro · Bản quyền → Nhập bản quyền**. License chứa email, product, order ID, ngày cấp và hạn; không chứa sách hay khóa bí mật. Khách phải tự nhập license mới sau khi gia hạn. App xác minh chữ ký bằng CryptoKit trên máy; không gọi server khi đọc hoặc tạo giọng. Hết hạn thì trở lại Nano/Kitten, giữ tài liệu/audio đã hoàn tất. Xuất hoặc tạo tiếp Turbo đòi hỏi Pro còn hạn.

Email là tên đăng nhập/thông tin liên hệ, **chưa được xác minh**. Đăng ký trả một mã khôi phục để khách lưu thành tệp. Khôi phục cần email + mã này; sau khi dùng, mã bị thay và mọi session cũ bị thu hồi. Không gửi email, không tích hợp nhà cung cấp mail. Không có tự phục hồi khi khách mất cả mật khẩu lẫn mã; cần bổ sung quy trình hỗ trợ trước khi mở bán rộng.

License hiện không khóa số máy; không bổ sung giới hạn thiết bị ngoài yêu cầu. Offline licensing phụ thuộc đồng hồ máy và không có thu hồi tức thì hoặc chống sửa mã chương trình. Đây không phải cơ chế chống sao chép tuyệt đối. Chưa có luồng hoàn tiền/thu hồi hoặc gia hạn tự động.

## Bằng chứng và phần chưa có

`npm test` kiểm tra tài khoản, giả mạo giá, phân quyền đơn, webhook, replay, chữ ký, thời hạn một năm, gia hạn, restart, CSRF và khôi phục bằng dữ liệu tổng hợp trong `.qa`. Package QR có 32 test riêng. Không test nào chuyển tiền thật.

Chưa deploy backend, chưa kết nối SePay thật, chưa nhận chuyển khoản/đối soát thật và chưa mở bán. Thông tin tài khoản ngân hàng chỉ đủ tạo QR; không thay cho khóa webhook hoặc một URL HTTPS nhận được webhook.
