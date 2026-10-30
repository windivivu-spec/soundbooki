> Cập nhật 24/10/2026: owner đã duyệt và bật thanh toán sách lẻ Mac qua SePay → queue HeyGen, đồng thời xác nhận quyền thương mại. Các trạng thái paid-deferred bên dưới là lịch sử. Xem [activation và kiểm chứng hiện tại](CLOUD-PAID-DEPLOYMENT.md).

# Rà soát Pro Cloud trên Mac — 23/10/2026

## Nguyên nhân đã xác minh

- Mẫu của Mac owner đã hoàn tất trên server (3/3 phần, 847 ký tự), và cả ba WAV trên máy hợp lệ, tổng khoảng 49,6 giây. Không tạo thêm mẫu để chẩn đoán; quota thật còn 4/5.
- Popup trước đây tiếp tục hiển thị câu xác nhận sau khi dịch vụ đã nhận yêu cầu. Trạng thái `ready` trên server làm dừng polling dù Mac chưa nhận đủ audio; kết quả retry đơn đã xong cũng chưa tự nhận audio.
- Nội dung/segment hiện tại không còn khớp hoàn toàn snapshot mẫu cũ. Mẫu cũ được giữ trong lịch sử; không tự gắn audio đó với chữ mới.
- App chỉ biết có URL gateway, chưa kiểm tra khả năng mua. Server vẫn đóng thanh toán (`WSN_BOOKS_ENABLED=false`); yêu cầu báo giá bị từ chối trước khi sinh đơn. Vì vậy chưa có mã đơn/số tiền/tài khoản được server chốt để dựng QR thật. Đây không phải lỗi bộ dựng QR native.

## Bản sửa

- Kiểm tra profile chỉ khi người dùng mở popup Pro: trả riêng khả năng tạo thử và mua sách, cùng quota có xác thực. Không gửi chữ sách, không đăng ký thiết bị mới ở bước kiểm tra. Action native được whitelist rõ ràng.
- Sau xác nhận, popup hiển thị đang gửi → đã nhận/chờ lượt → đang tạo → đang nhận về Mac → sẵn sàng. Nút nghe hiện ngay khi có audio local hợp lệ. Mất kết nối giữ request key; retry và nhận lại không tiêu thêm lượt.
- Tiếp tục kiểm tra có giới hạn khi server đã xong nhưng Mac chưa nhận đủ. Đóng/ẩn popup dừng lịch kiểm tra. Không báo take `ready` khi còn thiếu file.
- Mẫu/đơn cũ nằm đầu vùng cuộn, kể cả popup mẫu. Khi chọn snapshot cũ, giao diện nói rõ đây là bản chữ đã xác nhận trước đây.
- Thanh toán chưa mở thì khóa nút mua và báo đúng lý do. Với quote hợp lệ, vùng QR được đưa ra trước, dùng đúng số tiền/tài khoản/mã từ server, chờ xác nhận giao dịch rồi mới tạo. Client không nhận audio trả về cho đơn `awaiting_payment`/`expired`.

Gateway `wsn-books` đã cập nhật riêng lên version 8; không sửa secrets, schema, dispatcher, quota hoặc flag thu tiền. Worker vẫn chỉ nhận trial HeyGen theo phạm vi đã được duyệt. Giấy phép/giao dịch cũ không bị sửa.

## Kiểm chứng

- 136 Python core tests PASS ngoài sandbox để dùng codec macOS. Lần chạy sandbox ban đầu có lỗi codec M4A; chạy lại bộ đầy đủ ngoài sandbox PASS.
- 28 Deno gateway/worker tests và 9 commerce tests PASS.
- PGlite kiểm tra quota, retry không trừ lại, giá/receipt/paid claim, limiter, fairness, private grants PASS. Đây là database WASM một connection, không phải thử tải nhiều khách.
- HTTPS local integration PASS: nhận WAV nguyên tử, SHA, giữ phần đã tải khi gián đoạn, cache mẫu riêng, không phát snapshot mới bằng audio cũ, take và export WAV.
- Ba native WebKit harness PASS: xác nhận theo chương/quota; QR fixture được CoreImage quét đúng báo giá 25.000đ và tài khoản QA; các trạng thái gửi/lỗi/tiếp tục/nhận audio, mẫu cache, nhận mẫu lịch sử và chặn quote khi paid chưa mở.
- Profile/status thật sau cập nhật: trial mở trên Mac owner, purchase đóng, còn 4/5, mẫu cũ ready 3/3 và ba WAV hợp lệ. Không gửi yêu cầu synthesis, xác nhận tiền hoặc sửa thư viện khách trong chẩn đoán.
- Build local bằng `./scripts/build.sh` PASS. Bằng chứng trong `.qa/cloud-repair/`; ảnh QR QA ở `.qa/book-ui/payment-light.png`.

## Phần chưa kích hoạt

Chưa có thanh toán thật hoặc queue sách HeyGen trả phí. Theo `AGENTS.md` và `CLOUD-TRIAL-DEPLOYMENT.md`, cần xác nhận quyền thương mại HeyGen, phạm vi bật bán, đối soát ngân hàng tự động và activation queue paid trước khi mở thu tiền. Không bật chỉ để làm xuất hiện QR; các test fixture không chứng minh giao dịch tiền thật hoặc tạo cả sách production.
