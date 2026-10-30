> Triển khai mới nhất 23/10/2026: gateway và worker **đã hoạt động cho test private trên Mac owner**, profile 5/5 và mẫu giọng thật đã nhận thành công. Thanh toán/public rollout vẫn tắt. Các mô tả "chưa deploy" bên dưới là bằng chứng lịch sử trước activation này. Xem [trạng thái triển khai và cách test](CLOUD-TRIAL-DEPLOYMENT.md).

> Quyết định mới nhất 23/10/2026: **5 lượt miễn phí trọn đời/thiết bị**, không reset lượt đã dùng. Mặc định **Tạo thử · 1 lượt** (5.000 ký tự); người dùng có thể chọn **Tạo chương · Tối đa 4 lượt** (20.000 ký tự), app hiển thị số lượt thực tế trước khi xác nhận. SQL mới `commerce/manual/trial-five-unit-policy.sql` áp sau bản gộp; chưa áp live. Các mô tả 10 lượt bên dưới là lịch sử, được thay thế bởi quyết định này. Xem [chính sách hiện tại](DEVICE-PAYMENTS-AND-QUEUE.md#nam-luot-mien-phi).

> Cập nhật mới 23/10/2026: một chương được gộp **tối đa 4 lượt Pro miễn phí**, mỗi lượt 5.000 Unicode code point; một yêu cầu tối đa **20.000 ký tự**, chi phí `ceil(số ký tự thực/5.000)`. Tổng trọn đời vẫn **10 lượt/thiết bị**, giữ số đã dùng. Xem [luồng thiết bị và quota gộp](DEVICE-PAYMENTS-AND-QUEUE.md#gom-luot-pro-theo-chuong). Gateway/dispatcher vẫn chưa triển khai; SQL gộp mới ở `commerce/manual/trial-group-up-to-four.sql` chưa áp dụng live.

> Cập nhật 23/10/2026: quota mới **10 × 5.000 ký tự**, bảo toàn lượt đã dùng; đã có Hồ sơ local và mẫu theo chương. Owner chốt các thiết bị độc lập, không đăng nhập/sync; IAP và dispatcher chưa kích hoạt. SQL quota bổ sung ở `commerce/manual/trial-10x5000.sql`, chưa áp dụng live. Xem [thiết kế thanh toán theo thiết bị và kết quả rà queue](DEVICE-PAYMENTS-AND-QUEUE.md). Các số 4.000/bằng chứng bên dưới ghi lại trạng thái trước cập nhật này; chunk provider đề xuất vẫn 4.000.

# HeyGen: công suất, queue và thanh toán — 22/10/2026

## Quyết định và phạm vi

Owner xác nhận: **10 lượt miễn phí trọn đời/Mac; mỗi lượt tối đa 4.000 ký tự**, không phải 10 sách không giới hạn. Giữ số lượt đã dùng; trước đây dùng 3 lượt thì còn 7. Lite/Kitten local vẫn miễn phí. Không bán credit hoặc gói năm mới.

Thông tin owner cung cấp cho tài khoản HeyGen: **30 request/phút, tối đa 5.000 ký tự/request, ưu đãi miễn phí đến hết 30/11/2026**. Đây là đầu vào vận hành cho tài khoản này; chưa xác minh dashboard, timezone kết thúc, giới hạn đồng thời, hạn mức ngày hoặc quyền áp dụng trên endpoint đang dùng. Không hiểu 5.000 là tổng quota tài khoản. Không suy ra có thể phục vụ vô hạn người dùng từ một giới hạn/phút.

Đã sửa source local của quota, cache hiển thị, gateway và chuẩn bị migration `20261022083604_book_trial_10x4000.sql`. **Chưa áp dụng migration lên database thật, chưa deploy gateway, chưa kích hoạt worker HeyGen nhiều người dùng, chưa nhận tiền/chạy request tạo giọng thật.** Phần queue phân tán, bảng và RPC bổ sung bên dưới là thiết kế triển khai, chưa phải chức năng đã chạy.

Luồng commerce hiện có dùng `pro-cloud-modal-v1` và worker owner `commerce/books-admin.py` gọi Modal. Catalog local đã dùng ID HeyGen; migration combo mới chuẩn bị thêm hợp đồng snapshot HeyGen riêng, còn RPC trên database thật chưa được nâng cấp vẫn chỉ nhận alias sáu giọng Modal. Không thể chỉ đổi URL rồi tuyên bố HeyGen đã tích hợp; cần provider snapshot/version riêng và kiểm chứng mapping bảy giọng. Đơn Modal cũ giữ nguyên nội dung, giọng, model và nơi nhận lại audio.

## 1. Tính công suất

Đề xuất trần vận hành **25 attempt/phút/tài khoản**, tối thiểu 2,4 giây giữa hai lần dispatch, không burst/catch-up. Còn 5 request/phút làm biên an toàn so với mức owner cung cấp; mọi retry vẫn tiêu thụ trong 25. Tất cả key/workspace/CLI dùng chung quota phải qua một limiter; không coi thêm key, worker hoặc Mac là thêm công suất.

Gộp văn bản đến khoảng 4.000 ký tự/request, ưu tiên ranh giới câu/đoạn và không vượt chương đã xác minh. Cận 5.000 chỉ là hard limit; không cố lấp đầy bằng cách nối nhiều sách/giọng. Các đoạn editor 500–2.000 ký tự không nên mặc định thành từng request HeyGen. Lưu mapping offset về segment/chương gốc. Chữ gửi đi chia nguyên văn; originalText, dấu tiếng Việt, khoảng trắng và nguồn đã sửa không bị ghi đè. Nếu một câu quá dài thì cắt theo offset, không viết lại. Lưu tổng Unicode code point để báo giá; kiểm thêm đơn vị độ dài endpoint thực sự dùng, tránh chuỗi emoji vượt giới hạn UTF-16. Các con số dưới đây giả định đóng gói lý tưởng; số chunk thực tế có thể cao hơn.

| Nội dung/một giọng | Request tối thiểu ở 4.000 ký tự | Ngân sách cấp lượt ở 25/phút |
|---|---:|---:|
| 4.000 ký tự | 1 | 2,4 giây |
| 27.000 ký tự | 7 | 16,8 giây |
| 54.000 ký tự | 14 | 33,6 giây |
| 108.000 ký tự | 27 | 64,8 giây |
| 216.000 ký tự, khoảng 4 giờ audio | 54 | 2,16 phút |
| 300.000 ký tự | 75 | 3 phút |

Đây là **khối lượng công việc chia tốc độ cấp lượt**, không phải thời gian hoàn thành. Request đầu có thể gửi ngay; request cuối còn phải xử lý và tải xuống. Chưa đo tốc độ HeyGen 4.000 ký tự trên tài khoản này.

| Người cùng sử dụng | Số lượt/người | Request | Ngân sách ở 25/phút nếu chỉ có miễn phí |
|---|---:|---:|---:|
| 10 | 1 | 10 | 24 giây |
| 100 | 1 | 100 | 4 phút |
| 100 | 10 | 1.000 | 40 phút |
| 1.000 | 1 | 1.000 | 40 phút |
| 1.000 | 10 | 10.000 | 400 phút, khoảng 6 giờ 40 |

Mỗi Mac có tối đa 40.000 ký tự miễn phí, khoảng 44 phút audio theo hệ số cũ 900 ký tự/phút. 100 khách dùng đủ là 4 triệu ký tự. Một lượt 100 ký tự vẫn dùng một request nếu không có cache, nên chỉ nhìn ký tự sẽ đánh giá thiếu tải. Bảng trên là tổng nhu cầu, không có nghĩa admission sẽ nhận toàn bộ đồng thời.

Tốc độ thực dụng: `R = min(25, 60 × concurrency / latency_trung_bình)` attempt/phút. Khởi đầu concurrency 4; chỉ tăng đến 6 nếu endpoint cho phép và số đo cho thấy ổn định. Không suy ra concurrency từ RPM. Ví dụ với concurrency 6:

| Thời gian xử lý/request (giả định) | Trần thực dụng | 54 request chưa retry | Cộng 10% request retry |
|---|---:|---:|---:|
| 10 giây | 25/phút | 2,16 phút | 2,376 phút |
| 20 giây | 18/phút | 3 phút | 3,3 phút |
| 30 giây | 12/phút | 4,5 phút | 4,95 phút |

Không đặt SLA từ bảng này. Khi vận hành dùng latency và throughput đo được theo cỡ chunk; ETA hiển thị khoảng, kèm trạng thái upstream. Công cụ tính offline: `.runtime/bin/python commerce/heygen_capacity.py`; ví dụ 10 sách 216.000 ký tự, phần đơn trả tiền 20/phút: thêm `--characters 216000 --books 10 --rpm 20`. Kết quả mặc định lưu ở `.qa/heygen-capacity.json`.

## 2. Queue phục vụ nhiều người

`App → gateway xác thực Mac → transaction tạo snapshot/giữ lượt → Postgres queue → dispatcher chung → HeyGen → private object storage → app nhận từng phần`.

Gateway trả `202` và order/job ID sau khi commit. Đóng app hoặc timeout không làm mất job. Client lưu idempotency key trước khi gửi; retry cùng key + cùng payload trả đúng job; payload khác phải báo conflict. Mở popup, chọn giọng hoặc nghe mẫu thu sẵn không gọi HeyGen. App không giữ HeyGen/SePay/service-role key.

1. **Hai lớp lịch, một giới hạn chung:** khi cả hai đều có việc, mặc định 4 slot đơn trả tiền : 1 slot miễn phí, tương đương 20 : 5 request/phút khi thực đạt 25. Lớp trống cho lớp kia mượn slot; không cộng vượt tổng. Retry tiêu thụ slot của chính lớp đó. Có lượt miễn phí trong mỗi vòng để không bị bỏ đói.
2. Trong mỗi lớp, xoay vòng theo **Mac**, rồi theo sách của Mac; mỗi lượt chỉ một chunk. Một máy không tăng ưu tiên bằng cách tạo nhiều đơn. Tối đa một trial chưa kết thúc/Mac và một chunk HeyGen đang chạy/Mac; mặc định tối đa hai đơn sách đang chờ/Mac. Chunk đầu sách có cơ hội sớm, sách dài quay lại cuối vòng. Đoạn hoàn tất có thể tải/nghe tiếp theo thứ tự.
3. Limiter nằm trong DB, khóa một hàng `provider_account`, dùng đồng hồ DB và cửa sổ trượt 60 giây, cộng kiểm `next_dispatch_at` và `cooldown_until`. Không dùng token bucket có burst 25 hoặc limiter trong RAM của từng worker. Không cấp trước hàng loạt permit; dispatcher xin permit sát lúc gửi. Permit bị bỏ lỡ tính là đã dùng, không hoàn lại để burst.
4. Claim chunk bằng `FOR UPDATE SKIP LOCKED`, `lease_token`, `lease_expires_at`, heartbeat 15 giây, lease khởi đầu 120 giây và gia hạn khi tải audio. Chỉ token hiện hành được ghi kết quả; không giữ transaction DB mở lúc gọi HeyGen. Hết lease trước khi gửi thì được claim lại; đã có dấu dispatch mà chưa rõ kết quả thì vào đối soát, không tự coi là chưa chạy.
5. Worker tải audio, kiểm decode/thời lượng/hash rồi ghi object; transaction gắn artifact và đánh dấu chunk xong. Object đã có cùng hash thì dùng lại. Upload/download/RPC lỗi chỉ tiếp tục lưu/tải; không tạo TTS lại. Chỉ đủ chunk đúng manifest mới ghi sách `ready`; giữ từng phần hoàn tất khi hủy/lỗi.
6. Cache key gồm hash text chính xác + provider + voice ID + model/revision + ngôn ngữ + boost/tham số synthesis + phiên bản xử lý âm thanh. Player speed/nhạc không nằm trong narration key. Cache thử và sách mua có manifest riêng; không cho khách khác truy cập artifact chỉ vì đoán được hash. Retry/cùng nội dung đã có audio không phát sinh thêm lượt. Giữ cache trong phạm vi Mac trước khi có chính sách dùng chung dữ liệu.

**Admission trước thanh toán:** khởi điểm trần 300 request-equivalent còn phải xử lý, tính cả quote giữ chỗ, đơn đã trả và trial đã nhận; không đếm số sách vì sách dài ngắn khác nhau. Dùng kế hoạch chunk thực tế, không dùng `ceil(chars/4000)` để bán suất. Trần quote thêm: ETA dự kiến không quá 20 phút, tính từ throughput bảo thủ đo được và phần chia lịch. Nếu chưa có số đo hoặc circuit đang mở thì dừng quote thanh toán. Sách vượt trần nhận đơn cần đợi queue rỗng hơn hoặc xử lý theo phạm vi đã được người dùng chọn; không nhận tiền rồi tự chia thành nhiều đơn mới.

Quote giữ chỗ và giá có TTL 10 phút; mỗi Mac chỉ một quote giữ chỗ đang hiệu lực. Tạo quote mới phải nguyên tử bỏ/chuyển hold cũ, không giữ chồng suất. Ngân sách còn lại giảm khi chunk hoàn tất; quote hết hạn giải phóng suất chưa trả tiền. Trial chỉ giữ lượt khi admission thành công, queue đầy không mất lượt. Rate limit đầu gateway theo Mac và giới hạn đăng ký mới/IP có xét nhiều máy chung mạng; Keychain không phải hardware attestation, không hứa chống sửa app tuyệt đối.

Ở mức 20 request/phút dành cho trả tiền, 10 cuốn 216.000 ký tự cần ít nhất 27 phút khối lượng cấp lượt; 100 cuốn cần 270 phút. Queue 300 sẽ không nhận cả batch 540 request. Một tài khoản 30 RPM phù hợp ra mắt có giới hạn; để nhiều trăm khách cùng tạo cả sách cần nâng quota qua nhà cung cấp hoặc thêm provider được duyệt, đồng thời công khai thời gian chờ.

## 3. Lỗi quá tải và phục hồi

| Kết quả HeyGen | Hành vi cần có |
|---|---|
| 429 có mã rate-limit rõ ràng | Ghi trạng thái và provider request ID; đặt cooldown **chung** theo Retry-After (hỗ trợ giây hoặc HTTP date). Không gọi lại trước mốc đó. |
| 429 không có Retry-After | Backoff khởi điểm 5, 10, 20, 40, 80 giây, thêm jitter; cooldown chung. Tối đa 5 lần gửi lại an toàn trong 10 phút/chunk rồi chuyển chờ hỗ trợ. Không reset attempts bằng job mới. |
| 503 / 5xx | Mặc định kết quả chưa rõ nếu đã gửi POST. Chỉ tự retry khi hợp đồng endpoint đảm bảo chưa nhận việc hoặc có idempotency đã kiểm chứng. Retry-After chỉ cho biết lúc được thử lại, không chứng minh POST chưa chạy. |
| Timeout/reset sau khi gửi, body lỗi hoặc thiếu audio_url | `reconciling`; giữ request fingerprint, provider ID và dấu gửi. Tra kết quả cũ hoặc phát lại cùng provider idempotency key trong thời hạn được hỗ trợ. Không tự POST mới. |
| Đã có audio_url, tải file lỗi | Lưu URL/response trước khi tải; retry tải riêng, không tạo TTS lần nữa. URL hết hạn thì tra artifact cũ nếu endpoint hỗ trợ, nếu không cần đối soát. |
| 400 / 413 / 422 | Lỗi payload/cỡ chunk/voice: dừng chunk, sửa kế hoạch có kiểm soát; không retry mù. Không thay snapshot đơn đã thu tiền. |
| 401 / 403 / hết ưu đãi hoặc quota | Khóa nhận quote/trial mới cho provider; giữ đơn/audio đã có; hiển thị cần kiểm tra cấu hình. Không chuyển model trả phí. |

Sau 3 lần rate-limit liên tiếp hoặc tỷ lệ lỗi >20% trong ít nhất 20 dispatch/60 giây: circuit mở 60 giây hoặc lâu hơn nếu Retry-After yêu cầu. Half-open chỉ gửi **một chunk thật đang chờ hợp lệ**, không tạo mẫu vô ích để probe. Thành công tăng dần 10 → 15 → 20 → 25 RPM, mỗi mức ít nhất 60 giây ổn định; 429 lại giảm tốc và nghỉ chung. Chỉ log kỹ thuật tối thiểu không chứa sách, khóa hoặc signed URL. Không thêm analytics khách hàng.

HeyGen công bố convention Idempotency-Key 24 giờ, nhưng bài hướng dẫn dẫn endpoint `/v3/voices/speech`, trong khi script hiện gọi `/v3/models/audio/tts`. Phải xác minh khả năng này trên **đúng endpoint/model free** trước khi bật retry POST tự động. Trước khi xác minh, timeout/5xx đã gửi tiếp tục vào đối soát. Idempotency của app/DB không tự tạo ra exactly-once ở nhà cung cấp.

## 4. Database

Dùng Postgres/Supabase và Storage private đang có, khởi đầu chưa cần thêm Redis. Queue custom cần lease, công bằng, admission và lịch provider; chỉ đổi sang pgmq không tự giải quyết những phần này. Không chạy cả sách trong Edge Function hoặc trong HTTP của app; [Edge Functions có giới hạn thời gian chạy](https://supabase.com/docs/guides/functions/limits), worker phải độc lập và tiếp tục từ DB.

| Bảng | Dữ liệu/khóa cần có |
|---|---|
| `wsn_book_devices` (giữ) | Mac hash/code + hash bí mật Keychain, không email. `trials_used` cũ giữ nguyên khi nâng 3 → 10. |
| `wsn_book_orders` (giữ, bổ sung) | Snapshot bất biến: chữ/phạm vi/voice/provider/model/settings, character_count, giá VND nguyên, pricing_version; tách `payment_status` khỏi `generation_status`. Giữ đơn Modal cũ, không rewrite trigger lịch sử. |
| `wsn_generation_jobs` (mới) | UNIQUE(order_id), class trial/paid, device, state, remaining_requests, fair-turn position, deadline, created/updated_at. Job không tự xác nhận thanh toán. |
| `wsn_generation_chunks` (mới) | UNIQUE(job_id, ordinal), source offset/segment membership, text hash/cache key, state, not_before, attempts, lease/token/expiry, artifact_id. |
| `wsn_generation_attempts` (mới) | UNIQUE(chunk_id, attempt_no), provider idempotency/request ID, prepared/dispatched/result_unknown/complete/rejected, status code, timestamps; một lần dispatch có audit bền vững. Không lưu key hay response chứa signed URL vào log. |
| `wsn_provider_accounts` (mới) | Row cho quota scope, hard 30/planned25, next_dispatch_at, cooldown, circuit, concurrency limit, campaign cutoff; chỉ định danh secret, không chứa merchant key ở client. |
| `wsn_provider_dispatches` (mới) | account_id, attempt_id UNIQUE, dispatched_at; index(account_id, dispatched_at) cho cửa sổ 60 giây; prune theo retention vận hành, không xóa audit đơn. |
| `wsn_capacity_holds` (mới) | Quote/job, request-equivalent còn giữ, TTL, committed/released; giữ suất + tính giá cùng transaction. Không tự bỏ hold của đơn đã trả tiền vì hết TTL quote. |
| `wsn_trial_reservations` (mới) | UNIQUE(device, request_key), order_id UNIQUE, reserved/consumed/released. Khi chuyển sang ledger: seed `used_before_ledger=trials_used` một lần, không reset; kiểm `used_before + consumed + reserved <=10` dưới khóa hàng Mac. |
| `wsn_audio_artifacts` (mới) | Cache key + object path + SHA-256 + duration + codec/revision, entitlement chủ sở hữu, retention_until. Object audio ở Storage, không base64/bytea trong DB. |
| `wsn_book_receipts` + ledger giấy phép (giữ) | Receipt đối chiếu ngân hàng, số tiền, đơn và thời điểm. Khóa chung `(bank_account, transaction_id)` trên tất cả sổ; tiếp tục chặn tái sử dụng xuyên sổ. |
| `wsn_refunds` (mới) | UNIQUE(receipt_id), số tiền, lý do, pending/approved/sent/verified; transaction hoàn tiền duy nhất. Đề xuất ban đầu operator chuyển khoản/đối soát, chưa tự gọi ngân hàng. |

Index chính: chunks `(not_before, job_id, ordinal) WHERE state IN ('queued','retry_wait')`; `(lease_expires_at) WHERE state='inflight'`; jobs `(class,device_code,fair_turn,id) WHERE state='queued'`; order history `(device_code,created_at DESC,id)`; holds `(expires_at) WHERE state='reserved'`. Không append/rewrite toàn bộ JSON results của cả sách sau mỗi chunk khi scale; manifest dựng từ bảng chunk và phân trang.

RPC dự kiến: `quote_and_hold`, `reserve_trial`, `accept_verified_receipt_and_enqueue`, `claim_chunk`, `grant_provider_dispatch`, `complete_chunk`, `schedule_retry`, `reconcile_attempt`, `cancel_and_release`, `request_refund`. Mỗi RPC tự kiểm quyền và transition, trả idempotent. Khóa theo thứ tự cố định provider/capacity → device → order/job → chunk để giảm deadlock. [SKIP LOCKED phù hợp cho nhiều consumer của bảng queue](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE); nó không phải giới hạn RPM hoặc bảo đảm công bằng.

RLS bật; client không có SELECT/EXECUTE trực tiếp. Chỉ gateway đã kiểm Mac+Keychain và backend service-role được gọi RPC với grants tường minh; functions `SECURITY INVOKER`, search_path chặt. URL tải ký có TTL ngắn, endpoint xác minh quyền sở hữu order trước khi ký. Khi rollout kiểm cả grants/exposure Data API vì [Supabase thay cách tự expose bảng từ 30/10/2026](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically). Không mở policy anon để chữa lỗi quyền.

**Nâng quota ngay:** migration local chỉ thay hai CHECK và `wsn_book_create` để cho 10×4.000, giữ dữ liệu cũ, giá và grants. Quota vẫn tiêu thụ lúc server chấp nhận như hợp đồng hiện tại. Sau khi queue/reservation ledger mới hoàn tất, terminal failure được release đúng reservation một lần; retry, timeout chưa rõ và hủy sau dispatch không tự hoàn lượt. Không hứa cơ chế hoàn lượt này đã có trong migration quota.

### Lưu trữ và tải trạng thái

Âm thanh là phần tốn dung lượng nhất, không phải hàng queue. Với các **định dạng giả định đã chọn**, không phải khẳng định output gốc HeyGen:

| Định dạng mono | Dung lượng 1 giờ | Một sách 4 giờ | 1.000 Mac dùng đủ 40.000 ký tự miễn phí/Mac |
|---|---:|---:|---:|
| PCM WAV 24 kHz / 16 bit | 172,8 MB | 691,2 MB | Khoảng 128 GB |
| MP3 CBR 128 kbit/s | 57,6 MB | 230,4 MB | Khoảng 42,7 GB |
| AAC 64 kbit/s | 28,8 MB | 115,2 MB | Khoảng 21,3 GB |

Đơn vị thập phân, chưa tính header, bản tạm, metadata và tải lại; thời lượng vẫn dựa trên 900 ký tự/phút. Một lần tải đủ sẽ phát sinh egress xấp xỉ cùng dung lượng; tải ba lần gần gấp ba. Không cam kết “hạ tầng miễn phí” vì inference được ưu đãi.

Nên lưu bản nén riêng để nhận/nghe; WAV làm tạm khi xử lý/xuất, rồi xóa theo retention đã công bố. Đây là **thay đổi giao thức cần triển khai sau**: hiện client/Storage chỉ kiểm WAV, không được tự đổi MIME/path và coi client cũ nhận được MP3/AAC. Giữ nguyên original của người dùng. DB chỉ giữ manifest/hash/path; không cho job lỗi gom vô hạn file tạm. Nên đặt ngân sách byte/egress theo ngày cùng cap request trước khi mở bán.

100 popup mở polling mỗi 10 giây là 600 request gateway/phút; 1.000 popup là 6.000/phút. Hiện một status còn đọc lại payload JSON cả sách và có thể ký tới 20 URL. Cần đổi sang status nhẹ gồm counters/state + cursor phân trang artifact, chỉ ký URL mới khi nhận audio. Đề xuất 10 giây lúc chờ tiền, sau đó 15 → 30 giây có jitter, tối đa 30 lần/phiên popup; đóng/ẩn dừng ngay, không fallback polling HeyGen từ app. Tốc độ gateway này độc lập với quota HeyGen. Worker là nơi duy nhất xử lý/poll provider nếu endpoint đòi hỏi; những call đó cũng tính vào quota scope nếu provider quy định.

## Cập nhật ưu đãi ngày 22/10

Owner thay phương án giá lẻ khuyến mãi bằng **combo 50.000đ/5 cuốn/Mac**, mỗi Mac một combo, mua và dùng cả 5 lượt trước hết 01/11/2026. Mua lẻ giữ book-v1. Source/migration/gateway local có ledger quota và hạn giờ server; chưa deploy/bật bán. Chi tiết ở [LAUNCH-COMBO.md](LAUNCH-COMBO.md). Bảng và đề xuất giá dưới đây là giá **mua lẻ**, không phủ nhận ưu đãi combo.

## 5. Giá và thanh toán

Giữ **book-v1** trong giai đoạn đầu, không giảm về 0 chỉ vì TTS đang miễn phí. Khoản khách mua là bản audio của snapshot sách/giọng đã chốt, có vận hành, lưu trữ, nhận lại và xử lý lỗi. Không bán quyền HeyGen vĩnh viễn hoặc bảo đảm tạo mới sau hết ưu đãi.

| Ký tự | Giá một sách/một giọng hiện tại | Trần chi phí biến đổi nếu mục tiêu lãi gộp 60% |
|---|---:|---:|
| Đến 27.000 | 10.000đ | 4.000đ |
| 27.001–54.000 | 25.000đ | 10.000đ |
| 54.001–108.000 | 40.000đ | 16.000đ |
| 108.001–162.000 | 50.000đ | 20.000đ |
| 162.001–216.000 | 60.000đ | 24.000đ |
| Mỗi 54.000 tiếp theo hoặc phần lẻ | +10.000đ | +4.000đ |

60% là **mục tiêu đề xuất**, không phải lợi nhuận đã đo. Chi phí gồm TTS theo giá sau ưu đãi + retry hợp lệ + worker + storage/egress + phí nhận/hoàn tiền và hỗ trợ. Chưa có giá HeyGen sau 30/11 thì không thể khẳng định mức lời bền vững. Công thức cho bảng giá kế tiếp: `giá >= tổng_chi_phí_biến_đổi / (1 - margin_mục_tiêu)`; tính phí phần trăm thanh toán ở mẫu số nếu có, không đếm phí hai lần. Tạo `book-heygen-v2` chỉ khi biết chi phí thật; quote đã tạo không được sửa giá/model sau khi khách chuyển tiền.

Luồng đề xuất:

1. Người dùng chọn snapshot/giọng, xác nhận gửi chữ; server kiểm provider/ưu đãi/capacity rồi giữ chỗ và báo **giá cố định + thời gian chờ ước tính + hạn QR 10 phút**. Không giữ chỗ thì không hiện QR thu tiền.
2. Mỗi order có mã SB riêng; QR lấy số tiền/tài khoản của server quote. SePay phải xác thực callback và đối chiếu transaction thật: tiền vào, account, amount, mã đúng một đơn, thời điểm. Thiếu/thừa hoặc nhiều mã → `payment_review`, không chạy TTS.
3. Cùng transaction ghi receipt, chuyển payment `paid`, chốt hold và enqueue đúng một job. Webhook retry không nhân đơn/receipt/lượt. Một receipt không cấp cả đơn sách lẫn license cũ. Không dùng generation `ready` để thay cho payment `paid` hoặc ngược lại.
4. Timeout tạo/đóng app không cần trả lại. Nghe lại, đổi player speed/nhạc, nhận lại audio còn trong chính sách lưu trữ không thu thêm. Sửa chữ/giọng/model tạo snapshot và báo giá mới.
5. Webhook tới muộn: nếu tiền thực vào trước expiry nhưng hold đã giải phóng, vẫn ghi receipt; chỉ enqueue nếu admission còn chỗ, nếu không đặt `paid_capacity_review` và quyền hoàn tiền. Không tự bỏ qua tiền hoặc overbook. Tiền vào sau expiry, sai account/amount, hoặc quote cũ sau đổi provider cũng cần đối soát/hoàn, không tự mở sách.
6. Lỗi dứt điểm sau thanh toán: khôi phục đúng snapshot nếu khả thi; nếu không thì hoàn **toàn bộ đơn chưa giao đầy đủ** theo đề xuất ban đầu, không ép khách mua credit. Trial lỗi rõ chưa tạo được thì trả lại reservation khi ledger mới triển khai; lỗi không rõ thì chờ đối soát. Refund chỉ đánh dấu verified khi có giao dịch hoàn thật; đã hoàn thì ngừng phát signed URL mới, file đã tải về Mac không thể thu hồi.

Nên bắt đầu retention server 30 ngày sau hoàn tất, ghi rõ trên quote trước mua; audio đã nhận về Mac tiếp tục nghe/xuất local. Đơn cũ giữ quyền/chính sách đã mua. Sau hết retention, không hứa tái tạo miễn phí bằng TTS đã hết ưu đãi. Cần chốt retention trước kích hoạt, không tự xóa file khách hiện có.

## 6. Mốc 30/11 và triển khai

Campaign cutoff phải là cấu hình server có timezone, không dùng clock Mac. Tạm hiểu “đến hết 30/11” là **01/12/2026 00:00 Asia/Ho_Chi_Minh**, nhưng phải đối chiếu mốc thật của provider trước mở bán. Mốc dừng nhận việc sớm hơn: `cutoff - thời_gian_backlog_bảo_thủ - p95_request - biên_an_toàn_30_phút`; lúc sát cutoff chỉ nhận nếu còn đủ ngân sách hoàn thành. Không chỉ kiểm ngày tạo order.

Đến cutoff: chặn dispatch model free, dừng quote/trial mới, tiếp tục cho nhận audio đã có. Chunk đang chạy chờ kết quả/đối soát; không tự chuyển sang model trả phí hoặc thay giọng của đơn. Đơn đã thu tiền chưa giao phải được xử lý/hoàn theo chính sách, không đẩy chi phí bất ngờ sang khách. Nếu giá sau ưu đãi được duyệt thì phát hành phiên bản quote mới cho **đơn mới**.

Thứ tự local → staging → kích hoạt:

1. Local: quota 10×4.000, bảo toàn số đã dùng, migration bổ sung, fixture Python/Edge/native, công cụ tính và tài liệu này.
2. Sau khi được chọn phạm vi triển khai: triển khai schema/RPC queue + dispatcher/provider adapter riêng; xác minh endpoint free, idempotency, voice mapping, cutoff và hạn mức thật. Deploy quota migration + gateway đồng bộ trước bật flag.
3. Load test giả lập 100/1.000 Mac, nhiều worker: không quá25 dispatch/60 giây, claim/receipt/quota không nhân đôi, kill worker sau gửi/nhận/upload, circuit chung, failover DB, quote expiry/webhook trễ, dữ liệu gốc và snapshot giữ nguyên. Không gửi 1.000 request thật để “test tải”.
4. Chỉ khi owner cho phép: mẫu nhỏ endpoint thật → đơn ngân hàng có kiểm soát → tải/xuất đúng snapshot → kiểm soát retention/refund. Đo latency theo 500/2.000/4.000 ký tự trước chốt concurrency/ETA.

Chưa có kết quả load test dispatcher hoặc thanh toán thật trong lượt tính toán này. Không dùng Python/HTTPS fixture làm bằng chứng đã phục vụ nhiều người thật.

## Bằng chứng local của lượt cập nhật

- 116 test Python core PASS; 15 test gateway/SePay giả lập PASS. Không có request TTS thật hoặc giao dịch ngân hàng trong các test.
- PostgreSQL/WASM PGlite 0.5.11: áp dụng hai migration lịch sử + migration mới trong DB riêng; giữ 3 lượt cũ, tạo thêm 7 lượt ×4.000, chặn lượt 11; retry sample cũ giữ 500 ký tự, receipt/license cũ và RLS/grants không đổi. Bộ SQL giá/receipt/snapshot/claim hồi quy PASS. PGlite chỉ một connection, **không chứng minh tranh chấp đa worker** hoặc database Supabase thật.
- HTTPS localhost: gửi mẫu đúng 4.000 ký tự, audio lỗi giữ phần đã xong, retry dùng cache, sửa chữ/giọng không phát take cũ, nhận lại và xuất WAV đúng snapshot PASS.
- `./scripts/build.sh` PASS cho bản app local; native WebKit fixture xác minh quota 10×4.000, consent, nghe mẫu, quét QR đúng 25.000đ, dark/light, focus và dừng polling PASS. Bằng chứng trong `.qa/heygen-*.log`, `.qa/heygen-db-report.json`, `.qa/book-ui/`.

Nguồn kỹ thuật tham khảo ngày 22/10/2026: [HeyGen API guide: 5.000 ký tự và convention idempotency](https://www.heygen.com/blog/heygen-api-guide), [PostgreSQL row locking](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE), [Supabase Edge limits](https://supabase.com/docs/guides/functions/limits). Giới hạn 30 RPM và thời hạn miễn phí của model đang dùng do owner cung cấp; bài hướng dẫn HeyGen không xác nhận hai thông tin tài khoản này.
