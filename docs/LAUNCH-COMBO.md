> Quyết định mới nhất 23/10/2026: **5 lượt miễn phí trọn đời/thiết bị**, không reset lượt đã dùng. Mặc định **Tạo thử · 1 lượt** (5.000 ký tự); người dùng có thể chọn **Tạo chương · Tối đa 4 lượt** (20.000 ký tự), app hiển thị số lượt thực tế trước khi xác nhận. SQL mới `commerce/manual/trial-five-unit-policy.sql` áp sau bản gộp; chưa áp live. Các mô tả 10 lượt bên dưới là lịch sử, được thay thế bởi quyết định này. Xem [chính sách hiện tại](DEVICE-PAYMENTS-AND-QUEUE.md#nam-luot-mien-phi).

> Cập nhật mới 23/10/2026: một chương được gộp **tối đa 4 lượt Pro miễn phí**, mỗi lượt 5.000 Unicode code point; một yêu cầu tối đa **20.000 ký tự**, chi phí `ceil(số ký tự thực/5.000)`. Tổng trọn đời vẫn **10 lượt/thiết bị**, giữ số đã dùng. Xem [luồng thiết bị và quota gộp](DEVICE-PAYMENTS-AND-QUEUE.md#gom-luot-pro-theo-chuong). Gateway/dispatcher vẫn chưa triển khai; SQL gộp mới ở `commerce/manual/trial-group-up-to-four.sql` chưa áp dụng live.

> Cập nhật 23/10/2026: quota mới **10 × 5.000 ký tự**, bảo toàn lượt đã dùng; đã có Hồ sơ local và mẫu theo chương. Owner chốt các thiết bị độc lập, không đăng nhập/sync; IAP và dispatcher chưa kích hoạt. SQL quota bổ sung ở `commerce/manual/trial-10x5000.sql`, chưa áp dụng live. Xem [thiết kế thanh toán theo thiết bị và kết quả rà queue](DEVICE-PAYMENTS-AND-QUEUE.md). Các số 4.000/bằng chứng bên dưới ghi lại trạng thái trước cập nhật này; chunk provider đề xuất vẫn 4.000.

# Combo ra mắt — 50.000đ / 5 cuốn / Mac

Owner chốt ngày 22/10/2026, thay phương án 15.000đ/cuốn không giới hạn và 5.000đ cho sách ngắn. **Mua lẻ tiếp tục theo book-v1**, không giảm về 5.000đ hoặc 15.000đ.

## Quyền lợi và thời hạn

- 50.000đ trả một lần, được đặt tạo 5 cuốn Pro trên đúng Mac đã mua. Mỗi Mac chỉ mua một combo của chương trình; không bán nối tiếp cùng combo khi dùng hết.
- **Mua và dùng cả 5 lượt trước 23:59 ngày 01/11/2026, giờ Việt Nam**. Server dùng khoảng thời gian nửa mở: `2026-10-22T00:00:00+07:00 <= now < 2026-11-02T00:00:00+07:00`. Mốc cuối là `2026-11-01T17:00:00Z`.
- “Dùng lượt” là server chấp nhận snapshot và tạo đơn sách trước hạn, không bắt audio phải hoàn thành trước hạn. Đơn đã nhận vẫn chạy/được nhận lại sau khi chương trình kết thúc. Lượt chưa dùng hết hạn cùng chương trình; không quảng cáo quyền sử dụng đến 30/11 hoặc vô thời hạn.
- Mỗi lượt gắn một bản chữ + một giọng + một revision của sách. Đổi chữ hoặc giọng tạo snapshot mới; retry, tiếp tục đơn lỗi và nhận lại audio cùng đơn không trừ lại. Đổi tốc độ nghe hoặc nhạc không làm mất lượt.
- Mỗi sách giữ giới hạn hiện tại 1–2.000.000 ký tự; không thêm hạn độ dài không được công bố. Cho phép đặt đủ 5 cuốn vào queue trước hạn, kể cả khi cuốn trước chưa hoàn tất. Không buộc chờ hai cuốn xong rồi mới được dùng phần còn lại, tránh mất lượt vì thời gian chờ của dịch vụ. Tốc độ xử lý/concurrency vẫn do dispatcher chung điều phối; 5 lượt không có nghĩa chạy 5 request song song.
- Giữ 10 lượt thử/Mac ×4.000 ký tự đã chốt trước đó, độc lập với 5 cuốn combo. Lite/Kitten local vẫn miễn phí.

## Thiết kế ra mắt

Banner xuất hiện ngay khi vào app trong thời gian chương trình: “5 cuốn sách. Một góc nghe riêng.”, giá 50.000đ lớn và CTA xem combo. Theo chỉnh sửa ngày 22/10, banner ngoài bỏ dòng thời hạn; thời hạn mua/dùng vẫn hiện rõ trong popup chi tiết. Popup giải thích trọn giá, 10.000đ/cuốn **khi dùng đủ 5 lượt**, giới hạn một Mac và hạn dùng. Không dùng đồng hồ tự reset, số khách mua hoặc “còn X suất” giả.

Sau khi tiền được xác nhận, popup hiển thị số cuốn thực còn trên Mac. Trong popup Pro, có nút dùng một lượt combo, tách khỏi mua lẻ theo giá thường. Nút cập nhật cuốn đã dùng combo kiểm tra đơn cũ thay vì tạo redemption mới. Mục “Combo trên Mac này” trong Thông tin ứng dụng giữ đường vào kiểm tra đơn cả sau khi banner ưu đãi hết hạn.

Giao diện dùng font hệ thống và CSS/SVG local; khối ưu đãi dùng xanh chủ đạo ở light mode và nền sáng ở dark mode, tách khỏi vùng đọc, có dark/light, reduced motion, increased contrast, nhãn trợ năng và focus. Mở app hoặc hiển thị banner không gọi mạng, không tạo giọng. Chỉ mở popup/nhấn hành động combo mới kiểm tra server; polling 10 giây, tối đa 30 lần khi popup mở và hiển thị. Đóng/ẩn dừng lịch polling; kết quả cũ không mở lại popup.

## Sổ đơn và bảo vệ thanh toán

Migration local `20261022090045_launch_combo_five_books.sql`, chạy sau migration quota 10×4.000:

1. Đơn mua combo nằm trong `wsn_book_orders`, `kind=bundle`, giá server cố định 50.000đ, mã SB riêng, pricing_version `launch-combo-v1`. Không gửi sách khi mua combo. QR hết hạn sau tối đa 10 phút và không vượt thời hạn chương trình.
2. `wsn_launch_quote` khóa Mac, kiểm bí mật Keychain, trả lại quote đang hiệu lực hoặc cùng request key; không tạo nhiều QR còn hiệu lực bằng cách bấm nhiều lần. Không tạo quote mới sau khi Mac có combo đã trả tiền.
3. SePay tiếp tục xác thực webhook và tra giao dịch thật. `wsn_book_confirm` kiểm đúng account, amount, mã đơn và thời điểm tiền vào. Thiếu/thừa/sai account không mở combo. Receipt được ghi một lần trong ledger sẵn có; không tạo một receipt cho mỗi lần dùng lượt.
4. Cùng transaction xác nhận tiền, server tạo `wsn_launch_bundles`: UNIQUE(device_code), UNIQUE(source_order_id), deadline cố định. Mua combo không xếp một job TTS giả vào queue. Retry callback trả duplicate; tiền chuyển thêm cần đối soát, không mở combo thứ hai.
5. `wsn_launch_redemptions`: PRIMARY KEY(bundle_id, slot), slot chỉ 1–5, order_id UNIQUE. `wsn_book_create(..., bundle_book, ...)` khóa Mac + grant, kiểm thời hạn/số lượt, tạo snapshot bất biến và ghi slot trong **cùng transaction**. Đơn sách được tài trợ có amount_vnd=0, funding_bundle_id và paid_at từ combo; không hiện QR riêng để khách trả thêm.
6. Receipt combo tiếp tục bị chặn dùng lại xuyên đơn sách/máy/license cũ bởi ledger/khóa receipt chung. Không thay đổi hay xóa receipt, giấy phép, giá hoặc snapshot cũ. Thông tin tài khoản nhận được khóa trong payload quote combo và dùng lại khi vẽ QR; callback phải khớp tài khoản đã báo giá. Funding của sách nằm trong trigger bất biến, không gán combo cho đơn cũ bằng UPDATE.
7. Hai bảng mới bật RLS, không cấp quyền cho anon/authenticated. Chỉ gateway service-role sau xác thực Mac + bí mật Keychain mới gọi RPC. Thay clock hoặc balance cache trên Mac không thể tạo quyền trong DB. “Một Mac” hiện ràng buộc theo mã Mac + bí mật Keychain đang có, không phải chứng thực phần cứng chống app đã bị sửa; limiter/admission chung vẫn cần chống đăng ký mã giả và mở nhiều máy.

Đơn mua combo là bằng chứng trả tiền; 5 redemption là cách phân bổ quyền đã mua, không phải 5 lần sử dụng lại receipt ngân hàng. Lượt đã gắn vào đơn lỗi được giữ để tiếp tục đúng đơn, không tự trả lại lượt rồi tạo thêm job ngoài sổ. Hoàn tiền/đối soát cần operator như chính sách vận hành; chưa có hoàn tiền ngân hàng tự động. Giao dịch đến quá muộn khiến khách không còn thời gian dùng phải được đối soát, không coi mã chuyển khoản là quyền tạo vô hạn.

## Snapshot và provider

Đơn mới từ catalog HeyGen dùng `pro-cloud-heygen-v1`, audio revision riêng, đúng 7 voice ID hiện tại. Alias lịch sử trong sách local được chuẩn hóa khi tạo **snapshot mới**, không sửa snapshot đã mua. RPC mới vẫn đọc/nhận hợp đồng Modal cũ cho đơn cũ. Worker Modal chỉ claim revision Modal và từ chối chạy đơn HeyGen; không âm thầm đổi giọng/provider cho khách combo.

Dispatcher HeyGen chung, admission 25 request/phút và lưu artifact thật vẫn là công việc kích hoạt riêng trong [kế hoạch công suất](HEYGEN-CAPACITY-PLAN.md). Không mở bán chỉ vì ledger/test giao diện chạy được. Server có thêm flag `WSN_LAUNCH_COMBO_ENABLED=true`, bên cạnh flags books/rights hiện có; mặc định chưa bật. Trước khi bật phải triển khai đồng bộ migration, gateway, app và provider dispatcher/admission đã kiểm chứng.

## Công suất của combo

5 cuốn điển hình ×216.000 ký tự là 1.080.000 ký tự, ít nhất 270 request khi gộp 4.000 ký tự, khoảng 13,5 phút **khối lượng cấp lượt** ở 20 request/phút. 100 Mac dùng đủ cùng kích thước sẽ cần 27.000 request, khoảng 22,5 giờ khối lượng cấp lượt. Chưa gồm latency, tải xuống hoặc retry.

Theo trần 2 triệu ký tự hiện tại, một combo có thể tạo tối đa 10 triệu ký tự, khoảng 2.500 request trước hao hụt đóng gói. Vì vậy giới hạn 5 cuốn ngăn tạo vô hạn trên cùng Mac nhưng **không thay thế limiter và admission toàn hệ thống**. Khi kích hoạt cần ngân sách số combo bán ra/công suất còn lại trước hạn, không bảo đảm mọi người được phục vụ ngay. Không quảng cáo số suất còn lại nếu chưa có inventory thực trên server.

## Trạng thái triển khai

Source, migration, gateway và giao diện được chuẩn bị local. **Chưa áp dụng schema lên Supabase thật, chưa deploy gateway, chưa bật bán combo, chưa tạo TTS hoặc xác nhận giao dịch ngân hàng thật.** Bản build là app phát triển local, không phải bộ cài phát hành.

Kiểm tra bằng core/Edge fixture, PostgreSQL WASM một connection, HTTPS localhost và native WebKit. Bằng chứng nằm trong `.qa/launch-*.log`, `.qa/launch-db-report.json`, `.qa/book-ui/launch-*.png`. Fixture không chứng minh contention đa worker, giao dịch thật hoặc tốc độ HeyGen thật.

### Kết quả QA local ngày 22/10/2026

- 122 test Python core PASS; 19 test Edge/gateway/SePay giả lập PASS.
- PostgreSQL WASM: giá đúng 50.000đ, tài khoản nhận khớp quote, một combo/Mac, retry không nhân lượt, cho đặt đủ 5 cuốn vào queue, chặn cuốn thứ 6, chặn replay xuyên ledger, deadline server và RLS/grants PASS. Chưa kiểm chứng contention nhiều connection.
- HTTPS localhost: snapshot/voice/revision mới, tải lỗi giữ audio hoàn tất, nhận lại đúng take và xuất WAV PASS; không gọi HeyGen.
- Native WebKit: banner màn đầu, popup ở 1180×800 và 1000×720, QR combo 50.000đ quét được, balance 5→4, retry kiểm tra đơn cũ, expiry, dark/light, focus và dừng polling PASS. Popup thử/mua lẻ cũ hồi quy PASS.
- `./scripts/build.sh` PASS; `git diff --check` PASS. Không deploy, không phát hành installer, không thu/chuyển tiền thật hoặc gọi inference trả phí.
