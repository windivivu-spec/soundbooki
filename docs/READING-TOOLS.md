# Đọc, ghi nhớ và xuất sách nói — 25/10/2026

Mac local **0.8.3 · Build 19** và Android local **0.2.7-test · versionCode 10** bổ sung các tính năng được chủ sở hữu chọn từ kế hoạch cạnh tranh. Không có thay đổi activation thanh toán, trial, credential hoặc phát hành public.

## Cách sử dụng

| Tính năng | Mac | Android |
|---|---|---|
| Dán văn bản | Không còn trong giao diện Mac; các sách đã tạo vẫn được giữ | **Tạo sách → Dán văn bản** → Thêm vào thư viện |
| Việt–Anh cùng sách | Bật **Đọc Việt–Anh tự động · local** cạnh Quản lý giọng, hoặc trong tùy chỉnh reader. Cần có Kitten đã tải. Dùng khi đọc Lite hoặc tạo sách bằng Lite. | Chi tiết sách → menu **⋯ → Bật đọc Việt–Anh**. Cần giọng Anh offline đã cài trong hệ thống. |
| Tìm nội dung | Mở **Đọc sách → Tìm nội dung**; Command-F trong reader cũng mở tìm nội dung | Mở reader → kính lúp → **Tìm trong nội dung** |
| Tô và ghi chú | Chọn chữ trong ebook → **Tô / Ghi chú đoạn chọn** → màu, ghi chú và Lưu. Có thể chọn qua nhiều câu. | Reader → kính lúp → **Chọn chữ để tô / ghi chú** → nhấn giữ chữ → **Tô / Ghi chú** trong menu chọn chữ. Khi chọn chữ, chuyển trang bằng nút mũi tên. Bật lại menu để kết thúc chọn chữ. |
| Sổ tay | **Sổ tay** trong reader → đến đoạn, sửa hoặc xóa ghi chú | Reader → kính lúp → **Sổ tay của cuốn sách** → chọn ghi chú để đến vị trí và sửa/xóa |
| M4B | Tạo đủ audio trong phạm vi đã chọn → **Tải về → M4B · Có chương và bìa**. Bản sách nói đã lưu cũng có lựa chọn M4B. | Chi tiết sách → **⋯ → Xuất M4B / WAV** → cả sách/chương → M4B. Audio Cloud đã nhận có lựa chọn M4B riêng. |

Gõ tìm có hoặc không dấu đều được; mỗi lần hiển thị tối đa 200 kết quả đầu. Sổ tay lưu riêng từng cuốn trên thiết bị. Khi đổi chữ làm thay edition, ghi chú bản trước vẫn giữ và hiện nhãn, không tự gắn nhầm vào nội dung mới. Đổi font, lề và dàn trang không làm lệch vị trí ghi chú.

## Việt–Anh

- Mac: câu Việt dùng Lite/Nano; câu Anh dùng Kitten/Jasper. Android: câu Việt dùng Nano; câu Anh dùng một giọng hệ thống được xác nhận không yêu cầu mạng, có khóa tên voice và version engine vào cache. Nếu giọng biến mất/cập nhật, báo người dùng bật lại Việt–Anh để cập nhật cấu hình.
- Lựa chọn này không thay model/giọng hoặc snapshot của đơn Pro đã mua. Không có API key hay yêu cầu Cloud trong đường đọc Việt–Anh local.
- Bộ nhận diện dùng quy tắc từ vựng thận trọng ở cấp câu; tên riêng, câu ngắn, tiếng Anh ít từ nhận diện và câu trộn Việt–Anh có thể vẫn dùng Lite. Đây chưa phải nhận diện mọi ngôn ngữ hoặc chuyển giọng từng từ.
- Bật/tắt Việt–Anh có cache riêng; tốc độ phát không đổi cache. Đoạn chưa hoàn tất không được commit thành audio dùng được. Chữ nguồn/originalText được giữ riêng.
- Android cần cài sẵn dữ liệu giọng Anh offline qua cài đặt TTS hệ thống. App không tự tải giọng và không dùng giọng network để thay thế.

## M4B và giới hạn

- Mốc chương được tính từ thời lượng WAV thực, bắt đầu lại từ 0 với phạm vi được chọn. Mac dùng segment membership và snapshot chương khi tạo bản đọc; Android dùng cùng `BookChapters.Plan` với producer, không suy luận mốc bằng tỷ lệ ký tự.
- M4B có AAC, tên sách/tác giả nếu có, bìa từ nguồn hoặc bìa chữ khi nguồn không có ảnh, QuickTime chapter text track và metadata chương tương thích MP4. Android trộn nhạc đang lưu theo cuốn khi xuất M4B; đổi nhạc không tạo lại narration.
- Mac cần ffmpeg local trong môi trường phát triển. Android dùng MediaCodec/MediaMuxer của hệ thống, không đóng gói ffmpeg.
- Các bản Pro cũ không mang thông tin chương bất biến chỉ có một phần audio trong M4B. Đơn Mac mới lưu nhãn chương local bên ngoài snapshot gửi server; không thay hợp đồng giá/thu tiền/dispatcher.
- Xuất Mac giữ nguyên file đích cũ nếu hủy trước commit. Android chuẩn bị hoàn chỉnh trong cache rồi mới chép ra tài liệu người dùng chọn; hủy trước bước chép giữ narration và dọn file tạm. Android không có bảo đảm atomic replace với mọi nhà cung cấp tài liệu SAF.
- Pipeline Mac hiện vẫn có giới hạn PCM trung gian WAV 4 GB; xuất từng chương/phạm vi nhỏ hơn khi gặp giới hạn. Chưa xác minh sách hàng chục giờ hay mọi player/xe hơi. Chưa kiểm tra tương thích trực tiếp Apple Books/VLC bằng giao diện trong đợt này.

## Kiểm chứng

Bằng chứng cô lập ở `.qa/reading-features/`:

- 151 Python core tests: PASS, 1 skipped. Bao gồm tìm không dấu, ghi chú UTF-16 có emoji, giữ edition cũ, cache Việt–Anh, snapshot chương giữa cùng trang, file M4B thật có bìa và hủy không ghi đè file đích.
- `tests/bilingual_integration.py`: suy luận Lite → Kitten → Lite và reader bắt đầu ở câu Anh, PASS; không gọi Cloud. Một đoạn QA ngắn mất khoảng 5,6 giây trên Mac này; không là cam kết tốc độ sách bất kỳ.
- `tests/verify_reading_tools.swift`: WebKit native + worker thật, dán chữ, tìm/đến kết quả, lưu/mở lại ghi chú, tô sau reflow, setting Việt–Anh, M4B UI, sáng/tối và cửa sổ 1000×700; PASS. Nhận diện chữ được kiểm từ dữ liệu fixture, không chứng minh mọi PDF/OCR.
- Android `ReadingToolsTest`: kiểm mô hình dữ liệu, UI reader/tìm/sổ tay/paste, MediaCodec AAC/M4B thật với nhạc, chương/bìa và cancellation; 4 test đầu PASS. Giọng Anh offline của emulator `en-US-language` tạo audio thật PASS.
- Test bổ sung `actualBilingualServiceProducesBothLanguages`: service thật tạo đủ đoạn Việt và Anh, giữ originalText, emulator tắt Wi-Fi/data; PASS.
- File M4B Android thật được đưa qua ffprobe: AAC + chapter track + JPEG attached picture; hai chương `Chương Một`, `Chương Hai 🌍` ở mốc 0/1 giây, tổng 3 giây. Header do mã MP4 riêng cũng được kiểm bằng JVM/ffprobe.
- Regression Android reader/chapter + tính năng mới: 17 trường hợp; 16 qua ở lượt đầy đủ, test đệm còn lại qua sau khi đổi fixture câu lặp thành câu khác nhau. Fixture cũ có thể tạo xong cả chương từ cache trước callback phát trên emulator nhanh, nên điều kiện kiểm thử tiến độ không ổn định. Không sửa producer để làm chậm nhằm khớp test.
- Build Mac và Android bằng `scripts/build.sh` / `scripts/build.sh --android`; APK signer preview giữ nguyên, để cài đè bản thử. Đây không phải installer portable/notarized hay bản Google Play.

Android QA hiện dùng emulator API 35 ARM64. Chưa kiểm trên điện thoại thật, chưa benchmark pin/nhiệt hoặc sách nhiều giờ. SDK/AVD tạm dùng cho lượt QA đã được dọn sau kiểm thử; giữ log, screenshot và artifact kết quả trong `.qa/reading-features/`.
