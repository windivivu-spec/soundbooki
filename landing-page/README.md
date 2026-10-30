# Soundbooki landing page

Thư mục độc lập với ứng dụng Mac/Android. HTML, CSS, JavaScript và toàn bộ asset đã có sẵn; không cần `npm install`.

```sh
cd "/Users/win/Documents/đọc sách/landing-page"
npm run dev
```

Mở `http://127.0.0.1:4173`. Landing hiện tại dùng nền xanh đêm và các bề mặt kính, 5 tính năng từ walkthrough, nghe thử giọng và hướng dẫn tải app.

Hero ngày 25/10/2026 dùng audio và timestamp mới do owner cung cấp: `sound_booki_intro_kho_khan.mp3` và `sound_booki_intro_kho_khan_timestamps.json`. Phần chưa đọc hiện thành nốt đơn, nốt kép và khóa nhạc bay tự do, không có khuông nhạc; chỉ giữ 12 ký hiệu, chia đều theo khoảng rộng của từng dòng để nhìn cân đối; dùng một khóa nhạc mở đầu và các nốt nhỏ với độ nghiêng rất nhẹ. Các nốt lơ lửng liên tục theo nhịp chậm 10–12,8 giây, dao động tối đa khoảng 4px; đến cue, ký hiệu tan nhẹ để chữ sáng dần, nâng nhẹ rồi ổn định. Nốt nhạc và sóng lan xuất hiện mỗi 2–4 từ, trôi chậm khoảng 4–5 giây. Không còn viên bi hoặc chuyển động nảy.

Bấm **Nghe lời chào** để chạy đồng thời audio và hiệu ứng; không tự phát âm thanh. Khi bật lời chào, Piano Podcast bài 01 phát nền ở mức 18%, fade-in trong 0,5 giây; giọng bắt đầu sau 1 giây. Có tạm dừng, nghe lại và tua; audio luôn phát ở tốc độ 0.95×, không có bộ chọn tốc độ. Bản nhạc chỉ được giữ trong asset/local preview, không tự phát. Khi giọng kết thúc, piano tiếp tục đến mốc 60 giây tính từ lúc nhạc bắt đầu, rồi fade-out 3 giây. Tạm dừng, ẩn tab, mở dialog hoặc rời hero sẽ dừng cả nhạc; có thể tiếp tục nhạc sau khi giọng đã kết thúc. Chế độ giảm chuyển động vẫn nghe được audio với chữ tĩnh. Hero và mẫu giọng không phát chồng; ẩn tab, mở dialog hoặc cuộn hero khỏi màn hình sẽ tạm dừng lời chào.

Mã lật sách cũ giữ làm nguồn tham khảo; bundle 3D không được đưa vào build hiện tại. Audio chỉ là các file có sẵn, không gọi dịch vụ tạo giọng.


```sh
npm run check
npm run build
npm run preview
```

`dist/` là bản web static để triển khai. Build tự gắn hash vào tên asset cho cache; không chứa source script vận hành R2, ảnh gốc thiết kế hoặc báo cáo QA. `npm run preview` dùng cùng port, dừng dev server trước bằng Ctrl+C. Có thể đổi port: `npm run preview -- --port 4174`.

## Chỉnh ở đâu

Loading mở sách nằm ở đầu `index.html`, cuối `styles.css` và phần `Articulated covers` trong `hero-animation.js`. Mô hình ở `assets/vendor/book-opening.js`: bìa có độ dày, các lớp trang cùng mở quanh gáy, giữ dáng cong khi mở hết; giấy màu ngà, bìa xám than và phản chiếu rất nhẹ. WebGL tự dựng hình, không tải Three.js/model/texture; `assets/images/loading-book.svg` là ảnh dự phòng tĩnh khi không có WebGL. Renderer chỉ vẽ trong lúc mở và khi resize/xem lại; mobile giới hạn độ phân giải, số tam giác và tối đa 30 lần vẽ/giây. Reload sẽ chạy lại; có Bỏ qua/Esc và nút xem lại. Câu ngắn ở loading không thay thế audio hero. Clip kiểm tra chuyển động ở `qa/book-opening-motion.mp4`, không đưa vào build.

| File | Nội dung |
| --- | --- |
| `index.html` | Câu chữ, bố cục, FAQ và điều kiện ưu đãi |
| `styles.css` | Màu, font, khoảng cách, responsive và chuyển động |
| `app.js` | Audio, dialog tải app, ưu đãi và chuyển động xuất hiện |
| `hero-animation.js` | Điều phối mở sách, chữ hóa nốt nhạc và đồng bộ audio |
| `assets/vendor/book-opening.js` | Mô hình bìa/trang cong, bản lề gáy và renderer WebGL nhẹ |
| `scene.js` | Hình học, chất liệu, ánh sáng, camera, CSS3D và cache hình in trên trang |
| `site-config.js` | Link tải bộ cài, checksum, phiên bản và hạn ưu đãi; chỉ chứa dữ liệu công khai |
| `assets/` | Asset web đã tối ưu, font local, icon và mẫu giọng |
| `design-assets/` | Ảnh gốc AI/nhận diện để thiết kế tiếp, không được đưa vào bản build |
| `DESIGN.md` | Hướng thiết kế và các nội dung đã đối chiếu với app |
| `qa/` | Bằng chứng kiểm tra, ảnh giao diện và xác minh download |

## Bộ cài Mac trên R2

Nút tải đã nối tới ZIP 0.8.2 có tên theo checksum, không ghi đè các bản khác. Link công khai và SHA-256 nằm trong `site-config.js` và `qa/download-verification.json`. Đã tải ngược toàn bộ 558.126.746 bytes và so SHA-256; HTTP range 206 qua.

Đây là **bản trải nghiệm Apple Silicon, macOS 15+**, ký ad hoc, chưa được Apple notarize. Có sẵn Lite/Kitten; không chứa thư viện sách, Keychain, khóa dịch vụ, nhạc cá nhân, private F5 hoặc training dataset. Dialog tải ghi rõ trạng thái và hướng dẫn cài. R2 hiện dùng địa chỉ `r2.dev`; khi mở rộng phát hành có thể thay bằng domain tải riêng đã cấu hình cho bucket.

Thao tác cập nhật bộ cài cho owner, chạy từ thư mục dự án cha:

```sh
node --env-file=.env.local landing-page/scripts/publish-download.mjs --check
node --env-file=.env.local landing-page/scripts/publish-download.mjs --artifact dist/Soundbooki-0.8.2-macOS-AppleSilicon-preview.zip
# Sau khi đã kiểm tra bản ZIP và muốn công khai chính bản đó:
node --env-file=.env.local landing-page/scripts/publish-download.mjs --artifact dist/Soundbooki-0.8.2-macOS-AppleSilicon-preview.zip --confirm-public
```

CLI kiểm tra archive, chặn tài nguyên riêng, xác minh bucket đã chọn, không ghi đè object khác nội dung, tải ngược đủ file và so checksum rồi mới cập nhật link. Biến R2 chỉ ở môi trường owner; không đưa `.env.local` vào website. Phiên bản/path hiện cố định cho đợt 24/10/2026; sửa cùng metadata khi tạo một bản phát hành khác.

## Asset và phạm vi xuất bản

- Hai minh họa AI được tạo riêng cho trang, bản gốc giữ ở `design-assets/`.
- Logo và font từ nhận diện app hiện có; font web đã subset Unicode tiếng Việt, tổng khoảng 120KB.
- Icon: Phosphor Icons 2.1.1, MIT, bản license giữ trong `assets/icons/LICENSE`.
- Mẫu giọng là các đoạn demo local hiện có, được chuyển MP3 cho bản xem thử này, không gọi HeyGen. Chúng giữ phạm vi demo local hiện tại; việc xuất bản website có các recording này cần phạm vi cho phép xuất bản riêng.
- Đoạn văn trong demo ebook tự viết. Năm bìa ở phần ưu đãi chỉ minh họa năm cuốn người dùng chọn tạo, không phải catalog/sách bán kèm.

Landing page mới được chuẩn bị local; bộ cài là file đã tải lên R2. Khi chọn domain để đưa website lên mạng, cập nhật URL tuyệt đối cho Open Graph/canonical và dùng thư mục `dist/`. Không tự bật combo, thu tiền trên web hoặc thay đổi backend chỉ vì triển khai landing page.
