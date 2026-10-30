> Cập nhật 24/10/2026: owner đã duyệt và bật thanh toán sách lẻ Mac qua SePay → queue HeyGen, đồng thời xác nhận quyền thương mại. Các trạng thái paid-deferred bên dưới là lịch sử. Xem [activation và kiểm chứng hiện tại](CLOUD-PAID-DEPLOYMENT.md).

> Triển khai mới nhất 23/10/2026: gateway và worker **đã hoạt động cho test private trên Mac owner**, profile 5/5 và mẫu giọng thật đã nhận thành công. Thanh toán/public rollout vẫn tắt. Các mô tả "chưa deploy" bên dưới là bằng chứng lịch sử trước activation này. Xem [trạng thái triển khai và cách test](CLOUD-TRIAL-DEPLOYMENT.md).

> Chính sách hiện tại: **5 lượt miễn phí trọn đời/thiết bị**, chọn **1 lượt thử** hoặc **tạo chương bằng tối đa 4 lượt**. Xem [chi tiết cập nhật](#nam-luot-mien-phi); các số 10 lượt bên dưới ghi lại các bước triển khai trước.

# Thiết bị độc lập, thanh toán tự động và queue — 23/10/2026

**Quyết định mới nhất của owner:** Mac, PC và Android hoạt động độc lập. Bỏ phương án tài khoản Soundbooki dùng chung vừa được cân nhắc. Không Google/Gmail login, không OAuth/Apple login, không đồng bộ sách hoặc audio. Hồ sơ chỉ là tên hiển thị và trạng thái trên thiết bị; mỗi thiết bị có mã hash và credential riêng.

Voice/model Pro tiếp tục chạy trên cloud. **Audio Pro đã tạo** được nhận về máy, xuất file để người dùng tự chép và phát ở thiết bị khác. Điều này không đưa model/key API về máy và không chuyển quyền tạo/gói còn dư sang máy khác. Không hứa zero storage hay loại trừ trách nhiệm bản quyền: cloud TTS vẫn cần xử lý chữ và trả artifact tạm. Phạm vi hiện tại không xây thư viện cloud hay công cụ công bố sách.

## Luồng trên mỗi thiết bị

1. Mở app → đọc/nghe Lite ngay. Hồ sơ có tên hiển thị, mã thiết bị, trạng thái kết nối, lượt Pro và đường vào combo. Không cần tạo tài khoản app.
2. Chọn chương/giọng → **Tạo Pro cho chương này** → xác nhận số lượt đã tính (1–4). Mỗi lượt **5.000 Unicode code point**, một yêu cầu tối đa **20.000 ký tự**, tổng 10 lượt trọn đời trên thiết bị. Đủ dưới trần thì tạo trọn chương; vượt trần thì báo rõ chỉ tạo phần đầu. Chương ngắn không lấy chữ chương sau; mẫu mở đầu cũ vẫn dùng 1 lượt. Mẫu thử chỉ để nghe.
3. Mua gói/sách theo kênh phân phối. Store sử dụng Apple/Google account của chính hệ thống; Soundbooki không đọc Gmail hoặc lưu mật khẩu store. Không đồng bộ quota/sách giữa Mac, PC và Android.
4. Server xác minh thanh toán, ghi quyền cho **đúng thiết bị mua**, rồi redeem thành order khóa snapshot/giọng/model. Retry nhận cùng đơn, không trừ lượt lần nữa. Đổi tài khoản Google Play/App Store trên cùng máy không cấp thêm 10 lượt hoặc nhân combo. Tài khoản store khác không được dùng lại receipt đã cấp ở thiết bị khác.
5. Đóng app không hủy đơn trên server. Mở lại để nhận những phần đã tạo; lỗi mạng không cần thanh toán lại. Nhận audio, nghe lại, đổi tốc độ/nhạc và xuất file không mua lại.
6. Người dùng tự chép WAV/M4A/MP3 sang máy khác để nghe bằng player. Không tự upload/export web hoặc chuyển file sang thiết bị khác.

## Thiết bị, khôi phục và quyền cũ

- Giữ mã SN + random Keychain credential trên Mac; Android dùng app-scoped Android ID hash + random credential mã hóa Keystore. Không dùng mã máy công khai để xác thực. PC chưa triển khai, cần credential an toàn theo hệ điều hành riêng; không sao chép danh tính Mac.
- Backend là nơi quyết định quota/giá/receipt/order. Cache tên/số dư không tạo quyền; cài lại app hoặc đổi store account không phải một lượt mua mới.
- Một receipt chỉ cấp quyền một lần. Khóa provider+environment+transaction/token; receipt ngân hàng duy nhất xuyên ledger. Khi receipt đã gắn thiết bị A được gửi từ B, trả trạng thái đã dùng/đối soát, không chuyển quyền hoặc cấp lại.
- Khôi phục trên cùng thiết bị dùng credential và ledger đã có. Nếu app bị xóa/mất Keystore/Keychain, không hứa tự khôi phục từ tên hiển thị, mã máy hoặc email; cần luồng chứng minh giao dịch và hỗ trợ an toàn. Không dùng non-consumable product với thông điệp “mua lại trên mỗi thiết bị” khi quy tắc restore của store đòi quyền rộng hơn; chọn và test product type đúng trước phát hành.
- Giữ nguyên mọi snapshot, provider, giá, receipt, order và hạn dùng cũ. Mẫu 4.000 ký tự đang gửi dở giữ request key/body cũ khi nâng quota lên 5.000, không gửi lại body khác. Đơn Modal cũ không tự đổi HeyGen.
- Combo hiện đã chốt trên Mac: một combo 50.000đ/5 cuốn/Mac, mua và redeem trước `2026-11-02T00:00:00+07:00`. Các sản phẩm mới cho Android/PC sẽ hoạt động riêng theo thiết bị; chưa kích hoạt bán hay tự đổi hạn của combo cũ.

## Thanh toán tự động, không cần tài khoản app

| Kênh | Cách mua dự kiến | Căn cứ tự xác nhận |
|---|---|---|
| Mac App Store | StoreKit | Signed transaction được server xác minh đúng app/product/environment |
| Google Play Android | Play Billing | Purchase token được Google Play Developer API xác minh đúng package/product, trạng thái PURCHASED |
| Mac/PC tải trực tiếp | QR/SePay | Giao dịch thật khớp quote, amount, account, mã đơn và thời điểm |
| Microsoft Store nếu chọn sau này | Rà theo loại app/kênh được chọn | Chưa có bản Windows hoặc payment adapter |

StoreKit/Play Billing không yêu cầu xây Gmail login trong Soundbooki. Phương án kênh Việt Nam là IAP chuẩn cho dịch vụ số; không mặc định được miễn theo reader app hoặc ngoại lệ thị trường khác. Luôn hiển thị giá trả từ store/server; chưa hardcode 50.000đ nếu giá store khác. Không subscription tự gia hạn.

**Android QR:** Google Play yêu cầu Play Billing cho chức năng/dịch vụ số mua và dùng trong app. Việt Nam hiện không nằm trong danh sách thị trường của chương trình alternative billing/user-choice được Google công bố; không gắn SePay QR vào bản Play để bán lượt tạo/audio Pro. Bản tải trực tiếp có thể dùng QR/SePay sau khi có offer Android riêng, nhận tiền tự động, kiểm đúng amount/account/transaction rồi cấp quyền idempotent. Ưu đãi 50.000đ/5 cuốn đang chốt cho Mac, không tự áp sang Android. Android đã có phần dựng QR cho đơn sách lẻ khi gateway trả quote `awaiting_payment` cùng bank; gateway/deployment/dispatcher hiện chưa bật nên màn này chưa nhận được quote thanh toán thật. Xem [Payments policy](https://support.google.com/googleplay/android-developer/answer/9858738) và [các thị trường alternative billing](https://support.google.com/googleplay/android-developer/answer/13821247).

Owner chọn hỗ trợ **cả hai kênh Android, tách theo bản phát hành**: Google Play Billing cho app trên Play và QR/SePay cho APK tải trực tiếp. Đây là lựa chọn kiến trúc, chưa phải mở bán. Cần product ID/giá Play Console, backend xác minh purchase token/notifications, offer Android device-bound, cấu hình SePay và gateway, cùng dispatcher HeyGen đã triển khai trước khi bật. Ưu đãi Mac 50.000đ/5 cuốn, quota và receipt cũ giữ nguyên.

Một luồng tự động dùng được khi:

1. **Chuẩn bị:** server tạo purchase intent có UUID, thiết bị, product/offer version, giá/kênh và hạn nếu phù hợp. Lưu intent/request key trước khi mở payment sheet/POST. Bind metadata theo contract được store hỗ trợ; token client gửi không tự chứng minh chủ sở hữu.
2. **Chờ xác nhận:** đóng sheet, app bị tắt hoặc mạng mất không tạo receipt thứ hai. Store PENDING, QR chưa có tiền, thiếu/thừa/sai tài khoản đều chưa cấp gói. Hiển thị chờ hoặc đối soát, không thông báo thất bại rồi thúc khách mua lại.
3. **Xác minh:** server kiểm chữ ký hoặc hỏi API ngân hàng/store thật. Cùng transaction khóa intent+device+receipt, ghi receipt duy nhất, tạo grant đúng một lần. Client callback, notification hoặc retry chỉ là đường đến cùng hàm cấp quyền. Không lấy ảnh chuyển khoản/payment code làm bằng chứng.
4. **Báo đã xử lý:** sau ghi ledger thành công, backend acknowledge/consume Google theo đúng product type; StoreKit finish sau khi quyền đã được giao bền vững. Nếu ack/finish lỗi, retry ack/finish, không cấp thêm gói. Server notification có xác minh và idempotency để xử lý khi app đang đóng; không phụ thuộc polling của app để nhận tiền.
5. **Tạo sách:** mua combo tạo grant, không xếp TTS giả. Redeem dưới khóa grant: kiểm số lượt/deadline/capacity, tạo snapshot và slot **trong cùng transaction**. Chỉ một job cho cùng request/snapshot. Đơn sách lẻ có snapshot khóa trước thanh toán; trả tiền không đồng nghĩa audio sẵn sàng.
6. **Nhận lại/hoàn tiền:** hồ sơ trên máy xem đơn đã mua và tiếp tục nhận. Refund/revoke notification không được nhân receipt hoặc âm số dư; phân biệt lượt chưa dùng, order đang chạy và audio đã tải. Hoàn tiền thật phải được provider/ngân hàng xác nhận. Không thể thu hồi file người dùng đã xuất.

Store account đổi giữa lúc mua đang pending: đối chiếu intent/transaction và credential ban đầu, không grant vào ý định mua mới. Restore/replay cùng giao dịch không bán/cấp thêm lần nữa. Nếu mất binding thì đưa đối soát, không “tìm theo email” để chuyển quyền tự động. Test cả hai tài khoản store trên một máy và một tài khoản store trên hai máy trước phát hành.

**Xung đột store chưa giải quyết:** Apple không cho credit mua IAP hết hạn, trong khi combo Mac trực tiếp buộc redeem trước 02/11. Không đưa nguyên combo này lên StoreKit. Đề xuất product store phiên bản riêng: thời hạn chỉ giới hạn giá ưu đãi lúc mua, 5 quyền đã mua không hết hạn; phương án này cần owner chốt trước khi mở bán. Giữ deadline/receipt combo cũ. Product IDs, giá store, retention/refund mới và scope deploy chưa được chốt.

## Lưu trữ tối thiểu để giao audio

Không có thư viện cloud/sync. Chỉ giữ snapshot cần cho inference/khôi phục đơn, artifact để giao lại có thời hạn và metadata thanh toán/tiến độ. Khách tải file về máy và tự quản lý. Cần công bố retention trên quote trước mua; đề xuất ban đầu 30 ngày sau hoàn tất còn cần chốt, **chưa có job xóa tự động**. Sau hết retention vẫn giữ đủ ledger để chống replay/hỗ trợ; không hứa tái tạo TTS miễn phí vô thời hạn. Không xóa dữ liệu cũ trong lần sửa này, không lập máy chủ công bố sách. Thiết kế local giảm phạm vi lưu trữ nhưng không tự chứng minh nội dung có quyền sử dụng.

## HeyGen: kết quả rà source và hướng chạy chung

- Đã có catalog `pro-cloud-heygen-v1`, ledger đơn/snapshot, phân quyền device-secret, xác nhận tiền, quota và claim RPC. Operator Modal chỉ nhận revision Modal. **Chưa có dispatcher HeyGen production**, chưa có limiter dùng chung cho tài khoản HeyGen, fairness nhiều người hoặc load test nhiều connection.
- Script demo `cloud/heygen_studio/synthesize_book_heygen.py` nghỉ 2,4 giây mỗi vòng, chỉ giới hạn một process. Nhiều process có thể vượt tổng RPM. Không lấy script này làm queue dịch vụ.
- GET `/v3/users/me` chỉ đọc đã trả HTTP 200 ngày 23/10/2026; không gọi TTS. Phản hồi không cung cấp trường quota/RPM được xác minh trong bộ trường lọc, nên không dùng kết quả này để xác nhận 30 RPM hoặc thời hạn model miễn phí. Input 30 RPM và model free trước đây vẫn cần đối chiếu dashboard/contract tài khoản.
- Source demo dùng `/v3/models/audio/tts`; tài liệu tham khảo chính chủ trên repo HeyGen archived liệt kê `/v3/voices/speech`. Không tự thay endpoint/model hay đoán hai contract tương đương. Cần xác minh schema/response, voice IDs, mã lỗi, idempotency và giá đúng endpoint model hiện dùng trong bước activation. Không chạy inference thật trong lần rà này.

Dispatcher đề xuất, tiếp tục [HEYGEN-CAPACITY-PLAN.md](HEYGEN-CAPACITY-PLAN.md):

1. Chỉ server nhận chữ đã consent; không đưa key provider vào app. Khóa quote/trial/redeem và admission trong database. Không thu tiền cho việc đã biết không thể nhận.
2. Một limiter phân tán cho cả API key/workspace, khởi điểm **25 request/60 giây** theo cửa sổ trượt, không phải mỗi worker. Tổng cả trial/book/retry đều dùng limiter; 30 RPM là đầu vào chưa xác minh. Giữ chunk vận hành 4.000 để còn biên cho payload; một mẫu 5.000 có thể cần hai request. Đừng nhầm 5.000 ký tự/lượt app với một request provider.
3. Chia lượt round-robin theo thiết bị, mỗi vòng một chunk, tránh một sách 2 triệu ký tự chiếm toàn bộ hàng. Có trọng số trial/book (ví dụ 5 RPM trial / 20 RPM paid, cho mượn phần rỗi) nhưng không để một bên chết đói. Admission chặn backlog theo deadline/ngân sách thực; không quảng cáo slot giả.
4. Claim có lease, heartbeat/fencing token. Khóa idempotency theo order+segment+snapshot+model. Trước gửi lưu trạng thái dispatch. Worker chết sau gửi nhưng chưa nhận kết quả → `unknown` để đối soát, không tự gửi lại sau timeout. Chỉ retry lỗi được chứng minh chưa nhận upstream; 429 dùng Retry-After+jitter và cooldown **chung**. Không hứa exactly-once upstream nếu provider không bảo đảm.
5. Xác minh WAV/hash → artifact nguyên tử → commit segment → cập nhật tiến độ. Crash sau upload trước commit tiếp tục từ artifact, không TTS lại. Phần xong luôn được giữ. Chỉ đóng đơn ready khi đủ segment của snapshot. Đổi text/voice tạo snapshot khác; player speed/nhạc không đổi cache.
6. App chỉ xem gateway, không poll HeyGen. Counter và trạng thái nhẹ; download cursor độc lập. Poll bounded khi popup mở, foreground; dừng khi đóng/ẩn. Thông báo đẩy chỉ thêm khi có phạm vi được duyệt; không thêm silent polling/analytics nền.

Với chunk 4.000, 10 mẫu ×5.000 cần tối thiểu 20 request/thiết bị; 100 thiết bị dùng đủ cần 2.000 request: 80 phút khối lượng ở 25 RPM, hoặc 400 phút ở phần trial riêng 5 RPM. Đây là ngân sách cấp lượt lạc quan, **không phải thời gian khách phải chờ/ETA**; chưa tính latency, retry và packing. Một sách 216.000 ký tự cần tối thiểu 54 request; 100 sách là 5.400 request, 270 phút ở 20 RPM. Concurrency chỉ chốt sau đo p95 thật; không thể hứa đáp ứng tức thì từ RPM.


## Công suất khi mỗi thiết bị mua riêng

100 thiết bị mua và dùng đủ combo, mỗi cuốn 216.000 ký tự: 500 cuốn ×54 request = **27.000 request** tối thiểu. Phần paid 20 RPM cần **22 giờ 30 phút khối lượng cấp lượt**, chưa tính latency/retry/tải file; không phải ETA từng khách. Cho phép đặt đủ 5 cuốn, nhưng chia lượt từng chunk giữa thiết bị, không chạy trọn một combo rồi mới phục vụ thiết bị sau.

Ở trần đã công bố 2 triệu ký tự/cuốn, một combo có thể cần 2.500 request; 100 combo là 250.000 request, **208 giờ 20 phút** ở 20 RPM. Phải tính admission theo ký tự/request-budget thực của snapshot, không theo số đơn hoặc số trang. Không tự hạ giới hạn sách đã bán; khi quá capacity thì dừng quote mới trước thanh toán và thông báo chờ, không thu tiền rồi hứa xử lý ngay. Giá 50.000đ không thay thế giới hạn admission toàn dịch vụ.

## Trạng thái và kiểm chứng

Đã có Hồ sơ local, đường vào combo, sample theo chương, cap 10×5.000 và endpoint đọc quota. SQL bổ sung `commerce/manual/trial-10x5000.sql` phải áp dụng sau schema combo; **chưa áp dụng live**. Phần quota/đơn hiện vẫn theo thiết bị. Không cần gỡ OAuth hay sync runtime vì các phần đó chưa từng được thêm.

127 core tests, 11 gateway tests, PGlite một connection và HTTPS localhost đã qua. UI Mac và 3 Android emulator tests đã qua; fixture không chứng minh giao dịch store/ngân hàng, tốc độ HeyGen thật, contention nhiều worker hoặc máy vật lý.

Còn cần StoreKit/Play products và server credentials/notifications, kiểm thử sandbox payment/refund/replay, admission và dispatcher HeyGen phân tán, xác minh contract/giá/quota provider, retention và phạm vi vận hành trước mở bán. Không deploy hoặc inference thật trong lượt này. Hồ sơ và nút combo không phải bằng chứng thanh toán đã kích hoạt.

Supabase CLI help bị automatic approval review từ chối vì tự ghi telemetry ngoài dự án; không chạy vòng tránh. SQL được giữ trong dự án để review/QA local, chưa tạo migration CLI hay áp database thật.

Nguồn rà ngày 23/10/2026: [Apple payments](https://developer.apple.com/app-store/review/guidelines/), [Google Play Payments](https://support.google.com/googleplay/android-developer/answer/9858738), [Play Billing integration](https://developer.android.com/google/play/billing/integrate), [HeyGen reference repo (archived)](https://github.com/heygen-com/heygen-stack/blob/main/references/api-reference.md).


<a id="gom-luot-pro-theo-chuong"></a>
## Gộp lượt Pro theo chương — owner cập nhật 23/10/2026

Tổng quota vẫn là 10 lượt trọn đời cho mỗi thiết bị, 5.000 Unicode code point/lượt. Với một chương đã chọn, app tự tính `min(4, ceil(số ký tự của chương / 5.000))` và hiện số lượt/voice/chương trong xác nhận trước khi gửi. Chương 12.000 ký tự dùng 3 lượt để tạo trọn chương; chương 24.000 ký tự chỉ tạo 20.000 ký tự đầu với 4 lượt và báo rõ chưa đủ chương. Không tự chạy vòng tiếp hoặc tiêu lượt thứ 5. Không lấy chữ chương sau để lấp phần còn dư. Thiếu quota thì không gửi yêu cầu mới, không âm số dư và không hạ lượng chữ mà không báo. Mẫu hoàn thành vẫn lưu riêng để nghe; thay đổi này không mở bán hoặc thay quyền xuất của đơn cũ.

Mac truyền chapter ID, groupTrial để tính thông tin xác nhận và trialUnits khi bấm tạo. Android dùng cùng giới hạn và thêm xác nhận số lượt trước khi submit. Snapshot gộp có trialUnits; bản 1 lượt cũ không bị nhận nhầm là đã tạo đủ một chương dài. Pending/retry cùng request key giữ nguyên body; status/download và nhận lại mẫu không tiêu thêm lượt. Nội dung/voice đổi là snapshot khác. Các mẫu 500/4.000/5.000 ký tự trước đây vẫn giữ payload/hash, chi phí lịch sử 1 lượt và số đã dùng; không reset quota.

Gateway mới có POST `trial-group` riêng cho 2–4 lượt và RPC `wsn_book_create_group` riêng. Nếu server/database chưa nâng cấp, yêu cầu bị từ chối thay vì lùi về endpoint cũ, cắt còn 5.000 rồi báo đã tạo đủ. SQL nháp `commerce/manual/trial-group-up-to-four.sql` áp sau `trial-10x5000.sql`: backfill trial_units=1 cho trial cũ mà không sửa payload/hash/counter, thêm cost bất biến, cost server tính từ chữ đã khóa, `trials_used + cost <= 10` và ghi order/counter trong cùng transaction dưới khóa device. Idempotency check diễn ra trước trừ lượt. Chỉ service_role gọi RPC; RLS/grants/receipt/đơn trả tiền được giữ. SQL nháp chưa áp live, không deploy hoặc inference provider trong lượt sửa này.

Queue xử lý một order gộp với tối đa 20.000 ký tự; vẫn phân chunk tối đa 4.000 theo kế hoạch vận hành, dùng cùng account-wide limiter và fairness giữa thiết bị. Không coi 4 lượt app là 4 request HeyGen: 20.000 ký tự cần ít nhất 5 request ở chunk 4.000, có thể nhiều hơn theo partition/retry. Tổng miễn phí tối đa vẫn 50.000 ký tự/thiết bị nếu dùng đủ 10 lượt; gộp không tăng tổng hoặc cho phép request provider 20.000 ký tự.

<a id="nam-luot-mien-phi"></a>
## Năm lượt miễn phí và lựa chọn rõ ràng — cập nhật tiếp 23/10/2026

Mặc định chọn **Tạo thử · 1 lượt**, tối đa 5.000 Unicode code point trong chương đã chọn. Người dùng có thể chọn **Tạo chương · Tối đa 4 lượt**: chi phí thực `min(4, ceil(số ký tự chương/5.000))`. Chương 12.000 ký tự dùng 3 lượt; chương trên 20.000 ký tự chỉ tạo 20.000 ký tự đầu và báo rõ chưa hết chương. Đổi lựa chọn chỉ xem lại thông tin, không gửi đơn; dữ liệu, request key và polling cũ được tách khỏi lựa chọn mới. Cần xác nhận trước khi tạo. Giữ nguyên nội dung gốc, voice snapshot và thành viên segment của chương.

Tổng trọn đời giảm từ 10 xuống **5**; giữ nguyên `trials_used`. Đã dùng 3 còn 2; đã dùng từ 5 trở lên còn 0, kể cả thiết bị cũ dùng 6–10. Không thêm CHECK `trials_used <= 5`, không chỉnh hoặc xóa lịch sử. Request key cũ khớp hash được trả lại trước kiểm tra quota, không trừ thêm. Cache Mac/Android suy ra số đã dùng từ limit và remaining lịch sử để hiển thị theo cap 5.

Áp nháp `commerce/manual/trial-five-unit-policy.sql` **sau** `trial-group-up-to-four.sql`. Cả `trial` và `trial-group` của gateway mới gọi RPC `wsn_book_create_trial_v2`, từ chối nếu database chưa có bản nâng cấp; không fallback về quota 10. Database tính debit và khóa counter/order trong cùng transaction, chỉ service_role được gọi RPC. Luồng sách trả tiền, receipt và combo Mac không đổi. Đây là mã/SQL local, chưa triển khai hoặc kích hoạt dịch vụ thật.

Tổng miễn phí tối đa là 25.000 ký tự/thiết bị. App units và số request provider là hai đại lượng khác nhau: một chương 20.000 ký tự vẫn cần ít nhất 5 chunk provider ở mức 4.000 ký tự. Dispatcher và limiter cho toàn tài khoản HeyGen vẫn là điều kiện kích hoạt riêng.
