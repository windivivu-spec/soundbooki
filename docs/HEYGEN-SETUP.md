# Hướng Dẫn Thiết Lập HeyGen Cloud TTS API Cho Windi Studio

> [!NOTE]
> Script owner đã có cấu hình HeyGen. Chưa có queue HeyGen dùng chung, chưa triển khai gateway cho khách. Owner cung cấp giới hạn 30 request/phút, 5.000 ký tự/request và ưu đãi tới 30/11/2026. Xem [phương án công suất, queue, database và thanh toán](HEYGEN-CAPACITY-PLAN.md). Không hiểu 5.000 ký tự là tổng quota miễn phí.

---

## 1. Cung Cấp API Key Trong `.env.local`

1. Lấy API Key từ HeyGen Dashboard: [https://app.heygen.com/settings?nav=API](https://app.heygen.com/settings?nav=API)
2. Mở file [`.env.local`](file:///Users/win/Documents/đọc%20sách/.env.local) ở thư mục gốc của dự án.
3. Điền API Key vào dòng `HEYGEN_API_KEY`:

```bash
# HeyGen TTS Cloud API Configuration
HEYGEN_API_KEY=your_heygen_api_key_here
HEYGEN_MODEL=heygen-voice-1-turbo-free
HEYGEN_LANGUAGE=vi
HEYGEN_EXPRESSIVENESS_BOOST=0.6
HEYGEN_SPEED=1.0
HEYGEN_VOICE_ID=b2bfa6db13134af5a4e36754ea1ca22d
```

*(Nếu để trống `HEYGEN_VOICE_ID`, hệ thống sẽ tự động quét và chọn giọng tiếng Việt hoặc Instant Voice Clone đầu tiên trong tài khoản của bạn).*

---

## 2. Thông Số Kỹ Thuật Đã Cấu Hình Cố Định

Theo đúng yêu cầu của anh, các tham số mặc định đã được thiết lập:
* **Mô hình (Model):** `heygen-voice-1-turbo-free` (Miễn phí 5,000 ký tự với tốc độ sinh siêu nhanh).
* **Ngôn ngữ (Language):** `vi` (Tiếng Việt).
* **Tốc độ đọc (Speed):** `1.0` (Tốc độ gốc tự nhiên nhất; người nghe có thể tăng giảm tốc độ tùy ý trên Player của App như 0.8x, 1.25x mà không làm biến dạng giọng).
* **Độ biểu cảm (Expressiveness Boost):** Tự động điều chỉnh theo từng chất giọng:
  - **Thanh Thảo & Minh Bùi:** Cố định **`0.7`** (giúp giọng trẻ trung, tươi tắn, nhấn nhá rõ ràng).
  - **Các giọng còn lại (Đình Mạnh, Đình Gia, Minh Tài, Kim Thoa, Ngân Quỳnh...):** Mặc định **`0.5`** (điềm đạm, trầm ấm, tự nhiên).
* **Nhạc nền khi nghe thử giọng:** Đã tích hợp thanh chọn nhạc nền và âm lượng ngay trong bảng "Chọn giọng bạn thích", cho phép phát nhạc nền hòa quyện cùng mẫu giọng đọc thử.
* **Nhịp thở đoạn văn (Paragraph Pacing):** Tự động phân đoạn và chèn khoảng lặng âm thanh:
  - Giữa các đoạn văn / câu hỏi / trích dẫn: **0.8s - 1.0s**
  - Giữa các chương lớn: **3.0s**
* **Rate Limit:** Script demo nghỉ tối thiểu 2,4 giây sau mỗi lần tạo, chỉ giới hạn từng tiến trình. Đây chưa phải limiter chung cho nhiều máy/worker; không dùng script này để mở dịch vụ nhiều người. Queue đề xuất dùng tổng 25 request/phút và cooldown chung.
* **Định dạng xuất file:** **MP3 128kbps** chuẩn Audible/Spotify (tiết kiệm dung lượng, tải nhanh).
* **Lọc khoảng lặng (Silence Gate):** Quét và cắt gọt tự động mọi khoảng lặng chết $> 4.5s$.

---

## 3. Danh Mục 7 Giọng Đọc Ref Voice Đã Tích Hợp

Toàn bộ 7 giọng mẫu trong thư mục `ref voice/` đã được khớp chính xác với Instant Voice Clone trên tài khoản HeyGen và tích hợp vào App:

| Tên Giọng Trong App | File Mẫu Gốc | HeyGen Voice ID | Tên Trên HeyGen | Giới Tính / Phong Cách | Boost Mặc Định |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Đình Mạnh** *(Mặc định)* | `Đình Mạnh.wav` | `3414fd7fdaa64e619fb8b021534ce368` | Podcast | Nam · Truyền cảm, podcast chiêm nghiệm | **0.5** |
| **Đình Gia** | `Đình Gia.wav` | `3ab886ca76924521bbed407e45762540` | Đình Gia | Nam · Trầm ấm, đĩnh đạc | **0.5** |
| **Minh Bùi** | `Minh Bùi.wav` | `eff592346cac4febbba5d5fef4621ff0` | Minh Bùi | Nam · Tự nhiên, mạch lạc | **0.7** |
| **Minh Tài** | `Minh Tài.wav` | `b241299543834cd8994186e600280e25` | Minh Tài | Nam · Ấm áp, biểu cảm | **0.5** |
| **Kim Thoa** | `Kim Thoa.wav` | `60dce6af562449f294ceeddb4130a9ee` | Kim Thoa | Nữ · Thanh thoát, dịu dàng | **0.5** |
| **Ngân Quỳnh** | `Ngân Quỳnh.wav` | `6a92e2ed9d3843f2b059ef8e6809366c` | Ngân Quỳnh | Nữ · Truyền cảm, mượt mà | **0.5** |
| **Thanh Thảo** | `Thanh Thảo.wav` | `5ee4ba10bd0446ba85421ab177462aba` | Thanh Thảo | Nữ · Trẻ trung, trong trẻo | **0.7** |

> [!NOTE]
> * Voice cũ **`Podcast Nam`** (`b2bfa6db13134af5a4e36754ea1ca22d`) đã được xóa vĩnh viễn khỏi tài khoản HeyGen theo yêu cầu.
> * Voice **`Podcast`** đã được cấu hình định danh là **`Đình Mạnh`** trong toàn bộ hệ thống code, app UI và CLI.
> * Mẫu âm thanh nghe thử (previews) của cả 7 giọng đã được nén chuẩn hóa vào `assets/voice-previews/pro-cloud/`, người dùng có thể bấm **"Nghe thử"** trực tiếp trên giao diện app ngay tức thì mà không tốn quota hay chờ mạng.

---

## 4. Các Lệnh Thực Thi

### A. Kiểm tra kết nối & Xem danh sách giọng:
```bash
.runtime/bin/python cloud/heygen_studio/test_heygen.py
```

### B. Tạo sách nói với giọng bất kỳ:
```bash
# Tạo sách với giọng mặc định (Đình Mạnh):
.runtime/bin/python cloud/heygen_studio/synthesize_book_heygen.py

# Hoặc chọn giọng theo tên trực tiếp (VD: Kim Thoa, Minh Tài, Đình Gia...):
.runtime/bin/python cloud/heygen_studio/synthesize_book_heygen.py \
  --voice "Kim Thoa" \
  --title "Tên Sách" \
  --author "Tác Giả"
```

Hoặc chạy thử với đoạn văn bản mẫu chuẩn 2 chương sách:
```bash
.runtime/bin/python cloud/heygen_studio/synthesize_book_heygen.py
```

---

## 5. Giới hạn request và lượt miễn phí của khách

5.000 ký tự là giới hạn **mỗi request**, không phải quota tích lũy cả sách. Chính sách owner chốt ngày 22/10: **10 lượt/Mac × tối đa 4.000 ký tự/lượt**, giữ số lượt đã dùng. Chính sách app độc lập với ưu đãi tài khoản HeyGen. Migration nâng quota mới chuẩn bị local, chưa áp dụng database thật. Endpoint/model free, thời điểm hết ưu đãi và idempotency cần xác minh trước kích hoạt.

Script owner vẫn là demo đọc đoạn, không có admission/payment/distributed queue; không coi file script là bằng chứng hệ thống đã sẵn sàng phục vụ nhiều khách.
