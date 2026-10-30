# Pro: gộp request và lưu mẫu local — 25/10/2026

## Hành vi

- Đoạn đọc của trình biên tập (~420 ký tự) không còn là đơn vị gọi HeyGen cho yêu cầu mới. Snapshot `chunkingVersion=heygen-5000-v1` gộp tối đa 5.000 Unicode code point/request trong cùng chương thực, qua ranh giới đoạn và trang.
- 4.977 ký tự trong một chương được gửi một lần. Chữ gốc, dấu, Unicode tổ hợp, khoảng trắng và xuống dòng được giữ nguyên. `sourceSpans` giữ vị trí nguồn; không ghi text tổng hợp trở lại sách.
- Khi vượt giới hạn, lấy cuối câu gần 5.000 (vùng 85–100% dung lượng); bảo vệ số thập phân và viết tắt. Câu quá dài dùng mệnh đề, khoảng trắng, cuối cùng mới cắt token không có khoảng trắng. Không bỏ câu, không thêm chữ. Một ít dung lượng có thể dư để giữ câu nguyên vẹn; không đảm bảo mọi request đầy đúng 5.000.
- Mẫu đầu bị giới hạn quota kết thúc tại ranh giới tự nhiên gần giới hạn, hiển thị đúng số chữ trước xác nhận. Lượt thử tính theo `ceil(actual characters/5000)`, không phải số file; nhóm tối đa 4 lượt và tổng lifetime 5 vẫn do server quyết định.
- Snapshot đã gửi/đã thanh toán bất biến: tiếp tục đúng body/request key cũ. Đơn cũ chia 14 phần vẫn nhận đủ 14 phần; không gom lại bằng cách tạo TTS lần nữa. So khớp nguồn cho phép mở/nhận lại đơn trước nâng cấp.
- Mẫu tải về vẫn giữ nguyên file trong `cloud-trials`; đồng thời có bản audio local và immutable take trong **Sách nói của bạn**, nghe/xuất như các bản đọc khác. Mở lại sách tự khôi phục mẫu cũ từ cache, không network hoặc dùng lượt. Chỉ file WAV hoàn chỉnh mới xuất hiện; từng file hoàn tất được giữ khi tải tiếp lỗi.
- Pro không còn dùng nhãn `0/14 phần đã tạo` của cache đoạn đọc local. Hiển thị số bản Pro đã lưu và số request của nội dung xác nhận. Các bản nhiều file dùng `auxQueue` để native chuẩn bị file kế tiếp trên cùng đồng hồ phát; xuất WAV nối PCM trực tiếp, không chèn khoảng nghỉ cố định giữa request.

## Server

Migration `20261025115543_heygen_request_5000.sql` chỉ nới kiểm tra segment của snapshot HeyGen có version gộp mới. Modal và client cũ giữ giới hạn 2.000. Không cập nhật row đơn/quota/receipt, không đổi grants, ngân hàng, giá, combo, payment activation hoặc dispatcher. Đã áp dụng và đối chiếu dữ liệu bất biến trước/sau.

Worker v10 bổ sung diagnostic tên bước tải/kiểm WAV/upload/commit, không lưu lỗi thô, key hay URL vào diagnostic. Lỗi sau khi có URL giữ trạng thái audio để nhận lại; không gửi TTS lần hai. Không gọi trực tiếp provider ngoài dispatcher.

## Kiểm chứng

- Python: 157 tests, PASS, 1 skip; kiểm tra mới gồm 4.977/5.000/5.001, dài không dấu câu, Unicode, giữ nguyên nguồn, chương giữa trang, nhãn chương xuất, retry đơn cũ và phục hồi/xuất mẫu local sau sửa chữ/giọng.
- PGlite: PASS giới hạn mới/cũ, 20.000 code point/4 request, retry giữ quota, cùng bộ kiểm tra receipt, immutable bank, admission rollback, quyền private, limiter và fairness. Đây là PostgreSQL WASM cô lập, không phải benchmark nhiều connection.
- Gateway/worker: 32 tests PASS với fetch giả lập.
- HTTPS localhost: PASS tải/kiểm SHA/WAV, gián đoạn giữ file xong, retry cache, immutable paid take và mẫu xuất WAV.
- WebKit native: PASS popup xác nhận, khôi phục tiến trình/mẫu cũ, bản Pro hiện trong thư viện, nút nghe/xuất và `auxAdvanced` không khởi động lại `auxPlay`. Đã kiểm tra ảnh light/dark. Bài queue UI dùng fixture, không phải phép đo âm học.
- **HeyGen thật:** một mẫu tự viết 4.977 ký tự trên thiết bị QA riêng, một dispatch/attempt, WAV mono 44,1 kHz dài 281,656 giây; Mac chuyển 24 kHz, lưu immutable take và xuất WAV thành công. Một lần status lỗi mạng được tiếp tục đúng đơn/audio cũ, không tạo TTS mới. Không dùng quota Mac owner hoặc gửi nguồn sách owner trong bài thử.
- **Sửa dữ liệu owner:** khôi phục hai mẫu đã tải (4.977 ký tự/14 file và 847 ký tự/3 file) vào sách nói local. Có backup metadata riêng trong `.qa/pro-batching/`; đối chiếu giữ nguyên chữ, giọng, orders, các take cũ và SHA audio gốc. Không gọi network hoặc dùng quota trong bước sửa này.
- `./scripts/build.sh` PASS với `WINDI_SKIP_REGISTRATION=1`; đây là app phát triển local, không phát hành installer.

Bằng chứng `.qa/pro-batching/` là dữ liệu QA/local riêng, không đưa credential, nguồn sách hoặc URL có quyền truy cập vào gói phát hành. Bài thật xác nhận tuyến 4.977 ký tự đã kiểm tra; không chứng minh mọi giọng/sách/độ trễ provider.
