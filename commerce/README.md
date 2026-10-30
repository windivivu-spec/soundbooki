# Thanh toán Sách Nói

Từ 21/10/2026, mã app chuyển sang **Lite miễn phí + Pro Cloud tính theo từng cuốn**, từ 10.000đ/cuốn. Sổ đơn mới đã thêm vào Supabase và kiểm tra; gateway/nhánh SePay mới chưa triển khai, chưa chạy GPU hay thu tiền thật trong luồng mới. Lịch sử giấy phép năm cũ được giữ.

Xem [giá, database, lệnh nhận tiền và xử lý đơn](../docs/BOOK-COMMERCE.md). `node --env-file=.env.local commerce/books.mjs list` xem đơn; `confirm` chỉ sau khi kiểm tra tiền vào; `process-next` chạy đúng snapshot đã thanh toán hoặc mẫu thử đã trừ quota. Không bán credit chung, không mở sách chỉ từ mã chuyển khoản.

Phần dưới mô tả backend giấy phép cũ để hỗ trợ khách đã mua; không dùng để mở bán gói mới.

Luồng giấy phép cũ: **Popup QR trong app → SePay đối chiếu giao dịch thật → Supabase lưu quyền → app kiểm tra license ký Ed25519**. Không có tài khoản/email khách. Pro 189.000đ/năm/máy, mở Turbo; Free có Nano + KittenTTS. Giọng F5 riêng chưa bán.

Xem [hướng dẫn setup SePay và thử thanh toán](../docs/SEPAY-SETUP.md). Token Supabase và token SePay mới đã kiểm tra đạt; TPBank đã liên kết và active. Hai bảng và hai Edge Functions đã triển khai. Còn cấu hình webhook bên SePay và kiểm chứng bằng giao dịch thật do người dùng thực hiện; chưa mở bán công khai.

```sh
# Sau khi đổi token/key trong .env.local
node --env-file=.env.local commerce/supabase.mjs secrets
# Quyền DB và kiểm tra live, không chuyển tiền
node --env-file=.env.local commerce/supabase.mjs status
node --env-file=.env.local commerce/probe-supabase.mjs
# Chỉ khi sửa mã hai functions
node --env-file=.env.local commerce/supabase.mjs deploy
```

`supabase.mjs` khóa đúng project WindiStudio, không deploy/prune hàm khác. Không chạy lại `apply`: DDL đã tạo thành công. Các secret chỉ ở backend, không đóng gói vào app. Giữ và sao lưu `commerce/private/license-private.pem`; public key phải khớp app.

`package qr pay` cung cấp QR, parser và kiểm tra API Key được tái sử dụng trong Edge Functions. Sổ thanh toán có unique receipt; RPC xử lý nguyên tử và gia hạn một năm, không cộng trùng khi SePay retry. License được ký từ quyền đã lưu và xác minh offline trong app sau lần kiểm tra chủ động.

[Phương án thủ công](manual/README.md) là dự phòng. Không trộn ledger thủ công và quyền DB mà chưa đối chiếu lịch sử. [Backend tài khoản cũ](LEGACY-ACCOUNT.md) dùng email/schema 1 và không chạy cho app consumer hiện tại.
