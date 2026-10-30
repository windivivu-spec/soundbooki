/** Owner CLI only. Excluded from the static build. Credentials come from env. */
import {createHash,createHmac} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {createReadStream,readFileSync,writeFileSync,mkdirSync,statSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const args=process.argv.slice(2),value=name=>args[args.indexOf(name)+1];
const env=name=>{const v=process.env[name]?.trim();if(!v)throw Error('Missing '+name);return v;};
const account=env('R2_ACCOUNT_ID'),access=env('R2_ACCESS_KEY_ID'),secret=env('R2_SECRET_ACCESS_KEY'),bucket=env('R2_BUCKET');
if(!/^[a-f0-9]{32}$/i.test(account)||bucket!=='windi-bucket')throw Error('Select the existing project R2 account and windi-bucket.');
const publicBase=new URL(env('R2_PUBLIC_BASE_URL'));if(publicBase.protocol!=='https:'||publicBase.username||publicBase.password||publicBase.search||publicBase.hash||publicBase.hostname.endsWith('.r2.cloudflarestorage.com'))throw Error('A public HTTPS download origin is required.');
const endpoint=new URL(`https://${account}.r2.cloudflarestorage.com`);
const hash=x=>createHash('sha256').update(x).digest('hex'),hmac=(key,x)=>createHmac('sha256',key).update(x).digest();
const encode=x=>encodeURIComponent(x).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase());
async function signed(method,key='',{body,contentHash=hash(''),headers:extra={},query={}}={}){
 const url=new URL(endpoint);url.pathname='/'+[bucket,...key.split('/').filter(Boolean)].map(encode).join('/');
 const canonicalQuery=Object.entries(query).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`${encode(k)}=${encode(v)}`).join('&');url.search=canonicalQuery;
 const date=new Date().toISOString().replace(/[:-]|\.\d{3}/g,''),day=date.slice(0,8);
 const headers={host:url.host,'x-amz-content-sha256':contentHash,'x-amz-date':date,...extra};
 const names=Object.keys(headers).sort();
 const canonical=[method,url.pathname,canonicalQuery,names.map(n=>`${n}:${headers[n]}\n`).join(''),names.join(';'),contentHash].join('\n');
 const scope=`${day}/auto/s3/aws4_request`,keyDate=hmac(hmac(hmac(hmac('AWS4'+secret,day),'auto'),'s3'),'aws4_request');
 headers.authorization=`AWS4-HMAC-SHA256 Credential=${access}/${scope}, SignedHeaders=${names.join(';')}, Signature=${hmac(keyDate,`AWS4-HMAC-SHA256\n${date}\n${scope}\n${hash(canonical)}`).toString('hex')}`;
 return fetch(url,{method,headers,body,duplex:body?'half':undefined,redirect:'error',signal:AbortSignal.timeout(600000)});
}
const probe=await signed('GET','',{query:{'list-type':'2','max-keys':'0',prefix:'soundbooki/downloads/mac/'}});
if(!probe.ok)throw Error('R2 preflight HTTP '+probe.status);await probe.arrayBuffer();
if(args.includes('--check')){console.log(JSON.stringify({bucket,readable:true,publicHost:publicBase.hostname,mutation:false}));process.exit(0);}
if(!args.includes('--artifact'))throw Error('Use --artifact <zip> [--confirm-public]');
const artifact=resolve(value('--artifact'));if(!artifact.endsWith('.zip'))throw Error('Only the reviewed ZIP installer is accepted.');
const audit=JSON.parse(execFileSync('python3',[resolve(dirname(fileURLToPath(import.meta.url)),'audit-release.py'),artifact],{encoding:'utf8',maxBuffer:2*1024*1024}));if(!audit.passed)throw Error('Release audit failed');
const size=statSync(artifact).size;if(size<1000000||size>5*1024**3)throw Error('Invalid archive size.');
const digest=createHash('sha256');for await(const chunk of createReadStream(artifact))digest.update(chunk);const sha256=digest.digest('hex');
const filename=`Soundbooki-0.8.2-macOS-AppleSilicon-preview-${sha256.slice(0,12)}.zip`;
const key='soundbooki/downloads/mac/2026-10-24/'+filename;
const publicUrl=publicBase.href.replace(/\/$/,'')+'/'+key;
const report={filename,url:publicUrl,sha256,sizeBytes:size,version:'0.8.2',preview:true,notarized:false,privateF5Included:false,ownerMusicIncluded:false};
if(!args.includes('--confirm-public')){console.log(JSON.stringify({...report,dryRun:true}));process.exit(0);}
const existing=await signed('HEAD',key);
if(existing.status===404){
 console.log(JSON.stringify({stage:'upload',sizeBytes:size,immutable:true}));
 const uploaded=await signed('PUT',key,{body:createReadStream(artifact),contentHash:sha256,headers:{'content-type':'application/zip','content-length':String(size),'content-disposition':`attachment; filename="${filename}"`,'cache-control':'public, max-age=31536000, immutable','x-amz-meta-sha256':sha256}});
 if(!uploaded.ok)throw Error('Upload HTTP '+uploaded.status);await uploaded.arrayBuffer();
}else if(!existing.ok||existing.headers.get('x-amz-meta-sha256')!==sha256)throw Error('An existing object differs; never overwrite a release.');
const metadata=await signed('HEAD',key);if(!metadata.ok||Number(metadata.headers.get('content-length'))!==size||metadata.headers.get('x-amz-meta-sha256')!==sha256)throw Error('Stored metadata mismatch.');
console.log(JSON.stringify({stage:'verify-public-download',sizeBytes:size}));
const download=await fetch(publicUrl,{redirect:'error',headers:{'accept-encoding':'identity'},signal:AbortSignal.timeout(600000)});
if(!download.ok||Number(download.headers.get('content-length'))!==size)throw Error('Public download HTTP/size mismatch.');
const remote=createHash('sha256');let received=0;for await(const chunk of download.body){remote.update(chunk);received+=chunk.length;}
if(received!==size||remote.digest('hex')!==sha256)throw Error('Downloaded archive checksum mismatch.');
const range=await fetch(publicUrl,{headers:{range:'bytes=0-3'},redirect:'error',signal:AbortSignal.timeout(30000)});if(range.status!==206||Buffer.from(await range.arrayBuffer()).toString('hex')!=='504b0304')throw Error('Download range/ZIP signature failed.');
report.publicDownloadVerified=true;report.rangeVerified=true;report.verifiedAt=new Date().toISOString();
const site=resolve(dirname(fileURLToPath(import.meta.url)),'..');
writeFileSync(resolve(site,'site-config.js'),`/* Public release metadata only. Verified from the complete R2 download. */\nwindow.SOUNDBOOKI_SITE = Object.freeze(${JSON.stringify({brand:'Soundbooki',mac:{...report,requirements:'Mac Apple Silicon · macOS 15 trở lên'},offer:{priceVND:50000,books:5,endsAt:'2026-11-02T00:00:00+07:00'}},null,2)});\n`);
mkdirSync(resolve(site,'qa'),{recursive:true});writeFileSync(resolve(site,'qa/download-verification.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
