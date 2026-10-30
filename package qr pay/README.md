# @windi/qr-payment

Module thanh toán VND qua VietQR + webhook SePay. Tạo đơn → trả QR → nhận tiền → lưu trạng thái `paid` → project kiểm tra để giao sản phẩm. Không phụ thuộc WindiStudio, React, Voice Studio, tài khoản Supabase hay RPC riêng.

Node.js **22.13+**, khuyến nghị Node 24. Package ESM có khai báo TypeScript, không cần build. Với PHP/Python/mobile hoặc backend khác, chạy service HTTP riêng rồi gọi API từ backend của project.

## 1. Cài đặt

Trong project đích:

```sh
npm install /absolute/path/windi-qr-payment-1.0.0.tgz
```

Hoặc copy cả thư mục module rồi `npm install ./vendor/qr-payment`. File tgz đóng kèm driver PostgreSQL và dependency của driver, có thể cài offline bằng `npm install --offline /absolute/path/windi-qr-payment-1.0.0.tgz`. Package chưa được publish lên npm registry.

## 2. Cấu hình môi trường

Copy `env.example` thành `.env` của project/service, thay ngân hàng và hai khóa. Sinh mỗi khóa bằng `node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"`.

```dotenv
QR_BANK_BIN=970422
QR_BANK_ACCOUNT=1234567890
QR_BANK_NAME=NGUYEN VAN A
SEPAY_WEBHOOK_API_KEY=your-random-webhook-secret-at-least-16-characters
QR_API_KEY=a-different-random-backend-secret-at-least-32-characters
QR_CODE_PREFIX=WD
QR_CODE_LENGTH=6
QR_CODE_CHARSET=digits
QR_PROJECT_ID=my-project
QR_SQLITE_PATH=./data/qr-payments.sqlite
```

Ví dụ mã: `WD029292`. Mã sinh ngẫu nhiên bằng crypto, giữ số 0 đầu, kiểm tra trùng trong database và không tái sử dụng mã cũ. Mặc định hậu tố 10 ký tự; dùng 6 khi muốn mã ngắn như ví dụ. `QR_CODE_CHARSET=alphanumeric` cho phép cả chữ/số. Tiền tố 2–5 chữ, hậu tố 6–10 ký tự. `QR_ORDER_TTL_SECONDS=900` mặc định 15 phút.

`SEPAY_WEBHOOK_API_KEY` là khóa **API Key của webhook**, không phải Bearer token của SePay User API. Không đặt khóa vào `NEXT_PUBLIC_*`, `VITE_*`, HTML hay mã frontend. Module không cần gọi User API để dò giao dịch.

Lưu dữ liệu:

- Local/VPS/Docker: SQLite tự tạo thư mục/bảng. Giữ file cùng WAL/SHM trên ổ bền vững; với Docker mount `/data`. Không đặt file DB trong thư mục public, git hoặc filesystem tạm.
- Serverless/nhiều máy: đặt `QR_DATABASE_URL=postgresql://...`, module tự tạo schema riêng `windi_qr_private` và bảng PostgreSQL, bật RLS, thu hồi quyền PUBLIC/anon/authenticated. Kết nối bằng backend DB owner, giữ schema này ngoài Data API. Dùng connection string/pooler và TLS theo nhà cung cấp, không tắt kiểm tra chứng chỉ. User DB cần quyền tạo schema/bảng. SQLite bị chặn khi nhận diện Vercel/Lambda/Cloud Run/Netlify mà chưa có Postgres.
- `QR_PROJECT_ID` ổn định qua các lần deploy, khác nhau giữa các project dùng chung DB. Mỗi project dùng chung tài khoản nhận nên dùng tiền tố riêng, cấu hình webhook riêng và lọc tiền tố ở SePay. Giữ nguyên ngân hàng/tài khoản/tiền tố/namespace khi còn đơn chờ. Sao lưu DB; mất lịch sử đồng nghĩa mất khả năng chống replay qua các lần khởi động.

## 3. Chạy hoặc nhúng

### Service HTTP dùng cho mọi backend

```sh
node --env-file=.env node_modules/@windi/qr-payment/src/cli.js
```

Hoặc trong thư mục source module: `npm ci && npm start`. Mặc định `127.0.0.1:8787`. Đặt `HOST=0.0.0.0` khi chạy Docker. Đưa service sau reverse proxy HTTPS và giới hạn tần suất request ở proxy. Không mở CORS mặc định; frontend đi qua backend cùng origin.

Docker từ thư mục source: `docker build -t windi-qr-payment .`, rồi `docker run --env-file .env -p 8787:8787 -v qr-payments:/data windi-qr-payment`.

### Next.js App Router

Copy `examples/nextjs/app/api/payments/[...path]/route.ts` vào đúng đường dẫn trong project. Các route là Node runtime, dùng Request/Response chuẩn. Vercel cần `QR_DATABASE_URL`; mọi biến trên là server-only. Không cần sửa mã module.

### Express / Node / backend có Fetch API

Xem `examples/express/server.mjs`. Mount adapter trước `express.json()`. Nếu tự xử lý Request/Response, gọi `payments.handle(request, {basePath:'/api/payments'})`.

```js
import { createPaymentModule } from '@windi/qr-payment';
const payments = await createPaymentModule();
const order = await payments.createOrder({
  amount: 69000,
  idempotencyKey: 'invoice-123',
  metadata: { invoiceId: 'invoice-123', userId: 'your-user-id' },
});
// order.qrUrl, order.code, order.statusToken → trang thanh toán của khách.
// payments.getOrder(order.id) → trạng thái + metadata riêng cho backend.
```

`createPaymentModule` đọc env và khởi tạo DB một lần, giữ instance/promise dùng lại. Có thể truyền `store` riêng theo `PaymentStore` hoặc `createPostgresStore(pool)` để dùng connection pool hiện hữu.

## 4. API

### Tạo đơn — backend gọi, không đưa QR_API_KEY cho khách

```sh
curl http://127.0.0.1:8787/api/payments/orders \
  -H "Authorization: Bearer $QR_API_KEY" -H 'Content-Type: application/json' \
  -d '{"amount":69000,"idempotencyKey":"invoice-123","metadata":{"invoiceId":"invoice-123"}}'
```

Trả HTTP 201 với `id`, `amount`, `currency`, `code`, `status`, `createdAt`, `expiresAt`, `paidAt`, `bank`, `qrUrl`, `statusToken`. Gọi lại cùng key và dữ liệu trả đúng đơn cũ; cùng key nhưng đổi dữ liệu trả 409. Key giữ trong lịch sử, không dùng lại để tạo đơn sau khi đơn hết hạn.

Project phải xác thực người mua, kiểm tra quyền mua và **tính giá từ dữ liệu server** trước khi tạo đơn. HTTP API này dành cho backend tin cậy; một token được quyền tạo mọi đơn trong namespace của nó. Không proxy trực tiếp số tiền do browser gửi lên.

### Xem trạng thái — browser dùng token riêng của đơn

```sh
curl http://127.0.0.1:8787/api/payments/orders/ORDER_ID \
  -H 'Authorization: Bearer ORDER_STATUS_TOKEN'
```

Chỉ trả thông tin thanh toán, không trả metadata, khóa backend, payload ngân hàng hay token. Browser poll mỗi 3 giây và dừng khi `paid`/`expired`. Token trạng thái chỉ đọc một đơn. Backend cũng có thể dùng `QR_API_KEY` để đọc hoặc `getOrder(id)` để lấy metadata.

Trang mẫu chạy được ở `examples/checkout.html`: serve từ cùng origin API, dẫn khách tới `/checkout.html#id=ORDER_ID&token=ORDER_STATUS_TOKEN`. Fragment chứa token đọc đơn, không chứa QR_API_KEY. Trang có QR, số tiền, STK, sao chép nội dung, tự kiểm tra và dừng khi nhận tiền/hết hạn. QR ảnh do VietQR cung cấp qua Internet.

### Nhận webhook

`POST /api/payments/webhook`, header `Authorization: Apikey <SEPAY_WEBHOOK_API_KEY>`.

Tại SePay tạo webhook sự kiện tiền vào, chọn đúng tài khoản, phương thức API Key với khóa trên, URL `https://your-domain/api/payments/webhook`. Nếu dùng nhận diện/lọc mã của SePay, đặt tiền tố, độ dài và kiểu hậu tố tương ứng. Module tự đọc mã trong `content` nên không phụ thuộc bộ nhận diện mã; chỉ dùng `code` dự phòng khi content rỗng. Hai mã trong cùng content hoặc code/content mâu thuẫn bị bỏ qua. Theo [tài liệu webhook SePay](https://docs.sepay.vn/tich-hop-webhooks.html), kết quả nhận hợp lệ cần HTTP 200/201 và `success:true`.

## 5. Quy tắc xác nhận và giao sản phẩm

- Chỉ giao dịch **tiền vào**, đúng STK, đúng một mã, **đúng chính xác số tiền nguyên VND** mới được xác nhận. Không cộng dồn tiền thiếu, không tự chấp nhận chuyển dư, không tự hoàn tiền.
- Ngày giao dịch SePay theo giờ Việt Nam (UTC+07). Thiếu/sai ngày bị từ chối. Chuyển trước thời điểm tạo đơn, sau hạn hoặc quá 5 phút trong tương lai được lưu để kiểm tra, không xác nhận.
- Webhook đến trễ vẫn xác nhận nếu giao dịch ngân hàng xảy ra trong thời hạn đơn. Vì vậy có thể thấy `expired` rồi `paid` khi webhook của giao dịch đúng hạn đến muộn; backend cần đối soát lại trước khi đóng vĩnh viễn giao dịch.
- Mã cũ không tái sử dụng. ID giao dịch unique theo tài khoản, cập nhật đơn + lưu giao dịch trong cùng DB transaction; retry/đồng thời không xác nhận hai lần. Payload sai số tiền/đến muộn được lưu cùng lý do, quản trị có thể xem trong `windi_qr_events`, và tiền cần xử lý riêng theo nghiệp vụ project.
- Module kết thúc tại trạng thái `paid`. Backend project kiểm tra trạng thái tin cậy rồi cấp hàng/quyền với khóa idempotency là order ID trong transaction nghiệp vụ riêng. Không cấp hàng chỉ dựa trên UI, token frontend hoặc một lần polling thành công. Nếu cần job giao hàng, dùng worker đọc các đơn paid chưa fulfill và unique payment order ID; không có callback giao hàng với cam kết exactly-once giữa hai DB.
- Lỗi auth/input trả 401/400, quá kích thước 413, lỗi storage 503 để SePay retry. Các giao dịch không phù hợp trả 200 `success:true,status:'ignored'`; retry giao dịch đã ghi nhận trả `duplicate`.

## 6. Kiểm thử và đóng gói

```sh
npm test
npm pack
```

Test dùng tài khoản/khóa giả và webhook local, không gọi ngân hàng/SePay, không tạo giao dịch thật. PostgreSQL SQL được kiểm tra bằng harness PGlite ở repo chủ; cần kiểm tra kết nối, quyền schema và khóa đồng thời trên PostgreSQL đích trước khi triển khai. Không kèm `.env`, DB, khóa thật hoặc dữ liệu khách hàng trong tgz.

Triển khai xong hãy dùng tính năng Gửi thử/Test Mode của SePay để kiểm tra URL/auth, rồi đối soát giao dịch thật theo quy trình của bạn. Việc đóng gói và test local không chứng minh thanh toán ngân hàng thật đã thành công.
