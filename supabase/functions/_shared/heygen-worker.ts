import {Env,Fetch} from './wsn.ts';
import {rest,reply} from './books.ts';
export function audioHost(value:string):boolean {
 try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&(!u.port||u.port==='443')&&['heygen.ai','heygen.com','cloudfront.net','amazonaws.com'].some(h=>u.hostname===h||u.hostname.endsWith('.'+h));}catch{return false;}
}
export function validWav(b:Uint8Array):boolean {
 if(b.length<44||b.length>50*1024*1024)return false;const s=(at:number,n:number)=>new TextDecoder().decode(b.slice(at,at+n));if(s(0,4)!=='RIFF'||s(8,4)!=='WAVE')return false;
 const v=new DataView(b.buffer,b.byteOffset,b.byteLength);let fmt=false,data=false;for(let at=12;at+8<=b.length;){const size=v.getUint32(at+4,true);if(at+8+size>b.length)return false;if(s(at,4)==='fmt '){if(size<16)return false;fmt=[1,3].includes(v.getUint16(at+8,true))&&v.getUint16(at+10,true)>=1&&v.getUint16(at+10,true)<=2&&v.getUint32(at+12,true)>=8000;}if(s(at,4)==='data')data=size>0;at+=8+size+(size%2);}return fmt&&data;
}
export async function authorizedWorker(request:Request,secret:string):Promise<boolean>{
 if(request.headers.get('authorization')==='Bearer '+secret)return true;
 const proof=request.headers.get('x-wsn-worker-proof')||'',m=proof.match(/^(\d{10})\.([a-f0-9]{32})\.([a-f0-9]{64})$/);
 if(!m||Math.abs(Date.now()/1000-Number(m[1]))>120)return false;
 const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
 return crypto.subtle.verify('HMAC',key,Uint8Array.from(m[3].match(/../g)!.map(x=>parseInt(x,16))),new TextEncoder().encode(m[1]+'.'+m[2]));
}
export async function worker(request:Request,env:Env,fetcher:Fetch=fetch):Promise<Response>{
 if(request.method!=='POST')return reply({error:'Method not allowed'},405);
 const secret=env('WSN_HEYGEN_WORKER_TOKEN');if(!secret||!await authorizedWorker(request,secret))return reply({error:'Unauthorized'},401);
 const paid=env('WSN_HEYGEN_PAID_ENABLED')==='true'&&env('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')==='true'&&env('WSN_PAYMENTS_READY')==='true';
 if(env('WSN_BOOKS_TRIALS_ENABLED')!=='true'&&!paid)return reply({state:'disabled'},503);
 let task:any;let stage='claim';const rpc=async(name:string,args:Record<string,unknown>={})=>rest(env,'rpc/'+name,{method:'POST',body:JSON.stringify(args)},fetcher);
 const record=async(state:string,url:string|null=null,retry=30,diagnostic:string|null=null)=>rpc('wsn_heygen_result',{p_order:task.orderId,p_segment:task.segment.id,p_token:task.token,p_state:state,p_url:url,p_retry:retry,p_diagnostic:diagnostic});
 try{
  task=await rpc('wsn_heygen_next_v2',{p_paid_enabled:paid});if(!task)return reply({state:'idle'});
  if(task.kind==='book'&&(!paid||task.paid!==true))throw Error('Unpaid book dispatch rejected');
  if(!task.audioURL){
   const key=env('WSN_HEYGEN_API_KEY');if(!key){await record('failed',null,30,'Missing provider configuration');return reply({state:'failed'},503);}
   let response:Response;
   try{response=await fetcher('https://api.heygen.com/v3/models/audio/tts',{method:'POST',redirect:'error',headers:{'X-Api-Key':key,'content-type':'application/json'},body:JSON.stringify({model:'heygen-voice-1-turbo-free',voice_id:task.voice,text:task.segment.text,language:'vi',expressiveness_boost:['eff592346cac4febbba5d5fef4621ff0','5ee4ba10bd0446ba85421ab177462aba'].includes(task.voice)?0.7:0.5,speed:1}),signal:AbortSignal.timeout(70000)});}catch{await record('uncertain',null,30,'Provider request outcome unknown; no automatic second synthesis');return reply({state:'uncertain'},502);}
   if(response.status===429){const header=response.headers.get('retry-after');const retry=header?(/^\d+$/.test(header)?Number(header):Math.ceil((Date.parse(header)-Date.now())/1000)):30;await record('retry',null,Number.isFinite(retry)?Math.max(3,retry):30,'Provider capacity busy');return reply({state:'backoff'});}
   if(!response.ok){await record(response.status>=500?'uncertain':'failed',null,30,'Provider HTTP '+response.status);return reply({state:response.status>=500?'uncertain':'failed'},502);}
   const result=await response.json().catch(()=>null);const url=result?.data?.audio_url;
   if(typeof url!=='string'||!audioHost(url)){await record('uncertain',null,30,'Provider returned an invalid audio location');return reply({state:'uncertain'},502);}
   // Save successful synthesis BEFORE downloading so recovery never re-synthesizes.
   await record('audio',url,120);task.audioURL=url;
  }
  if(!audioHost(task.audioURL))throw Error('Invalid saved audio location');
  stage='download';const audio=await fetcher(task.audioURL,{redirect:'error',signal:AbortSignal.timeout(25000)});if(!audio.ok)throw Error('Audio download unavailable');
  if(Number(audio.headers.get('content-length')||0)>50*1024*1024)throw Error('Audio too large');const bytes=new Uint8Array(await audio.arrayBuffer());stage='validation';if(!validWav(bytes))throw Error('Audio validation failed');
  const sha=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  stage='commit';const progress=await rpc('wsn_book_audio_direct',{p_order:task.orderId,p_claim:task.claim,p_segment:task.segment.id,p_sha:sha});await record('done');return reply({state:'committed',...progress});
 }catch{
  // A saved audio URL is retryable without another provider POST. Unknown POSTs stay blocked.
  // Persist only a bounded stage name; never provider URLs, keys or raw errors.
  if(task?.audioURL)try{await record('audio',task.audioURL,120,'Audio recovery: '+stage);}catch{/* retain the original durable URL */}
  return reply({state:'reconcile',stage,error:'Dispatcher operation did not complete; durable state retained'},502);
 }
}
