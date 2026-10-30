# Sách Nói — QR và SePay trên Supabase

Cập nhật 20/10/2026. Pro **189.000đ/năm/máy**, Free có Nano tiếng Việt + KittenTTS tiếng Anh; Pro thêm Turbo và sáu giọng F5 đã train. Không cần tài khoản hoặc email khách. Không tự trừ tiền gia hạn.

## Đã triển khai

Project WindiStudio `zpjphixcttehkkgxlmsn` dùng chung với hệ sinh thái:

- `public.wsn_payments`: giao dịch SePay đã được xác minh, duy nhất theo tài khoản + ID giao dịch.
- `public.wsn_licenses`: hạn Pro và payload license theo mã máy.
- `wsn_accept_payment`: nhận tiền/gia hạn trong một transaction; webhook trùng không cộng năm lần nữa.
- Hai bảng bật RLS, chặn `anon`/`authenticated`, chỉ backend dùng `service_role`. Không sửa bảng hay Storage của sản phẩm khác.
- Edge Function `wsn-sepay-webhook`: xác thực API Key, gọi API SePay để đối chiếu tiền thật rồi ghi DB.
- Edge Function `wsn-license`: trả license Ed25519 gắn mã máy; app xác minh chữ ký và hạn sử dụng ngay trên máy.

Mã máy **14 ký tự**, `SN` + 12 ký tự hex từ hash. Dùng nguyên chuỗi làm nội dung chuyển khoản. Không thêm một tiền tố SN nữa. Serial phần cứng gốc không gửi đi. Mã chỉ định danh máy, không chứng minh đã trả tiền.

QR trực tiếp do `package qr pay` tạo: **TPB / 55111685555 / BUI QUOC HUNG / 189.000đ**. App tạo QR VietQR ngay trên máy và hiển thị popup thanh toán, không mở trình duyệt hoặc tải ảnh QR từ ngoài. Chưa cần hosting hoặc DNS cho `sachnoi.windistudio.app` để test luồng này.

## Việc cần hoàn tất trước khi chuyển tiền thử

1. **API token đã đạt:** token mới đã đọc được API SePay và đã cập nhật vào Supabase. Khi đổi token về sau, điền `.env.local`, chạy cập nhật secrets và probe. Không gửi token vào chat; đây không phải API Key của webhook.
2. **Tài khoản TPBank 55111685555 đã hiện hoạt động trong API SePay.** Cần xác minh đồng bộ giao dịch mới và webhook khi có lần chuyển tiền thật; trạng thái active chưa phải chứng minh đã nhận tiền.
3. **Tạo webhook riêng** theo bảng bên dưới. Giữ nguyên webhook của các dự án khác.
4. Cập nhật secrets trên Supabase sau khi thay token, chạy probe lại và kiểm tra nhật ký Gửi thử. Chỉ chuyển tiền khi không còn lỗi cấu hình/API.

## Cấu hình webhook trong SePay

Vào Webhooks → Thêm webhook, cấu hình:

| Trường | Giá trị |
|---|---|
| Tên | Windi Sách Nói Pro |
| Sự kiện | Có tiền vào |
| URL | `https://zpjphixcttehkkgxlmsn.supabase.co/functions/v1/wsn-sepay-webhook` |
| Tài khoản | TPBank — 55111685555 |
| Xác thực | API Key |
| API Key | Giá trị `SEPAY_WEBHOOK_API_KEY` trong `.env.local` — không phải `SEPAY_API_TOKEN` |
| Header tương ứng | `Authorization: Apikey <SEPAY_WEBHOOK_API_KEY>` |
| Bộ lọc mã | Ban đầu để trống nếu SePay chưa nhận diện định dạng SN + 12 hex. Backend tự đọc mã trong nội dung và chỉ nhận đúng một mã. Nếu bật lọc SN, phải xác minh bộ nhận diện SePay hỗ trợ đủ 14 ký tự trước. |
| Retry/cảnh báo lỗi | Bật; theo dõi nhật ký webhook khi thử |

Không tắt xác thực. Không đặt `service_role`, token quản trị Supabase hoặc private key ký license vào SePay. Không nhập chuỗi `Apikey ` vào ô giá trị API Key nếu giao diện tự tạo header.

Dùng **Gửi thử** để kiểm tra endpoint và API Key: payload mẫu có thể trả `success:true,status:ignored`, nghĩa là kết nối đã nhận nhưng chưa cấp Pro. Sai API Key trả 401. Thiếu/dư tiền, sai tài khoản hoặc mã không hợp lệ không kích hoạt. Lỗi API/DB trả 503 để SePay retry. Payload khớp giá/mã vẫn phải có giao dịch thật tương ứng trong API SePay mới được cấp Pro.

## Sau khi cập nhật env

Từ thư mục project:

```sh
# Chỉ đổi token/key: không cần deploy lại mã function.
node --env-file=.env.local commerce/supabase.mjs secrets
node --env-file=.env.local commerce/supabase.mjs status
node --env-file=.env.local commerce/probe-supabase.mjs
```

Token triển khai `SUPABASE_ACCESS_TOKEN` đã được kiểm tra. Script khóa đúng project ref, chỉ deploy `wsn-sepay-webhook` và `wsn-license`, không prune function khác. Chỉ bốn secret riêng được gửi: `WSN_SEPAY_API_TOKEN`, `WSN_SEPAY_WEBHOOK_API_KEY`, `WSN_BANK_ACCOUNT`, `WSN_LICENSE_PRIVATE_KEY_PEM`. Không upload cả `.env.local`. Secret tạm bị xóa sau lệnh; không đóng gói vào app.

DDL đã áp dụng từ `supabase/migrations/20261020074917_wsn_device_commerce.sql`; **không chạy lại `apply` hoặc `db push` trên project dùng chung**. Kiểm tra SQL nghiệp vụ bằng `node --env-file=.env.local commerce/supabase.mjs verify`: mọi receipt QA được rollback, không lưu fake-paid. Không trộn ledger thủ công cũ vào luồng tự động mà chưa đối chiếu hạn trong DB.

## Bài test bằng tiền thật — người dùng tự chuyển

Chỉ sau khi API token, ngân hàng và webhook đã hoạt động:

1. Chạy app consumer QA mới `dist/mac-0.6.2-preview-autopay/Windi Sách Nói.app`; app development mặc định không dùng để chứng minh Pro trả phí.
2. Mở Free / Pro → Mua Pro, popup QR hiện ngay trong app. Kiểm tra đúng ngân hàng, chủ tài khoản, **189.000đ**, nội dung là mã máy đang hiển thị. Chuyển từ tài khoản khác vào tài khoản nhận.
3. Xem SePay đã đồng bộ giao dịch và webhook trả `success:true,status:paid`. Hai bảng có một receipt và license tương ứng, không chỉ có ảnh chuyển khoản.
4. Giữ popup thanh toán mở; app tự kiểm tra sau mỗi khoảng 5 giây và phải hiện thành công khi nhận bản quyền hợp lệ. Nút **Kiểm tra ngay** chỉ là phương án chủ động dự phòng. Với gia hạn, hạn mới phải lớn hơn hạn trước khi mở popup; bản quyền cũ không được coi là vừa trả tiền. Tải gói giọng là bước chủ động riêng.
5. Mở lại app khi offline: license đã lưu vẫn được xác minh tại máy. Gửi lại **cùng giao dịch thật** từ nhật ký SePay: hạn không được cộng thêm. Giao dịch mua mới đúng điều kiện mới gia hạn thêm một năm.

Chưa có chuyển khoản thật hoặc chứng minh tự kích hoạt từ ngân hàng. App hiện là bản QA local ký ad-hoc; kiểm thử thanh toán nội bộ không thay cho phát hành công khai. Trước khi bán cho khách cần Apple Developer/Developer ID + notarization, kiểm thử Mac khác, kênh hỗ trợ/chính sách mua và xử lý giấy phép phân phối. Giữ và sao lưu private key Ed25519 an toàn; không tạo key mới sau khi khách đã dùng app pin public key cũ.

Tài liệu chính thức: [SePay webhook](https://docs.sepay.vn/tich-hop-webhooks.html), [API giao dịch](https://docs.sepay.vn/api-giao-dich.html), [API token](https://docs.sepay.vn/tao-api-token.html), [Supabase Edge Functions](https://supabase.com/docs/guides/functions/deploy).

## Kiểm tra đã thực hiện

35 core tests, 32 package QR tests, 9 commerce/manual groups và 9 Edge Function tests đã qua. DB thực đã kiểm tra nhận tiền trùng, gia hạn, sai giá và conflict trong transaction rollback; sau đó cả hai bảng vẫn 0 hàng. Security Advisor chỉ có INFO `rls_enabled_no_policy` cho hai bảng: đây là chủ đích chặn mọi client và chỉ cho backend service_role; không có WARN/ERROR liên quan wsn. Probe live xác minh token SePay, TPBank active, client bị chặn, backend có quyền, chữ ký server trùng key app, webhook sai key/sai giá không cấp Pro. Native QA thấy Free, mã 14 ký tự, mở QR đúng mã/số tiền, và nhận thông báo chưa có bản quyền từ endpoint live. Không có thanh toán thật hoặc license Pro giả được lưu trên DB.

## Popup tự cập nhật — 20/10/2026

- Native bridge chỉ gọi endpoint license khi người dùng mở thanh toán hoặc chủ động cập nhật Pro. Popup kiểm tra khoảng 5 giây/lần, chậm lại 15 giây khi lỗi mạng, dừng sau 15 phút, khi đóng popup, khi ẩn trang hoặc sau thành công. Trở lại cửa sổ tiếp tục kiểm tra; sau giới hạn thời gian cần bấm Kiểm tra ngay.
- HTTP 404/410 là trạng thái chưa có kích hoạt mới, không phải thanh toán thành công. Envelope được worker xác minh Ed25519, mã máy và hạn trước khi lưu; gia hạn phải có expiresAt lớn hơn giá trị lúc mở popup.
- Build consumer có cấu hình public bằng `node --env-file=.env.local commerce/build-preview.mjs`. Chỉ public key, URL endpoint và thông tin QR được đưa vào app; script lọc biến môi trường khi gọi builder. Không nhúng token SePay/Supabase/private key.
- UI dùng fixture trong WebKit; test chữ ký và trạng thái dùng key QA. Health endpoint là kiểm tra chỉ đọc. Các kiểm tra này không thay thế giao dịch ngân hàng thật.
