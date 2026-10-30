# Đọc & nghe — 0.8.2, Build 18

Trong mỗi sách, chọn **Đọc & nghe** để vừa đọc vừa nghe. **Tạo sách nói** giữ nguyên luồng kiểm tra/sửa chữ, chọn chương và tạo audio. Chế độ được nhớ riêng cho từng sách.

## Không gian ebook

**Đọc & nghe** mở kín cửa sổ, ẩn thư viện và các công cụ tạo audio. Mặc định dùng nền theo app, hai trang cạnh nhau, thanh nghe nổi phía dưới. Nút **×** góc trái hoặc Esc trở về giao diện chính, không xóa sách. Có nút toàn màn hình macOS riêng. Ở vùng rất hẹp, tự chuyển thành một trang để giữ chữ đọc được.

- Mũi tên hai bên, phím trái/phải, Page Up/Down hoặc cuộn trackpad lật trang. Hiệu ứng gấp trang chỉ chạy khi chuyển trang, không chạy lại theo tick audio; tôn trọng Giảm chuyển động.
- Nút **Aa** chọn nền sáng dịu/tối, chỉnh cỡ chữ, bật/tắt bám theo, nhập số trang nguồn, chọn **Ebook** / **PDF / ảnh gốc** và **Lưu bản EPUB…**. Nút mục lục chuyển đến chương đã có trong dữ liệu sách.
- Trang ebook tự thay đổi theo cỡ chữ và kích thước cửa sổ. Số **Trang đọc** là trang đã dàn lại; **Nguồn** là trang PDF/mục EPUB tương ứng. Mốc câu/đoạn nguồn giữ vị trí khi đổi cỡ chữ, không coi số trang ebook là số trang PDF.
- PDF tạo EPUB dẫn xuất trong `reader/<content-hash>/book.epub` khi mở lần đầu, dùng chữ hiện tại và ảnh raster lấy được từ bản gốc. EPUB đầu vào cũng dùng cùng cách dàn trang an toàn. Cache này không đổi khi thay giọng/tốc độ hoặc có thêm audio; sửa chữ tạo phiên bản dẫn xuất mới. Có thể lưu EPUB ra vị trí do người dùng chọn.
- Ảnh PDF được lấy theo ma trận đặt ảnh, gộp các mảnh ảnh gần nhau và crop bằng PDFKit. Hiện chỉ lấy ảnh raster đủ lớn trên PDF có chữ, không hứa giữ mọi đồ họa vector, trang xoay, ảnh nền toàn trang hoặc bố cục phức tạp. PDF scan vẫn dùng chữ OCR đã nhập; chọn bản gốc để đối chiếu. EPUB chỉ nhận ảnh raster nội bộ, không thực thi script/SVG hay tải mạng.

## Lite đọc liên tục và chọn câu

Trong view đọc, **Play chỉ dùng Lite local**, độc lập với giọng/phạm vi đã chọn ở màn hình tạo sách nói. Bộ chọn giọng Lite ở thanh trên lưu riêng trong thiết lập đọc; không đổi giọng Pro của sách hay đơn đã mua. Không tự tạo giọng khi chỉ mở sách.

Bấm một câu (hoặc Tab tới câu rồi Enter) để nghe ngay từ nội dung đó. App tổng hợp audio theo từng câu/đoạn câu, không tua bằng tỷ lệ ký tự vào bản đọc cũ. Vì vậy highlight chuyển theo đúng audio của câu đang phát; chưa có highlight từng từ. Các đoạn câu cực dài vẫn theo ranh giới trích chữ hiện có.

Lite tạo đệm tối đa 16 câu, hướng tới khoảng 65 giây, rồi bổ sung khi nghe. Bộ phát native dùng cùng `NarrationQueue` để xếp WAV kế tiếp trên đồng hồ thiết bị. Play tiếp tục đến cuối sách, không bị giới hạn bởi chương/phạm vi tạo đang chọn. Nếu chưa tạo kịp câu tiếp theo, hiện **Đang chuẩn bị Lite** rồi tự phát khi xong. Pause/resume, tua, câu trước/sau và đổi tốc độ giữ nguyên cache. Đổi giọng trong lúc nghe bắt đầu lại câu hiện tại bằng giọng mới; audio hoàn tất của giọng cũ vẫn được cache.

Mốc đọc lưu theo cue nguồn trong `reader.json`. Ra giao diện chính dừng phiên đọc; lần vào lại có thể Play từ câu đã lưu. PDF gốc không có bề mặt chữ bấm trực tiếp: dùng chế độ Ebook để chọn câu.

## Hiển thị và theo dõi

- Tùy chọn **PDF / ảnh gốc** vẫn mở trực tiếp bằng PDFKit/ImageIO để giữ số trang và bố cục nguồn. Mặc định PDF mở bằng chế độ ebook đã dàn lại, tránh nền trắng của trang gốc trong giao diện tối.
- **Ebook** trình bày chữ đã nhập/sửa theo thứ tự đọc, có chỉnh cỡ chữ. Đây là dàn trang lại, chưa giữ nguyên mọi CSS/kiểu trình bày của EPUB gốc.
- Trang tự chuyển theo trang nguồn của đoạn audio. Khi đang tạo giọng, nhãn vị trí báo trang đang tạo. Tạo giọng không có highlight câu giả đang phát.
- Với phiên đọc Lite mới, highlight đi theo file audio của từng câu. Vị trí của các bản sách nói theo đoạn cũ (khi xem theo mốc trước khi bắt đầu Lite) vẫn là **ước lượng** theo tỷ lệ ký tự/thời lượng; chưa có căn chỉnh tiếng nói từng từ.
- Với PDF có chữ, vị trí highlight lấy từ vùng chữ gốc. Ảnh/PDF scan dùng Vision OCR local cho trang đang mở. Chữ sửa không khớp hoặc kết quả mơ hồ không được gắn highlight sai vào bản gốc; chuyển **Ebook** để theo dõi nội dung đã sửa.
- Bản sách nói đã lưu dùng nội dung bất biến của chính bản đó, kể cả sau khi sửa sách. **Nghe từ trang này** tiếp tục trong bản đang nghe.
- Lật trang hoặc cuộn tay tắt bám theo; bấm **Về vị trí đang đọc** để tiếp tục. Có nút trang trước/sau, nhập số trang, zoom bản gốc và phím trái/phải khi vùng đọc có focus.

Thiết lập lưu atomically trong `reader.json` cạnh `book.json`, tránh checkpoint nhập sách ghi đè lựa chọn mới. Đổi chế độ, cỡ chữ hoặc trang xem không làm mất cache audio. Ảnh minh họa chỉ nạp cho trang đang xem và các trang gần đó, giữ chỗ theo kích thước trước để tránh nhảy chữ. Trang gốc được render theo yêu cầu và cache giới hạn; không render lại PDF theo mỗi tick phát. Renderer và OCR đều local, không upload sách hay gọi Cloud.

## Xóa và hoàn tác

Bấm **×** cạnh sách, kiểm tra tên trong hộp thoại rồi xác nhận. Sách được chuyển nguyên thư mục vào `.trash` riêng của thư viện, gồm audio đã tạo, chữ và snapshot đơn sách. Tệp gốc bên ngoài thư viện được giữ. Đây là xóa có thể khôi phục, **chưa giải phóng dung lượng ngay**.

Thông báo **Hoàn tác** có tên sách; trạng thái này còn sau khi mở lại app. Sau khi khôi phục sách mới nhất, có thể tiếp tục hoàn tác sách đã xóa trước đó. Không ghi đè sách đang tồn tại. Phải lưu/bỏ thay đổi chưa lưu trước khi xóa; công việc tạo/xuất đang chạy cho sách phải hủy hoặc đợi hoàn tất. Bộ đệm nghe của sách được dừng trước khi di chuyển thư mục.

## Kiểm chứng

- Core tests bao gồm: nguồn UTF-16/tiếng Việt, không gắn vị trí sai sau sửa, bản audio cũ, xóa/khôi phục, guard công việc đang chạy, thiết lập không đổi audio và không bị checkpoint cũ ghi đè.
- `tests/reader_audio_integration.py`: tạo Lite/Nano thật với đoạn thử tổng hợp trong thư viện `.qa`; có sự kiện trang đang tạo, audio giữ nguyên hash sau xóa/khôi phục, không gọi Cloud. Không phải bằng chứng toàn bộ giọng hoặc sách dài.
- Kiểm thử Build 15 (`tests/verify_reader_ui.swift`, lưu lịch sử trước khi thay layout): worker thật + PDFKit + WKWebView, PDF gốc 203 trang đã được chọn ở đợt kiểm thử trước, đổi highlight/trang, bám theo, sáng/tối, cỡ chữ, giữ màn hình tạo, xóa/hủy/hoàn tác, EPUB tổng hợp và cửa sổ 1000×700. Clock phát trong bài này là fixture để kiểm tra UI, không chứng minh căn chỉnh tiếng nói chính xác.
- `tests/verify_source_pages.swift`: ảnh và PDF scan tiếng Việt tổng hợp qua extractor/Vision thật, mỗi loại có 4 câu lấy được vùng highlight. Không khẳng định mọi bản scan đều nhận đúng.
- Native UI kiểm tra loading/hủy/tiếp tục và luồng chương cũ vẫn đạt. Build bằng `./scripts/build.sh`.
- Build 16: `tests/test_ebook_reader.py` kiểm tra EPUB/escape XML, bảo toàn chữ, mốc nguồn, cache theo nội dung, bản audio cũ, ghi atomic, nhiều yêu cầu đồng thời và đọc nền không chặn input/xóa giữa chừng. `tests/ebook_assets_integration.py` kiểm tra ma trận/crop/chiều màu của ảnh PDF tổng hợp thật.
- `tests/verify_ebook_ui.swift`: worker thật tạo EPUB từ PDF được chọn; WebKit kiểm tra hai trang, font, highlight theo clock fixture, hiệu ứng lật/giảm chuyển động, mục lục, cửa sổ nhỏ, bản gốc và trở về màn hình tạo, nhập EPUB tổng hợp. Clock fixture không chứng minh căn chỉnh tiếng nói. Việc xuất EPUB có kiểm tra cấu trúc ZIP/XML và mốc nội dung; chưa chạy chứng nhận EPUBCheck hay mọi ứng dụng đọc bên ngoài.

Kết quả/screenshot nằm trong `.qa/reader-ui`, `.qa/reader-audio`, `.qa/source-pages`. PDF người dùng chỉ được dùng trong thư viện QA riêng, không đóng gói vào app. Đây là bản phát triển local trên máy kiểm thử, chưa phải installer/notarized release hoặc bảo đảm cho mọi sách/macOS.

Build 16 kiểm chứng bổ sung: 105 core tests đạt. `tests/reader_listening_integration.py` dùng Nano thật cho câu được chọn và câu kế tiếp, không đọc lại câu trước và không đổi cấu hình Pro. `tests/verify_reader_lite.swift` chạy WebKit → worker Nano → bộ phát native/queue với thư viện tổng hợp riêng; phát mute để kiểm tra trạng thái, không chấm chất lượng nghe. Các kiểm tra này không bảo đảm mọi giọng/mọi sách hoặc tốc độ trên mọi máy.

## Nếp giấy cong GulLabs Flipbook — Build 18

Dùng core HTML 3.2.2 của [`gul-labs/flipbook`](https://github.com/gul-labs/flipbook), khóa commit `3fb7192c02ecca559d67192d15a1479fd7cf3af8`. Engine tính nếp gấp chéo, cắt mép trang và bóng hai mặt theo vị trí kéo; thay mặt phẳng xoay của Build 17. Nguồn engine giữ nguyên tại `ui/vendor/gul-flipbook/source/`, đầy đủ MPL-2.0/NOTICE/upstream MIT ở `licenses/GulLabs-Flipbook/`; app local kèm cả nguồn tương ứng.

`EbookTurnBridge.swift` chỉ chụp hai spread local và che bước thay trang trong lúc chụp. `ui/flipbook-turn.js` đưa bốn mặt ảnh vào các trang HTML của GulLabs; engine tạo nếp gấp trong WebKit. Chỉ bốn mặt tồn tại trong một lượt, không clone toàn bộ sách 579 trang. Khi xong/hủy, giải phóng engine/ảnh, giữ nguyên DOM thật và nút câu Lite. Không thêm network, React hoặc runtime TTS.

- Phím/nút trang: lật từ góc dưới, bóng chạy theo nếp gấp.
- Trackpad ngang/kéo mép trang: nếp gấp bám theo khoảng kéo; thả sớm hoặc kéo ngược trả trang về. Cuộn dọc vẫn chuyển trang.
- Nhảy xa bằng mục lục, cửa sổ một trang hoặc Giảm chuyển động: đổi trang trực tiếp.
- Đổi cỡ chữ/nền, rời view hoặc chọn bản gốc hủy lớp lật. Lỗi/chậm snapshot trở về nội dung live; có giới hạn thời gian để tránh kẹt ảnh.
- Hình ảnh chỉ là lớp chuyển cảnh; lưu vị trí, chia trang, bấm câu và phát Lite vẫn dùng nội dung ebook gốc.

`tests/verify_flipbook_ui.swift` chạy worker và WKWebView thật với thư viện `.qa` riêng: PDF/EPUB, tới/lùi, kéo 42% có polygon/nếp gấp, kéo ngược/hủy, giảm chuyển động, đổi nền/cỡ chữ/mục lục và về màn hình tạo. `tests/verify_reader_lite.swift` kiểm tra Nano thật và hàng phát native. Bằng chứng fixture không thay thế kiểm thử mọi sách/macOS hay chứng nhận phát hành.

## Tối ưu đọc PDF · 23/10/2026

Clock phát chỉ cập nhật câu đang đọc và nhãn trạng thái, không dựng lại phần điều khiển hay so sánh toàn bộ chữ của sách mỗi tick. Chỉ mục cue/segment/cột/mục lục được dùng lại; thay nội dung hoặc sách làm mới khóa tương ứng. DOM ebook được dựng bằng fragment; phông/cỡ chữ/resize được gộp trước khi dàn lại và font tải xong sẽ cập nhật mốc trang.

Bộ dịch UI chỉ xử lý nhánh vừa thay đổi, bỏ qua toàn bộ chữ sách. Trang gốc cache bitmap + PNG trước bước PDFKit dựng ảnh, giới hạn 64 MiB theo ảnh giải mã + dữ liệu nén; OCR scan cache chữ/bounding boxes riêng theo trang, phiên bản nguồn và ngôn ngữ, vẫn đối chiếu lại chữ đã sửa. Request trang đã bị thay thế không được trả về UI.

Lật cong GulLabs vẫn được giữ: thời gian chuyển cảnh 420ms, ảnh chuyển cảnh giới hạn 1400px theo chiều ngang, nén PNG ngoài main thread. Có đường hoàn tất bằng timer nếu animation frame bị dừng khi cửa sổ bị che; không thay audio, EPUB xuất hoặc nguồn PDF.

Đo trên bản PDF QA 203 trang / 3.583 câu: mốc trước sửa 100 render ticks 3.641ms; sau sửa trong các lần đo 1–92ms; dàn trang 3.932ms xuống khoảng 521–819ms trong bộ đo. PDF scan tạo từ một trang của sách: hai lần mở lại/OCR 237–248ms xuống khoảng 3ms, giữ 13 anchors và không highlight nhầm câu đã sửa. Đây là phép đo thao tác có kiểm soát, không phải FPS hay bảo đảm cho mọi PDF/Mac. Báo cáo local `.qa/reader-performance/result.json`.

Kiểm tra khung hình bổ sung cùng ngày bắt được lỗi còn lại ở đường vẽ 3D của cả dải sách: lệnh đổi trang nhanh nhưng frame thật vẫn có thể đứng hơn 1,3 giây. Đã đổi sang dịch chuyển 2D, giới hạn vùng vẽ của viewport và chuẩn bị cột trước khi gắn nội dung. Giữ nguyên nếp gấp GulLabs. Phép đo native trước/sau, phạm vi và giới hạn nằm trong [PDF-READER-PERFORMANCE.md](PDF-READER-PERFORMANCE.md); kết quả này bổ sung phép đo lệnh JavaScript ở trên.
