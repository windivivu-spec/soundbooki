# Nhập EPUB trên Mac

Dùng **Thêm sách mới**, **Chọn EPUB, PDF hoặc ảnh**, hoặc **⌘O**. Có thể kéo file từ Finder và thả vào vùng đọc của cửa sổ app.

- Mỗi lần nhận một EPUB, một PDF hoặc nhiều ảnh; không trộn EPUB/PDF với tài liệu khác trong cùng lần nhập.
- Nhận EPUB dạng file nén và thư mục có đuôi `.epub`. Tên file tiếng Việt, khoảng trắng và đuôi `.EPUB` đều được giữ.
- Hộp chọn kiểm tra đuôi file thay vì phụ thuộc UTType do Finder gán. Thư mục thường vẫn duyệt được nhưng không được nhập làm sách.
- File được chọn/kéo qua native, kiểm tra khả năng đọc và định dạng, rồi chuyển vào cùng luồng nhập bằng selection token dùng một lần. JavaScript không được gửi đường dẫn tùy ý để đọc file.
- Nội dung đang sửa phải được lưu/hủy trước khi nhập sách khác. Đóng popup thanh toán/bản quyền trước khi thêm sách.
- App giữ bản sao EPUB gốc và nội dung tiếng Việt. Việc nhập không cần tải model hoặc gọi mạng.

Sách cũ có nhạc nền không còn trên máy vẫn mở được. Lựa chọn nhạc và âm lượng lưu trong sách được giữ; phần nhạc báo thiếu và yêu cầu chọn nhạc có sẵn trước khi nghe kèm/xuất file. Không tự đổi sang một bản nhạc khác.

Build qua `./scripts/build.sh`, gồm `native/App.swift`, `native/Payment.swift`, `native/Import.swift`.

Kiểm tra native policy:

```sh
swiftc -O native/Import.swift tests/verify_import.swift -o .qa/verify-import
.qa/verify-import "$PWD/.qa/import-native/policy"
.runtime/bin/python -m unittest discover -s tests -q
```

QA 20/10/2026: đã nhập EPUB thật bằng native file picker và native dragging session/file pasteboard qua WebKit trong app QA riêng; cả hai sách trích chữ thành công và giữ nguyên EPUB gốc/dấu tiếng Việt/phân đoạn. Policy kiểm tra tên có dấu, đuôi viết hoa, EPUB thư mục và chặn trộn định dạng/file không hỗ trợ/URL mạng. Báo cáo ở `.qa/epub-import/report.json`. Đây là kiểm thử fixture, không khẳng định mọi EPUB, DRM, ảnh scan hoặc mọi phiên bản macOS đều hoạt động.
