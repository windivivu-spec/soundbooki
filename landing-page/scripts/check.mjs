import {readFileSync,existsSync,readdirSync,statSync} from 'node:fs';
import {resolve,dirname,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),target=process.argv.includes('--dist')?resolve(root,'dist'):root;
const walk=dir=>readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()&&!['node_modules','design-assets','qa','dist','.git'].includes(e.name)?walk(resolve(dir,e.name)):e.isFile()?[resolve(dir,e.name)]:[]);
const html=readFileSync(resolve(target,'index.html'),'utf8');
const errors=[];if(!html.includes('lang="vi"'))errors.push('Missing Vietnamese language');if(/—/.test(html))errors.push('Unwanted em dash in copy');
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);if(new Set(ids).size!==ids.length)errors.push('Duplicate element IDs');
for(const file of ['app.js','site-config.js','hero-animation.js'])execFileSync(process.execPath,['--check',resolve(target,file)]);
const bookRenderer=html.match(/<script[^>]+src="([^"]*book-opening(?:-[a-f0-9]{10})?\.js)"/)?.[1];
if(bookRenderer)execFileSync(process.execPath,['--check',resolve(target,bookRenderer)]);else errors.push('Missing articulated book renderer');
const sourceFiles=walk(target).filter(p=>['.html','.css','.js','.json'].includes(extname(p))&&!p.includes('/scripts/')&&!p.endsWith('/asset-manifest.json'));
let references=0;
for(const file of sourceFiles){const content=readFileSync(file,'utf8');for(const match of content.matchAll(/(?:["'(\s,])(assets\/[a-zA-Z0-9_.\/-]+)/g)){const ref=match[1];if(!existsSync(resolve(target,ref)))errors.push('Missing '+ref);references++;}}
if(errors.length){console.error([...new Set(errors)].join('\n'));process.exit(1);}console.log(`PASS: scripts, Vietnamese copy, unique IDs, ${references} local asset references.`);
