# -*- coding: utf-8 -*-
from vietnam_stories_part1 import VN_STORIES_PART1
from vietnam_stories_part2 import VN_STORIES_PART2

VN_PREFACE_HTML = """
<p>Kho tàng truyện cổ tích và truyền thuyết Việt Nam là dòng chảy văn hóa tinh thần bất tận đã nuôi dưỡng tâm hồn của biết bao thế hệ con người đất Việt từ thuở nằm nôi. Qua từng câu chuyện, ông cha ta đã gửi gắm những khát vọng ngàn đời về công lý, lẽ công bằng: <em>"Ở hiền gặp lành, ác giả ác báo"</em>, ngợi ca lòng hiếu thảo, tình nghĩa thủy chung son sắt, ý chí quật cường chống ngoại xâm và tinh thần tự lực cánh sinh vượt qua mọi nghịch cảnh.</p>

<p>Trong ấn bản đặc biệt <strong>Kho Tàng Truyện Cổ Tích Việt Nam</strong> này, chúng tôi tuyển chọn <strong>20 tác phẩm kiệt xuất và thiêng liêng nhất</strong> của văn học dân gian Việt Nam:</p>
<ul>
  <li><strong>Những câu chuyện cổ tích kỳ ảo giàu triết lý nhân sinh:</strong> <em>Tấm Cám, Thạch Sanh, Cây Tre Trăm Đốt, Sọ Dừa, Sự Tích Cây Khế, Cậu Bé Thông Minh, Hồn Trương Ba Da Hàng Thịt...</em></li>
  <li><strong>Những thiên anh hùng ca và truyền thuyết dựng nước, giữ nước:</strong> <em>Thánh Gióng, Sơn Tinh - Thủy Tinh, Sự Tích Hồ Gươm, Chử Đồng Tử, Mỵ Châu - Trọng Thủy...</em></li>
  <li><strong>Những thiên tình sử và nguồn gốc sản vật dân tộc:</strong> <em>Sự Tích Trầu Cau, Bánh Chưng Bánh Giầy, Quả Dưa Hấu (Mai An Tiêm), Chú Cuội Cung Trăng, Hoa Cúc Trắng...</em></li>
</ul>

<p>Mỗi câu chuyện được biên soạn với phong cách văn xuôi hiện đại, trong sáng, nhịp điệu sinh động và trau chuốt, nhưng gìn giữ trọn vẹn 100% cốt cách tinh thần dân tộc, các chi tiết kỳ ảo cốt lõi và các câu ca dao, đồng dao bất hủ đã in sâu vào tiềm thức người Việt.</p>

<p>Kính chúc bạn đọc cùng gia đình có những giây phút thưởng thức trọn vẹn, tìm lại hơi ấm của cội nguồn và những bài học nhân văn sâu sắc qua từng trang sách!</p>
"""

VIETNAM_BOOK = {
    'id': 'urn:uuid:vietnamese-fairy-tales-vn-2026',
    'title': 'Truyện Cổ Tích Việt Nam',
    'subtitle': 'Kho Tàng Dân Gian Kinh Điển Chọn Lọc',
    'author': 'Văn Học Dân Gian Việt Nam',
    'cover_image_path': '/Users/win/Documents/đọc sách/build_fairy_tales/assets/cover_vietnam.jpg',
    'bg_rgb': (100, 15, 20),       # Royal lacquer crimson
    'border_rgb': (220, 180, 70),  # Traditional bronze gold
    'preface_html': VN_PREFACE_HTML,
    'stories': VN_STORIES_PART1 + VN_STORIES_PART2
}
