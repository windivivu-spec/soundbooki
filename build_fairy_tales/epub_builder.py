import os
import zipfile
import uuid
import datetime
from PIL import Image, ImageDraw, ImageFont

CSS_CONTENT = """
@charset "utf-8";

@page {
    margin: 1.5cm 1cm;
}

body {
    font-family: "Merriweather", "Times New Roman", "Palatino Linotype", "Georgia", serif;
    font-size: 1.05em;
    line-height: 1.75;
    color: #222222;
    background-color: #faf9f6;
    margin: 0;
    padding: 0 1.5em;
    text-rendering: optimizeLegibility;
}

h1, h2, h3, h4 {
    font-family: "Georgia", "Times New Roman", serif;
    font-weight: bold;
    color: #1a1a1a;
    text-align: center;
    line-height: 1.3;
}

.chapter-container {
    max-width: 780px;
    margin: 0 auto;
    padding: 1.5em 0 3em 0;
}

.chapter-header {
    text-align: center;
    margin-bottom: 2em;
    padding-top: 1em;
}

.chapter-title {
    font-size: 2em;
    margin: 0.2em 0 0.8em 0;
    color: #1a2a3a;
}

.chapter-body p {
    text-indent: 1.8em;
    margin: 0 0 0.8em 0;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

.chapter-body p:first-of-type {
    text-indent: 0;
}

.chapter-body p:first-of-type::first-letter {
    font-size: 3em;
    float: left;
    line-height: 0.85;
    margin: 0.08em 0.12em 0 0;
    font-family: "Georgia", serif;
    color: #8b6508;
    font-weight: bold;
}

.section-break {
    border: 0;
    height: 1px;
    background: #d8cebe;
    margin: 2.2em auto;
    width: 35%;
}

blockquote {
    font-style: italic;
    color: #4a5568;
    border-left: 3px solid #c5a059;
    margin: 1.5em 2em;
    padding: 0.5em 1em;
    background-color: #f7f5f0;
    border-radius: 4px;
}

.verse {
    text-align: center;
    font-style: italic;
    color: #2c3e50;
    margin: 1.5em auto;
    line-height: 1.8;
}

.toc-list {
    list-style-type: none;
    padding: 0;
    max-width: 650px;
    margin: 1.5em auto;
}

.toc-item {
    margin: 0.8em 0;
    border-bottom: 1px dotted #cbd5e0;
    padding-bottom: 0.4em;
}

.toc-item a {
    text-decoration: none;
    color: #2b6cb0;
    font-size: 1.1em;
    display: flex;
    justify-content: space-between;
}

.toc-item a:hover {
    color: #c53030;
}
"""

def generate_cover_image(out_path, title, author, subtitle, bg_rgb, border_rgb):
    width, height = 1600, 2400
    img = Image.new('RGB', (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)
    
    margin = 90
    draw.rectangle([margin, margin, width - margin, height - margin], outline=border_rgb, width=7)
    draw.rectangle([margin + 24, margin + 24, width - margin - 24, height - margin - 24], outline=border_rgb, width=2)

    font_title = ImageFont.truetype('/System/Library/Fonts/Supplemental/Times New Roman.ttf', 92)
    font_sub = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia.ttf', 44)
    font_author = ImageFont.truetype('/System/Library/Fonts/Supplemental/Times New Roman.ttf', 56)
    font_footer = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia.ttf', 36)

    draw.text((width/2, 500), subtitle, fill=border_rgb, font=font_sub, anchor='mm')
    draw.text((width/2, 750), title, fill=(255, 255, 255), font=font_title, anchor='mm')
    draw.text((width/2, 1750), author, fill=(245, 240, 225), font=font_author, anchor='mm')
    draw.text((width/2, 2150), 'ẤN BẢN ĐẶC BIỆT • 2026', fill=(190, 190, 190), font=font_footer, anchor='mm')

    img.save(out_path, quality=95)


def build_epub(book_data, output_filepath):
    """
    Streamlined EPUB builder optimized for reading and audiobook generation:
    - Cover page (cover.xhtml)
    - Table of contents (toc.xhtml)
    - Directly to Story 1, Story 2... (No intro/preface/titlepage to keep audiobook clean)
    """
    tmp_dir = os.path.join(os.path.dirname(output_filepath), f"tmp_{uuid.uuid4().hex[:8]}")
    oebps_dir = os.path.join(tmp_dir, "OEBPS")
    meta_dir = os.path.join(tmp_dir, "META-INF")
    os.makedirs(oebps_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)

    # 1. mimetype (first file, uncompressed)
    with open(os.path.join(tmp_dir, "mimetype"), "w", encoding="utf-8") as f:
        f.write("application/epub+zip")

    # 2. container.xml
    with open(os.path.join(meta_dir, "container.xml"), "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")

    # 3. CSS
    with open(os.path.join(oebps_dir, "stylesheet.css"), "w", encoding="utf-8") as f:
        f.write(CSS_CONTENT)

    # 4. Cover Image
    cover_img_path = os.path.join(oebps_dir, "cover.jpg")
    if book_data.get('cover_image_path') and os.path.exists(book_data['cover_image_path']):
        import shutil
        shutil.copy2(book_data['cover_image_path'], cover_img_path)
    else:
        generate_cover_image(
            cover_img_path,
            book_data['title'].upper(),
            book_data['author'].upper(),
            book_data['subtitle'].upper(),
            book_data['bg_rgb'],
            book_data['border_rgb']
        )

    # 5. Cover HTML
    with open(os.path.join(oebps_dir, "cover.xhtml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="vi" lang="vi">
<head>
  <title>Bìa sách</title>
  <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
  <style>
    body {{ margin: 0; padding: 0; text-align: center; background-color: #000; }}
    img {{ max-width: 100%; height: auto; max-height: 100vh; object-fit: contain; }}
  </style>
</head>
<body>
  <div>
    <img src="cover.jpg" alt="{book_data['title']}"/>
  </div>
</body>
</html>""")

    # 6. Table of Contents HTML (Immediate start: Cover -> TOC -> Stories)
    toc_items_html = ""
    for idx, story in enumerate(book_data['stories'], 1):
        t_name = story['title'].strip()
        if not t_name.endswith(('.', '!', '?')):
            t_name += '.'
        toc_items_html += f"""      <li class="toc-item">
        <a href="{story['id']}.xhtml">
          <span>{idx:02d}. {t_name}</span>
        </a>
      </li>\n"""

    with open(os.path.join(oebps_dir, "toc.xhtml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="vi" lang="vi">
<head>
  <title>Mục lục.</title>
  <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
</head>
<body>
  <div class="chapter-container">
    <div class="chapter-header">
      <h1 class="chapter-title">Mục Lục.</h1>
    </div>
    <ul class="toc-list">
{toc_items_html}
    </ul>
  </div>
</body>
</html>""")

    # 7. Story chapters (Clean headings with punctuation mark to ensure TTS pause before story body)
    import re
    for idx, story in enumerate(book_data['stories'], 1):
        story_file = os.path.join(oebps_dir, f"{story['id']}.xhtml")
        
        # Clean section-break text inside story content so TTS doesn't read decorative symbols like ❖ or ✦
        cleaned_content = re.sub(r'<div class="section-break">[^<]*</div>', '<hr class="section-break"/>', story['content_html'])

        # Add period after story title to ensure speech synthesis engine pauses before reading main story
        heading_title = story['title'].strip()
        if not heading_title.endswith(('.', '!', '?')):
            heading_title += '.'

        with open(story_file, "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="vi" lang="vi">
<head>
  <title>{story['title']}</title>
  <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
</head>
<body>
  <div class="chapter-container">
    <div class="chapter-header">
      <h1 class="chapter-title">{heading_title}</h1>
    </div>
    <div class="chapter-body">
      {cleaned_content}
    </div>
  </div>
</body>
</html>""")

    # 8. Nav.xhtml (EPUB 3) - Only Cover, TOC, and Story list
    nav_li_html = ""
    for idx, story in enumerate(book_data['stories'], 1):
        nav_li_html += f'      <li><a href="{story["id"]}.xhtml">{idx:02d}. {story["title"]}</a></li>\n'

    with open(os.path.join(oebps_dir, "nav.xhtml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="vi" lang="vi">
<head>
  <title>Mục lục Navigation</title>
  <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Mục lục</h1>
    <ol>
      <li><a href="cover.xhtml">Bìa sách</a></li>
      <li><a href="toc.xhtml">Mục lục</a></li>
{nav_li_html}
    </ol>
  </nav>
</body>
</html>""")

    # 9. toc.ncx (EPUB 2) - Streamlined
    from xml.sax.saxutils import escape as xml_escape
    esc_title = xml_escape(book_data['title'])
    esc_author = xml_escape(book_data['author'])
    esc_subtitle = xml_escape(book_data['subtitle'])

    ncx_points = f"""    <navPoint id="np-cover" playOrder="1">
      <navLabel><text>Bìa sách</text></navLabel>
      <content src="cover.xhtml"/>
    </navPoint>
    <navPoint id="np-toc" playOrder="2">
      <navLabel><text>Mục lục</text></navLabel>
      <content src="toc.xhtml"/>
    </navPoint>"""

    for idx, story in enumerate(book_data['stories'], 1):
        esc_story_title = xml_escape(story['title'])
        ncx_points += f"""
    <navPoint id="np-{story['id']}" playOrder="{idx+2}">
      <navLabel><text>{idx:02d}. {esc_story_title}</text></navLabel>
      <content src="{story['id']}.xhtml"/>
    </navPoint>"""

    with open(os.path.join(oebps_dir, "toc.ncx"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_data['id']}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{esc_title}</text>
  </docTitle>
  <docAuthor>
    <text>{esc_author}</text>
  </docAuthor>
  <navMap>
{ncx_points}
  </navMap>
</ncx>""")

    # 10. content.opf
    manifest_items = """    <item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>
    <item id="stylesheet" href="stylesheet.css" media-type="text/css"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml"/>"""

    spine_items = """    <itemref idref="cover"/>
    <itemref idref="toc"/>"""

    for story in book_data['stories']:
        manifest_items += f'\n    <item id="{story["id"]}" href="{story["id"]}.xhtml" media-type="application/xhtml+xml"/>'
        spine_items += f'\n    <itemref idref="{story["id"]}"/>'

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(os.path.join(oebps_dir, "content.opf"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookID">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookID">{book_data['id']}</dc:identifier>
    <dc:title>{esc_title}</dc:title>
    <dc:creator>{esc_author}</dc:creator>
    <dc:language>vi</dc:language>
    <dc:date>{now_iso}</dc:date>
    <dc:publisher>Soundbooki</dc:publisher>
    <dc:description>{esc_subtitle}</dc:description>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
{manifest_items}
  </manifest>
  <spine toc="ncx">
{spine_items}
  </spine>
  <guide>
    <reference type="cover" title="Cover" href="cover.xhtml"/>
    <reference type="toc" title="Table of Contents" href="toc.xhtml"/>
  </guide>
</package>""")

    # 11. Package to zip
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    if os.path.exists(output_filepath):
        os.remove(output_filepath)

    with zipfile.ZipFile(output_filepath, "w") as zf:
        # First file MUST be mimetype with ZIP_STORED
        mimetype_path = os.path.join(tmp_dir, "mimetype")
        zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        # Remaining files
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                if file == "mimetype":
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, tmp_dir)
                zf.write(full_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)

    # Clean up tmp_dir
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Built streamlined EPUB successfully: {output_filepath} ({os.path.getsize(output_filepath):,} bytes)")
