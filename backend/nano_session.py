"""A single local Nano process, reused without changing audio/cache settings."""
import json
from pathlib import Path
import subprocess
import sys
import threading


class NanoSession:
    def __init__(self, root, log):
        self.root=Path(root);self.log=Path(log)
        self.lock=threading.Lock();self.process=None;self.stderr=None;self.closed=False;self.model_key=None

    def stream(self, request, job):
        with self.lock:
            if self.closed or job['cancel'].is_set():return
            key=(request['models'],request.get('revision'))
            if self.process is None or self.process.poll() is not None or key!=self.model_key:
                self._dispose()
                self.log.parent.mkdir(parents=True,exist_ok=True)
                self.stderr=self.log.open('ab')
                self.process=subprocess.Popen([sys.executable,'-B',str(self.root/'backend/engine.py'),'--serve-nano'],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True)
                self.model_key=key
            p=self.process;job['process']=p
            if self.closed or job['cancel'].is_set():
                job['process']=None;return
            error=None
            try:
                p.stdin.write(json.dumps(request,ensure_ascii=False)+'\n');p.stdin.flush()
                for line in p.stdout:
                    value=json.loads(line)
                    if value.get('requestDone'):
                        if error:raise ValueError(error)
                        return
                    if 'error' in value:error=value['error']
                    elif not job['cancel'].is_set():yield value
                if not job['cancel'].is_set():raise ValueError('Bộ đọc Nano bị gián đoạn. Hãy bấm nghe để thử lại.')
            finally:
                job['process']=None
                if p.poll() is not None:self._dispose()

    def _dispose(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            for pipe in (self.process.stdin,self.process.stdout):
                if pipe:pipe.close()
        if self.stderr:self.stderr.close()
        self.process=None;self.stderr=None

    def close(self):
        # Shutdown may interrupt inference. Only atomic, completed files are usable.
        self.closed=True
        p=self.process
        if p and p.poll() is None:p.terminate()
        with self.lock:self._dispose()
