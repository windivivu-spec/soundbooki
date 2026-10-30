> Cập nhật 24/10/2026: owner đã duyệt và bật thanh toán sách lẻ Mac qua SePay → queue HeyGen, đồng thời xác nhận quyền thương mại. Các trạng thái paid-deferred bên dưới là lịch sử. Xem [activation và kiểm chứng hiện tại](CLOUD-PAID-DEPLOYMENT.md).

# Cloud trial trên Mac — triển khai 23/10/2026

Owner đã yêu cầu triển khai gateway để test tạo thử thật. **Supabase khỏe (`ACTIVE_HEALTHY`)**; nguyên nhân trước đó là thiếu `wsn-books`, dispatcher, schema quota mới và `booksBaseURL` trong app. Không phải lỗi đăng nhập Supabase hay mất dữ liệu.

## Trạng thái đã xác minh

- Project hiện dùng: `zpjphixcttehkkgxlmsn` (WindiStudio, shared). Chỉ triển khai hai function `wsn-books`, `wsn-heygen-worker`; không sửa/prune các function sản phẩm khác.
- `release.json` đã trỏ đến gateway HTTPS. Mã Mac băm đã bind trước với hash credential Keychain; profile gọi bằng chính credential Mac trả về **5/5**, registered=true. Khóa provider/service-role chỉ ở server.
- **Chỉ bật thử cho Mac owner** qua allowlist `WSN_BOOKS_TEST_DEVICES`. Không phải triển khai công khai đa thiết bị. Không bật thu tiền, combo hoặc StoreKit/Play Billing. `WSN_BOOKS_ENABLED=false`, `WSN_LAUNCH_COMBO_ENABLED=false`; không tự xác nhận quyền thương mại hoặc chuyển sang model tính phí.
- Trial chọn 1 hoặc tối đa 4 lượt; tổng trọn đời 5, mỗi lượt 5.000 Unicode code point. Idempotency, quota trừ nguyên tử, snapshot/hash và lịch sử cũ giữ nguyên. Quota trong máy là cache; server quyết định.

## Worker và bảo mật

Worker chỉ nhận trial HeyGen, không nhận sách chưa trả tiền hoặc đổi pipeline đơn Modal cũ. Mỗi đoạn giữ nguyên chữ, voice và snapshot. Model được khóa `heygen-voice-1-turbo-free`, không fallback model trả tiền. Một đoạn tối đa 2.000 ký tự theo snapshot hiện tại; số lượt app không phải số request provider.

`wsn_heygen_control` và `wsn_heygen_tasks` dùng RLS, không cho anon/authenticated đọc/ghi hoặc gọi RPC. Khóa database chung điều phối tối đa một dispatch/2,5 giây, tối đa 3 request đang gửi; ưu tiên luân phiên thiết bị rồi đơn cũ. Lịch `wsn-heygen-trial-dispatch` mỗi 3 giây chỉ gửi HTTP khi có trial hợp lệ đang chờ/xử lý. Đây là limiter chung cho mọi worker WSN dùng cùng control row; không kiểm soát được công cụ ngoài hệ thống gọi trực tiếp cùng tài khoản provider.

Vault giữ secret worker; pg_net chỉ chứa chữ ký HMAC ngắn hạn, không chứa khóa HeyGen, service-role hoặc token worker lâu dài. Token worker không có quyền đọc sách trực tiếp; worker bỏ qua body caller và lấy task từ database. Các bảng pg_net ở project hiện có PUBLIC SELECT nên dùng chữ ký là cần thiết; không thay quyền bảng dùng chung của sản phẩm khác.

Lưu URL provider thành công trước khi download. Download/upload/commit lại dùng URL cũ, không gửi lại TTS. HTTP429 tôn trọng Retry-After, cooldown chung, tối đa 4 lần dispatch an toàn. Timeout/HTTP500 hoặc worker chết sau gửi chuyển uncertain/failed để đối soát, không tự synthesize lại một request chưa rõ kết quả. Luồng này chưa hứa tự hoàn quota hoặc phục hồi mọi lỗi provider.

Bucket `wsn-book-audio` private; chỉ credential đúng đơn mới nhận signed URL ngắn hạn. Khi tạo link phải gửi cả API key server; thiếu header này là lỗi thực tế đã sửa. Mac kiểm SHA256 của file provider trước, rồi dùng SoXR HQ local đổi WAV 44,1 kHz về PCM mono 16 bit/24 kHz để khớp player/export. Không nới validation cache hoặc thay chữ gốc. Audio cũ Modal giữ contract cũ.

## Bằng chứng

- 27 tests gateway/worker PASS: scope trial, paid vẫn đóng, auth, HMAC hết hạn, format, retry429, unknown POST, private URL, nhận lại object và ký link có API key. `.qa/cloud-dispatcher-tests.log`.
- PGlite PASS: quota5/schema, limiter, max3, fairness, tách Modal, URL recovery, claim/grants và uncertain không tự gọi lại. `.qa/heygen-dispatcher-db-report.json`; một connection, chưa là load/concurrency benchmark.
- Đã tạo **một mẫu QA chữ tự viết** qua gateway và HeyGen thật, voice Đình Mạnh; duration **6,39 giây**. Dùng thiết bị QA riêng, không tiêu 5 lượt Mac owner. Nhận bằng chính `backend/book_cloud.py`, WAV hợp lệ 24 kHz, kiểm hash trước chuyển đổi và nhận lại lần hai không tạo TTS. `.qa/cloud-deploy/live-report.json`. Quyền gửi trial mới của thiết bị QA đã gỡ.
- Đối chiếu sau triển khai: 2 receipt cũ, 1 license cũ; owner trials_used=0; bucket không public, RPC mới không cho anon/member execute. Advisors HTTP200, chỉ INFO `rls_enabled_no_policy` cho bảng private đã revoke quyền; không mở policy public để dập thông báo. `.qa/cloud-deploy/final-report.json`.
- 132 core tests PASS, HTTPS localhost integration PASS; `./scripts/build.sh` PASS bản Mac local. `.qa/cloud-deploy/core-tests.log`, `https-integration.log`, `mac-build.log`.

## Vận hành và giới hạn

`commerce/cloud-deploy.mjs` dùng Management API chính thức, pin project, thao tác từng function, không cần CLI ghi telemetry ngoài dự án. Đã sao lưu riêng dữ liệu WSN trước thay đổi trong `.qa/cloud-deploy/before.private.json` (0600). DDL áp trong một transaction từ các bản quota/combo nháp đã QA rồi `heygen-trial-dispatcher.sql`; bản SQL thực tế ở `.qa/cloud-deploy/applied.sql`. Chưa tạo bản migration lịch sử bằng CLI; không chạy lại `schema` khi đã có bảng.

Chưa kiểm chứng thiết bị Android thật/PC, tất cả 7 giọng hoặc tải nhiều người. Trước mở công khai cần thêm quyền thương mại, chính sách lưu/xóa text/audio, hỗ trợ lỗi/quota, thử tải và activation riêng cho thanh toán/queue paid. Hiện là một luồng **test private theo thiết bị**, không phải thư viện cloud lâu dài hay bản Store phát hành.

Sau cập nhật, thoát hẳn rồi mở lại app Mac để Python worker nạp mã nhận audio mới. Chọn sách/chương, giọng Pro, `Tạo thử · 1 lượt` hoặc `Tạo chương · Tối đa 4 lượt`, rồi xác nhận. Mở lại đơn để nhận tiếp không tiêu lượt nữa.
