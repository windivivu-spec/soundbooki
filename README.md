# Windi Sách Nói

> **Local 0.8.3 · Build 19 (25/10/2026):** M4B có chương/bìa, đọc Việt–Anh local trong cùng sách, tìm nội dung không dấu, tô đoạn/ghi chú/sổ tay và dán văn bản. Android 0.2.7 cũng có các tính năng này. Xem [cách dùng và QA](docs/READING-TOOLS.md). Các phần phiên bản cũ bên dưới là lịch sử.

Build 18 dùng engine HTML của [GulLabs Flipbook](https://github.com/gul-labs/flipbook) cho nếp giấy cong, hai mặt trang và bóng đổ theo thao tác kéo. **Không gian đọc ebook kín cửa sổ**: PDF được dàn lại thành hai trang theo nền sáng/tối, có ảnh minh họa lấy được, lật trang, mục lục, cỡ chữ và thanh nghe nổi. Bấm câu để nghe liên tục bằng Lite, chọn giọng ngay trong view đọc và giữ riêng giọng/phạm vi tạo Pro. Có thể lưu bản EPUB dẫn xuất; PDF gốc, chữ và audio đã tạo vẫn được giữ. Nút **×** trong trang đọc trở về màn hình tạo sách nói; nút **×** cạnh sách trong thư viện là xóa có hoàn tác. [Cách dùng và giới hạn](docs/LIVE-READER.md).

PDF có ghép dòng dựa vào bố cục, nhận chuỗi tiêu đề chương thật và loading có hủy/tiếp tục. Cuốn 203 trang được chọn đã chạy toàn bộ trong 20,86 giây trên máy kiểm thử ở Build 14. [Pipeline local, bằng chứng và trạng thái Cloud](docs/BOOK-PROCESSING.md).

Bản local **0.8.2 · Build 18**: **Lite miễn phí** dùng Nano tiếng Việt cùng KittenTTS tiếng Anh; **Pro · Tạo từ Cloud** thanh toán theo từng cuốn, từ 10.000đ. Có 5 lượt miễn phí trọn đời/thiết bị, giữ số đã dùng. Chọn tạo thử 1 lượt (5.000 ký tự) hoặc tạo chương bằng tối đa 4 lượt (20.000 ký tự), xác nhận số lượt thực trước khi gửi; chương dài hơn giới hạn được báo rõ chưa hoàn tất. Quota5 và SQL queue đã áp dụng cho test private theo thiết bị. Đã thêm ledger Supabase, khóa đơn theo nội dung/giọng/máy và chặn trả thiếu tiền. Gateway/worker đã triển khai để test private trên Mac owner, đã tạo và nhận mẫu HeyGen thật; thu tiền vẫn tắt. Xem [cách test cloud](docs/CLOUD-TRIAL-DEPLOYMENT.md). Lịch sử giấy phép năm cũ vẫn được giữ. Xem [giá và vận hành đơn sách](docs/BOOK-COMMERCE.md).

Ưu đãi ra mắt đã chuẩn bị local: **50.000đ/5 cuốn, một combo/Mac; mua và dùng trước 23:59 ngày 01/11/2026 (giờ Việt Nam)**. Mua lẻ giữ bảng giá thường; không áp dụng đồng giá 15.000đ hoặc 5.000đ. Chưa bật bán/deploy. Xem [chính sách và kiểm tra combo](docs/LAUNCH-COMBO.md).


Ứng dụng Mac để nghe EPUB, PDF và ảnh chụp tiếng Việt. Thêm tài liệu, kiểm tra chữ, chọn giọng rồi nghe. Sách, nội dung đã sửa, audio và vị trí nghe được lưu trên máy.

MVP local 0.5.0 dành cho Mac Apple Silicon. Đã chạy trên macOS 26.5.2. Giao diện theo phong cách Liquid Glass, có chế độ sáng/tối, tìm trong thư viện và tùy chọn giảm chuyển động.

## Tính năng đang tạm hoãn

Pro Max tạo sách bằng API và ví credit đã được ẩn, chặn gọi API và chưa triển khai vì chi phí chưa phù hợp. Pro Cloud theo cuốn là luồng mới riêng, không dùng API/credit Clone Pro bị tạm hoãn. Mã thử nghiệm được giữ lại trong project để cân nhắc sau; xem [ghi chú](docs/PRO-MAX.md).

## Mở app trên máy hiện tại

Mở `dist/Windi Sách Nói.app`, hoặc chạy:

```sh
./scripts/run.sh
```

Bản này chạy từ thư mục project; cần giữ nguyên project và `.runtime`. Đây chưa phải installer độc lập hay bản notarized để gửi sang máy khác.

## Thiết lập lần đầu trên máy phát triển

Cần Mac Apple Silicon, Command Line Tools (`swiftc`) và [uv](https://docs.astral.sh/uv/getting-started/installation/). Chạy:

```sh
./scripts/setup.sh
./scripts/run.sh
```

Setup tải Python/dependency và model công khai, sau đó build app. Sau bước này, các giọng local tự trích chữ/OCR/tạo giọng trên máy, không cần API key hoặc dịch vụ cloud.

Có thể dùng cache model có sẵn mà không sao chép:

```sh
./scripts/setup.sh --reuse-cache '/đường/dẫn/tới/tts-nano'
```

Trên máy đã kiểm thử, `.resources/config.json` trỏ chỉ đọc tới cache `~/Library/Application Support/Windi Dubbing Local/models/tts-nano`. Sáu file model đã được đối chiếu dung lượng và SHA-256 trong `backend/models.json`. App không đọc sách hay dữ liệu dự án của Windi Dubbing. Nếu cache bị di chuyển, chạy lại setup để tải bản riêng vào `.resources/tts-nano`.

Model Nano: **281.756.486 bytes** (khoảng 282 MB decimal); runtime Python/dependency nền khoảng **607 MiB**, không bao gồm Python gốc và cache tải. Runtime nền không cài torch, engine dịch, ASR hoặc pipeline video. Giọng F5 riêng dùng runtime PyTorch tùy chọn tách biệt, mô tả bên dưới. SDK kéo theo một số dependency giao diện/web dù app không khởi chạy các dịch vụ đó.

## Nghe Nano liên tục

Khi mở sách/chọn đoạn bằng Nano, app chuẩn bị trước lời đọc trong phạm vi đang chọn: hướng tới 60 giây ở tốc độ nghe hiện tại, tối đa 12 đoạn. Bấm Play dùng audio có sẵn ngay; nếu chưa có thì chỉ chờ đoạn đầu, các đoạn sau tiếp tục được tạo khi nghe. Với đoạn đầu quá ngắn, app đợi một ít audio kế tiếp (khoảng 2 giây lời đọc) để tránh vừa phát tiêu đề đã phải dừng. Khi tiến tới đoạn tiếp theo, bộ đệm được bù thêm. Tệp kế tiếp được giải mã và xếp lịch trong bộ phát Mac, không đợi giao diện nhận sự kiện kết thúc rồi mới mở file.

Một tiến trình Nano được dùng lại cho bộ đệm, nghe thử và tạo sách nói, vẫn giữ 16 bước/seed 42 và cache theo chữ/giọng/revision. Tạo đệm không tạo thêm bản sách nói trong danh sách. Sửa chữ/đổi giọng/chuyển sách loại bỏ kết quả đệm cũ khỏi phiên phát; audio hoàn tất vẫn được giữ trong cache. Pause, tua và đổi tốc độ cập nhật lịch phát, không tạo lại audio. Thoát app đóng tiến trình Nano. Việc tạo trước chỉ áp dụng Nano, không tự chạy F5 hoặc dịch vụ mạng.

Kiểm thử local: `.runtime/bin/python tests/listening_integration.py`; native queue: biên dịch `native/NarrationQueue.swift` với `tests/verify_narration_queue.swift`. Các kết quả mẫu nằm trong `.qa/listening/report.json` và `.qa/native-listening/report.json`; không phải bảo đảm tốc độ với mọi sách/Mac. Đoạn chưa từng tạo vẫn cần thời gian suy luận, nên không cam kết phát tức thì khi chưa có audio.

## Chọn chất lượng giọng đọc

Mở **Model giọng đọc** ở góc dưới thư viện, hoặc **Chọn chất lượng / tải thêm** phía trên bộ chọn giọng. Model được lưu riêng cho từng sách:

| Lựa chọn | Tài nguyên tải riêng | Âm thanh | Khuyến nghị của app |
|---|---:|---:|---|
| VieNeu Nano | 282 MB | 24 kHz | Mac Apple Silicon, RAM 8 GB; nhanh, ngữ điệu đơn giản hơn |
| KittenTTS Mini 80M | 81,5 MB (model + 8 giọng) | 24 kHz | Chuyên tiếng Anh, chạy CPU, không cần PyTorch |
| Giọng của tôi · F5 | 6 checkpoint khoảng 3,8 GiB gồm model/reference/Vocos; thêm runtime PyTorch khoảng 1 GiB | 24 kHz | Sáu giọng đã train; Pro riêng, Metal trên Apple Silicon, nên có RAM 16 GB |

Khuyến nghị RAM là chính sách của app, không phải benchmark hoặc yêu cầu tối thiểu chính thức của tác giả. Nano và Kitten phù hợp Apple Silicon từ 8 GB RAM; F5 nên có 16 GB RAM. Hiển thị RAM và dung lượng trống thực tế trước khi tải. Không tự tải hoặc tự đổi model. Có tiến độ, hủy, tiếp tục tải và xác minh SHA-256 từng tệp; file chưa tải xong không được dùng. Model lỗi checksum trở về trạng thái cần tải lại.

**Dùng cho sách này** hoặc bộ chọn **Gói giọng đọc** áp dụng giọng đã có. Free dùng Nano tiếng Việt và Kitten tiếng Anh; Pro có 6 giọng riêng F5. Nút mua chỉ nằm trong gói giọng/Pro, không xuất hiện trên màn hình đọc lúc mở app. Turbo đã ngừng cung cấp: không hiện trong lựa chọn, không tải và không tạo mới; giữ các tệp/audio cũ để không mất dữ liệu. Mỗi model có cache riêng. Không đổi model khi đang tạo hoặc xuất audio.

Khi bấm tạo, thanh tiến độ xuất hiện ngay dưới hàng chọn giọng. Số đoạn và phần trăm tính theo đúng chương/phạm vi đang tạo, gồm audio đã có được dùng lại; không lấy tổng số đoạn của cả sách. Lúc chuẩn bị model có trạng thái riêng. Hủy giữ audio hoàn tất và số đoạn đã tạo. Không hiện thông báo lớn che thanh nghe ở dưới.

### Giọng đã train của bạn

Chọn **Giọng của tôi · F5**, giọng **Giọng của tôi · Bản train 001**, rồi tạo thử một đoạn trước khi chọn cả sách. Runtime `.runtime-f5` độc lập với `.runtime`; app gọi engine riêng, tự chọn Metal khi khả dụng và dùng CPU khi không có Metal. Adapter chạy 16 NFE, seed 42, các đoạn con tối đa 160 ký tự, Vocos/reference mel chạy CPU để tương thích FFT trên Mac. Tốc độ phát vẫn là thiết lập player, không sinh lại audio.

Tài nguyên riêng ở `.resources/tts-f5-private`; SHA-256 của model, vocab, reference audio/text và vocoder được kiểm tra theo `backend/models-f5-private.json`. Cache bao gồm toàn bộ revision tài nguyên cùng cấu hình inference. Không gửi giọng, sách hay reference lên mạng; không chạy ASR. Giữ các bản gốc ở `training/f5/artifacts/voice-*` nếu cần khôi phục.

Đầu vào đọc của F5 được chuyển về chữ thường như transcript khi train; bỏ dấu gạch/ngoặc kép trang trí và thêm dấu nghỉ cho tiêu đề in hoa hoặc dòng tác giả bọc dấu gạch. Ví dụ `NHỮNG CƠ HỘI TUYỆT VỜI` → `những cơ hội tuyệt vời.`, `-Khuyết Danh-` → `khuyết danh.`. Sách hiển thị và `originalText` giữ nguyên. Bản xử lý v2 có cache riêng: tạo lại chương bị lỗi để có audio mới; các bản sách nói cũ vẫn được giữ trong danh sách.

Setup chủ động, có tải dependency/vocoder một lần:

```sh
./scripts/setup_f5.sh
```

Chủ sở hữu model xác nhận đã có quyền thương mại áp dụng cho các checkpoint F5 và giọng đã train. Chỉ ứng viên Pro riêng chứa 6 checkpoint cùng các reference ngắn cần thiết để tạo tiếng nói; dữ liệu train gốc không nằm trong gói. Bản Free không chứa tài nguyên F5.

App đóng gói mới có sẵn VieNeu Nano tiếng Việt và KittenTTS tiếng Anh; không cần tải giọng Free ở lần mở đầu. Pro mở 6 giọng riêng F5. Với môi trường phát triển từ source, CLI setup tùy chọn: `./scripts/setup.sh --model kitten`; mặc định setup chọn Nano. Turbo không còn được cung cấp.

## Tiếng Việt và tiếng Anh

Nút bánh răng → **Ngôn ngữ giao diện / Interface language** chọn Tiếng Việt hoặc English. Lựa chọn được lưu trên máy, gồm menu macOS, nút, điều khiển và các trạng thái thường gặp. Tên sách, mục lục, nội dung gốc và chữ đã sửa không được dịch hoặc viết lại khi đổi giao diện.

**Ngôn ngữ sách / Book language** là lựa chọn riêng: chọn English để dùng KittenTTS Mini cho sách tiếng Anh; Tiếng Việt dùng Lite. Sách mới mặc định là tiếng Việt; Vision nhận dạng cả tiếng Việt và tiếng Anh. Sau khi nhập, có thể chọn English tại **Ngôn ngữ sách** để dùng giọng tiếng Anh. EPUB luôn lấy chữ trực tiếp. Đây là chức năng đọc nội dung có sẵn, không dịch sách sang ngôn ngữ khác.

Kitten Mini có 8 giọng Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki và Leo. Đã kiểm thử hai giọng Jasper/Bella; chưa chấm MOS hoặc toàn bộ 8 giọng trên sách nhiều giờ. Trọng số + cấu hình + giọng là **81.547.388 bytes**, độc lập với runtime app. Chỉ cài thêm phonemizer 3.4.0, espeakng-loader 0.2.4 và hai dependency nhỏ; tận dụng ONNX Runtime/NumPy đã có, không kéo spaCy/misaki/torch. Adapter local dựa theo API/chuẩn bị input chính thức KittenTTS 0.8.1, khóa revision model và checksum. Runtime hiện khoảng **632 MiB** trên máy kiểm thử, không phải toàn bộ app chỉ có 81,5 MB.

Bản mẫu local ở `output/demo/kitten-english-jasper.m4a`, `output/demo/kitten-english-bella.m4a`; bản có Warm Reflections 12% là `output/demo/kitten-english-with-music.m4a`. Gói web của sách tiếng Anh có nhãn/control tiếng Anh và vẫn giữ nguyên nội dung sách.

## Cách dùng

1. Chọn **Thêm sách mới**. Nhập một EPUB (file ZIP hoặc thư mục `.epub` đã giải nén), một PDF hoặc nhiều ảnh PNG/JPEG/HEIC/TIFF/WebP. Nhiều ảnh được xếp theo tên tự nhiên: 1, 2, 10.
2. EPUB lấy chữ và mục lục trực tiếp theo thứ tự spine, hỗ trợ NCX của EPUB 2 và nav của EPUB 3, kể cả nhiều mốc chương trong cùng file HTML. Không chạy HTML/script hay tải tài nguyên ngoài. PDF có lớp chữ được đọc trực tiếp. Trang scan và ảnh dùng OCR Vision local. Các trang không có lớp chữ được OCR tự động; nếu lớp chữ có sẵn nhưng sai hoặc thiếu, hãy đối chiếu và sửa nội dung với bản gốc.
3. Kiểm tra từng đoạn. Nút **Bản gốc** mở tài liệu đã nhập để đối chiếu. Sửa chữ và bấm **Lưu chữ**; **Khôi phục bản gốc** giữ lại đường quay về nội dung trích xuất ban đầu.
4. Chọn model, chọn giọng và bấm phát. App tạo đoạn đang chọn và tối đa hai đoạn kế tiếp để nghe sớm. **Tạo giọng → Phạm vi** chọn trang đang đọc, khoảng trang, chương hoặc toàn sách. Chương lấy từ mục lục EPUB/PDF; có thể đặt/sửa mốc chương tại vị trí đang đọc. EPUB dùng mục nội dung thay cho số trang in cố định. Bộ chọn **Chuyển đến chương** nhảy trực tiếp tới chương/lời mở đầu/lời kết có trong sách. Chỉ những đoạn thuộc phạm vi được tạo; audio đã có được dùng lại. Có thể hủy và tiếp tục; audio hợp lệ được dùng lại.
5. Phát/tạm dừng, chuyển đoạn, tua trong đoạn và đổi tốc độ. Vị trí lưu mỗi hai giây, khi tạm dừng/chuyển đoạn/thoát. Nếu còn trích chữ, app có thể đợi trang tiếp theo.
6. Mở **Nhạc nền** để chọn nhạc, nghe thử và chỉnh mức 0–50%. Nhạc phát cùng lời đọc trong app và được trộn vào file tải về; đổi nhạc không tạo lại giọng đọc.
7. Mở **Tải về**. Phạm vi ở tab Phạm vi cũng quyết định nội dung tải về. Chọn **M4A** (AAC mono: Nano/F5/Kitten 24 kHz/64 kbps), **WAV** (PCM16 mono theo tần số model) hoặc **gói nghe web ZIP**. Cần tạo đủ giọng trong phạm vi chọn; có tiến độ và hủy xuất. Tốc độ nghe trong app không làm thay đổi file xuất.
8. Gói web gồm audio M4A đã trộn nhạc, nội dung và trình nghe có chuyển đoạn, tốc độ và lưu vị trí trong trình duyệt. Giải nén và mở `index.html` bằng trình duyệt trên máy tính, hoặc đưa các file lên hosting của bạn. Mở gói ZIP trong ứng dụng Files trên điện thoại không được xem là một trình duyệt web đầy đủ; có thể nghe file M4A trực tiếp.

Nút bánh răng mở giao diện sáng/tối/theo hệ thống và bật/giảm chuyển động. App lưu lựa chọn trên máy. Space phát/tạm dừng khi không nhập chữ hoặc dùng một control khác. Command-O thêm sách, Command-F tìm trong thư viện, Command-comma mở hiển thị.

## Dữ liệu

Mặc định: `~/Library/Application Support/Windi Sach Noi/library/<book-id>/`. Mỗi sách có bản sao tài liệu gốc, `book.json`, các đoạn WAV và metadata. Không ghi vào EPUB/PDF/ảnh gốc. Thư mục EPUB được đóng gói thành bản sao ZIP riêng trong thư viện. Đường local không có đăng nhập, telemetry hoặc upload tài liệu/API inference. Pro Cloud là luồng chọn riêng có đồng ý gửi chữ; pipeline Cloud PDF mới chưa kích hoạt. Audio cũ được giữ trong cache khi sửa chữ/đổi giọng, giúp quay lại bản cũ mà không tạo lại.

Dùng `WINDI_SACH_HOME=/đường/dẫn/thư-viện` khi chạy executable trực tiếp để tách dữ liệu QA. Không commit thư viện, runtime, model hoặc tài liệu người dùng.

## Kiểm thử

```sh
.runtime/bin/python -m unittest discover -s tests -v
swiftc -module-cache-path /private/tmp/windi-sach-swift tests/Fixtures.swift -o .qa/fixtures
.qa/fixtures .qa/fixtures-data
.runtime/bin/python tests/integration.py
.runtime/bin/python tests/english_integration.py
# Kiểm thử riêng sách EPUB demo do người dùng cung cấp (không đưa sách vào repo):
.runtime/bin/python tests/epub_integration.py "/đường/dẫn/sách.epub"
```

Integration dùng PDF/ảnh tổng hợp tiếng Việt, engine thực và thư viện riêng `.qa/integration-library`. Vision cần môi trường được phép dùng framework hệ thống; sandbox của terminal agent từng chặn OCR bằng lỗi Foundation chung, trong khi app và test ngoài sandbox chạy được. Xem [QA.md](docs/QA.md) để biết kết quả và giới hạn chính xác.

## Giới hạn hiện tại

- Giọng đọc tiếng Việt dùng **VieNeu Nano hoặc giọng riêng F5**; tiếng Anh có **KittenTTS Mini** nhẹ hơn. EPUB không cần OCR; PDF scan/ảnh dùng Apple Vision. Không cần thêm model OCR hoặc LLM phân chương. Vision nhận chữ, không tự hiểu ranh giới chương ngữ nghĩa; PDF thiếu outline có thể lấy chuỗi tiêu đề đánh số và kiểu chữ thật; tài liệu không có các dấu hiệu đó vẫn cần mốc thủ công.
- EPUB có DRM/nội dung mã hóa chưa được hỗ trợ. Mục chỉ chứa ảnh (như bìa) được bỏ khỏi lời đọc và thông báo rõ; EPUB chỉ toàn ảnh cần chuyển sang PDF/ảnh để OCR. Mục lục lồng nhau hiện hiển thị phẳng theo các mốc nội dung.
- Nano là model preview 48M tham số; có thể nuốt âm hoặc đọc chưa tự nhiên, đặc biệt với tiếng Anh, câu song ngữ và chuỗi ký tự lạ. Chưa chấm chất lượng nghe với người dùng hay benchmark sách nhiều giờ.
- OCR ưu tiên trang một cột, ảnh rõ chữ. Bảng biểu, nhiều cột, công thức, chữ viết tay và ảnh xiên có thể sai thứ tự/chữ. PDFKit giữ thứ tự lớp chữ mà PDF cung cấp; không có AI tự sửa, tóm tắt hoặc viết lại sách.
- Chỉ kiểm thử Mac Apple Silicon hiện tại. Deployment target 15.0; OCR tiếng Việt được phát hiện lúc chạy và có thể cần macOS mới hơn. Chưa xác minh các macOS cũ, Intel hay Windows.
- File WAV chưa nén khoảng 173 MB mỗi giờ ở 24 kHz hoặc 346 MB mỗi giờ ở 48 kHz; giới hạn RIFF 4 GB. Đã có M4A và gói nghe web; chưa có MP3/M4B, metadata chương nhúng trong file audio hoặc gộp nhiều PDF.
- Khi trích sách dài, cần bấm tiếp tục trích chữ sau khi hủy/thoát. Bấm tạo giọng cho phạm vi lần nữa để bổ sung các đoạn mới trích. Checkpoint là từng trang/đoạn, không phải từng từ.
- Liquid Glass ở đây dùng AppKit vibrancy và hiệu ứng kính CSS; chưa dùng `NSGlassEffectView` từ SDK 26 vì toolchain hiện tại có SDK 15.5.

Xem [kiến trúc](docs/ARCHITECTURE.md), [thiết kế](docs/DESIGN.md) và [thành phần bên thứ ba](THIRD_PARTY.md).

## Nhạc demo và nghe online

Danh sách nhạc hiện có hai bản người dùng cung cấp: **Warm Reflections · Bản 1** và **Warm Reflections · Bản 2**, cùng ba loop nhạc không lời được tạo bằng code trong project. Hai file MP3 gốc không bị sửa; bản dùng trong app được chuyển sang PCM mono 24 kHz, chuẩn hóa peak và lưu dưới `assets/music/`. Build giữ lại danh sách nhạc demo đã nhập. Các file nhạc demo và audio mẫu không được commit mặc định.

Bản nghe thử với cùng lời đọc và nhạc 12% nằm ở `output/demo/warm-reflections-ban-1.m4a` và `output/demo/warm-reflections-ban-2.m4a`.

**Nghe online tích hợp chưa được kích hoạt.** Hiện đã có trình nghe web và gói export hoạt động local/localhost; chưa có upload cloud, tài khoản, đồng bộ giữa thiết bị hoặc thu phí. Người dùng đã yêu cầu để việc tính phí sau. Xem [ONLINE.md](docs/ONLINE.md) để biết phần triển khai tiếp theo và ranh giới dữ liệu.
