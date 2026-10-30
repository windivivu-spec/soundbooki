# Kiểm tra nhập PDF và phương án sửa — 22/10/2026

**Cập nhật triển khai:** đường local và loading đã được đưa vào Build 14, đo toàn bộ worker 20,86 giây trên cuốn 203 trang, nhận 20 chương cùng phần mở đầu. Xem [BOOK-PROCESSING.md](BOOK-PROCESSING.md) để biết kiểm chứng hiện tại và phần Cloud còn chưa kích hoạt. Phần bên dưới lưu lại đánh giá/prototype trước khi triển khai, không phải trạng thái sản phẩm mới nhất.

Phạm vi: kiểm tra bản PDF `tam-ly-hoc-ve-tien.pdf` mà chủ sở hữu đang thử trong app, và ba ảnh chụp đã gửi. Chỉ đọc sách gốc, chạy prototype trong `.qa/pdf-layout/`; chưa thay extractor, chưa sửa thư viện người dùng, chưa tải model hoặc gửi nội dung lên cloud.

## Kết quả trên file thật

- PDF 203 trang, khoảng 4,58 MB. App có đúng một bookmark tên `Start` ở trang PDF số 2. Extractor hiện chỉ chuyển bookmark thành chương, chưa dùng heading hiển thị trên trang.
- Ở trang PDF số 4, ảnh chiếm vùng x≈105–518 điểm, khiến cột chữ bên trái chỉ còn khoảng 29 điểm. Cỡ chữ thân bài khoảng 13,7 điểm. PDF đã chứa các dòng `nhữn`, `g`, `ngườ`, `i biết`, `Ron`, `ald`. Lớp chữ PDF và pdfplumber đều thấy cùng vấn đề; đây không phải lỗi OCR của Vision ở trang này.
- Đã lấy hình học/font của toàn bộ 203 trang. Tiêu đề chương có cỡ chữ khoảng 27,5–29,7 điểm, số chương 1–20 và tên in hoa. Prototype lấy được 20 ứng viên chương theo các dấu hiệu thật trên PDF, không đoán nội dung bằng LLM. Chương 1 ở trang PDF 10: `KHÔNG AI ĐIÊN`.
- Nhiều chương bắt đầu giữa trang. Chương 15 có số ở trang 131, tên ở trang 132; chương 18 tương tự ở trang 159–160. Kiểu dữ liệu chỉ có startPage/endPage hiện tại không thể biểu diễn chính xác các ranh giới này.

## Thử ghép từ bằng chứng từ chính sách

Prototype lấy tần suất từ trong những dòng có chiều rộng bình thường để làm từ điển của tài liệu. Chỉ ghép ranh giới dòng trong đoạn thử nghiệm khi từ nối có bằng chứng và một mảnh không phải từ độc lập đã biết; xử lý dấu câu riêng.

Đoạn trang 4 đã phục hồi sáu chỗ: `nhữn/g → những`, `ngườ/i → người`, `Ron/ald → Ronald`, `khôn/g → không`, `nhiề/u → nhiều`, `Cuộ/c → Cuộc`. Kết quả thành đoạn đọc bình thường. Ronald đã xuất hiện nguyên vẹn 12 lần trong phần từ vựng an toàn, nên không cần đoán tên bằng LLM.

Kiểm chứng bắt buộc: bỏ toàn bộ whitespace khỏi đầu vào và đầu ra cho ra chuỗi giống hệt nhau. Không thêm, xóa hoặc đảo bất kỳ chữ hay dấu tiếng Việt nào. Bước prototype sau khi đã có dữ liệu hình học chạy khoảng 0,03 giây; đây không phải thời gian xử lý PDF toàn cuốn hay benchmark OCR/model.

Giới hạn: mới chứng minh đoạn người dùng chỉ ra và việc tìm 20 ứng viên tiêu đề. Chưa đánh giá toàn bộ sách đã ghép đúng, chưa có ground truth cho PDF scan/multi-column/poetry/tables. Trường hợp từ chỉ xuất hiện một lần, từ ngoại ngữ, hoặc cả hai cách ngắt đều hợp lý phải được đánh dấu xem lại.

## Phương án đề xuất cho sản phẩm

1. Đọc chữ kèm bbox, font, cỡ chữ, dòng và block; giữ nguyên raw extraction theo trang. Không bỏ hình học rồi mới cố sửa chuỗi phẳng.
2. Dùng thứ tự block/cột, vị trí ảnh và khoảng cách dòng để tái dựng đoạn. Ghép từ có bằng chứng từ chính sách; không đổi chữ của người dùng. Giữ cả rawText và narrationText, nhật ký thay đổi, và cờ cần kiểm tra.
3. Tìm chương từ bookmark/mục lục thật, hoặc tiêu đề hiển thị có số thứ tự + kiểu chữ lặp lại. Lưu mốc theo sourcePage + vị trí chữ/block, không chỉ số trang. Bảo toàn phạm vi tạo/xuất, thứ tự nguyên văn và khả năng sửa chương. Tiêu đề cấp nhỏ không được tự nâng thành chương.
4. Những trang/chỗ lớp chữ hỏng mới cần OCR lại. Vision hiện có vẫn là một backend local; thêm OCR khác sau khi so sánh tiếng Việt trên Mac. Không OCR lại mọi trang có lớp chữ tốt.
5. Layout khó hơn có thể dùng Docling standard pipeline với model layout Heron làm thành phần nhận diện ảnh, text, header, title và section header. Dùng chữ gốc từ PDF để bảo toàn dấu; không giao toàn bộ sách cho model sinh lại. Docling heading hierarchy cũng ưu tiên bookmark, numbering, font/style; cần bật cấu hình này, không chỉ cài package.
6. Nếu thêm LLM sửa ranh giới từ, chỉ cho đề xuất chỉnh whitespace ở vùng nghi ngờ và từ chối mọi đầu ra đổi chuỗi ký tự không phải whitespace; hiển thị diff trước khi áp dụng. Không cho model viết lại/vắn tắt/đảo câu hay đặt chương theo nội dung. Chưa chọn hoặc chạy một LLM trong lượt kiểm tra này.

## Các model đã kiểm tra tài liệu chính chủ

- **Docling layout Heron:** mô hình phân vùng bố cục, phân loại text/picture/title/section-header…; Apache 2.0. Thích hợp làm lựa chọn layout mở rộng sau baseline native. Chưa tải/chạy trên Mac này, không có benchmark RAM/tốc độ để cam kết.
  - https://huggingface.co/docling-project/docling-layout-heron
  - https://docling-project.github.io/docling/usage/heading_levels/
- **Granite Docling 258M:** gọn và có hướng dẫn MLX cho Apple Silicon. Model card ghi English, Japanese/Arabic/Chinese experimental; không đủ căn cứ để chọn làm OCR tiếng Việt mặc định. Không suy diễn chất lượng tiếng Việt từ số tham số nhỏ.
  - https://huggingface.co/ibm-granite/granite-docling-258M
- **PaddleOCR-VL:** họ model 0,9B hỗ trợ đa ngôn ngữ, báo cáo gốc liệt kê tiếng Việt. Bản 1.6 là phương án thử OCR/layout nâng cao; hướng dẫn chính thức macOS hiện yêu cầu Docker cho pipeline Paddle, do đó chưa phù hợp làm dependency mặc định của app Mac nhẹ. Chưa benchmark bản này trên M1/16 GB; không khẳng định chạy local nhanh hoặc tốt hơn trên sách này.
  - https://ernie.baidu.com/blog/publication/PaddleOCR-VL_Technical_Report.pdf
  - https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6

Bước phù hợp trước mắt là nâng cấu trúc PDF/layout/chapter và dùng ghép ranh giới có kiểm chứng. Model layout/OCR chuyên dụng là fallback cần benchmark, thay vì bắt mọi sách đi qua LLM. Không cần thay engine TTS hoặc thay toàn bộ pipeline tạo giọng để giải quyết lỗi nhập này.

## Bằng chứng local

- `.qa/pdf-layout/geometry.json`: hình học dòng và cỡ chữ của PDF được chọn.
- `.qa/pdf-layout/probe_reflow.py`: prototype chạy offline, chỉ dùng dữ liệu của cuốn sách.
- `.qa/pdf-layout/result.json`: sáu chỗ ghép, kiểm chứng bảo toàn ký tự, danh sách 20 tiêu đề và vị trí nguồn.

Các artifact có nội dung sách là local-only, không đưa vào bản cài hoặc phát hành công khai. App hiện tại chưa tự áp dụng prototype này; cần tích hợp và chạy integration trước khi coi tính năng nhập đã được sửa.
