> Cập nhật 24/10/2026: owner đã duyệt và bật thanh toán sách lẻ Mac qua SePay → queue HeyGen, đồng thời xác nhận quyền thương mại. Các trạng thái paid-deferred bên dưới là lịch sử. Xem [activation và kiểm chứng hiện tại](CLOUD-PAID-DEPLOYMENT.md).

> Triển khai mới nhất 23/10/2026: gateway và worker **đã hoạt động cho test private trên Mac owner**, profile 5/5 và mẫu giọng thật đã nhận thành công. Thanh toán/public rollout vẫn tắt. Các mô tả "chưa deploy" bên dưới là bằng chứng lịch sử trước activation này. Xem [trạng thái triển khai và cách test](CLOUD-TRIAL-DEPLOYMENT.md).

> Quyết định mới nhất 23/10/2026: **5 lượt miễn phí trọn đời/thiết bị**, không reset lượt đã dùng. Mặc định **Tạo thử · 1 lượt** (5.000 ký tự); người dùng có thể chọn **Tạo chương · Tối đa 4 lượt** (20.000 ký tự), app hiển thị số lượt thực tế trước khi xác nhận. SQL mới `commerce/manual/trial-five-unit-policy.sql` áp sau bản gộp; chưa áp live. Các mô tả 10 lượt bên dưới là lịch sử, được thay thế bởi quyết định này. Xem [chính sách hiện tại](DEVICE-PAYMENTS-AND-QUEUE.md#nam-luot-mien-phi).

> Cập nhật mới 23/10/2026: một chương được gộp **tối đa 4 lượt Pro miễn phí**, mỗi lượt 5.000 Unicode code point; một yêu cầu tối đa **20.000 ký tự**, chi phí `ceil(số ký tự thực/5.000)`. Tổng trọn đời vẫn **10 lượt/thiết bị**, giữ số đã dùng. Xem [luồng thiết bị và quota gộp](DEVICE-PAYMENTS-AND-QUEUE.md#gom-luot-pro-theo-chuong). Gateway/dispatcher vẫn chưa triển khai; SQL gộp mới ở `commerce/manual/trial-group-up-to-four.sql` chưa áp dụng live.

> Cập nhật 23/10/2026: quota mới **10 × 5.000 ký tự**, bảo toàn lượt đã dùng; đã có Hồ sơ local và mẫu theo chương. Owner chốt các thiết bị độc lập, không đăng nhập/sync; IAP và dispatcher chưa kích hoạt. SQL quota bổ sung ở `commerce/manual/trial-10x5000.sql`, chưa áp dụng live. Xem [thiết kế thanh toán theo thiết bị và kết quả rà queue](DEVICE-PAYMENTS-AND-QUEUE.md). Các số 4.000/bằng chứng bên dưới ghi lại trạng thái trước cập nhật này; chunk provider đề xuất vẫn 4.000.

# Lite và Pro Cloud theo cuốn — cập nhật 22/10/2026

## Kiểm tra Mac và xác nhận theo chương — 23/10/2026

Nút tạo Pro ở chương đang mở, nút nghe khi chưa có audio và Hồ sơ → Tạo thử dùng xác nhận ngắn: chương/giọng đã lưu, tự tính 1–4 lượt để tạo tối đa 20.000 ký tự, bấm xác nhận để gửi lên cloud và dùng đúng số lượt đã hiện. Không mở bảng giá cả cuốn hoặc lặp toàn bộ chữ đã lưu trong bước này. Bảng báo giá/mua cả cuốn vẫn là đường vào riêng. Truyền chapter ID trực tiếp từ chương đang chọn; không dựa vào `selectedScope()` vốn trả `all` cho playback/export Pro. Nhận lại yêu cầu mẫu đã có không tiêu thêm lượt, kể cả số lượt hiện tại bằng 0. Xác minh endpoint/Keychain trước khi lưu yêu cầu mới để cấu hình thiếu không tạo đơn local dở.

Kiểm tra thực tế ngày 23/10: `release.json` đang là `consumer` và **không có `booksBaseURL`**. `WSN_BOOKS_API` chỉ áp dụng development, không phải đường sửa cho bản consumer này. Probe POST `{}` không có chữ sách/danh tính vào `/functions/v1/wsn-books/profile` trên cùng dự án Supabase của license nhận **HTTP 404**, code `NOT_FOUND`, message `Requested function was not found`. Chưa gọi TTS hoặc thay cấu hình live. Vì gateway chưa tồn tại và dispatcher HeyGen production chưa triển khai, không thể coi UI/fixture là tạo Pro thật. Cần triển khai dịch vụ/queue trong phạm vi activation riêng trước khi gắn URL đã xác minh vào app; không đưa key HeyGen vào client hoặc nối app trực tiếp vào script owner.

Đã sửa mã app, thêm ledger vào Supabase và kiểm tra hợp đồng bằng fixture. **Chưa triển khai gateway mới, chưa kích hoạt mua/tạo cloud thật, chưa chạy GPU trả phí.** App chưa có `booksBaseURL` sẽ báo chưa kết nối dịch vụ và vẫn dùng Lite được. Đây là bản app phát triển local, không phải bộ cài phát hành.

## Chính sách thử mới và phương án HeyGen

Owner chốt **10 lượt/Mac, tối đa 4.000 ký tự/lượt** ngày 22/10/2026. Mã app/gateway local đã cập nhật; migration `20261022083604_book_trial_10x4000.sql` **chưa áp dụng lên database thật**, gateway mới chưa deploy. Không reset số đã dùng: máy dùng 3 còn 7. QA database 3×500 bên dưới là bằng chứng lịch sử trước thay đổi.

Xem [tính công suất HeyGen, queue, database và thanh toán](HEYGEN-CAPACITY-PLAN.md): đầu vào owner 30 request/phút, 5.000 ký tự/request, ưu đãi tới 30/11/2026; đề xuất điều phối chung 25/phút. Queue phân tán/provider adapter trong tài liệu là phương án triển khai, chưa kích hoạt. Luồng đơn Modal đã có giữ nguyên; không tự chuyển đơn cũ sang HeyGen.

## Combo ra mắt — một lần trên mỗi Mac

Owner đã chốt **50.000đ/5 cuốn**, mua và dùng cả 5 lượt trước **23:59 ngày 01/11/2026 (giờ Việt Nam)**. Mua lẻ theo book-v1 bên dưới, không còn phương án đồng giá 15.000đ hay sách ngắn 5.000đ. Mỗi Mac chỉ mua một combo; mỗi lượt khóa một bản chữ/một giọng, retry không trừ lại; có thể đặt đủ 5 cuốn vào hàng đợi trước hạn dù cuốn trước chưa xử lý xong.

[Chính sách, giao diện, database và trạng thái triển khai](LAUNCH-COMBO.md). Migration `20261022090045_launch_combo_five_books.sql` và gateway mới chỉ chuẩn bị local, **chưa áp dụng/deploy/bật bán**. Đơn mới dùng snapshot HeyGen riêng; Modal operator không nhận đơn HeyGen. Các đơn/receipt cũ giữ nguyên.

## Giá bán book-v1

Giá tính theo số Unicode code point thực tế của các đoạn sẽ đọc, bao gồm dấu cách và dấu câu; bỏ các đoạn hoàn toàn không đọc được. Không tính theo số trang hoặc tốc độ player. 900 ký tự/phút là hệ số ước tính, cần hiệu chỉnh từ sách thật trước khi thay phiên bản bảng giá.

| Ký tự | Thời lượng ước tính ở 1× | Giá một cuốn / một giọng |
|---|---|---|
| 1–27.000 | Đến 30 phút | 10.000đ |
| 27.001–54.000 | Trên 30 phút đến 1 giờ | 25.000đ |
| 54.001–108.000 | Trên 1 đến 2 giờ | 40.000đ |
| 108.001–162.000 | Trên 2 đến 3 giờ | 50.000đ |
| 162.001–216.000 | Trên 3 đến 4 giờ | 60.000đ |
| Mỗi 54.000 ký tự hoặc phần lẻ tiếp theo | Khoảng 1 giờ | Thêm 10.000đ |

Ví dụ 500 hoặc 1.000 ký tự tạo toàn bộ sách vẫn là 10.000đ. Sách 216.000 ký tự phải trả 60.000đ. Mức chi phí 5.000đ/giờ do chủ sở hữu cung cấp chỉ là giả định đầu vào; chưa đo lại phí khởi động GPU, Qwen, lưu trữ và tải audio của luồng mới. Không dùng thời lượng thay đổi theo giọng để phụ thu sau khi khách đã trả đúng báo giá.

Mỗi đơn mua **một bản chữ + một giọng + một phiên bản model của cuốn sách**. Không bán credit hay gói lượt dùng chung. Sửa chữ hoặc đổi giọng sẽ báo giá lại; nghe lại, nhận lại audio của đơn cũ, đổi tốc độ và đổi nhạc không phải mua lại. Lỗi/tạm dừng tiếp tục cùng đơn và cùng snapshot. Không tự tạo đơn GPU mới sau một timeout không rõ kết quả.

## Trong app

- Lite dùng Nano local, mặc định Đức Trí. Adam, Ái Hân, Xuân Tiên và Minh Quân không còn trong danh sách giọng Nano; file nguồn/audio cũ không bị xóa.
- KittenTTS tiếng Anh vẫn miễn phí. Pro Cloud hiện chỉ tiếng Việt.
- Catalog Pro local hiện có bảy giọng HeyGen; snapshot mới dùng `pro-cloud-heygen-v1`, cần gateway/migration và dispatcher HeyGen trước khi mở bán. Đơn Modal cũ giữ sáu alias 002, 003, 004, 006, 007, 008 và operator Modal riêng. Không tải checkpoint F5 riêng để dùng Pro Cloud.
- 10 lượt thử tổng cộng trên mỗi mã Mac, không phải 10 lượt mỗi sách. Mỗi lần tối đa 4.000 ký tự (source local; database thật chờ migration quota), tự chọn chương 1 theo mốc EPUB/PDF/manual hoặc chương đầu đã có; nếu không có mốc dùng đầu sách. Không dùng LLM viết lại, không đoán chương từ văn xuôi. Chỉ đoạn mẫu được gửi khi tạo thử. Mẫu dùng cache riêng, có nút nghe, không tạo take hay nút xuất.
- Xác nhận gửi chữ trước khi bấm tạo thử/báo giá. Mở modal, đổi giọng, phát và xem giá local không gọi GPU. Toàn bộ chữ chỉ được gửi khi khách chọn chuyển đổi toàn bộ sách.
- Popup kiểm tra đơn tối đa 30 lần, cách 10 giây khi đang mở và hiển thị. Đóng popup/ngừng hiển thị sẽ dừng lịch kiểm tra. Một HTTP đang chạy có thể hoàn thành; kết quả cũ không mở lại popup. Đóng popup không hủy công việc đã được owner chạy.
- `Đơn sách đã có trên Mac này` nhận lại audio của snapshot cũ, kể cả sau khi sửa sách/đổi giọng. Chưa có chuyển quyền tự phục vụ sang Mac khác.

## Database đã áp dụng

Migration `supabase/migrations/20261021140853_book_orders.sql` thêm `wsn_book_devices`, `wsn_book_orders`, `wsn_book_receipts`, các RPC `wsn_book_*` và bucket private `wsn-book-audio`. Không xóa/reset bảng khách, giấy phép hoặc thanh toán cũ. Trước và sau thay đổi đều còn 2 receipt và 1 giấy phép cũ; không có đơn QA lưu lại sau test rollback.

Mã Mac `SN…` liên kết với bí mật ngẫu nhiên 256 bit ở Keychain `studio.windi.sachnoi.books`. Database chỉ lưu SHA-256 của bí mật. Secret không đi qua UI/log. Mỗi đơn có UUID toàn cục và mã chuyển khoản `SB…` riêng, không dùng lại mã máy để thanh toán sách.

Database tự đếm ký tự và tính giá từ snapshot. Trigger chặn thay nội dung, giọng, số tiền hoặc mã đơn sau báo giá. Chỉ backend service-role được gọi RPC/đọc bảng; app không nhận service-role key. RLS bật, không cấp quyền trực tiếp cho anon/authenticated. Advisors chỉ báo INFO `rls_enabled_no_policy` đúng với thiết kế đóng quyền client; không tạo policy mở để bỏ cảnh báo.

`wsn_book_confirm` yêu cầu số tiền/tài khoản/mã đơn khớp, thời điểm tiền vào nằm trong thời hạn đơn, transaction ID duy nhất. Trả thiếu/thừa hoặc ghi nhiều mã cần đối soát riêng, không tự mở sách. Callback đến trễ vẫn có thể nhận giao dịch thực sự vào trước khi đơn hết hạn. Giao dịch không được dùng lại giữa các đơn, các máy hoặc ledger giấy phép cũ. `wsn_book_claim` chỉ nhận đơn đã trả đủ hoặc mẫu thử đã trừ quota; worker lấy chữ từ DB, không lấy chữ mới từ lệnh operator.

Lượt thử được tiêu thụ khi server chấp nhận yêu cầu, không phải khi bấm nghe. Retry cùng request key không mất lượt thêm; key được lưu trước khi gửi và giữ sau lỗi mạng/restart. Bí mật Keychain mất hoặc người dùng cố giả mã máy cần hỗ trợ riêng; cơ chế này không phải chứng thực phần cứng chống app đã bị sửa. Chưa có tự khôi phục bằng email/tài khoản.

## Lệnh vận hành

Chỉ chạy trên máy owner có `.env.local`; không đóng gói file này vào app. Các lệnh sau không tự lấy key từ project khác.

```sh
# Xem đơn, trạng thái, giá, số ký tự, mã Mac và mã chuyển khoản.
node --env-file=.env.local commerce/books.mjs list

# Sau khi đã kiểm tra tiền thực vào đúng tài khoản ngân hàng.
node --env-file=.env.local commerce/books.mjs confirm \
  --code SB_MA_DON_THUC_TE \
  --transaction MA_GIAO_DICH_NGAN_HANG \
  --account SO_TAI_KHOAN_NHAN \
  --amount SO_TIEN_THUC_NHAN \
  --paid-at THOI_DIEM_ISO8601_CO_MUI_GIO \
  --confirm-received

# Lệnh này gọi GPU và có chi phí: chỉ chạy sau khi chủ sở hữu bật vận hành.
node --env-file=.env.local commerce/books.mjs process-next --order UUID_DON

# Tiếp tục đúng công việc đang xử lý, giữ các đoạn hoàn tất.
node --env-file=.env.local commerce/books.mjs process-next --resume UUID_DON
```

`process-next` không có `--order` sẽ nhận một đơn trong queue. RPC dùng khóa hàng và claim token, không có hai worker nhận cùng đơn. Operator gọi batch Modal đã có với planner ngữ điệu, 22 steps, Qwen director và giọng đã mua; upload WAV từng đoạn rồi ghi ledger. Cache phía owner nằm trong `commerce/private/book-jobs/` (quyền thư mục 0700), chỉ inference/output, không chứa dataset train. Chỉ WAV hợp lệ mới được ghi hoàn tất; client kiểm SHA-256, lưu file tạm rồi đổi tên nguyên tử.

Nếu có `.sent.json` nhưng chưa có WAV hợp lệ, operator dừng để đối soát yêu cầu Modal không rõ kết quả. Không xóa dấu gửi hoặc submit lại theo thói quen: upstream chưa có idempotency, gọi lại có thể tốn GPU lần nữa. Nếu đã có WAV hợp lệ mà upload/RPC gián đoạn, `--resume` chỉ tiếp tục lưu kết quả.

SePay mới có nhánh xác minh mã SB và số tiền của cuốn sách trong source `supabase/functions/_shared/wsn.ts`; phải triển khai bản mới mới dùng được nhánh này. Ledger thủ công và SePay cùng gọi RPC, không cấp trùng một giao dịch. Backend SePay annual đang chạy chưa được deploy thay trong lượt này.

## Bước kích hoạt còn lại

Theo AGENTS.md, không tự publish hay mở dịch vụ trả phí. Tài liệu `docs/RELEASE-MAC.md` đã ghi nhận chủ sở hữu xác nhận quyền thương mại ngày 20/10/2026; không cần hỏi lại quyền đã được xác nhận. Còn cần phạm vi triển khai/vận hành được duyệt trước khi bật:

1. Chọn Proxy Token của workspace Modal và đặt `WSN_MODAL_PROXY_KEY`, `WSN_MODAL_PROXY_SECRET` trong môi trường operator. Source Modal dùng `requires_proxy_auth=True` để chặn yêu cầu thiếu quyền ngay tại proxy, trước khi khởi động container ([tài liệu Modal](https://modal.com/docs/guide/webhook-proxy-auth)); **endpoint cũ đang chạy chưa được thay**. Chọn endpoint batch hiện có trong `WSN_MODAL_BATCH_URL`. Các script research cũ gọi trực tiếp endpoint cần header `Modal-Key` và `Modal-Secret` sau khi triển khai; app khách không được cầm các key này.
2. Triển khai `wsn-books` và bản `wsn-sepay-webhook` mới. Server cần `WSN_BOOKS_ENABLED=true`, `WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED=true`, `WSN_BANK_ACCOUNT`, `WSN_BANK_BIN`, `WSN_BANK_NAME`, `WSN_BANK_HOLDER`, cùng các secret Supabase/SePay hiện có. Flag rights dùng căn cứ quyền riêng đã được ghi nhận trong `docs/RELEASE-MAC.md`, không dựa vào MIT của code. Endpoint status vẫn cho khách nhận audio cũ khi việc mở bán bị tắt.
3. Cấu hình app bằng URL HTTPS đã chọn trong `booksBaseURL`, hoặc `WSN_BOOKS_API` khi chạy bản development. Tool đóng gói hỗ trợ `--books-api`; chưa tạo bộ cài mới trong lượt này. Helper Keychain được build/copy/sign cùng app.
4. Chạy thử một đơn có kiểm soát theo sự cho phép của owner, rồi kiểm chứng giao dịch thật, Modal thật, nhận audio và xuất. Fixture và rollback test không chứng minh các bước thật này.

## Bằng chứng QA

- 79 Python core tests PASS; 14 Edge Function tests PASS.
- Database live ngày 21/10/2026, trước nâng quota: các ngưỡng giá, đơn bất biến, quota 3×500, retry, trả thiếu, dùng lại transaction, tách máy, claim một lần, chặn đơn 25k cho sách 4 giờ PASS trong transaction rollback.
- RLS/grants/private bucket đã kiểm tra live; bộ đếm lịch sử cũ được giữ.
- HTTPS local fixture PASS: gửi đúng mẫu, cache mẫu tách biệt, tải lỗi giữ đoạn hoàn tất, retry không ghi lại cache, đổi chữ/giọng không phát audio cũ, nhận lại take đúng snapshot và xuất WAV.
- Nano/Lite thật PASS trong `.qa`: audio đầu 2,494 giây; lượt tiếp theo 1,509 giây; 12 đoạn/97,29 giây audio, đổi giọng làm mất hiệu lực cache, không tạo ngoài phạm vi.
- Build bằng `./scripts/build.sh` PASS; native WKWebView kiểm consent/mẫu/QR/dark/light/focus/polling. Báo cáo và ảnh trong `.qa/book-ui/`. Không có sách cá nhân, tiền thật hay GPU cloud trong các phép kiểm này.
