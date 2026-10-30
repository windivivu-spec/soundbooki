# -*- coding: utf-8 -*-
import os
import shutil
from epub_builder import build_epub
from grimm_data import GRIMM_BOOK
from andersen_data import ANDERSEN_BOOK

OUTPUT_DIR = "/Users/win/Documents/đọc sách/output"
DOWNLOADS_DIR = "/Users/win/Downloads"

COMBINED_PREFACE_HTML = """
<p>Tuyển tập <strong>Cổ Tích Kinh Điển Thế Giới: Tuyển Tập Grimm & Andersen</strong> là sự hội ngộ diệu kỳ giữa hai đỉnh cao văn học dân gian và huyền thoại châu Âu: <strong>Anh em nhà Grimm</strong> (Đức) và <strong>Hans Christian Andersen</strong> (Đan Mạch).</p>

<p>Cuốn sách tuyển chọn <strong>36 tác phẩm kiệt xuất và bất hủ nhất</strong>, được phân định thành hai phần tác giả rõ ràng:</p>
<ul>
  <li><strong>Phần I – Truyện Cổ Grimm (18 tác phẩm):</strong> Những câu chuyện kỳ ảo dân gian mộc mạc, đậm chất phiêu lưu, ca ngợi lòng can trường, sự khôn ngoan và đạo lý nhân quả ở đời (<em>Bạch Tuyết, Lọ Lem, Hansel & Gretel, Khăn Đỏ, Hoàng Tử Ếch...</em>).</li>
  <li><strong>Phần II – Truyện Cổ Andersen (18 tác phẩm):</strong> Những áng văn lãng mạn, giàu chất thơ, thấm đẫm lòng trắc ẩn, tình mẫu tử và khát vọng về cái đẹp và linh hồn bất tử (<em>Nàng Tiên Cá, Cô Bé Bán Diêm, Vịt Con Xấu Xí, Bà Chúa Tuyết, Họa Mi...</em>).</li>
</ul>

<p>Toàn bộ các tác phẩm được dịch mới sang tiếng Việt với văn phong hiện đại, tự nhiên, nhịp văn sống động và giàu cảm xúc, nhưng giữ trọn vẹn 100% cốt truyện nguyên tác và hệ thống tên gọi thân thương đã quen thuộc với nhiều thế hệ độc giả Việt Nam.</p>
"""

# Re-index stories for combined book
combined_stories = []
for s in GRIMM_BOOK['stories']:
    combined_stories.append({
        'id': f"c_{s['id']}",
        'title': f"[Grimm] {s['title']}",
        'subtitle': s['subtitle'],
        'content_html': s['content_html']
    })

for s in ANDERSEN_BOOK['stories']:
    combined_stories.append({
        'id': f"c_{s['id']}",
        'title': f"[Andersen] {s['title']}",
        'subtitle': s['subtitle'],
        'content_html': s['content_html']
    })

COMBINED_BOOK = {
    'id': 'urn:uuid:combined-fairy-tales-andersen-grimm-vn-2026',
    'title': 'Cổ Tích Kinh Điển Thế Giới',
    'subtitle': 'Tuyển Tập Tinh Hoa Andersen & Grimm',
    'author': 'H. C. Andersen & Anh Em Grimm',
    'bg_rgb': (20, 24, 40),       # Royal midnight navy
    'border_rgb': (218, 165, 32),  # Golden rod
    'preface_html': COMBINED_PREFACE_HTML,
    'stories': combined_stories
}

if __name__ == "__main__":
    out_epub = os.path.join(OUTPUT_DIR, "Tuyen_Tap_Co_Tich_Andersen_Va_Grimm_Tieng_Viet.epub")
    build_epub(COMBINED_BOOK, out_epub)
    dl_epub = os.path.join(DOWNLOADS_DIR, "Tuyen_Tap_Co_Tich_Andersen_Va_Grimm_Tieng_Viet.epub")
    shutil.copy2(out_epub, dl_epub)
    print(f"Combined EPUB created successfully at: {dl_epub}")
