# Mac Pro: nhận kết quả và giao diện — 28/10/2026

## Thay đổi trong app local

- Cửa sổ đang mở tự kiểm tra mỗi 3 giây, nhận các file đã hoàn tất và giữ nguyên đơn/snapshot. Bỏ giới hạn 30 lần kiểm tra; mỗi lần mở hoặc tiếp tục cho phép tối đa 20 phút cập nhật. Hết khoảng này có nút tiếp tục rõ ràng. Đóng cửa sổ hoặc ẩn ứng dụng dừng lịch kiểm tra; trở lại cửa sổ nhận tiếp. Không thêm dịch vụ nền.
- Lỗi nhận kết quả tự thử lại với khoảng chờ tăng dần, tối đa 30 giây giữa các lần. Không tự gửi lại yêu cầu tạo mẫu, không đổi request key hoặc dùng thêm lượt. Yêu cầu mới vẫn cần người dùng xác nhận.
- Worker thông báo lúc bắt đầu nhận và sau mỗi WAV đã kiểm hash/định dạng, chuyển đổi và đổi tên nguyên tử. UI hiển thị file đã lưu trong lúc các file sau còn đang tải. Chỉ tiền tố liên tục của snapshot được nghe, tránh bỏ qua phần đầu khi kết quả về sai thứ tự.
- Nút **Nghe phần đầu** giữ cửa sổ mở để tiếp tục nhận kết quả; có tạm dừng/tiếp tục nghe. File mới thêm vào hàng phát của cùng mẫu, không khởi động lại audio đang nghe. Nếu đóng cửa sổ, audio đang phát vẫn tiếp tục nhưng lịch kiểm tra dừng; mở lại để nhận phần còn lại.
- Tiến trình ban đầu dùng thanh chưa xác định thay cho thanh 0% trống. Sau khi có kết quả hiển thị số phần thực tế, không suy diễn phần trăm của bước tổng hợp chưa hoàn tất. Khi đủ audio hiện **Nghe ngay** hoặc **Mở sách nói**.
- Cửa sổ Pro dùng chữ hệ thống 14–18 px cho nội dung/điều khiển, giữ tiêu đề hiện có. Xác nhận còn chương, giọng, độ dài và lượt. Bỏ thông tin số request/chi tiết chia file khỏi xác nhận; lịch sử và mã đơn được thu gọn. Bỏ hai đoạn hướng dẫn lặp trong Sách nói của bạn. Không thay nguồn sách, nhạc nền, cache hoặc điều kiện thanh toán.

## Phép đo chỉ đọc

Lúc kiểm tra, đơn trial 8.462 ký tự ngày 28/10 có 2 file, bắt đầu 22:39:22 và hoàn tất 22:42:14 (UTC+7), khoảng 172 giây. Cả hai task một attempt, không có diagnostic lỗi; cron mỗi 3 giây vẫn active, queue không còn queued/processing và không có cooldown đang chặn. Dữ liệu này cho thấy chờ tổng hợp/tải/commit có thật; không thể quy toàn bộ cho polling. Không đo riêng được thời gian inference của provider từ các mốc này. Tối ưu local giảm trễ nhận/phản hồi và cho nghe sớm; không cam kết tổng hợp tức thì hoặc ETA cho sách khác.

## Kiểm chứng

- Python: 163 tests PASS, bao gồm snapshot, quota, cache, tiền tố nghe liên tục, xuất audio và lưu nhạc.
- HTTPS localhost thật: PASS callback trước kết quả cuối, SHA/WAV, tải gián đoạn giữ file đã xong, retry không tạo mới, xuất mẫu và đơn đã mua. Đây là dịch vụ QA nội bộ, không phải HeyGen inference thật.
- Native WebKit: xác nhận gộp lượt, khôi phục đơn, giao diện sáng/tối, tự nhận sau hơn 30 lần kiểm tra, lỗi mạng tự tiếp tục, nghe phần đầu trong lúc nhận file tiếp theo, dừng polling khi đóng và tiếp tục rõ ràng khi hết khoảng tự cập nhật. Dùng fixture riêng trong `.qa`.
- Build bằng `WINDI_SKIP_REGISTRATION=1 ./scripts/build.sh`. Chỉ thay app phát triển local; không triển khai function/SQL, đổi limiter, dùng trial Mac owner, tạo thanh toán hoặc phát hành installer.

Bằng chứng riêng ở `.qa/cloud-experience/`; không đưa dữ liệu QA hoặc báo cáo đơn vào gói phát hành. Thoát hẳn rồi mở lại app Mac để worker Python nạp callback mới.

## Tiếp nối: bỏ lưu trung gian

Owner đã phê duyệt triển khai cloud sau bản sửa UI. Luồng direct mới đã triển khai cùng Mac build 23; xem [DIRECT-AUDIO-DELIVERY.md](DIRECT-AUDIO-DELIVERY.md). Các mô tả “chỉ local, chưa triển khai” phía trên thuộc riêng lần sửa giao diện ban đầu.
