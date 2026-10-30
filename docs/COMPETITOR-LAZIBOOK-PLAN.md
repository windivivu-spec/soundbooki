# Kế hoạch cạnh tranh với LaziBook — 25/10/2026

## Cơ sở và phạm vi

- Video chủ sở hữu gửi: https://www.facebook.com/share/v/1DU1wwy7HE/ — reel 3365780863608564, dài khoảng 124 giây. Đã tải và kiểm tra 21 khung hình xuyên video; không có phụ đề. Phân tích này dựa vào hình ảnh/chữ demo, không phải phép chấm chất lượng âm thanh hay benchmark đối thủ.
- Đối chiếu trang chính thức https://book.lazidi.vn/ và https://apps.apple.com/us/app/lazibook/id6822248877 ngày 25/10/2026. Tính năng do nhà phát triển công bố chưa được kiểm thử trực tiếp. Trang chính thức và mô tả cửa hàng có khác biệt về một số số lượng/trạng thái nền tảng; không dùng số giọng làm mục tiêu cạnh tranh.
- Đối chiếu source Soundbooki Mac/Android và tài liệu hiện tại; không chạy QA hay sửa ứng dụng trong đợt lập kế hoạch này. README có chỗ cũ: source đã có MP3; thu tiền sách lẻ Mac đã được kích hoạt theo CLOUD-PAID-DEPLOYMENT.md, nhưng tài liệu đó chưa ghi nhận chuyển tiền thật toàn tuyến.
- Giữ quyết định thiết bị độc lập, không tài khoản/đồng bộ; không mở lại Clone Pro/credit cũ. Mọi HeyGen synthesis vẫn qua dispatcher chung. Kế hoạch không phải phê duyệt triển khai hoặc phát hành các phạm vi còn tách riêng.

## Những gì demo thể hiện

Mốc gần đúng theo khung hình, có thể lệch vài giây:

| Mốc | Nội dung thể hiện |
|---|---|
| 00:00–00:20 | Nhiều giọng Việt; giọng riêng cho người dẫn chuyện/lời thoại |
| 00:20–00:34 | Nhạc và âm thanh môi trường phát cùng lời đọc |
| 00:34–00:45 | Quy tắc sửa phát âm tên riêng |
| 00:45–00:54 | Tự chọn giọng Anh cho câu tiếng Anh |
| 00:54–01:14 | Chuyển sang Nano khi chậm/nóng; bộ đệm; điều khiển màn hình khóa |
| 01:14–01:34 | Clone từ bản ghi ngắn, công bố xử lý trên máy |
| 01:34–01:48 | Kịch bản nhiều vai, thẻ nghỉ/cảm xúc |
| 01:48–02:02 | Tạo đoạn dài; xuất M4B cả sách với bìa và chương |

## Định hướng

Tập trung vào sách tiếng Việt được nhập đúng, sửa dễ, đọc đúng và nghe liên tục. Chứng minh chất lượng Lite/Pro bằng cùng một bộ đoạn thử và nghe mù; không coi nhiều giọng, tần số mẫu cao hoặc đoạn quảng cáo là bằng chứng chất lượng.

LaziBook đang niêm yết miễn phí trên App Store. Giá trị Pro Cloud phải thể hiện qua giọng tốt hơn trên nội dung thực tế, tiết kiệm thao tác và giao nhận đáng tin cậy. Chưa đủ dữ liệu để khẳng định ưu thế này trước khi so sánh.

## Backlog theo thứ tự đề xuất

| Ưu tiên | Hạng mục | Hiện trạng và phạm vi cần làm | Điều kiện nghiệm thu |
|---|---|---|---|
| P0 | Đo và cải thiện nghe liên tục | Mac có Nano session/buffer/native queue; Android có service/buffer/MediaSession. Đo cold/warm, tốc độ 1×/1,5×, chuyển chương, tua, khóa màn hình Android, CPU/pin/nhiệt. Điều chỉnh lượng đệm theo tốc độ sinh và sức máy, có giới hạn dung lượng. Không tự đổi giọng/model. | Báo cáo thời gian phát đầu, số lần thiếu đệm và thời gian chờ trong phiên 30–60 phút trên máy thật; không phát stale audio sau sửa chữ/đổi giọng; mở lại đúng vị trí. Chỉ đặt cam kết tốc độ sau đo baseline. |
| P0 | Từ điển phát âm | Chưa thấy UI quy tắc người dùng; có normalization code. Thêm cặp chữ gốc → cách đọc, phạm vi cuốn/máy, nghe thử và bật/tắt; ưu tiên quy tắc theo sách. | Nội dung hiển thị/originalText không đổi; khớp theo ranh giới từ/cụm, ưu tiên cụm dài và quy tắc riêng; hash revision quy tắc vào cache; sửa quy tắc chỉ làm mới đoạn bị ảnh hưởng. |
| P0 | Hoàn thiện chất lượng chữ đầu vào | Đã có OCR/chương/dọn nội dung. Mở rộng xem trước dòng lặp, số trang, nối câu qua trang và tìm-thay thế có duyệt. Không tự sửa tên/số hay suy diễn chương. | Hiển thị đề xuất trước/sau, chọn áp dụng và hoàn tác; nguồn gốc vẫn giữ. Bộ mẫu EPUB/PDF chữ/scan/nhiều cột phải báo rõ giới hạn và không mất đoạn nguồn. |
| P0 | Xuất M4B có chương | Đã có MP3/M4A/WAV/Web ZIP và nhạc nền. Thêm M4B với bìa/tác giả/tên chương, ước lượng dung lượng và cảnh báo thiếu audio. | Mốc chương tính từ audio thật và segment membership; hỗ trợ chương giữa trang; phạm vi xuất khớp tạo giọng; hủy giữ bản cũ; kiểm tra file dài và mở/chọn chương trong Apple Books cùng ít nhất một player khác. |
| P1 | Đọc Việt–Anh trong cùng cuốn | Có Lite Việt và Kitten Anh nhưng chọn ngôn ngữ cấp sách. Thêm tùy chọn nhận câu Anh và đặt lại ngôn ngữ thủ công theo câu/đoạn. | Tên riêng/câu ngắn không bị chuyển tùy tiện; có ngưỡng chắc chắn và override; giữ offset nguồn, cache theo engine/voice/revision từng đoạn; mặc định tắt trước khi đạt QA. Bản đầu chỉ local, không thay snapshot Pro đã mua. |
| P1 | Điều khiển nghe hằng ngày | Android có hẹn giờ phút/dấu trang/ghi chú và MediaSession. Mac cần kiểm tra/bổ sung hẹn giờ, phím media và Now Playing; thêm dừng hết chương, tua ±15/30 giây nếu thiếu. | Dừng đúng ranh giới câu/chương; timer không tự phát lại sau mở app; kiểm tra tai nghe, mất audio focus, rút tai nghe và khôi phục phiên trên thiết bị phù hợp. |
| P1 | Tìm nội dung, dấu và sổ ghi chú | Hiện có tìm tên thư viện; Android có dấu trang/ghi chú, chưa tương đương tô đoạn/sổ tay. Tìm trong cuốn trước, rồi toàn thư viện; hỗ trợ gõ không dấu. | Kết quả trở về đúng đoạn gốc dù đổi font; ghi chú gắn edition/offset, không gắn số trang dàn lại; xuất Markdown/TXT; tìm sách dài không khóa giao diện. |
| P1 | Dán văn bản và định dạng thông dụng | Thêm dán chữ/TXT trước; DOCX sau nếu có nhu cầu. Tái sử dụng pipeline sách, không dựng studio riêng. | Lưu nguồn riêng; kiểm tra/sửa → nghe → xuất; không tải tài nguyên nhúng hoặc chạy nội dung chủ động. |
| P1 | Nhạc/âm môi trường vừa đủ | Có nhạc và gain lưu theo sách, đã đi theo export. Thêm ít âm mưa/sóng/rừng có quyền dùng rõ ràng, nghe thử và tự giảm âm nền khi cần. | Loop không lộ tiếng nối, không che lời, không clipping; đổi âm nền không tạo lại narration. Không dùng demo local-only làm asset phát hành. |
| P2 | Thư viện và sao lưu thủ công | Thêm Đang nghe/Đã xong, bộ sưu tập, metadata/bìa, chống nhập trùng và gói sao lưu người dùng chủ động. | Khôi phục chữ/ghi chú/vị trí/audio hợp lệ; không chuyển credential Keychain, trial, đơn mua hay quyền của máy khác; không biến thành đồng bộ nền. |
| P2 | Hai giọng dẫn chuyện/lời thoại | Thử nghiệm tùy chọn nếu người dùng đọc truyện cần; bắt đầu đánh dấu thủ công. Không tự gán nhân vật từ prose. | Preview đoạn và sửa gán vai; cache theo bản đồ vai; xuất khớp nghe. Pro nhiều giọng cần hợp đồng snapshot/giá riêng trước. |

## Kế hoạch các đợt

1. **Đợt 1 — nghe đúng:** lấy baseline tốc độ/độ ổn định, từ điển phát âm, rà sửa đầu vào. Ước lượng 5–8 ngày công, gồm QA.
2. **Đợt 2 — sách nói hoàn chỉnh:** M4B, hẹn giờ/điều khiển nghe còn thiếu, rà xuất sách dài. Ước lượng 4–7 ngày công.
3. **Đợt 3 — đọc tiện:** Việt–Anh cấp câu, tìm nội dung, hoàn thiện dấu/ghi chú. Ước lượng 7–12 ngày công.
4. **Đợt 4 — mở rộng theo nhu cầu:** dán chữ/TXT, âm môi trường, thư viện/sao lưu. Ước lượng 5–9 ngày công; DOCX và nhiều vai tách riêng.

Đây là khoảng ước lượng cho phát triển tuần tự và kiểm thử, chưa phải lịch giao hàng; triển khai cả Mac và Android cùng đợt có thể tăng công. Ưu tiên hoàn thiện Mac, kiểm chứng Android thật trước khi coi tính năng service/playback là sẵn sàng cho khách.

## Clone và nhiều giọng

Không đưa vào đường găng. Có thể làm spike tối đa 1–2 ngày công để xác định runtime hiện tại có hỗ trợ reference voice hay không, dung lượng tăng, độ trễ, chất lượng và phạm vi quyền; không hứa hoàn thành clone trong 1–2 ngày. Chỉ đưa vào sản phẩm nếu cải thiện rõ khi nghe thử, chạy phù hợp máy mục tiêu và không kéo lại luồng Clone Pro cũ. Không thêm hàng chục giọng có chất lượng thấp để chạy đua số lượng.

## Những việc riêng trước phát hành

- Kiểm chứng giao dịch thật từ SePay tới nhận audio cho sách lẻ Mac vẫn là một cổng QA riêng; không dùng callback giả hoặc demo bypass dispatcher để tuyên bố thành công.
- Đo iOS/Android của đối thủ trực tiếp mới có thể kết luận về pin, độ trễ và chất lượng. Video/App Store là chứng cứ tính năng được quảng bá.
- iOS là khoảng trống tiếp cận khách hàng so với đối thủ; khảo sát nhu cầu trước khi mở dự án riêng. Installer/notarization/public release, combo, Android/PC paid activation vẫn giữ phạm vi phê duyệt riêng.
- Không đưa dịch sách, OAuth/Drive đăng nhập, đồng bộ tài khoản, truyện tranh hoặc highlight từng từ vào backlog gần chỉ để khớp danh sách đối thủ. Highlight từng từ chỉ cân nhắc khi có timing đủ tin cậy; không giả thời gian theo tỷ lệ ký tự.
