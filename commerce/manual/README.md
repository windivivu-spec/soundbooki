# QR + SN/mã máy — phương án đối soát thủ công dự phòng

Luồng mới được triển khai bằng [SePay/Supabase](../../docs/SEPAY-SETUP.md). Nội dung dưới đây giữ làm tài liệu phương án thủ công; không đồng thời cấp bằng ledger SQLite và DB mà chưa đối chiếu lịch sử hạn.

Giá Pro **189.000đ/năm**, thêm Turbo; Free giữ Nano tiếng Việt + KittenTTS tiếng Anh. Giọng F5 riêng chưa mở bán. Trang mua dự kiến ở **sachnoi.windistudio.app**, chưa upload/cấu hình DNS. Không cần VPS, tài khoản hay email khách. Phương án thủ công này không dùng webhook; luồng SePay hiện tại được mô tả ở tài liệu setup riêng.

## Luồng thực tế

1. App lấy IOPlatformUUID trên máy, băm SHA-256 có tiền tố riêng của app, chỉ xuất `SN` + 12 ký tự hex. Không gửi hoặc log ID phần cứng gốc.
2. Khách bấm Mua; mã được đưa vào fragment của link trang mua. Trang tạo QR đúng **TPB / 55111685555 / BUI QUOC HUNG / 189.000đ**, nội dung đúng mã SN. URL QR được tạo dựa trên `createQrUrl` của `package qr pay`.
3. Khách chuyển tiền. **Mã SN chỉ định danh máy; không xác nhận thanh toán.** Người bán phải xem giao dịch tiền vào trong ngân hàng/SePay, kiểm tra số tiền, nội dung và ID giao dịch.
4. Người bán dùng công cụ local bên dưới ký bản quyền một năm cho đúng mã máy. Upload đúng tệp đã ký vào `licenses/` trên hosting tĩnh đã chọn. Private key/ledger không upload.
5. Khách bấm **Kiểm tra bản quyền** trong app. Đây là thao tác tải mạng chủ động tới URL cố định `licenses/SNxxxxxxxxxxxx.windilicense`; không gửi sách hay bản thu. App kiểm tra chữ ký Ed25519, mã máy và hạn ngay trên Mac rồi lưu atomically. Không chạy polling tự động. Tệp nhập tay vẫn là phương án dự phòng.
6. Sau khi tải Turbo, việc đọc/tạo audio vẫn local. Gia hạn dùng lại mã máy với một giao dịch ngân hàng mới, cộng thêm một năm vào hạn còn lại. Không tự trừ tiền.

Một file license không dùng trên Mac có mã khác. IOPlatformUUID có thể thay đổi khi đổi phần cứng; chuyển máy/cấp lại cần quy trình hỗ trợ của người bán, hiện chưa có UI tự chuyển máy. Mã băm rút gọn không có cam kết tuyệt đối không va chạm ở quy mô tùy ý. License offline phụ thuộc đồng hồ hệ thống và không có chống sửa app hoặc thu hồi tức thì.

## Xuất trang tĩnh

Chạy từ thư mục project:

```sh
node commerce/manual/build.mjs dist/qr-checkout
```

Mặc định trang ghi **chưa mở bán** và không hiện QR để tránh nhận tiền khi chưa thể giao bản Mac. Khi đã hoàn tất ký/phân phối, có nơi hỗ trợ khách và chọn hosting, bật rõ ràng:

```sh
WSN_MANUAL_SALES_ENABLED=true node commerce/manual/build.mjs dist/qr-checkout
```

Output HTML/CSS/JS/config công khai, không có server, key, email hoặc tài khoản khách. Upload toàn bộ thư mục lên hosting tĩnh của subdomain đã chọn. Mở từ app sẽ có dạng `https://sachnoi.windistudio.app/#device=SNxxxxxxxxxxxx`; phần fragment không đi theo request HTTP tới hosting. Mã sẽ xuất hiện trong yêu cầu tạo ảnh QR và giao dịch ngân hàng, không phải serial gốc.

Trang không bao giờ tự báo “đã thanh toán”. Không bấm xác nhận thay cho ngân hàng, không tạo giao dịch thật khi test. Cần chốt kênh hỗ trợ và thời gian đối soát trước khi mở bán. Bản build hiện tại vẫn tắt nhận tiền.

## Cấp quyền sau khi đã kiểm tra tiền vào

Key local ở `commerce/private/license-private.pem`, public key tương ứng được pin trong app; ledger local ở `commerce/private/manual.sqlite`. Sao lưu cả key và ledger. Chỉ người bán được dùng công cụ này.

```sh
node commerce/manual/issue.mjs \
  --device-code 'SNABCDEF123456' \
  --transaction-id 'ID_GIAO_DICH_THAT' \
  --received-amount 189000 \
  --paid-at '2026-10-20T10:00:00+07:00' \
  --confirm-received \
  --output-dir output/licenses
```

Các giá trị trên là mẫu, không phải thanh toán thật. Lấy mã SN và ID từ giao dịch ngân hàng đã kiểm tra. Công cụ **không gọi ngân hàng**, nên `--confirm-received` là xác nhận của người bán đã thấy tiền, không phải một cơ chế xác minh tự động. Không chạy chỉ vì khách nói đã trả hoặc gửi ảnh chụp. Khoản thiếu/dư, sai mã hoặc tranh chấp cần đối soát riêng; không tự cấp/hoàn tiền.

Output là `SNABCDEF123456.windilicense`; chỉ upload tệp này vào `licenses/` của hosting tĩnh. Upload là bước bên ngoài project, cần đích và hành động chọn tệp rõ ràng. Bản quyền có mã máy, mã chứng từ đã băm, ngày cấp/hạn và chữ ký, không có private key hoặc email. Khi gia hạn, thay file cùng tên; ghi local atomically. Tải license phải bypass cache, hoặc cấu hình hosting `Cache-Control: no-store` cho `licenses/*`, để khách không nhận bản cũ.

Ledger giữ ID giao dịch unique: một receipt không cấp cho hai máy. Chạy lại receipt đã dùng không cộng thêm năm và trả bản quyền mới nhất của máy, tránh ghi đè gia hạn bằng license cũ. Giao dịch mới cho cùng máy gia hạn một năm lịch từ ngày trả tiền hoặc hạn cũ nếu còn hạn. Sao lưu ledger để chống dùng lại giao dịch và tính gia hạn. Không xóa hoặc trộn lịch sử khi chuyển sang backend tự động.

## Kết nối vào gói Mac

Sau khi trang tĩnh đã được đưa lên đúng nơi và kiểm tra đường dẫn license, build với:

```sh
.runtime/bin/python scripts/package_macos.py \
  --output dist/mac-preview-next \
  --public-key-file commerce/private/license-public.txt \
  --checkout-url https://sachnoi.windistudio.app/
```

Script pin `licenseMode=device`, chỉ nhận license schema 2 khớp mã máy. License email schema 1 của backend tự động cũ không mở khóa bản consumer này. Không đổi private/public key khi đã có khách trước khi có kế hoạch rotation. Preview hiện chưa cấu hình URL mua/nhận quyền thật vì chưa có hosting/deployment và chưa có Developer ID.
