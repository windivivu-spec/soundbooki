import {createServer} from 'node:http';
import {readFileSync,statSync,existsSync} from 'node:fs';
import {resolve,dirname,extname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';
const args=process.argv.slice(2),arg=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const site=resolve(dirname(fileURLToPath(import.meta.url)),'..'),root=resolve(site,arg('--dir','.')),port=Number(arg('--port',process.env.PORT||'4173'));
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.mp3':'audio/mpeg','.woff2':'font/woff2'};
const compressed=new Map();
const server=createServer((req,res)=>{
 try{
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);res.end();return;}
  let name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(name==='/')name='/index.html';
  const path=resolve(root,'.'+name);
  if(!path.startsWith(root+sep)||/\/(?:\.env[^/]*|node_modules|scripts|qa|design-assets)(?:\/|$)/.test(name)||!existsSync(path)||!statSync(path).isFile()){res.writeHead(404,{'content-type':'text/plain; charset=utf-8'});res.end('Không tìm thấy trang.');return;}
  const stat=statSync(path),type=types[extname(path)]||'text/plain; charset=utf-8';let data=readFileSync(path);
  const headers={'content-type':type,'cache-control':/[-][a-f0-9]{10}\./.test(name)?'public, max-age=31536000, immutable':'no-cache','x-content-type-options':'nosniff','referrer-policy':'strict-origin-when-cross-origin','accept-ranges':'bytes'};
  if(req.headers.range){const m=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range);if(m){const from=Number(m[1]),to=Math.min(m[2]?Number(m[2]):data.length-1,data.length-1);if(from>to){res.writeHead(416);res.end();return;}headers['content-range']=`bytes ${from}-${to}/${data.length}`;data=data.subarray(from,to+1);headers['content-length']=data.length;res.writeHead(206,headers);res.end(req.method==='HEAD'?undefined:data);return;}}
  if(/text\/|json|svg|javascript/.test(type)&&req.headers['accept-encoding']?.includes('gzip')){const cached=compressed.get(path);if(cached?.mtime===stat.mtimeMs)data=cached.data;else{data=gzipSync(data);compressed.set(path,{mtime:stat.mtimeMs,data});}headers['content-encoding']='gzip';headers.vary='Accept-Encoding';}
  headers['content-length']=data.length;res.writeHead(200,headers);res.end(req.method==='HEAD'?undefined:data);
 }catch{res.writeHead(500);res.end('Không thể đọc tài nguyên.');}
});
server.listen(port,'127.0.0.1',()=>console.log(`Soundbooki preview: http://127.0.0.1:${port}\nRoot: ${root}`));
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>process.exit(0)));
