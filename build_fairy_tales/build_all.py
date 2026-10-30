# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
from epub_builder import build_epub
from grimm_data import GRIMM_BOOK
from andersen_data import ANDERSEN_BOOK

OUTPUT_DIR = "/Users/win/Documents/đọc sách/output"
DOWNLOADS_DIR = "/Users/win/Downloads"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def build_and_verify(book_data, filename_base):
    out_epub = os.path.join(OUTPUT_DIR, f"{filename_base}.epub")
    print(f"\n==========================================")
    print(f"Building: {book_data['title']} ({len(book_data['stories'])} stories)")
    build_epub(book_data, out_epub)

    # Copy to Downloads
    dl_epub = os.path.join(DOWNLOADS_DIR, f"{filename_base}.epub")
    shutil.copy2(out_epub, dl_epub)
    print(f"Copied to Downloads: {dl_epub}")

    # Verify EPUB
    with zipfile.ZipFile(out_epub, 'r') as zf:
        namelist = zf.namelist()
        assert namelist[0] == "mimetype", "First file must be mimetype!"
        assert zf.read("mimetype").decode("utf-8") == "application/epub+zip", "Mimetype content mismatch!"
        assert "META-INF/container.xml" in namelist, "Missing container.xml"
        assert "OEBPS/content.opf" in namelist, "Missing content.opf"
        assert "OEBPS/toc.ncx" in namelist, "Missing toc.ncx"
        assert "OEBPS/nav.xhtml" in namelist, "Missing nav.xhtml"
        assert "OEBPS/cover.jpg" in namelist, "Missing cover.jpg"
        
        # Count total Vietnamese words
        total_words = 0
        for story in book_data['stories']:
            # strip html tags roughly
            import re
            text = re.sub(r'<[^>]+>', ' ', story['content_html'])
            total_words += len(text.split())

        size_kb = os.path.getsize(out_epub) / 1024
        print(f"VERIFIED: {out_epub}")
        print(f"  - Size: {size_kb:.1f} KB")
        print(f"  - Total Vietnamese words in stories: ~{total_words:,} words")
        print(f"  - Total chapters: {len(book_data['stories'])}")

if __name__ == "__main__":
    build_and_verify(GRIMM_BOOK, "Tuyen_Tap_Truyen_Co_Grimm_Tieng_Viet")
    build_and_verify(ANDERSEN_BOOK, "Tuyen_Tap_Truyen_Co_Andersen_Tieng_Viet")
    print("\nALL EPUB FILES BUILT AND VALIDATED SUCCESSFULLY!")
