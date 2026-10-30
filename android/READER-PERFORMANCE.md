> Cập nhật 0.2.6 (24/10/2026): thêm bước đo lại từng trang ứng viên trước khi chốt ranh giới; đoạn văn có thể ngắt dòng khác sau khi tách khỏi khối, đặc biệt khi chữ hệ thống lớn. Vẫn đo theo khối ở worker, cache bốn bố cục và chỉ rebase khi ranh giới thay đổi. Các số đo 0.2.5 dưới đây là lịch sử; xem [QA mới](QA.md) và [tính năng reader](READER-FEATURES.md).

# Màn đọc Android 0.2.5 · 23/10/2026

Android dùng native TextView một trang, StaticLayout và worker riêng. PDF và EPUB đã nhập dùng cùng luồng đọc từ bản chữ hiện tại.

## Vấn đề và thay đổi

Trước đây mỗi trang lại tạo StaticLayout cho tối đa 6.000 ký tự tiếp theo, lấy riêng các dòng của trang đầu rồi bỏ phần đo còn lại. Sách dài, chữ lớn và viewport thấp làm số lần đo lặp tăng. Sau thay đổi, mỗi cửa sổ chữ được đo một lần và dùng cho nhiều trang liên tiếp; trang cuối chưa đủ được mang sang cửa sổ kế. Cửa sổ không cắt surrogate; ranh giới chương và toàn bộ chữ nguồn được giữ.

`ReaderDialog` đưa việc lấy mốc chương vào worker, gộp callback đổi kích thước/phông trong 40 ms, hủy tác vụ cũ và chỉ nhận kết quả đúng revision. Bốn bố cục gần đây được cache trong dialog theo chiều rộng/cao, phông và text size thực tế. Cache chỉ chứa ranh giới trang; không giữ nhiều cây view hay toàn bộ bitmap sách.

Anchor đọc là offset nguồn theo hash chữ, không bị thay bằng đầu trang mới sau mỗi lần đổi cỡ chữ. Đóng/mở lại, đổi phông/cỡ chữ và ẩn/hiện điều khiển giữ anchor này. Chỉ lật/chọn trang mới thay vị trí đọc. Tick trạng thái nghe không ghi lại nhãn giống hệt; thao tác ở biên trang không chạy lại animation hoặc ghi preference trùng.

TextView được giới hạn theo viewport, padding rõ ràng và wrap ngang. Phông fallback và khoảng cách dòng của worker khớp với renderer. Nội dung và audio cache không thay đổi do dàn lại.

## Đo trên emulator

AOSP API 35 ARM64, 1080×2400, density 420, dark mode. Cùng 312.297 đơn vị UTF-16 từ bản chữ của PDF QA 203 trang, cài APK trước/sau bằng cùng signer. Đo lúc reader được mở trong activity đã sẵn sàng; không gồm import PDF, OCR, cài model hoặc TTS. Bộ đo chờ ranh giới trang được gắn vào UI, có chi phí điều phối/polling.

| Thao tác | Trước | Sau |
|---|---:|---:|
| Mở reader ở cỡ 19 | 1.821 ms | 582 ms |
| Đổi sang cỡ 30 | 3.309 ms | 285 ms |
| Quay về cỡ 19 | 1.483 ms | 346 ms |

Hai bản đều cho 596 trang ở cỡ 19 và 1.292 trang ở cỡ 30 trong cấu hình này. Kiểm tra nối lại mọi range cho đúng nguyên văn và đo TextView của tất cả trang cỡ 30 để phát hiện chữ vượt mép/ngang hoặc dưới. Khoảng trắng cuối dòng được loại khỏi phép đo mép ký tự, không bị xóa khỏi chữ sách. Đây không phải phép đo FPS hoặc benchmark điện thoại vật lý.

## Kiểm tra và build

- 5 unit tests Java về chia chữ, dọn và reflow qua.
- Native: sách dài/chữ lớn; Unicode/emoji/combining marks và biên cửa sổ; ranh giới chương; hủy dàn trang; đổi typography liên tục; ẩn/hiện controls; giữ đúng anchor; đóng/mở lại. Các bài reader hiện có cũng được chạy.
- Thư viện fixture nằm trong `.qa/reader-performance` và `.qa/reader-chapters` của emulator, không dùng thư viện khách hàng. Không gọi cloud hay inference.
- Build: `./scripts/build.sh --android :app:testDebugUnitTest :app:assembleDebugAndroidTest --offline`. APK đầy đủ model Lite, cùng package `studio.windi.soundbooki.preview`, versionCode 8 / `0.2.5-test`; apksigner và ZIP alignment 16 KB được kiểm tra trong build script.

Raw evidence local: `.qa/android-reader/` ở project Mac; test sources `ReaderPerformanceTest.java`, `ReaderPaginatorTest.java`, `ReaderChapterTest.java`. Chưa đo tốc độ/pin/nhiệt trên Pixel 8 Pro hoặc Redmi Note 13 thật; kết quả không đại diện mọi tài liệu/font/system font scale.
