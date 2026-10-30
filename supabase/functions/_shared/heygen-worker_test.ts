import {worker,audioHost,validWav} from './heygen-worker.ts';import type {Fetch} from './wsn.ts';
const assert=(x:unknown)=>{if(!x)throw Error('Assertion failed');};
const env=(n:string)=>({SUPABASE_URL:'https://qa.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'private-server',WSN_HEYGEN_WORKER_TOKEN:'worker-secret',WSN_HEYGEN_API_KEY:'provider-secret',WSN_BOOKS_TRIALS_ENABLED:'true'} as Record<string,string>)[n];
const req=(token='worker-secret')=>new Request('https://qa/worker',{method:'POST',headers:{authorization:'Bearer '+token}});
const task={orderId:'11111111-1111-1111-1111-111111111111',claim:'claim',token:'task',voice:'3414fd7fdaa64e619fb8b021534ce368',segment:{id:'a'.repeat(32),text:'Giữ nguyên tiếng Việt 😀. Không viết lại.'}};
const json=(o:unknown,status=200,headers={})=>new Response(JSON.stringify(o),{status,headers});
function wav(){const b=new Uint8Array(52);const v=new DataView(b.buffer);const text=(at:number,s:string)=>b.set(new TextEncoder().encode(s),at);text(0,'RIFF');v.setUint32(4,44,true);text(8,'WAVE');text(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,24000,true);v.setUint32(28,48000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);text(36,'data');v.setUint32(40,8,true);return b;}
async function fixture(mode:string){const events:any[]=[];let posts=0;const fetcher=(async(url:any,init?:RequestInit)=>{
 const path=String(url);const body=typeof init?.body==='string'?JSON.parse(init.body):{};
 if(path.endsWith('rpc/wsn_heygen_next_v2'))return json(mode==='idle'?null:{...task,...(mode==='resume'?{audioURL:'https://resource.heygen.ai/s.wav'}:{})});
 if(path.endsWith('rpc/wsn_heygen_result')){events.push(body);return mode==='no-content'?new Response(null,{status:204}):json(null);}
 if(path==='https://api.heygen.com/v3/models/audio/tts'){posts++;assert(body.text===task.segment.text&&body.model==='heygen-voice-1-turbo-free'&&body.voice_id===task.voice);assert(!JSON.stringify(body).includes('private-server'));
  if(mode==='timeout')throw Error('Network interrupted');if(mode==='429')return json({},429,{'retry-after':'60'});if(mode==='500')return json({},500);
  return json({data:{audio_url:mode==='private'?'https://127.0.0.1/a.wav':'https://resource.heygen.ai/s.wav'}});
 }
 if(path==='https://resource.heygen.ai/s.wav')return new Response(mode==='badwav'?new Uint8Array([1,2,3]):wav());
 if(path.endsWith('/rpc/wsn_book_audio_direct')){assert(/^[a-f0-9]{64}$/.test(body.p_sha));return json({done:1,total:1});}
 throw Error('Unexpected request '+path);
 }) as Fetch;const result=await worker(req(),env,fetcher);return {status:result.status,body:await result.json(),posts,events};}
Deno.test('dispatcher is authenticated and remains off without explicit trial activation',async()=>{const forbidden=(()=>{throw Error('Network forbidden');}) as Fetch;assert((await worker(req('bad'),env,forbidden)).status===401);assert((await worker(req(),n=>n==='WSN_BOOKS_TRIALS_ENABLED'?'false':env(n),forbidden)).status===503);});
Deno.test('empty dispatcher does not call the provider',async()=>{const r=await fixture('idle');assert(r.posts===0&&r.body.state==='idle');});
Deno.test('success persists provider URL before direct delivery, then atomically commits exact segment',async()=>{const r=await fixture('ok');assert(r.status===200&&r.body.state==='committed'&&r.posts===1);assert(r.events.map(x=>x.p_state).join(',')==='audio,done');});
Deno.test('429 honors Retry-After and never immediately calls TTS twice',async()=>{const r=await fixture('429');assert(r.posts===1&&r.events[0].p_state==='retry'&&r.events[0].p_retry===60);});
Deno.test('unknown POST outcome and HTTP500 do not automatically spend again',async()=>{for(const mode of ['timeout','500']){const r=await fixture(mode);assert(r.status===502&&r.posts===1&&r.events[0].p_state==='uncertain');}});
Deno.test('private network URLs are rejected after provider response',async()=>{const r=await fixture('private');assert(r.status===502&&r.events[0].p_state==='uncertain');assert(!audioHost('https://localhost/a')&&!audioHost('http://resource.heygen.ai/a')&&!audioHost('https://heygen.ai.evil.test/a'));});
Deno.test('invalid or partial WAV never gets committed; URL and safe failure stage remain recoverable',async()=>{const r=await fixture('badwav');assert(r.status===502&&r.posts===1&&r.events.length===2&&r.events.every(x=>x.p_state==='audio'));assert(r.events[1].p_diagnostic==='Audio recovery: validation');assert(validWav(wav())&&!validWav(wav().slice(0,48)));});
Deno.test('recovery downloads a saved URL without another TTS request',async()=>{const r=await fixture('resume');assert(r.status===200&&r.posts===0&&r.events[0].p_state==='done');});
Deno.test('direct delivery makes no Storage requests',async()=>{const r=await fixture('conflict');assert(r.status===200&&r.body.state==='committed'&&r.posts===1);});

Deno.test('cron uses expiring HMAC proof without exposing a reusable worker or provider key',async()=>{
 const {authorizedWorker}=await import('./heygen-worker.ts');const stamp=Math.floor(Date.now()/1000),nonce='a'.repeat(32),message=stamp+'.'+nonce;
 const key=await crypto.subtle.importKey('raw',new TextEncoder().encode('worker-secret'),{name:'HMAC',hash:'SHA-256'},false,['sign']);const signature=[...new Uint8Array(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(message)))].map(n=>n.toString(16).padStart(2,'0')).join('');
 assert(await authorizedWorker(new Request('https://qa',{headers:{'x-wsn-worker-proof':message+'.'+signature}}),'worker-secret'));
 assert(!await authorizedWorker(new Request('https://qa',{headers:{'x-wsn-worker-proof':(stamp-300)+'.'+nonce+'.'+signature}}),'worker-secret'));
 assert(!await authorizedWorker(new Request('https://qa',{headers:{'x-wsn-worker-proof':message+'.'+'0'.repeat(64)}}),'worker-secret'));
});

Deno.test('paid dispatch needs its activation, verified payment marker and shared queue RPC',async()=>{
 const paidEnv=(n:string)=>['WSN_HEYGEN_PAID_ENABLED','WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED','WSN_PAYMENTS_READY'].includes(n)?'true':n==='WSN_BOOKS_TRIALS_ENABLED'?'false':env(n);
 let claims=0,providerPosts=0;
 const check=(async(url:any,init?:RequestInit)=>{
  if(String(url).endsWith('rpc/wsn_heygen_next_v2')){const args=JSON.parse(init?.body as string);assert(args.p_paid_enabled===true);claims++;return json({...task,kind:'book',paid:false});}
  providerPosts++;throw Error('Unpaid provider POST');
 }) as Fetch;
 const blocked=await worker(req(),paidEnv,check);assert(blocked.status===502&&claims===1&&providerPosts===0);
 const idle=await worker(req(),paidEnv,(async(url:any,init?:RequestInit)=>{assert(String(url).endsWith('rpc/wsn_heygen_next_v2'));assert(JSON.parse(init?.body as string).p_paid_enabled===true);return json(null);}) as Fetch);
 assert(idle.status===200&&(await idle.json()).state==='idle');
});
Deno.test('void RPC 204 completes without waiting for recovery or re-synthesizing',async()=>{
 const r=await fixture('no-content');
 assert(r.status===200&&r.body.state==='committed'&&r.posts===1);
 assert(r.events.map(x=>x.p_state).join(',')==='audio,done');
});
