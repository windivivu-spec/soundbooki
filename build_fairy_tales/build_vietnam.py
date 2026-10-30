# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
from epub_builder import build_epub
from vietnam_data import VIETNAM_BOOK

OUTPUT_DIR = "/Users/win/Documents/đọc sách/output"
DOWNLOADS_DIR = "/Users/win/Downloads"

def build_vn_epub():
    out_epub = os.path.join(OUTPUT_DIR, "Kho_Tang_Truyen_Co_Tich_Viet_Nam.epub")
    print(f"\n==========================================")
    print(f"Building: {VIETNAM_BOOK['title']} ({len(VIETNAM_BOOK['stories'])} stories)")
    build_epub(VIETNAM_BOOK, out_epub)

    # Copy to Downloads
    dl_epub = os.path.join(DOWNLOADS_DIR, "Kho_Tang_Truyen_Co_Tich_Viet_Nam.epub")
    shutil.copy2(out_epub, dl_epub)
    print(f"Copied to Downloads: {dl_epub}")

    # Verify EPUB
    with zipfile.ZipFile(out_epub, 'r') as zf:
        namelist = zf.namelist()
        assert namelist[0] == "mimetype", "First file must be mimetype!"
        assert zf.read("mimetype").decode("utf-8") == "application/epub+zip", "Mimetype mismatch!"
        assert "META-INF/container.xml" in namelist
        assert "OEBPS/content.opf" in namelist
        assert "OEBPS/toc.ncx" in namelist
        assert "OEBPS/nav.xhtml" in namelist
        assert "OEBPS/cover.jpg" in namelist
        
        # Count words
        import re
        total_words = 0
        for story in VIETNAM_BOOK['stories']:
            text = re.sub(r'<[^>]+>', ' ', story['content_html'])
            total_words += len(text.split())

        size_kb = os.path.getsize(out_epub) / 1024
        print(f"VERIFIED: {out_epub}")
        print(f"  - Size: {size_kb:.1f} KB")
        print(f"  - Total Vietnamese words: ~{total_words:,} words")
        print(f"  - Total chapters: {len(VIETNAM_BOOK['stories'])}")

if __name__ == "__main__":
    build_vn_epub()
