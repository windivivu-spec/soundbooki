# -*- coding: utf-8 -*-
from grimm_stories_part1 import STORIES_PART1
from grimm_stories_part2 import STORIES_PART2

GRIMM_PREFACE_HTML = """
<p>Truyện cổ Grimm (<em>Kinder- und Hausmärchen</em>) do hai anh em học giả người Đức Jacob Grimm (1785–1863) và Wilhelm Grimm (1786–1859) dày công sưu tầm và ghi chép, là một trong những di sản văn học dân gian vĩ đại và trường tồn nhất của nhân loại.</p>

<p>Hơn hai thế kỷ qua, những câu chuyện về lòng dũng cảm, sự thông minh, đức hy sinh và tình người đã nuôi dưỡng tâm hồn biết bao thế hệ độc giả trên khắp địa cầu. Trong ấn bản đặc biệt này, chúng tôi tuyển chọn <strong>18 truyện cổ tích tinh hoa và quen thuộc nhất</strong> với bạn đọc Việt Nam, được chuyển ngữ theo phong cách văn xuôi hiện đại, trong sáng, nhịp điệu sinh động và giàu cảm xúc.</p>

<p>Bản dịch giữ trọn vẹn toàn bộ cốt truyện nguyên tác, các chi tiết kỳ ảo đặc sắc và thông điệp nhân văn bất hủ, đồng thời sử dụng hệ thống tên gọi nhân vật đã trở nên thân thương, gần gũi với tuổi thơ của độc giả Việt Nam nhiều thế hệ như: <em>Cô Bé Quàng Khăn Đỏ, Nàng Bạch Tuyết, Hansel và Gretel, Cô Bé Lọ Lem, Hoàng Tử Ếch, Công Chúa Ngủ Trong Rừng...</em></p>

<p>Kính chúc quý độc giả có những phút giây phiêu lưu kỳ thú và tìm lại những miền ký ức trong trẻo nhất qua từng trang sách!</p>
"""

GRIMM_BOOK = {
    'id': 'urn:uuid:grimm-fairy-tales-vn-2026',
    'title': 'Truyện Cổ Grimm',
    'subtitle': 'Tuyển Tập Tinh Hoa Kinh Điển',
    'author': 'Jacob & Wilhelm Grimm',
    'cover_image_path': '/Users/win/Documents/đọc sách/build_fairy_tales/assets/cover_grimm.jpg',
    'bg_rgb': (15, 43, 30),       # Deep pine emerald
    'border_rgb': (212, 175, 55),  # Classic gold
    'preface_html': GRIMM_PREFACE_HTML,
    'stories': STORIES_PART1 + STORIES_PART2
}
