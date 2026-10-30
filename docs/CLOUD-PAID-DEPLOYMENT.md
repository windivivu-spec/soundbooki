# Mac: thu tiền SePay và tạo sách HeyGen — 24/10/2026

Owner đã yêu cầu bật thu tiền thật cho sách lẻ trên Mac và xác nhận **đã có quyền thương mại HeyGen** trong cùng phiên. Đây là phạm vi activation thay cho trạng thái paid deferred ngày 23/10. Không phát hành installer, bật StoreKit/Play Billing, đổi chính sách thiết bị hoặc đưa API key vào app.

## Trạng thái đã triển khai

- Project vẫn khóa vào `zpjphixcttehkkgxlmsn`. Chỉ cập nhật `wsn-books` v9, `wsn-heygen-worker` v8 và `wsn-sepay-webhook` v11; giữ nguyên function/license của các sản phẩm khác.
- `WSN_BOOKS_ENABLED`, `WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED`, `WSN_HEYGEN_PAID_ENABLED`, `WSN_PAYMENTS_READY` đã bật. Đối chiếu digest secrets sau activation thành công. Không đổi khóa SePay/HeyGen/worker hoặc khóa ký license.
- Bổ sung BIN/name/holder cho tài khoản TPBank đã có. API SePay xác nhận tài khoản active và đúng BIN. Webhook `book` #65318 trong Safari: đúng URL function, chỉ tiền vào, JSON, API Key, đúng tài khoản, không lọc bỏ `SB…`; đã bật và đọc lại retry khi HTTP lỗi.
- Combo vẫn theo flag activation riêng; không tự bật bán combo trong lần bật sách lẻ này. Các quyền/đơn combo đã có vẫn được giữ.
- Model giữ `heygen-voice-1-turbo-free`, không fallback sang model tính phí. Đây là dịch vụ best effort của provider, không hứa ETA. Provider công bố ưu đãi đến 30/11/2026 và có thể trả 429 khi hết công suất: [thông báo chính thức](https://www.heygen.com/blog/heygen-voice-turbo). Cần rà lại model/giá trước khi ưu đãi kết thúc.

## Luồng tiền và quyền nhận sách

1. Mac gửi snapshot chữ/giọng đã được đồng ý, hashed Mac code và random credential Keychain. Backend định giá bằng số Unicode code point, không nhận giá client tự khai.
2. RPC `wsn_book_quote` lấy khóa admission, kiểm tra công suất và tạo/nhận lại đơn bất biến. `receiving_bank` được chốt vào đơn trước khi trả QR; không đổi ngân hàng cho đơn đã chốt. Retry cùng snapshot/request giữ đơn cũ.
3. App dựng QR bằng đúng amount/account/payment code từ đơn server. Đơn ở `awaiting_payment`, chưa có task HeyGen.
4. Webhook xác thực API Key, rồi đọc **giao dịch thật** từ API SePay để đối chiếu ID, tiền vào, tiền ra, account, mã và thời điểm. Nội dung callback tự khai hoặc ảnh chuyển khoản không đủ để mở đơn. [Hợp đồng webhook SePay](https://docs.sepay.vn/tich-hop-webhooks.html).
5. `wsn_book_confirm` khóa receipt và order, đối chiếu số tiền/thời hạn/ngân hàng đã báo giá, ghi receipt và chuyển đơn `queued` trong một transaction. Receipt duy nhất xuyên ledger sách/license; callback lặp không cấp thêm quyền.
6. Worker chỉ claim sách có receipt hợp lệ hoặc redemption combo đã được tài trợ. Một `paid_at` tự gắn vào row không đủ. Đơn giữ device, snapshot, voice và segment; khách chỉ nhận status/link audio sau khi gateway xác thực cả device code lẫn credential. Không lấy device mới từ callback thanh toán.
7. Audio được kiểm WAV/SHA, lưu private theo order/segment rồi commit claim. Mac kiểm SHA, tải nguyên tử và chỉ báo ready khi đủ file của snapshot. Đổi chữ/giọng không dùng audio cũ cho bản mới. Đóng app không hủy queue; mở lại đơn để nhận audio.

## Hàng đợi

- Một row lock chung cho admission và cấp lượt, cộng log dispatch để giới hạn **25 lần/60 giây trượt**, bao gồm safe retry; giãn ít nhất 2,5 giây và tối đa 3 request đang gửi. Cron hiện có chạy mỗi 3 giây, được cập nhật predicate để nhận cả sách có tiền. Không tạo cron thứ hai.
- Vòng 4 lượt sách trả tiền / 1 lượt trial; một nhóm được mượn phần rỗi của nhóm kia. Trong mỗi nhóm chia lượt giữa các máy, chọn chunk kế tiếp thay vì chạy trọn một cuốn dài trước.
- Chặn quote mới khi tổng backlog/quote còn hạn vượt 6.000 segment; mỗi Mac tối đa hai đơn chưa trả tiền đang giữ chỗ. Từ chối trước khi khách chuyển khoản. Trial admission lỗi rollback cả quota; không reset lượt đã dùng.
- 429 dùng Retry-After và cooldown chung. Timeout/HTTP500/kết quả gửi không rõ giữ trạng thái uncertain để đối soát, không tự gửi TTS lần hai. Phần đã hoàn tất và URL provider được giữ. Recovery tải lại URL/artifact, không synthesize lại.
- Script HeyGen owner gọi trực tiếp đã bị khóa bằng `release.json: heygenDispatchOnly=true` để không vượt limiter của dịch vụ. GET setup/list voices vẫn được dùng. Không chạy phần mềm khác ngoài dự án bằng cùng provider key; limiter này kiểm soát các worker thuộc dịch vụ, không thể kiểm soát client ngoài hệ thống.

## Bằng chứng

- 137 Python core tests; 32 gateway/worker tests; HTTPS local integration PASS.
- PGlite PASS: ngân hàng bất biến, receipt trùng/sai, chặn unpaid/paid_at giả, legacy Modal, 4:1/fairness, 3 inflight, cửa sổ trượt, admission và rollback quota. Đây là một connection WASM, chưa là benchmark nhiều connection/khách thật.
- Native WebKit PASS: consent, QR đúng giá server, không tạo trước trả tiền, trạng thái paid rồi mới queue, dừng polling khi đóng. CoreImage đã quét **ảnh QR thật trên Mac**, khớp toàn bộ amount/account/payment code từ đơn server.
- Kiểm tra live chỉ đọc: bank, runtime GET, schema/grants/RLS, cron, security advisors và đối chiếu đơn thật với **Mac code + hash của Keychain credential hiện tại** PASS. Advisors không có WARN/ERROR cho bảng WSN, chỉ INFO private RLS không có policy cho client.
- Đơn thực tế `Tư Duy Phản Biện`: 113.169 ký tự / 322 segment / 50.000đ, đã hiện QR trên Mac; lúc kiểm chứng còn `awaiting_payment`, receipt/task/audio đều 0. Trial, 2 receipt license cũ và 1 license được giữ.
- Build `./scripts/build.sh` PASS. Bằng chứng ở `.qa/paid-cloud/`; không đóng gói `.env.local`, credential, source sách hoặc dữ liệu QA.

**Chưa có lần chuyển tiền thật trong lượt activation này.** Phép thử gửi callback giả vào webhook live và gọi worker trực tiếp đã bị automatic approval review chặn vì có thể dispatch công việc ngoài dự kiến; không chạy vòng qua chặn. Đã thay bằng QA cô lập và kiểm tra live chỉ đọc. Khách/owner tự chuyển tiền qua QR khi muốn kiểm chứng thực tế toàn tuyến SePay → queue → HeyGen; không ghi fake-paid vào live ledger.

## Vận hành

```sh
# Chỉ đọc: schema/cron/grants/runtime/bank/advisors, không gọi worker POST.
node --env-file=.env.local commerce/paid-cloud-status.mjs

# Dừng báo giá mới, vẫn cho xử lý/nhận sách đã trả tiền.
node --env-file=.env.local commerce/paid-cloud-deploy.mjs pause-sales

# Xác minh cấu hình đã bật, không đổi flag.
node --env-file=.env.local commerce/paid-cloud-deploy.mjs verify-activation --commercial-rights-confirmed
```

Migration `20261023170720_heygen_paid_book_dispatch.sql` được tạo bằng CLI rồi áp riêng qua Management API sau backup các hàm. Không chạy lại migration, `schema`, full `db push` hoặc script setup trial để reset dịch vụ. Script trial cũ có guard khi schema paid đã tồn tại. Các function liên quan vẫn `security invoker`, chỉ service_role có quyền gọi; không mở policy public để bỏ INFO advisors.
