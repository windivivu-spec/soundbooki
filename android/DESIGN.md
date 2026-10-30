# Soundbooki Android — tủ sách và trình nghe

23/10/2026 · bản thử local 0.2.1.

## Hướng giao diện

Giữ palette `UiTheme`: nền xanh xám sạch, mặt đọc đặc, xanh dương cho hành động chính, font local SF Pro Rounded / SVN Nexa và system sans cho mô tả. Giữ light/dark theo hệ thống. Không dùng neon, remote asset, số lượt nghe hoặc nội dung danh mục giả.

## Điều hướng

- **Trang chủ**: sách mở gần đây, kệ sách ngang từ thư viện thực, đường vào nghe thử giọng Pro, empty state thêm sách.
- **Thư viện**: lưới bìa, tìm theo tên, lọc tất cả/đang đọc/đã lưu. Dữ liệu tải ở worker; sách trống khởi tạo không xuất hiện như một cuốn đã nhập.
- **Tạo sách**: thêm tập tin hoặc tạo bản văn bản, giữ workspace import/chỉnh sửa/dọn nội dung/chương/xuất hiện có. CTA nghe cố định dưới vùng soạn thảo.
- **Đang nghe**: màn hình tập trung; ẩn nav để dành chỗ cho điều khiển và văn bản. Nút back và system Back cùng về chi tiết sách. Home, Thư viện, Tạo sách và Cài đặt có mini player khi audio đang chạy.
- **Cài đặt**: giọng, nhạc/tốc độ, Pro theo sách và hướng dẫn. Không có tài khoản/avatar giả.

**Chi tiết sách** là màn hình sâu, ẩn nav và dùng back về tủ sách để dành chỗ cho các chương: bìa + metadata thực, đọc/sửa, tìm chương, chọn chương và phát liên tục tùy chọn. Tab sách nói dùng take đã hoàn tất, nghe/chia sẻ đúng WAV đã chọn.

## Dữ liệu và phản hồi

- Bìa lấy từ EPUB/PDF bằng nguồn local; sách text dùng jacket typography. Bìa chỉ là cache bên cạnh sách, không sửa nguồn.
- Chương dùng `BookChapters`, không suy luận semantic từ văn xuôi. Trạng thái chưa tạo/đang nghe/sẵn sàng và thời lượng chỉ hiển thị khi có dữ liệu thực.
- Timeline đọc thời lượng WAV. Chưa tạo đủ chương thì không giả tổng thời lượng; hiển thị lượng audio đã tạo và chỉ cho kéo timeline khi đủ chương. Tua ±15 giây đi qua các đoạn đã sẵn sàng, giữ vị trí khi pause.
- Văn bản đi cùng audio là đoạn thật đang phát, không phải word-level alignment. Take cũ không khớp bản chữ hiện tại sẽ không mở theo dõi nhầm sang bản mới.
- Panel tạo có trạng thái đang tạo/đang hoàn tất đoạn/tạm dừng/đã lưu, phần trăm thật và nút dừng/tiếp tục riêng với playback. Phát sớm sau khoảng 500 ký tự đầu; UI không hiển thị quy tắc đệm này. Mở lại app cần chủ động tiếp tục, không bật tiếng bất ngờ.
- Hẹn giờ ngủ là deadline monotonic trong foreground playback service. Pause không làm mất các đoạn hoàn tất.
- Mẫu giọng Pro lấy từ bảy recording owner đã có, phát offline theo hành động bấm; waveform được đo từ WAV. Không gửi sách, tạo đơn hay dùng quota khi chỉ nghe mẫu. Thử với chữ sách đi qua Cloud popup/đồng ý/gateway hiện có.
- Demo recordings chỉ dùng bản local owner; quyền publication và paid/deployment vẫn là phạm vi riêng. Không thêm F5 riêng, dataset hoặc key.

## Điểm mã

`AppShell.java`, `MobileUi.java`, `BookArtwork.java`, `VoicePreview.java` là lớp giao diện mới. `MainActivity.java` tiếp tục sở hữu import/editor/Cloud. `PlaybackService.java` giữ một producer và một player, thêm timeline/tua/hẹn giờ. Không dựng lại tủ sách theo mỗi playback tick.

## Banner đọc sách bằng code · 23/10/2026

`ReadingBanner.java` giữ dải ngang gọn theo chiều rộng đo được, giữ chữ/nút là native views và tap target từ 48dp. `BannerBooksView.java` vẽ 5 jacket, tựa, cảnh và biểu tượng bằng Canvas theo vùng thực tế, giữ khoảng thở quanh cụm sách (~80%). Bìa luôn có tỷ lệ 2:3, chỉ scale đồng đều cả hai chiều để chữ/hình không bị dẹt. Không dùng ảnh banner raster. Banner này mở thêm sách; không mở bán combo Mac hoặc tạo giao dịch Android mới.
