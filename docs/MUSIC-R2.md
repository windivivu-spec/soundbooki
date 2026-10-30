# Nhạc nền và R2

## Trong app local

`assets/music/` có 5 thư mục mới với 17 bài. Tên thư mục là thể loại; tên bài dạng số hiển thị “Bài 01”, còn tên riêng được giữ nguyên. Chỉ dùng nhạc người dùng thêm; đã bỏ Sương sớm, Trang giấy và Dịu êm cùng cơ chế tự tạo chúng.

Chọn thể loại → chọn một bài hoặc Ngẫu nhiên. Ngẫu nhiên phát toàn bộ bài của thể loại theo thứ tự đã chọn; “Đảo lại” tạo thứ tự khác. “Lặp nhạc” lặp một bài hoặc cả danh sách; tắt thì nhạc dừng sau lượt cuối, lời đọc tiếp tục. Các lựa chọn, thứ tự và âm lượng lưu riêng theo sách, áp dụng khi nghe và xuất WAV/M4A/web. Đổi nhạc không làm mất cache giọng.

`./scripts/build.sh` chuẩn bị WAV mono 24 kHz trong `assets/music/prepared/` bằng `scripts/music_library.py`. File gốc không bị sửa. Công cụ chuẩn bị dùng bộ giải mã macOS, dự phòng ffmpeg có sẵn cho codec không hỗ trợ; app không cần ffmpeg để nghe hoặc xuất các bài đã chuẩn bị.

## Các trường trong .env.local

| Trường | Điền gì |
| --- | --- |
| `R2_ACCOUNT_ID` | Account ID trên trang R2 Overview |
| `R2_ACCESS_KEY_ID` | Access Key ID khi tạo R2 API token |
| `R2_SECRET_ACCESS_KEY` | Secret Access Key của cùng token |
| `R2_BUCKET` | Tên bucket thật trong R2, không phải tên binding trong Worker |
| `R2_PUBLIC_BASE_URL` | URL HTTPS công khai để tải tài nguyên, từ custom domain hoặc Public Development URL |

Tạo R2 API token có quyền **Object Read & Write**, giới hạn vào bucket này. Hai khóa S3 khác với một Cloudflare API token dạng Bearer. Không gửi khóa vào chat. Các trường này chỉ dành cho công cụ quản lý tài nguyên, không đưa vào app.

Người dùng xác nhận tên bucket là `windi-bucket`; đã cập nhật `R2_BUCKET` theo tên này. R2 chỉ cho chữ thường, số và dấu `-`. Không tạo bucket mới.

`R2_PUBLIC_BASE_URL` dùng cho nhạc/public resources; checkpoint giọng Pro cần tải qua dịch vụ kiểm tra bản quyền và URL ký có thời hạn. Không đưa private checkpoint vào catalog công khai.

## Chuẩn bị để upload

```sh
.runtime/bin/python scripts/prepare_music_r2.py
```

Tạo 5 ZIP riêng theo thể loại và `.release-assets/music/upload-plan.json`. Mỗi ZIP chứa WAV đã chuẩn bị, catalog, SHA-256 và dung lượng từng bài; object key có version và hash. Chỉ gồm 17 bài mới, không kèm sách, bản thu demo cũ, training dataset, `.env` hoặc bất kỳ khóa bí mật nào. Script không upload, không dùng mạng. Chỉ upload đúng các object trong kế hoạch sau khi cấu hình bucket hợp lệ và có hành động upload rõ ràng.

Bản local và preview nội bộ đã được cập nhật để chọn được 17 bài của người dùng. Bản preview cũ chỉ kèm ba bài tự tạo là nguyên nhân danh sách nhạc mới không xuất hiện. Preview nội bộ hiện kèm WAV đã chuẩn bị của 17 bài để nghe ngay; tải gói nhạc R2/F5 khi cần chưa được nối vào app và chưa upload nhạc/model lên R2.

## Kiểm tra kết nối R2 — 20/10/2026

```sh
node --env-file=.env.local commerce/probe-r2.mjs
```

Đã xác nhận bucket `windi-bucket`: đọc danh sách HTTP 200, ghi marker nhỏ HTTP 200, tải qua URL công khai HTTP 200 với nội dung khớp SHA-256. Đã xóa marker HTTP 204 và xác nhận HEAD 404 sau khi xóa. Báo cáo không chứa khóa ở `.qa/r2/connection.json`.

Probe chỉ dùng marker ngẫu nhiên trong `sachnoi/_connection-check/` và dọn trong `finally`; không upload gói nhạc, checkpoint hay dữ liệu người dùng. Kiểm tra này chứng minh kết nối/đọc/ghi/tải công khai, chưa chứng minh app tải và cài gói tài nguyên từ R2.

Nguồn cấu hình: [R2 S3](https://developers.cloudflare.com/r2/get-started/s3/), [R2 API tokens](https://developers.cloudflare.com/r2/api/tokens/), [Public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/), [Bucket naming](https://developers.cloudflare.com/r2/api/error-codes/).

## Kiểm tra

- 43 Python tests, gồm lưu/mở lại thứ tự, giữ cache giọng, timeline 24/48 kHz, loop, thiếu bài và WAV/M4A/web thật trong `.qa`.
- `tests/verify_music_playback.swift`: AVAudioPlayer chuyển hai bài im lặng, dừng cuối danh sách, seek qua bài và lặp timeline.
- `tests/verify_music_ui.swift`: WebKit thật, chọn thể loại/bài, shuffle/đảo lại, volume/loop, payload nghe thử, khóa khi xuất, VI/EN sáng/tối. Ảnh ở `.qa/music-ui/`.

Tạo fixture UI trước khi chạy harness:

```sh
.runtime/bin/python tests/music_ui_fixture.py
swiftc -parse-as-library -O -target arm64-apple-macosx15.0 -module-cache-path "$TMPDIR/windi-sach-swift" tests/verify_music_ui.swift -o .build/verify-music-ui
.build/verify-music-ui
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "$TMPDIR/windi-sach-swift" tests/verify_music_playback.swift native/Music.swift -o .build/verify-music-playback
.build/verify-music-playback
```

Codec AudioToolbox và WebKit/AVAudioPlayer cần chạy trong phiên desktop macOS; sandbox của công cụ CLI có thể từ chối codec AAC dù app desktop hoạt động bình thường.

## Mở đúng app

`./scripts/run.sh` đăng ký lại đường dẫn app local với LaunchServices trước khi mở. Đã tái hiện macOS gọi nhầm bản preview cũ khi mở local, và xác nhận tiến trình local đúng đường dẫn sau khi đăng ký lại. Không reset thư viện hoặc bản quyền.
