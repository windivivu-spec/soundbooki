import { Env, Fetch } from './wsn.ts';
export const reply = (value: unknown, status=200) => new Response(JSON.stringify(value), {status,headers:{'content-type':'application/json','cache-control':'no-store'}});
export function providerAudioHost(value:string):boolean {try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&(!u.port||u.port==='443')&&['heygen.ai','heygen.com','cloudfront.net','amazonaws.com'].some(h=>u.hostname===h||u.hostname.endsWith('.'+h));}catch{return false;}}
export const trialQuota = (used:number) => ({trialLimit:5,trialCharacters:5000,trialMaxUnits:4,trialsRemaining:Math.max(0,5-used)});
export function bookAvailability(env:Env,device:string){
 const paid=env('WSN_BOOKS_ENABLED')==='true'&&env('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')==='true';
 const bank=!!env('WSN_BANK_ACCOUNT')&&!!env('WSN_BANK_HOLDER');
 const ready=env('WSN_PAYMENTS_READY')==='true'&&env('WSN_HEYGEN_PAID_ENABLED')==='true';
 const trial=env('WSN_BOOKS_TRIALS_ENABLED')==='true'&&(env('WSN_BOOKS_TEST_DEVICES')||'').split(',').includes(device);
 return {trialAvailable:paid||trial,purchaseAvailable:paid&&bank&&ready,paymentRequired:true};
}
class BookServiceError extends Error {}
const bookMessages=['Combo đã hết hạn','Mac này chưa có combo','Mac này đã dùng đủ 5 cuốn','Mỗi Mac chỉ mua một combo','Ưu đãi đã kết thúc','Hàng đợi Pro đang đầy','Mac này đang có hai đơn'];
export async function rest(env:Env, path:string, init:RequestInit={}, fetcher:Fetch=fetch) {
 const base=env('SUPABASE_URL'),key=env('SUPABASE_SERVICE_ROLE_KEY');
 if(!base||!key)throw Error('Service unavailable');
 const r=await fetcher(base+'/rest/v1/'+path,{...init,signal:AbortSignal.timeout(15000),headers:{apikey:key,authorization:'Bearer '+key,'content-type':'application/json',...init.headers}});
 if(!r.ok){
  const problem=await r.json().catch(()=>({}));
  if(problem.message==='Trial limit reached')throw new BookServiceError('Không đủ lượt Pro để tạo phần đã chọn. Các lượt đã dùng vẫn được giữ.');
  if(typeof problem.message==='string'&&bookMessages.some(prefix=>problem.message.startsWith(prefix)))throw new BookServiceError(problem.message);
  throw Error('Database rejected request');
 }return r.status===204?null:r.json();
}
async function digest(value:string){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export function publicOrder(o:Record<string,any>){return {id:o.id,kind:o.kind,trialUnits:o.kind==='trial'?(o.trial_units||1):0,state:o.state==='awaiting_payment'&&Date.parse(o.expires_at)<Date.now()?'expired':o.state,paymentCode:o.payment_code,contentHash:o.content_hash,characters:o.character_count,amountVND:o.amount_vnd,pricingVersion:o.pricing_version,fundingBundleId:o.funding_bundle_id,bank:o.receiving_bank||o.bank||o.payload?.bank,estimatedMinutes:Math.ceil(o.character_count/900),expiresAt:o.expires_at,done:o.results?.length||0,total:o.payload?.segments?.length||0};}
async function launchStatus(env:Env,fetcher:Fetch,device:string,hash:string){
 const result=await rest(env,'rpc/wsn_launch_status',{method:'POST',body:JSON.stringify({p_device:device,p_secret:hash})},fetcher);
 return {...result,order:result.order?publicOrder(result.order):null,available:env('WSN_LAUNCH_COMBO_ENABLED')==='true'&&env('WSN_BOOKS_ENABLED')==='true'&&env('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')==='true'};
}
export async function books(request:Request,env:Env,fetcher:Fetch=fetch):Promise<Response>{
 if(request.method!=='POST')return reply({error:'Method not allowed'},405);
 try{
  const length=Number(request.headers.get('content-length')||0);if(length>12_000_000)return reply({error:'Book too large'},413);
  const raw=await request.text();if(raw.length>6_000_000)return reply({error:'Book too large'},413);
  const input=JSON.parse(raw),secret=request.headers.get('authorization')?.replace(/^Bearer /,'');
  if(!/^wsn_book_[a-f0-9]{64}$/.test(secret||'')||!/^SN[A-F0-9]{12}$/.test(input.deviceCode||''))return reply({error:'Invalid device'},401);
  const hash=await digest(secret!);const path=new URL(request.url).pathname.split('/').pop();
  if(path==='bundle-status'||path==='bundle-quote'){
   let quoted=null;
   if(path==='bundle-quote'){
    if(env('WSN_LAUNCH_COMBO_ENABLED')!=='true'||env('WSN_BOOKS_ENABLED')!=='true'||env('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')!=='true')return reply({error:'Combo ra mắt chưa mở. Bạn vẫn có thể dùng Lite miễn phí.'},503);
    if(!env('WSN_BANK_ACCOUNT')||!env('WSN_BANK_HOLDER'))throw Error('Bank unavailable');
    quoted=await rest(env,'rpc/wsn_launch_quote',{method:'POST',body:JSON.stringify({p_device:input.deviceCode,p_secret:hash,p_request:input.requestKey,p_bank:{bin:env('WSN_BANK_BIN')||'970423',name:env('WSN_BANK_NAME')||'TPBank',account:env('WSN_BANK_ACCOUNT'),holder:env('WSN_BANK_HOLDER')}})},fetcher);
   }
   const result=await launchStatus(env,fetcher,input.deviceCode,hash);
   return reply({...result,order:quoted?publicOrder(quoted):result.order,bank:quoted?.payload?.bank||result.order?.bank||{bin:env('WSN_BANK_BIN')||'970423',name:env('WSN_BANK_NAME')||'TPBank',account:env('WSN_BANK_ACCOUNT'),holder:env('WSN_BANK_HOLDER')}});
  }
  if(path==='quote'||path==='trial'||path==='trial-group'||path==='bundle-redeem'){
   const trial=path==='trial'||path==='trial-group';
   const testDevices=(env('WSN_BOOKS_TEST_DEVICES')||'').split(',').filter(Boolean);
   const trialTest=trial&&env('WSN_BOOKS_TRIALS_ENABLED')==='true'&&testDevices.includes(input.deviceCode);
   if(!trialTest&&(env('WSN_BOOKS_ENABLED')!=='true'||env('WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED')!=='true'))return reply({error:'Pro Cloud chưa mở. Bạn vẫn có thể tạo với Lite miễn phí.'},503);
   if(!trial&&!bookAvailability(env,input.deviceCode).purchaseAvailable)return reply({error:'Thanh toán sách đang tạm dừng. Chưa cần chuyển khoản.'},503);
   if(!trial&&(!env('WSN_BANK_ACCOUNT')||!env('WSN_BANK_HOLDER')))throw Error('Bank unavailable');
   if(input.consent!==true)return reply({error:'Confirm sending book text'},400);
   const units=input.snapshot?.trialUnits;
   if(path==='trial-group'&&(!Number.isInteger(units)||units<2||units>4))return reply({error:'Chỉ được gộp tối đa 4 lượt Pro mỗi lần.'},400);
   if(path!=='trial-group'&&units!==undefined&&units!==1)return reply({error:'Yêu cầu gộp lượt cần dùng đúng phiên bản dịch vụ.'},400);
   if(path==='bundle-redeem'&&env('WSN_LAUNCH_COMBO_ENABLED')!=='true')return reply({error:'Chưa thể dùng combo lúc này. Các lượt đã mua vẫn được giữ.'},503);
   const receivingBank={bin:env('WSN_BANK_BIN')||'970423',name:env('WSN_BANK_NAME')||'TPBank',account:env('WSN_BANK_ACCOUNT'),holder:env('WSN_BANK_HOLDER')};
   const route=path==='quote'?'rpc/wsn_book_quote':trial?'rpc/wsn_book_create_trial_v2':'rpc/wsn_book_create';
   const o=await rest(env,route,{method:'POST',body:JSON.stringify({p_device:input.deviceCode,p_secret:hash,p_payload:input.snapshot,p_request:input.requestKey,...(path==='quote'?{p_bank:receivingBank}:{p_kind:trial?'trial':'bundle_book'})})},fetcher);
   const devices=await rest(env,'wsn_book_devices?select=trials_used&device_code=eq.'+input.deviceCode+'&secret_hash=eq.'+hash,{},fetcher);
   const bank=o.receiving_bank||o.bank||receivingBank;
   if(!trial&&(!bank.account||!bank.holder))throw Error('Bank unavailable');
   const launch=path==='bundle-redeem'?await launchStatus(env,fetcher,input.deviceCode,hash):{};
   return reply({...launch,order:publicOrder(o),bank,...trialQuota(devices[0].trials_used)});
  }
  if(path==='profile'){
   const rows=await rest(env,'wsn_book_devices?select=trials_used,secret_hash&device_code=eq.'+input.deviceCode,{},fetcher);
   if(rows.length&&rows[0].secret_hash!==hash)return reply({error:'Device key mismatch'},401);
   return reply({...trialQuota(rows[0]?.trials_used||0),...bookAvailability(env,input.deviceCode),verified:true,registered:rows.length>0});
  }
  const devices=await rest(env,'wsn_book_devices?select=trials_used&device_code=eq.'+input.deviceCode+'&secret_hash=eq.'+hash,{},fetcher);
  if(!devices.length)return reply({error:'Device key mismatch'},401);
  if(path==='history'){
   const rows=await rest(env,'wsn_book_orders?select=*&device_code=eq.'+input.deviceCode+'&order=created_at.desc&limit=30',{},fetcher);
   return reply({orders:rows.map(publicOrder),...trialQuota(devices[0].trials_used)});
  }
  if(path!=='status'||!/^[a-f0-9-]{36}$/.test(input.orderId||''))return reply({error:'Invalid order'},400);
  const rows=await rest(env,'wsn_book_orders?select=*&id=eq.'+input.orderId+'&device_code=eq.'+input.deviceCode,{},fetcher);
  if(!rows.length)return reply({error:'Order not found'},404);const o=rows[0];
  const known=new Set(Array.isArray(input.knownSegments)?input.knownSegments.filter((id:unknown)=>typeof id==='string'&&/^[a-f0-9]{32}$/.test(id)):[]);
  if(o.kind==='book'&&o.paid_at==null&&o.results?.length)return reply({error:'Đơn chưa xác nhận thanh toán.'},409);
  const pending=o.results.filter((item:{id:string})=>!known.has(item.id));
  const audio=[];
  const direct=pending.some((item:any)=>item.delivery==='provider')?await rest(env,'wsn_heygen_tasks?select=segment_id,audio_url&order_id=eq.'+o.id,{},fetcher):[];
  for(const item of pending.slice(0,20)){
   if(item.delivery==='provider'){
    const task=direct.find((t:any)=>t.segment_id===item.id),url=task?.audio_url;
    if(typeof url!=='string'||!providerAudioHost(url))throw Error('Provider audio unavailable');
    audio.push({id:item.id,sha256:item.sha256,delivery:'provider',url});continue;
   }
   const r=await fetcher(env('SUPABASE_URL')+'/storage/v1/object/sign/wsn-book-audio/'+item.path,{method:'POST',headers:{apikey:env('SUPABASE_SERVICE_ROLE_KEY')!,authorization:'Bearer '+env('SUPABASE_SERVICE_ROLE_KEY'),'content-type':'application/json'},body:JSON.stringify({expiresIn:300}),signal:AbortSignal.timeout(10000)});
   if(!r.ok)throw Error('Audio signing HTTP '+r.status);const signed=await r.json();
   audio.push({...item,url:env('SUPABASE_URL')+'/storage/v1'+signed.signedURL});
  }
  return reply({order:publicOrder(o),bank:publicOrder(o).bank,audio,hasMoreAudio:pending.length>20,...trialQuota(devices[0].trials_used)});
 }catch(error){const diagnostic=error instanceof Error&&/^Audio signing HTTP \d+$/.test(error.message)?error.message:error instanceof Error&&error.message==='Database rejected request'?'database_rejected':'gateway_request';return reply({diagnostic,error:error instanceof BookServiceError?error.message:'Chưa xử lý được yêu cầu. Kiểm tra kết nối, số lượt thử hoặc mở lại đơn đã có.'},409);}
}
