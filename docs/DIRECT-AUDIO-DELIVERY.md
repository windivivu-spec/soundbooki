# Mac direct audio — 28/10/2026

Owner requested removing intermediate audio storage and rebuilding the Mac app for testing.

## Prepared change

- New worker results validate the provider WAV and calculate SHA256 in memory, then commit delivery metadata. No new Storage upload or object readback. The Mac downloads the provider URL directly, verifies SHA256/WAV, resamples and saves atomically as before. The worker still downloads bytes once for integrity checking; this is not streaming synthesis or a measured guarantee of faster provider inference.
- `wsn_book_audio_direct` delegates to the existing funded claim validation and marks only that segment result as `delivery=provider`, removing its Storage path. The private wrapper requires a durable audio task first and retains snapshot, device binding, quota, payment/receipt checks and the shared dispatcher. Existing RPC behavior and existing rows remain unchanged.
- Gateway returns provider links only for the authenticated order's committed direct results, with the same HTTPS provider-host allowlist. Legacy results retain signed private Storage downloads. No API/provider keys enter the client. Provider-link expiry may prevent later recovery if the file has not reached the Mac; no automatic re-synthesis is introduced.
- Mac 0.8.3 build 23 accepts explicitly marked, allowlisted provider links and continues supporting existing Storage links. Local audio and older orders remain intact.

## Validation

164 Python tests PASS; 43 gateway/worker tests PASS, including no Storage calls in worker success/recovery and direct-link ownership/payment/host guards. PGlite private/funded claim and unchanged snapshot checks PASS. Real localhost TLS integration PASS for direct-provider URL routing, atomic/hash/WAV checks and cache retry (provider host mapped to the isolated local TLS fixture; no HeyGen generation). Mac build PASS with `WINDI_SKIP_REGISTRATION=1 ./scripts/build.sh`.

Evidence in `.qa/direct-audio/`. No new live synthesis, trial debit or payment was performed. Source/build validation does not prove end-to-end production latency.

## Deployment status

**DEPLOYED**, after the owner explicitly selected “Phê duyệt triển khai cloud ngay” for this exact scope. `wsn-books` v11 and `wsn-heygen-worker` v11 are ACTIVE; the private `wsn_book_audio_direct` RPC is installed. HTTP method health checks PASS. Post-deploy checks matched all preflight order/device digests, payment/license counts, dispatcher definition and the existing schedule. RPC execute remains denied for anon/authenticated and granted to service_role. No secrets, activation flags, bank or webhook were changed; deployment issued zero provider synthesis requests.

The two earlier attempts were blocked by automatic approval review pending explicit cloud approval; neither attempt ran. Evidence for the successful deployment is `.qa/direct-audio/deploy.log` and `deployed.json` (2026-10-28T16:31:01Z, 23:31 UTC+7).

Mac 0.8.3 build 23 must be reopened so its Python worker loads direct-link support. New completed segments use direct provider delivery. Existing committed Storage results stay unchanged and downloadable. End-to-end real-provider latency after this change remains unmeasured; the owner can test a new explicit generation in the updated app. Android/PC paid activation and installer/public distribution remain separate scope.

## Kiểm tra lần tạo của owner — 29/10/2026

- Mẫu 4.759 ký tự/1 request tạo 23:54:02 và commit 23:56:31 (UTC+7), khoảng 149,5 giây. Task bắt đầu 23:54:05; hiện đã hoàn thành. Đây là thời gian toàn tuyến server, không phải thời gian inference HeyGen riêng.
- Trong cùng khoảng thời gian, `net._http_response` ghi worker 502 `reconcile/claim`, 503 `SUPABASE_EDGE_RUNTIME_SERVICE_DEGRADED`, và 502 `reconcile/commit`. Các worker chạy đồng thời; log hiện không gắn order/task vào mỗi phản hồi nên chưa thể khẳng định từng lỗi thuộc chính request này hoặc xác định thời gian từng bước HeyGen/download/commit. Không có đủ timestamp để kết luận chính xác 120 giây phục hồi hay tốc độ riêng của provider. Không có dấu hiệu queue đang còn chờ lúc kiểm tra.
- Theo yêu cầu owner, đã xác thực đúng mã Mac + hash credential Keychain và đặt lại `trials_used` từ 5 về 0 cho đúng thiết bị, không đụng thiết bị khác. Đối chiếu hash các đơn và số receipt không đổi; gọi profile thật xác nhận 5/5. Lịch sử đơn/trial và audio không bị xóa. Không gọi tạo giọng trong bước kiểm tra/reset.
- Log và báo cáo chỉ đọc đã che dữ liệu ở `.qa/direct-audio/`. Cần đo riêng các mốc dispatch → provider response → tải/kiểm WAV → commit → Mac lưu trên một lần tạo mới qua dispatcher trước khi kết luận bottleneck hoặc cam kết độ trễ. HeyGen Turbo Free là best effort, theo thông báo chính thức không bảo đảm latency.

## Phép đo thật — 29/10/2026

Owner yêu cầu tạo một đoạn thử API và so với app. Một QA device riêng tạo 4.759 ký tự, một request, giọng Thanh Thảo qua đúng shared dispatcher; không dùng quota owner. Task `sending` lúc 00:02:47, provider URL đã lưu 00:03:12 (~25,05 giây), sau đó task giữ trạng thái `audio` với `available_at` 00:05:12 (thêm 120 giây). Tải URL provider về Mac riêng mất 3,34 giây/23.516.628 byte. Qua `sync_order` như app, audio chỉ sẵn sàng sau 159,86 giây; file WAV thử được lưu trong `.qa/latency-20261029/trial-export.wav`.

Log edge ghi RPC `wsn_heygen_result` trả HTTP 204 lúc 00:03:12. Helper `rest` gọi `r.json()` trên phản hồi rỗng, ném lỗi sau khi database đã lưu URL, và worker không tiếp tục đến commit. Hàng đợi bảo vệ URL với lease 120 giây rồi mới phục hồi. Worker cũ có cùng lỗi 204 cả ở bước ghi `done`. Đã sửa helper chấp nhận 204 là thành công và thêm regression fixture dùng phản hồi 204 thật. 44 gateway/worker tests PASS; không đổi dispatcher SQL, quota, thanh toán hay quyền.

**Bản sửa chưa triển khai**: automatic approval review từ chối sửa worker production vì cần owner duyệt riêng thay đổi mới. Script chuẩn bị `commerce/fix-worker-204-deploy.mjs` chỉ cập nhật `wsn-heygen-worker`, yêu cầu queue trống, đối chiếu đơn/quota/receipt/limiter và kiểm tra health; không tự tạo test mới. Chưa thể cam kết thời gian sau sửa đến khi đo lại bằng một request được chủ sở hữu cho phép.

## Sửa worker 204 và đo lại — 29/10/2026

Sau khi owner chọn **Triển khai và đo lại**, worker `wsn-heygen-worker` v12 được triển khai lúc 00:09:06 UTC+7. Preflight hàng đợi rỗng; so sánh sau triển khai xác nhận đơn, quota, receipt và limiter không đổi; GET health trả 405 như dự kiến. Không cập nhật RPC/schema, gateway, bank, flag hay secrets. Regression 44 gateway/worker tests PASS, gồm `wsn_heygen_result` trả HTTP 204 với body rỗng.

Đã gửi đúng một yêu cầu QA mới qua gateway + dispatcher bằng một thiết bị QA riêng, không tiêu quota Mac owner. So sánh cùng 4.759 ký tự tổng hợp, cùng giọng Thanh Thảo, cùng một request và cùng luồng tải/ghi audio local: trước sửa **159,86 giây**; sau sửa **37,04 giây**, nhanh hơn 122,82 giây (khoảng 77%). Trong lần sau sửa task bắt đầu lúc 00:09:22, URL được ghi khoảng 00:09:46 và task hoàn tất lúc 00:09:49: không xuất hiện khoảng chờ phục hồi 120 giây. File đã kiểm tra WAV, resample 24 kHz và export thành công. Bằng chứng `.qa/latency-20261029-after/`.

Đây là phép so sánh hai lần thực tế, không phải cam kết thời gian cho mọi giọng, sách hoặc điều kiện tải. HeyGen free vẫn best effort; app có thể cần thêm thời gian phụ thuộc mạng/tải file. Để tránh lặp trả phí hoặc reset quota, không gửi request tổng hợp nào ngoài hai mẫu QA đã được owner cho phép. Bản Mac build 23 đã hỗ trợ luồng này; worker sửa trên cloud không yêu cầu build Mac lại.
