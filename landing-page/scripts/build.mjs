import {readFileSync,writeFileSync,mkdirSync,readdirSync,rmSync,copyFileSync,statSync} from 'node:fs';
import {resolve,dirname,relative,extname,basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),out=resolve(root,'dist');
rmSync(out,{recursive:true,force:true});mkdirSync(out,{recursive:true});
const walk=dir=>readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(resolve(dir,e.name)):[resolve(dir,e.name)]);
// Keep previous design sources locally; ship only assets used by this landing.
const files=walk(resolve(root,'assets')).filter(file=>!file.includes('/book-pages/')&&!['book-scene.js','THREE-LICENSE.txt','book-and-sound.webp','book-and-sound-640.webp','book-and-sound-768.webp','quiet-listening.webp','soundscape-desktop.webp','soundscape-mobile.webp'].includes(basename(file))),map=new Map();
function destination(file,data){const path=relative(root,file),ext=extname(path),stem=path.slice(0,path.length-ext.length),digest=createHash('sha256').update(data).digest('hex').slice(0,10);return stem+'-'+digest+ext;}
function write(path,data){const target=resolve(out,path);mkdirSync(dirname(target),{recursive:true});writeFileSync(target,data);}
const rewrite=text=>[...map].sort((a,b)=>b[0].length-a[0].length).reduce((s,[from,to])=>s.replaceAll(from,to),text);
for(const file of files.filter(f=>!['.json','.js'].includes(extname(f)))){const data=readFileSync(file),dest=destination(file,data);map.set(relative(root,file),dest);write(dest,data);}
for(const file of files.filter(f=>extname(f)==='.json')){const data=Buffer.from(rewrite(readFileSync(file,'utf8'))),dest=destination(file,data);map.set(relative(root,file),dest);write(dest,data);}
// Vendored scene code reads the local, hashed page-print manifest. Resolve its
// dependencies before hashing the script itself, just like the audio catalog.
for(const file of files.filter(f=>extname(f)==='.js')){const data=Buffer.from(rewrite(readFileSync(file,'utf8'))),dest=destination(file,data);map.set(relative(root,file),dest);write(dest,data);}
for(const name of ['index.html','styles.css','app.js','site-config.js','hero-animation.js'])write(name,rewrite(readFileSync(resolve(root,name),'utf8')));
write('_headers',`/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n`);
write('404.html','<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Soundbooki</title><body><h1>Trang này không còn ở đây.</h1><p><a href="/">Về trang chủ Soundbooki</a></p></body></html>');
write('asset-manifest.json',JSON.stringify(Object.fromEntries(map),null,2));
const total=walk(out).reduce((n,p)=>n+statSync(p).size,0);console.log(`Built ${walk(out).length} static files, ${(total/1024).toFixed(0)} KiB → ${out}`);
