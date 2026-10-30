import { createServer } from 'node:http';
import { Readable } from 'node:stream';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createCommerce } from './service.mjs';
const service=await createCommerce();
const files={'/':['index.html','text/html; charset=utf-8'],'/checkout.js':['checkout.js','text/javascript; charset=utf-8'],'/checkout.css':['checkout.css','text/css; charset=utf-8']};
const server=createServer(async(req,res)=>{
  try {
    const path=new URL(req.url,'http://localhost').pathname;
    res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');
    res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://img.vietqr.io; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    res.setHeader('Cache-Control','no-store');
    if(req.method==='GET'&&files[path]) {
      const [name,type]=files[path];res.setHeader('Content-Type',type);res.end(await readFile(fileURLToPath(new URL('public/'+name,import.meta.url))));return;
    }
    const request=new Request(new URL(req.url,process.env.WSN_PUBLIC_ORIGIN),{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Readable.toWeb(req),duplex:'half'}:{})});
    const response=await service.handle(request,{ip:req.socket.remoteAddress||'unknown'});
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  }catch{res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Dịch vụ tạm thời gián đoạn.'}));}
});
server.requestTimeout=15000;server.headersTimeout=10000;
server.listen(Number(process.env.PORT||8789),process.env.HOST||'127.0.0.1',()=>process.stdout.write('Windi Sách Nói checkout is listening.\n'));
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(async()=>{await service.close();process.exit(0);}));
