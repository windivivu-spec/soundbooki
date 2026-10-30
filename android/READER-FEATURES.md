# Reader Android 0.2.6

## Sử dụng

- Mở sách → **Đọc**. Vuốt trái/phải hoặc chạm mép trang để chuyển; chạm giữa để ẩn/hiện điều khiển. Nút trang, mục lục, thanh vị trí và bàn phím vẫn hoạt động.
- **Aa** → chọn nền Theo máy / Giấy ấm / Trắng / Nâu dịu / Xanh dịu / Ban đêm / Đen. Nền Đen là `#000000`, chỉ phủ trang đọc; palette của app giữ nguyên. Chọn cỡ chữ, phông có chân, giãn dòng, lề, hiệu ứng Lật giấy / Trượt nhẹ / Không hiệu ứng rồi **Áp dụng**. Kéo xuống để thấy độ sáng và giữ màn hình sáng.
- Icon dấu trang ở góc trên thêm/bỏ dấu tại trang hiện tại. **Dấu trang** ở thanh dưới mở tất cả dấu của sách; chạm để đọc, nhấn giữ để sửa ghi chú hoặc xóa. Nhấn giữ icon phía trên cũng mở danh sách.
- Độ sáng chỉ áp dụng cho cửa sổ reader; mặc định theo máy. Giữ màn hình sáng là tùy chọn, hết tác dụng khi đóng reader.

## Dữ liệu và hiệu năng

Thiết lập riêng từng sách; vị trí và dấu trang gắn với hash của bản chữ. Nhiều dấu trên cùng trang sau khi đổi cỡ chữ vẫn giữ offset riêng. Dấu đơn của phiên bản cũ được chuyển sang danh sách một lần; xóa hết không làm dấu cũ quay lại. Nguồn văn bản, tiếng Việt, cache giọng và các chương giữ nguyên.

Chỉ gắn một trang TextView. Lật giấy dùng hai bitmap viewport có giới hạn pixel và giải phóng sau chuyển/hủy/đóng; không dựng bitmap cho toàn sách. Tắt animation hệ thống hoặc TalkBack touch exploration sẽ bỏ hiệu ứng. Kéo rồi hủy giữ vị trí trước đó; nhả tay xác nhận mới ghi offset. Màu nền đổi ngay không chạy paginator. Typography/lề thay đổi được gộp và dàn trên worker, có hủy tác vụ/cache bốn bố cục.

Paginator vẫn đo theo khối, kiểm thêm từng trang độc lập vì Android có thể ngắt dòng khác khi tách đoạn từ khối dài. Chỉ rebase khối khi ranh giới thực tế thay đổi. Phân hoạch nguồn được kiểm tra nguyên văn, gồm ký tự ngoài BMP và dấu tổ hợp. Reader mở lại đúng offset sau Activity recreation, giữ chế độ ẩn điều khiển và thiết lập.

## Kiểm chứng

Kết quả cấu hình, checksum và giới hạn được ghi tại [QA.md](QA.md). Raw evidence local ở `.qa/android-ebook/`; thư viện fixture nằm riêng `.qa/reader-features`, `.qa/reader-performance`, `.qa/reader-chapters` trong emulator. Không gọi synthesis, thanh toán hay upload trong đợt kiểm tra reader này.

Đây là APK thử Android 13+ ARM64, chưa phải phát hành Google Play. Chưa có xác minh mới trên Pixel 8 Pro/Redmi Note 13 thật hoặc phép đo pin/nhiệt/FPS trên máy vật lý.
