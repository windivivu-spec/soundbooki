# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
from epub_builder import build_epub
from grimm_data import GRIMM_BOOK
from andersen_data import ANDERSEN_BOOK
from vietnam_data import VIETNAM_BOOK

OUTPUT_DIR = "/Users/win/Documents/đọc sách/output"
DOWNLOADS_DIR = "/Users/win/Downloads"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def build_book(book_data, filename_base):
    out_epub = os.path.join(OUTPUT_DIR, f"{filename_base}.epub")
    print(f"\n==========================================")
    print(f"Building streamlined: {book_data['title']} ({len(book_data['stories'])} stories)")
    build_epub(book_data, out_epub)

    # Copy to Downloads
    dl_epub = os.path.join(DOWNLOADS_DIR, f"{filename_base}.epub")
    shutil.copy2(out_epub, dl_epub)
    print(f"Copied to Downloads: {dl_epub}")

    # Verify EPUB structure
    with zipfile.ZipFile(out_epub, 'r') as zf:
        namelist = zf.namelist()
        assert namelist[0] == "mimetype", "First file must be mimetype!"
        assert "OEBPS/toc.xhtml" in namelist, "Missing toc.xhtml"
        assert "OEBPS/titlepage.xhtml" not in namelist, "titlepage should be removed!"
        assert "OEBPS/preface.xhtml" not in namelist, "preface should be removed!"
        
        # Verify spine in content.opf
        opf_content = zf.read("OEBPS/content.opf").decode("utf-8")
        assert "titlepage" not in opf_content
        assert "preface" not in opf_content

        size_kb = os.path.getsize(out_epub) / 1024
        print(f"VERIFIED: {out_epub}")
        print(f"  - Size: {size_kb:.1f} KB")
        print(f"  - Stories: {len(book_data['stories'])}")
        print(f"  - Spine items: cover -> toc -> {book_data['stories'][0]['id']} -> ...")

if __name__ == "__main__":
    build_book(ANDERSEN_BOOK, "Tuyen_Tap_Truyen_Co_Andersen_Tieng_Viet")
    build_book(GRIMM_BOOK, "Tuyen_Tap_Truyen_Co_Grimm_Tieng_Viet")
    build_book(VIETNAM_BOOK, "Kho_Tang_Truyen_Co_Tich_Viet_Nam")
    print("\nALL 3 STREAMLINED EPUB BOOKS REBUILT SUCCESSFULLY FOR AUDIOBOOK GENERATION!")
