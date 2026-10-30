# Điều hướng và bìa sách — 22/10/2026

Tham khảo [swift-macos-template](https://github.com/simonweniger/swift-macos-template): sidebar có lựa chọn rõ ràng, vùng nội dung theo lựa chọn và thông tin ứng dụng trong cửa sổ riêng. Giữ AppKit/WKWebView và mức macOS 15 của dự án; không nhập toàn bộ runtime SwiftUI/macOS 26 của template.

- App mở ở Trang chủ. Sidebar, biểu tượng Home trên toolbar và menu Tệp → Về Trang chủ (⌘1) đưa về vùng kéo thả. Cập nhật từ sách đang xử lý ở nền không tự mở lại sách. Chữ chưa lưu vẫn được bảo vệ.
- Hai chế độ Tạo sách nói / Đọc sách có biểu tượng, mô tả và trạng thái chọn riêng. Giữ giao diện đọc toàn màn hình hiện có.
- Thông tin phiên bản, nơi lưu sách, trạng thái giọng, bảng giá và mở thư mục nằm trong Thông tin ứng dụng; menu Giới thiệu cũng mở cùng cửa sổ này. Popup có nhãn accessibility, giới hạn focus và đóng bằng Escape.
- Bìa dùng cover-image/metadata/guide của EPUB; PDF và ảnh dùng trang đầu. Không tìm ảnh trên mạng. Bìa là JPEG thu nhỏ tối đa 480 px, cache `cover-v1.json` tách khỏi `book.json` và audio. Thay nguồn sẽ làm mới cache. Thiếu bìa dùng chữ đầu tên sách.
- Cửa sổ nhỏ cho phép cuộn vùng làm sách tới các nút Lưu/Tạo; thanh nghe giữ vùng riêng. Không tải tài liệu hoặc tạo audio trên cloud trong thay đổi UI này.

## Kiểm tra local

`./scripts/build.sh` thành công. Bộ `unittest discover -s tests -v` có **109 bài đạt**, gồm kiểm tra bìa PDF/EPUB/ảnh thật, cache và đường dẫn ngoài sách. Fixture PDF có sẵn từ `tests/Fixtures.swift` trong `.qa/fixtures-data`; những bài xuất M4A cần quyền chạy framework âm thanh macOS.

WebKit native + worker thật kiểm tra Home, sự kiện sách cũ khi ở Home, chữ chưa lưu, hai chế độ, popup → quản lý giọng, nhập EPUB, bìa, cuộn tới Lưu, cửa sổ 860×660, sáng/tối và chế độ giảm chuyển động/tăng tương phản. Không chuyển tiếp lệnh TTS/cloud trong harness.

```sh
mkdir -p .qa/app-shell
.runtime/bin/python tests/prepare_app_shell.py > .qa/app-shell/setup.log 2>&1
swiftc -parse-as-library -module-cache-path /private/tmp/windi-sach-swift tests/verify_app_shell.swift -o .qa/app-shell/verify
.qa/app-shell/verify > .qa/app-shell/native-ui.log 2>&1
```

Ảnh kiểm tra nằm trong `.qa/app-shell/`. Đã kiểm tra thêm ứng dụng native đang chạy: bìa trên EPUB/PDF hiện có, Home và accessibility của popup thông tin. Đây là bằng chứng local trên Mac hiện tại; không phải kiểm chứng mọi EPUB/PDF, suy luận giọng mới hay bản phân phối công khai.
