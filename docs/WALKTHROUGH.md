# Walkthrough — khám phá Windi Sách Nói

Năm trang trong app, không dùng tài nguyên mạng. Tự hiện khi thư viện trống và chưa bỏ qua/hoàn tất hướng dẫn trên bản cài này. Thư viện có sách giữ luồng mở app hiện có; mọi người có thể mở lại từ “Khám phá ứng dụng · 5 bước” trên trang chủ hoặc “Thông tin ứng dụng → Khám phá ứng dụng”. Dấu đã xem lưu bằng localStorage cùng cơ chế tùy chọn giao diện hiện có.

| Trang | Nội dung ngắn | Nguồn đã đối chiếu |
| --- | --- | --- |
| Sách nói miễn phí | PDF/EPUB thành sách nói ngay trên Mac bằng Lite; không cần mạng sau khi có gói giọng | backend/worker.py, backend/models.py, backend/core.py |
| Giọng Pro trên cloud | Giọng đọc giàu cảm xúc; từ 10.000đ/cuốn; 10 lượt thử × 4.000 ký tự/Mac | backend/book_pricing.py, ui/book-cloud.js |
| Đọc như ebook | Lật trang, chọn chương, cỡ chữ, đọc và nghe, tự lưu dấu trang đang đọc | ui/ebook-reader.js, ui/live-reader.js, backend/worker.py readerSettings |
| Nghe offline | Lưu bản nghe, thêm nhạc thư giãn, xuất WAV/M4A có nhạc nền | ui/app.js, backend/core.py, native/App.swift |
| Combo mở bán | 5 cuốn Pro / 50.000đ, một lần/Mac; mua và dùng trước hết 01/11/2026 | backend/launch_offer.py, ui/launch-offer.js, docs/LAUNCH-COMBO.md |

Đã đọc Graphify hiện có trước khi thiết kế. Graph cũ chủ yếu mô tả cloud synthesis, nên generator được bổ sung community “Mac App Discovery” và cạnh từ walkthrough đến năm luồng đã đối chiếu source. Graph không được dùng làm bằng chứng tính năng đã hoạt động trên production.

Hướng dẫn mở, chuyển trang, bỏ qua, hoàn tất, xem lại đều không gọi cloud/TTS/thanh toán. Chỉ nút “Xem chương trình Pro” do người dùng bấm mới chuyển sang popup Pro hiện có và kiểm tra trạng thái dịch vụ. Không tạo quote hoặc mua tự động. Sau hạn, trang Pro bỏ giá combo và chuyển sang thông tin giá thường/đơn hiện có. Không quảng cáo số suất, đếm ngược giả hay cam kết thời gian tạo.

Bố cục onboarding kiểu iPad: minh họa lớn ở trên, tiêu đề và mô tả ngắn ở dưới, 5 chấm điều hướng có nhãn accessibility. Vuốt pointer/touch hoặc trackpad ngang để chuyển trang; giữ cuộn dọc, chặn quán tính làm lật nhiều trang liên tiếp. Có phím mũi tên, Escape, focus và xem lại. Hiệu ứng xuất hiện theo lớp và chuyển trang chỉ chạy khi mở/chuyển thật; tôn trọng thiết lập giảm chuyển động và giảm transparency. Nút cuối “Nghe Sách của bạn Ngay” mở chọn tệp khi chưa có cuốn đang mở, không tự tổng hợp hay phát audio. Dấu trang ở trang 3 là vị trí đọc tự lưu, không quảng cáo danh sách bookmark thủ công.

QA native: `tests/verify_walkthrough_ui.swift`; ảnh `.qa/book-ui/tour-{1..5}-{light,dark}.png`; log `.qa/walkthrough-native.log`. Dùng fixture cô lập, không gọi provider hoặc ngân hàng. Build qua `./scripts/build.sh`, log `.qa/walkthrough-build.log`. Đây là bản phát triển local; trạng thái kích hoạt bán Pro giữ theo docs/LAUNCH-COMBO.md.

Bản rút gọn đã build và QA native PASS ở 1180×800 sáng, 1000×720 tối: 5 trang, dots, animation xuất hiện, vuốt pointer hai chiều, giữ cuộn dọc, debounce wheel, reduced motion, bàn phím, bỏ qua/xem lại/persist, hết hạn combo và nút cuối mở picker. Gesture được kiểm tra bằng DOM event fixture trong WKWebView; không phải chứng nhận cảm ứng trên thiết bị iPad. Hồi quy chương trình Pro vẫn dùng fixture ngân hàng/provider.

## Chuyển động calm và lời chào (22/10/2026)

Owner yêu cầu giảm tốc xuất hiện, dùng file WAV Cartesia được cung cấp và bài đầu của nhóm Podcast. Hiệu ứng mới dùng easing nhẹ, chuyển động 7–18px, scale 0.985; cửa sổ 1.25s, minh họa 1.4s, chữ 1.1s với các độ trễ nhỏ (toàn bộ khoảng 1.64s). Vẫn tắt chuyển động theo thiết lập hệ thống/app.

- Lời chào: `assets/welcome/welcome.wav`, bản sao nguyên vẹn file owner cung cấp, 18.08 giây. Hash và nguồn trong `assets/welcome/source.json`. File WAV được gitignore; chỉ dùng local trong phạm vi đã cho phép, chưa cho phép phát hành tài sản này.
- Nhạc: `Piano podcast/1.mp3` → `assets/music/prepared/music-96aee74561b611f1.wav`, “Bài 01” trong catalog hiện có.
- `native/Welcome.swift` phát hai AVAudioPlayer local: lời 0.8, nhạc 0.4. Nhạc vào dần 1.8s, lời phát một lần mỗi lần mở; nhạc lặp đến khi đóng. Khi đóng, lời tắt dần 0.35s, nhạc 0.7s. Không thay đổi file gốc hoặc thiết lập nhạc/sách của người dùng.
- Chuyển trang không khởi động lại âm thanh. Có bật/tắt âm ở header, lưu lựa chọn trên máy. Mở lại nhanh không bị timer cũ dừng phiên mới. Nếu trước đó đang nghe sách/mẫu, dừng phiên phát đó trước khi phát lời chào; giữ nội dung và audio sách.
- Bridge chỉ nhận thao tác `start/mute/stop`, không nhận đường dẫn hoặc volume tùy ý. Không dùng Web audio, network hay provider. Đóng bằng bỏ qua/Escape/kết thúc/xem Pro đều dừng; reload/thoát app giải phóng ngay.

QA bổ sung: `tests/verify_welcome_playback.swift` đọc/phát file thực, kiểm tra mức 80%/40%, mute, không restart khi start lặp, fade/rapid reopen và thiếu asset. `tests/verify_walkthrough_ui.swift` kiểm tra 6 lần mở/đóng, hai lần mute, không phát lại khi chuyển 5 trang. Log `.qa/welcome-playback.log`, `.qa/walkthrough-calm-native.log`, `.qa/walkthrough-calm-core.log`, `.qa/walkthrough-calm-build.log`.
