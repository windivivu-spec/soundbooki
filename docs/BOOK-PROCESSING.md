# Xử lý sách local và Cloud — 22/10/2026

## Đã chạy trong app local, v0.6.5 / Build 14

PDFKit trả chữ cùng tọa độ dòng, cỡ font và vị trí UTF-16. Vision chỉ OCR trang không có lớp chữ, trừ khi người dùng bật nhận lại mọi trang. Backend chuyển offset Unicode, dùng các từ xuất hiện trong dòng có chiều rộng bình thường của chính cuốn sách làm bằng chứng để nối từ bị ngắt quanh ảnh. Không dùng từ điển mạng, LLM hay dịch vụ trả phí trên đường local này.

Chỉ tự động sửa whitespace; chuỗi ký tự sau khi bỏ whitespace phải giống nguyên bản, giữ cả dấu tiếng Việt và thứ tự. Mỗi trang vẫn có `text` gốc; `narrationText` là bản ghép dòng; mỗi segment có `originalText` ánh xạ về phần nguồn tương ứng. Có nhật ký nối từ, số chỗ cần xem lại và cảnh báo theo trang. Tên lạ không có bằng chứng được giữ nguyên để kiểm tra.

Mốc chương ưu tiên bookmark/manual có ý nghĩa. Nếu PDF chỉ có bookmark chung `Start`, nhận diện chuỗi số chương tăng liên tục kèm tiêu đề in hoa có cỡ chữ lớn hơn thân bài. Mốc lưu vị trí ký tự và segment membership: chương bắt đầu giữa trang, số và tiêu đề nằm trên hai trang vẫn không lấy nhầm phần trước. Không đoán chương từ nội dung văn xuôi. EPUB và ảnh vẫn dùng hợp đồng hiện có.

Loading hiện bước đọc bố cục, ghép dòng/tìm chương, số trang và thời gian đã chạy. Thanh tiến độ dựa trên trang hoàn tất của từng bước, không dùng đồng hồ đếm giả. Chưa biết số trang thì dùng trạng thái indeterminate. Sau 30 giây có lời giải thích sách cần thêm thời gian, không báo hoàn tất khi chưa xong. Hủy giữ checkpoint; tiếp tục xử lý từ phần đã lưu. Bản chưa xử lý xong không bắt đầu tạo giọng/đọc nền.

PDF đã nhập bằng phiên bản cũ có nút **Sắp xếp lại PDF**. Lấy bổ sung geometry theo trang, giữ chữ gốc và lưu riêng audio đã hoàn tất. Nếu đã sửa chữ, app yêu cầu nhập thành cuốn mới để giữ chỉnh sửa. Không tự động sửa thư viện người dùng khi nâng cấp.

## Bằng chứng thực tế

- Cuốn PDF được chủ sở hữu chọn: SHA-256 `a13209565f3ace4dd24e0909ce8be235e2cc6360d464bef85eab8662b53f295e`, 203 trang, khoảng 4,58 MB.
- Extractor native riêng: 8,19 giây. Toàn bộ đường worker JSON-lines, lưu từng trang, reflow và chia chương: **20,86 giây**. Sự kiện tiến độ đầu sau **0,80 giây**. Đây là kết quả trên máy hiện tại/cuốn này; không phải SLA cho mọi sách, cold model, toàn bộ PDF scan hay thời gian tạo audio.
- Nhận 20 chương đánh số và phần mở đầu; bao gồm chương 15/18 có số và tên ở hai trang liên tiếp. Tự nối 33 ranh giới có bằng chứng; 24 ranh giới khác để kiểm tra. Chưa có ground truth chứng minh mọi chữ/OCR của 203 trang đều đúng.
- Đoạn ảnh minh họa trang 4 trở thành: “Đối với những người biết Ronald Read, không có nhiều điều để nói. Cuộc sống của ông không có gì nổi bật.” Không thêm/bớt/đảo ký tự ngoài whitespace.
- Mọi phần chương chia đúng tập segment, không thiếu/trùng; sửa một chương không đổi chương khác cùng trang. Xuất WAV đúng chương bằng audio fixture; đây không phải bằng chứng chất lượng TTS.
- PDF legacy: hủy sau checkpoint geometry 4 trang, tiếp tục hoàn tất trong tổng 23,78 giây; còn đủ 203 trang, giữ raw text và bản audio fixture đã có. Không ghi vào thư viện thật của người dùng.
- Native WebKit: loading, thời gian thực, quá 30 giây, hủy/tiếp tục qua bridge, dark/light, reduced motion và cửa sổ 1000×700. Ảnh ở `.qa/processing-ui/`. File nguồn người dùng không được upload.

Tái kiểm tra:

```sh
.runtime/bin/python -m unittest discover -s tests -p 'test_*.py'
.runtime/bin/python tests/pdf_layout_integration.py '/absolute/selected.pdf' --expected-chapters 20
./scripts/build.sh
```

Report gần nhất: `.qa/pdf-layout/latest-integration.json`. Thư viện mỗi lần chạy integration độc lập dưới `.qa/pdf-layout/worker-*/`.

## Pipeline Cloud riêng đã chuẩn bị, chưa kích hoạt

Không tự upload khi phát hiện mạng. Người dùng phải chọn gửi đúng cuốn PDF tới dịch vụ đã cấu hình; mất mạng vẫn giữ được đường local. Không đưa Modal proxy key hoặc service-role vào app.

`cloud/pdf_processing.py` chứa pipeline Docling layout/reading order và hybrid OCR Tesseract tiếng Việt/Anh. Đầu vào chỉ là đường dẫn PDF cục bộ, không nhận URL tùy ý, không gọi dịch vụ bên ngoài để viết lại sách. Có giới hạn 25 MiB, 2.000 trang và 2.000.000 ký tự. Kết quả có SHA-256 của PDF, block/bbox/page, chữ trích, ứng viên tiêu đề và `requiresReview=true`. Không tự biến mọi section-header thành chương hoặc tự ghi đè bản local.

`cloud/pdf_modal.py` đóng gói đường này thành endpoint Modal có proxy authentication; file tạm được xóa khi xong. Model/dependency download ở bước build chủ động; runtime dùng cache offline. Không có persistent volume lưu sách. `commerce/process-pdf.py` là CLI **chỉ dành chủ sở hữu**, gửi một PDF đã chọn với `--allow-upload`, xác minh hash kết quả rồi lưu JSON để xem lại. Không tự thử lại một request GPU bị timeout.

**Chưa chạy Docling/model thật, chưa deploy endpoint, chưa có benchmark RAM/tốc độ/tiếng Việt của Cloud, chưa nối cổng upload của khách và nút gửi PDF vào app.** Chỉ có kiểm thử adapter/provenance bằng fixture và kiểm tra cú pháp. Cổng khách cần xác thực device, quota riêng cho xử lý tài liệu, job idempotent theo hash + revision, giới hạn đồng thời, trạng thái tiến độ và chính sách xóa dữ liệu trước khi bật. Không dùng ba lượt thử giọng làm ba lượt OCR một cách ngầm định.

Trình tự sản phẩm được chốt: local preview → người dùng tùy chọn Cloud → xem/duyệt chỗ nghi lỗi → tạo snapshot chữ/giọng cuối → báo giá theo snapshot → thanh toán đúng đơn → tạo giọng. Chi phí xử lý bố cục Cloud có thể tính trong gói Pro/cuốn sau khi benchmark; chưa mở một khoản thu riêng. Nếu duyệt sửa chữ sau khi đã báo giá thì cần snapshot/giá mới, không mở rộng quyền của đơn cũ.

Tài liệu API chính chủ đã đối chiếu:

- [Docling heading hierarchy](https://docling-project.github.io/docling/usage/heading_levels/): nguồn bookmark, numbering và visual style; không phải mô hình tự viết mục lục.
- [Docling hybrid/full-page OCR options](https://docling-project.github.io/docling/_generated/examples/full_page_ocr/): chọn OCR backend; full-page OCR thường chậm hơn hybrid.
- [Docling package](https://pypi.org/project/docling/): cài trong môi trường Cloud riêng; không thêm dependency nặng vào app Mac mặc định. Cần khóa phiên bản/dependencies sau integration thật trước deployment.

## Lớp kiểm tra thêm khi tạo giọng Pro

Batch Modal nhận `quality_review=true` từ operator. Qwen đọc ngữ cảnh và tìm những đoạn nghi lỗi trong cùng lượt phân tích ngữ điệu. Mọi đề xuất phải trỏ đúng đoạn nguồn xuất hiện duy nhất; chặn đề xuất chồng lấn/ngoài nguồn, không thay chữ trong sách. Kết quả là báo cáo cần xem lại, **không phải các sửa lỗi được tự động chấp nhận**. Endpoint proofread cũ cũng chuyển sang trả đề xuất, không `.replace()` cả cuốn theo câu trả lời model.

Nếu model không hoàn tất JSON review thì batch không tiếp tục tạo giọng. Audio từng unit và cả batch phải qua kiểm tra dữ liệu hữu hạn, thời lượng hợp lý, tín hiệu im lặng và clipping trước khi trả thành công. Đây là QA tín hiệu, không xác minh phát âm bằng ASR và không chứng minh mọi chữ đã được đọc đúng. Operator lưu `.review.json`, kiểm hash/nội dung kiểm tra, rồi mới nhận WAV/upload. Không tự retry request trả kết quả không rõ ràng.

Snapshot báo giá vẫn dùng protocol `pro-cloud-modal-v1`; snapshot mới có `audioRevision=pro-cloud-modal-v1-quality-v1` để tách cache. Đơn cũ không có trường này dùng revision cũ và vẫn giữ audio/take đã mua. Server giữ nguyên snapshot giá/đơn; quality review không mở rộng số ký tự đã mua. Báo cáo Qwen hiện lưu ở operator, chưa có màn duyệt đề xuất Cloud cho khách.

Chưa deploy code Modal mới hoặc gọi GPU tính phí trong lần làm này. Không có bằng chứng inference/provider live hoặc chất lượng nghe của lớp mới; các chốt review/audio và ánh xạ provenance đã qua fixture tests.
