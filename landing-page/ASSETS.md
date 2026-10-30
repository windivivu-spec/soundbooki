# Nguồn asset

| Asset | Nguồn / cách tạo |
| --- | --- |
| `book-and-sound*.webp` | Imagegen: sách bìa xanh mở, tai nghe trắng, đế kính mờ, alpha thật; render trang trí riêng cho hero |
| `quiet-listening.webp` | Imagegen: góc đọc trong căn hộ, sách/tai nghe trắng cạnh cửa sổ; ảnh lifestyle riêng |
| `mac-app-light.webp` | Ảnh native Mac local `.qa/brand-preview/home-light.png`, thư viện trống, không có sách/dữ liệu khách hàng |
| `brand/*` | `ui/brand/` hiện tại; đổi kích thước/codec cho web, giữ ảnh gốc trong design-assets |
| `fonts/*` | SFProRounded-Black, SVN Nexa Light/Bold từ `ui/fonts/`; subset tiếng Việt, Latin và ký hiệu UI |
| `icons/sprite.svg` | Các SVG chính thức từ `@phosphor-icons/core@2.1.1`, không dùng CDN runtime |
| `audio/*.mp3` | Preview local 8,5 giây tại `assets/voice-previews/pro-cloud/` của dự án cha, tương ứng recording tham chiếu cùng tên. MP3 96kbps; waveform đo RMS từ PCM thật |
| `social-card.png` | Ảnh chụp giao diện landing page đã dựng |
| `vendor/gsap.min.js`, `vendor/ScrollTrigger.min.js` | GSAP 3.15.0 từ package npm chính thức, giữ header bản quyền và link GSAP Standard License trong `vendor/NOTICE.txt` |

Hero hiện dùng cảnh sách Three.js, DOM CSS3D và SVG waveform inline. Ảnh `book-and-sound*.webp` được giữ làm nguồn thiết kế cũ, không dùng trong hero mới. Các SVG icon vẫn dùng Phosphor; waveform là đồ họa minh họa thanh âm, không phải icon hoặc dữ liệu audio đo được.

Mẫu giọng giữ phạm vi local trước khi có yêu cầu xuất bản website; bộ cài Mac công khai không chứa các recording này.

## Cảnh sách 3D hiện tại

- `scene.js`: bìa/gáy/block giấy/trang cong dựng bằng Three.js; textile, giấy, mép giấy và bóng là texture Canvas xác định, tạo local.
- `assets/vendor/book-scene.js`: bundle Three.js + CSS3DRenderer + RoundedBoxGeometry, esbuild; giấy phép trong `THREE-LICENSE.txt`.
- Texture chữ trên trang là `assets/book-pages/*.png`, xuất từ DOM demo của chính website trước khi build. `pages.json` chọn bản desktop/mobile và được gắn hash cùng asset. Không có sách khách hàng, tải lên hoặc chụp DOM lúc người xem cuộn.
- `plinth.mp4`, `aerflora.mp4` là tài liệu tham khảo chuyển động local; không được sao chép vào website/bản build.
