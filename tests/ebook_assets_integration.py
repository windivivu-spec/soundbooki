"""Real PDF image placements/crops using a private, synthetic local fixture."""
from pathlib import Path
import io
import json
import subprocess
import sys
import time
import uuid
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from core import Library
from ebook_reader import prepare
folder=ROOT/'.qa/ebook-assets'/uuid.uuid4().hex;folder.mkdir(parents=True)
image=Image.new('RGB',(200,100),'#e71d36')
for x in range(100,200):
    for y in range(100):image.putpixel((x,y),(0,100,240))
buf=io.BytesIO();image.save(buf,format='JPEG',quality=95);jpeg=buf.getvalue()
content=b'q 200 0 0 100 100 250 cm /Im0 Do Q\nBT /F1 18 Tf 50 700 Td (Vietnamese image fixture.) Tj ET'
objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /XObject << /Im0 4 0 R >> /Font << /F1 6 0 R >> >> /Contents 5 0 R >>',b'<< /Type /XObject /Subtype /Image /Width 200 /Height 100 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '+str(len(jpeg)).encode()+b' >>\nstream\n'+jpeg+b'\nendstream',b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
pdf=bytearray(b'%PDF-1.4\n');offsets=[0]
for i,obj in enumerate(objects,1):offsets.append(len(pdf));pdf+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
xref=len(pdf);pdf+=b'xref\n0 7\n0000000000 65535 f \n'
for offset in offsets[1:]:pdf+=f'{offset:010d} 00000 n \n'.encode()
pdf+=f'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode();source=folder/'fixture.pdf';source.write_bytes(pdf)
lib=Library(folder/'library');book=lib.create([source]);lib.add_page(book,0,dict(page=0,text='Vietnamese image fixture.',method='text',warning=''));book['status']='ready';lib.save(book)
started=time.monotonic();data,path=prepare(lib,book);assert len(data['figures'])==1
figure=data['figures'][0];assert abs(figure['y']-.5625)<.01 and abs(figure['bottom']-.6875)<.01
crop=Image.open(path.parent/'images'/figure['file']);assert crop.size==(400,200),crop.size
red=crop.getpixel((50,100));blue=crop.getpixel((350,100));assert red[0]>180 and red[2]<100,(red,blue);assert blue[2]>150 and blue[0]<100,(red,blue)
assert figure['image'].startswith('data:image/jpeg;base64,')
result=dict(result='PASS',seconds=round(time.monotonic()-started,2),crop=list(crop.size),sourcePage=figure['page'],cloudRequests=0,epub=str(path));(folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
