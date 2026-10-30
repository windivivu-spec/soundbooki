from pathlib import Path
import json, subprocess, sys, zipfile, uuid
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'backend'))
from core import Library
folder=root/'.qa/app-shell';lib=Library(folder/('library-'+uuid.uuid4().hex))
book=lib.create([root/'.qa/fixtures-data/text-viet.pdf'])
for line in subprocess.check_output([str(root/'.build/windi-extract'),str(root/'.qa/fixtures-data/text-viet.pdf'),'0'],text=True).splitlines():
    page=json.loads(line)
    if 'page' in page:lib.add_page(book,0,page)
book.update(title='Những trang sách Việt',status='ready');lib.save(book)
epub=folder/'Sách có bìa.epub'
with zipfile.ZipFile(epub,'w') as z:
    z.writestr('mimetype','application/epub+zip')
    z.writestr('META-INF/container.xml','<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
    z.writestr('OPS/book.opf','<package><metadata><title>Sách có bìa tiếng Việt</title></metadata><manifest><item id="body" href="body.xhtml" media-type="application/xhtml+xml"/><item id="cover" href="cover.png" media-type="image/png" properties="cover-image"/></manifest><spine><itemref idref="body"/></spine></package>')
    z.writestr('OPS/body.xhtml','<html><body><h1>Chương một</h1><p>Sách giữ nguyên tiếng Việt, những dấu câu và nội dung ban đầu.</p></body></html>')
    z.write(root/'.qa/fixtures-data/chu-viet.png','OPS/cover.png')
(folder/'fixture.json').write_text(json.dumps(dict(bookID=book['id'],library=str(lib.root),epub=str(epub)),ensure_ascii=False))
