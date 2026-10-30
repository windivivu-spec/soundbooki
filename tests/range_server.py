"""Local-only static QA server with single HTTP byte-range support for audio."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'.qa/enhanced-web'),**kw)
    def send_head(self):
        self.remaining=None
        path=Path(self.translate_path(self.path))
        if not path.is_file():return super().send_head()
        size=path.stat().st_size;first=0;last=max(0,size-1)
        header=self.headers.get('Range')
        if header:
            m=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
            if not m or not any(m.groups()):self.send_error(416);return None
            if m[1]:first=int(m[1]);last=min(last,int(m[2])) if m[2] else last
            else:first=max(0,size-int(m[2]))
            if first>=size or first>last:self.send_error(416);return None
        f=path.open('rb');f.seek(first);self.remaining=last-first+1
        self.send_response(206 if header else 200)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(self.remaining))
        self.send_header('Cache-Control','no-store')
        if header:self.send_header('Content-Range',f'bytes {first}-{last}/{size}')
        self.end_headers();return f
    def copyfile(self,source,out):
        if self.remaining is None:return super().copyfile(source,out)
        while self.remaining:
            data=source.read(min(65536,self.remaining))
            if not data:break
            out.write(data);self.remaining-=len(data)
if __name__=='__main__':
    (ROOT/'.qa/range-server.pid').write_text(str(os.getpid()))
    print('QA player: http://127.0.0.1:4174/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',4174),Handler).serve_forever()
