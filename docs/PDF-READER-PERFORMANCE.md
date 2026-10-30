# Độ mượt màn đọc PDF · 23/10/2026

## Nguyên nhân đã tái hiện

Màn Ebook dàn chữ thành một dải CSS multicolumn dài rồi dịch dải đó để chọn spread. `translate3d` trên toàn bộ dải khiến đường vẽ/compositing của WebKit chậm nặng. Chỉ đổi trang trực tiếp, tắt cả hiệu ứng GulLabs, vẫn mất 1.353–1.385 ms giữa các khung hình. Giữ `translate3d` và thêm containment vẫn tái hiện lỗi. Dùng dịch chuyển 2D với viewport giới hạn vùng vẽ giảm còn 42–57 ms trong phép thử đối chứng. Vì vậy lỗi không chỉ nằm ở engine lật giấy hay tốc độ trích chữ PDF.

Hiệu ứng lật giấy phải chụp spread cũ, đổi spread, chụp spread mới rồi dựng bốn mặt ảnh. Đường vẽ chậm ở trên kéo dài cả quá trình chụp, đôi khi chạm fallback. Bộ đo cũ gọi nhiều lần `commitEbookSpread` trong cùng một JavaScript task, không chờ browser vẽ; kết quả vài mili giây của nó không phản ánh độ khựng người đọc nhìn thấy.

Một chi phí riêng lúc mở: nội dung được gắn vào DOM trước khi xác định kích thước cột. Lần đọc kích thước đầu tiên buộc WebKit dàn sách theo thông số cũ; thay kích thước cột sau đó lại buộc dàn toàn sách lần nữa.

## Thay đổi

- Dịch dải sách bằng `translateX`, bỏ perspective trên viewport của toàn sách và dùng `contain: layout paint`. Phối cảnh của GulLabs vẫn nằm trong lớp bốn mặt chuyển cảnh có kích thước hữu hạn.
- Chuẩn bị phông, cỡ chữ, kích thước cột và ảnh trước khi gắn nội dung vào DOM; dùng lại cùng cách tính khi resize/đổi phông.
- Giữ nguyên DOM câu nguồn, chỉ mục cue, mục lục, follow, bookmark, ảnh tải gần vị trí xem và hiệu ứng lật giấy. Không đổi extraction, audio cache hoặc EPUB xuất.

## Phép đo WebKit native

Thư viện `.qa/reader-ui` riêng, bản sao PDF 203 trang / 3.583 câu, cửa sổ 1180 × 850 point trên máy phát triển. Cùng bộ đo chạy UI trước/sau; bốn lần lật ở đầu sách, nhảy tới khoảng 75%, rồi ba lần lật tiếp. Không chạy TTS hoặc cloud.

| Chỉ số | Trước | Sau |
|---|---:|---:|
| Từ `drawEbook` nhận payload tới frame có chỉ mục trang | 575 ms | 309 ms |
| Từ yêu cầu lật tới nhận đủ hai ảnh | 1.422–2.741 ms | 109–117 ms |
| Một lần lật hoàn tất, gồm animation 420 ms | 1.933–2.767 ms | 633–634 ms |
| Nhảy trực tiếp tới khoảng 75% sách | 1.382 ms | 60 ms |
| Khoảng cách lớn nhất giữa hai frame trong lượt đo | 1.383 ms | 93 ms |
| Phân vị 95% khoảng cách frame | 53 ms | 18 ms |

Đây là đo frontend sau khi đã nhận dữ liệu sách, không phải thời gian import/OCR hay chuẩn bị EPUB lần đầu. Việc giảm thời gian trong riêng hàm `layoutEbook` xuống 11 ms không được dùng để khẳng định tổng dàn trang chỉ mất 11 ms: browser vẫn phải làm layout/paint ngoài JavaScript. Không suy ra mọi frame đều đạt 60 fps, mọi PDF hoặc mọi phiên bản macOS đều tương đương.

`tests/verify_reader_smoothness.swift` đo `requestAnimationFrame` và các mốc capture/stage/finish thật, kiểm tra đủ cue và DOM ổn định. Chế độ thường báo lỗi nếu có frame gap ≥300 ms hoặc một thao tác ≥1.500 ms để bắt lại lỗi đứng hình cỡ giây. Kết quả local: `.qa/reader-smoothness/verified-before.json`, `verified-after.json`; ảnh chụp tương ứng cùng thư mục. `READER_BASELINE=1` dùng bản sao UI đối chứng trong `.qa/reader-smoothness/before-ui`.

22 core tests qua: `test_core`, `test_reading_library`, `test_ebook_reader`, `test_reader_listening`. Native UI integration và build được ghi trong `.qa/reader-smoothness/`.
