# -*- coding: utf-8 -*-
from andersen_stories_part1 import STORIES_PART1
from andersen_stories_part2 import STORIES_PART2

ANDERSEN_PREFACE_HTML = """
<p>Hans Christian Andersen (1805–1875), đại văn hào vĩ đại của Đan Mạch, được tôn vinh là "Ông hoàng truyện cổ tích thế giới". Khác với những câu chuyện dân gian truyền khẩu thông thường, những câu chuyện của Andersen là những kiệt tác văn chương đầy chất thơ, thấm đẫm lòng trắc ẩn, tính nhân văn sâu sắc và sự thấu hiểu vô bờ đối với những mảnh đời bất hạnh, nhỏ bé.</p>

<p>Trong ấn bản tuyển tập tinh hoa này, chúng tôi mang đến cho độc giả Việt Nam <strong>18 tác phẩm kinh điển và kiệt xuất nhất</strong> của Andersen: từ nỗi niềm thương xót khôn nguôi trong <em>Cô Bé Bán Diêm</em>, bản tình ca bi tráng và linh hồn bất tử của <em>Nàng Tiên Cá</em>, hành trình vươn mình rực rỡ của <em>Chú Vịt Con Xấu Xí</em>, tiếng cười châm biếm sâu cay trong <em>Bộ Quần Áo Mới Của Hoàng Đế</em>, cho đến sức mạnh kỳ diệu của lòng nhân ái trong <em>Bà Chúa Tuyết</em>...</p>

<p>Bản dịch được thực hiện với văn phong hiện đại, trau chuốt từng câu chữ, giàu hình tượng nghệ thuật nhưng tuyệt đối tôn trọng cốt truyện nguyên tác và giữ trọn hệ thống danh xưng thân quen đã gắn liền với ký ức tuổi thơ của độc giả Việt Nam suốt nhiều thế hệ.</p>

<p>Hy vọng cuốn sách sẽ là chiếc cầu nối đưa bạn đọc trở về với miền cổ tích diệu kỳ, nơi vẻ đẹp của lòng thiện lương, tình yêu thương và sự can trường mãi mãi tỏa sáng!</p>
"""

ANDERSEN_BOOK = {
    'id': 'urn:uuid:andersen-fairy-tales-vn-2026',
    'title': 'Truyện Cổ Andersen',
    'subtitle': 'Tuyển Tập Tinh Hoa Kinh Điển',
    'author': 'Hans Christian Andersen',
    'cover_image_path': '/Users/win/Documents/đọc sách/build_fairy_tales/assets/cover_andersen.jpg',
    'bg_rgb': (12, 27, 51),       # Deep celestial navy
    'border_rgb': (212, 175, 55),  # Classic gold
    'preface_html': ANDERSEN_PREFACE_HTML,
    'stories': STORIES_PART1 + STORIES_PART2
}
