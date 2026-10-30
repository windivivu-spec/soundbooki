import {books,publicOrder,trialQuota,bookAvailability} from './books.ts';
import {webhook,bookCode,type Fetch} from './wsn.ts';
function assert(v:unknown):asserts v{if(!v)throw Error('Assertion failed');}
const vars:Record<string,string>={WSN_BOOKS_ENABLED:'true',WSN_PAYMENTS_READY:'true',WSN_HEYGEN_PAID_ENABLED:'true',WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED:'true',WSN_BANK_ACCOUNT:'0000000000',WSN_BANK_HOLDER:'QA ONLY',SUPABASE_URL:'https://fixture.supabase.co',SUPABASE_SERVICE_ROLE_KEY:'server-only',WSN_SEPAY_API_TOKEN:'bank-token',WSN_SEPAY_WEBHOOK_API_KEY:'hook-key'};
const env=(name:string)=>vars[name];
const req=(path:string,body:Record<string,unknown>={})=>new Request('https://fixture.supabase.co/functions/v1/wsn-books/'+path,{method:'POST',headers:{authorization:'Bearer wsn_book_'+'a'.repeat(64)},body:JSON.stringify({deviceCode:'SNAAAAAAAAAAAA',...body})});
const fake=(v:unknown)=>new Response(JSON.stringify(v));
const o={id:'11111111-1111-1111-1111-111111111111',kind:'book',state:'awaiting_payment',payment_code:'SB'+'A'.repeat(32),content_hash:'a'.repeat(64),character_count:40000,amount_vnd:25000,results:[],payload:{segments:[{id:'a'.repeat(32)}]}};
Deno.test('cloud is closed before activation and rights confirmation',async()=>{
 const response=await books(req('quote'),n=>n==='WSN_BOOKS_ENABLED'?'false':env(n),(()=>{throw Error('network forbidden')}) as Fetch);assert(response.status===503);
});
Deno.test('explicit consent required before transmitting a quote',async()=>{
 const response=await books(req('quote'),env,(()=>{throw Error('network forbidden')}) as Fetch);assert(response.status===400);
});
Deno.test('quote price and text hash come from the server; merchant keys stay server-side',async()=>{
 let calls=0;const response=await books(req('quote',{consent:true,requestKey:'b'.repeat(32),snapshot:{segments:[]},amountVND:1}),env,(async(url,init)=>{
  calls++;if(calls===1){const body=JSON.parse(init?.body as string);assert(String(url).endsWith('/rpc/wsn_book_quote')&&body.p_bank.account==='0000000000'&&!('p_kind' in body));assert(!('p_amount' in body));assert(!('amountVND' in body));return fake(o);}return fake([{trials_used:2}]);
 }) as Fetch);assert(response.status===200);const result=await response.json();assert(result.order.amountVND===25000&&result.trialsRemaining===3&&result.trialLimit===5&&result.trialCharacters===5000);assert(!JSON.stringify(result).includes('server-only'));
});
Deno.test('another device cannot fetch or sign an order audio',async()=>{
 let calls=0;const response=await books(req('status',{orderId:o.id}),env,(async()=>{calls++;return fake(calls===1?[{trials_used:0}]:[]);}) as Fetch);assert(response.status===404&&calls===2);
});
Deno.test('bank matching is required for exact book price and code',async()=>{
 const code=o.payment_code;assert(bookCode(code)===code);assert(bookCode(code+' '+code)===null);assert(bookCode(code+' SNAAAAAAAAAAAA')===null);
 const body={id:123,accountNumber:vars.WSN_BANK_ACCOUNT,transferType:'in',transferAmount:25000,content:code,transactionDate:'2026-10-21 15:00:00'};
 let calls=0;const response=await webhook(new Request('https://fixture/webhook',{method:'POST',headers:{authorization:'Apikey hook-key'},body:JSON.stringify(body)}),env,(async(url,init)=>{
  calls++;if(calls===1)return fake({status:200,transaction:{id:'123',account_number:vars.WSN_BANK_ACCOUNT,amount_in:'25000.00',amount_out:'0.00',transaction_content:code,transaction_date:'2026-10-21 15:00:00'}});
  assert(String(url).endsWith('/rpc/wsn_book_confirm'));const args=JSON.parse(init?.body as string);assert(args.p_amount===25000&&args.p_code===code);return fake({status:'paid'});
 }) as Fetch);assert(response.status===200&&calls===2);
});

Deno.test('existing trials remain consumed under the new five-trial limit',()=>{
 assert(trialQuota(3).trialsRemaining===2);
 assert(trialQuota(10).trialsRemaining===0);
 assert(trialQuota(11).trialsRemaining===0);
});

Deno.test('grouped trial uses its versioned RPC and reports the server debit',async()=>{
 let calls=0;const response=await books(req('trial-group',{consent:true,requestKey:'c'.repeat(32),snapshot:{trialUnits:4,segments:[]},trialsUsed:0}),env,(async(url,init)=>{
  calls++;if(calls===1){assert(String(url).endsWith('/rpc/wsn_book_create_trial_v2'));const args=JSON.parse(init?.body as string);assert(args.p_kind==='trial'&&args.p_payload.trialUnits===4&&!('trialsUsed' in args));return fake({...o,kind:'trial',state:'queued',amount_vnd:0,character_count:20000,trial_units:4});}
  return fake([{trials_used:4}]);
 }) as Fetch);
 const result=await response.json();assert(response.status===200&&result.order.trialUnits===4&&result.trialsRemaining===1&&result.trialMaxUnits===4&&calls===2);
});
Deno.test('invalid groups and sending groups to the old single route fail before database access',async()=>{
 const network=(()=>{throw Error('network forbidden')}) as Fetch;
 for(const trialUnits of [undefined,0,1,5,2.5,'4',true]){const response=await books(req('trial-group',{consent:true,snapshot:{trialUnits}}),env,network);assert(response.status===400);}
 const single=await books(req('trial',{consent:true,snapshot:{trialUnits:4}}),env,network);assert(single.status===400);
});
Deno.test('missing grouped RPC never falls back to a truncating single trial',async()=>{
 let calls=0;const response=await books(req('trial-group',{consent:true,snapshot:{trialUnits:2}}),env,(async(url)=>{calls++;assert(String(url).endsWith('/rpc/wsn_book_create_trial_v2'));return new Response(JSON.stringify({message:'Could not find function'}),{status:404});}) as Fetch);
 assert(response.status===409&&calls===1);
});
Deno.test('insufficient group quota is explained without resetting the allowance',async()=>{
 const response=await books(req('trial-group',{consent:true,snapshot:{trialUnits:4}}),env,(async()=>new Response(JSON.stringify({message:'Trial limit reached'}),{status:400})) as Fetch);
 assert(response.status===409&&(await response.json()).error.includes('Không đủ lượt Pro'));
 assert(publicOrder({...o,kind:'trial'}).trialUnits===1&&publicOrder(o).trialUnits===0);
});

Deno.test('launch combo is closed without its own activation flag',async()=>{
 const response=await books(req('bundle-quote',{requestKey:'c'.repeat(32)}),env,(()=>{throw Error('network forbidden')}) as Fetch);
 assert(response.status===503);
});
Deno.test('launch quote price cannot be supplied by the client',async()=>{
 let calls=0;
 const quote={...o,kind:'bundle',amount_vnd:50000,pricing_version:'launch-combo-v1',payload:{segments:[]}};
 const response=await books(req('bundle-quote',{requestKey:'d'.repeat(32),amountVND:1}),n=>n==='WSN_LAUNCH_COMBO_ENABLED'?'true':env(n),(async(url,init)=>{
  calls++;const args=JSON.parse(init?.body as string);
  assert(!('p_amount' in args)&&!('amountVND' in args));
  return fake(calls===1?quote:{offer:{active:true,amountVND:50000,books:5},bundle:null,order:quote});
 }) as Fetch);
 const result=await response.json();assert(response.status===200&&result.order.amountVND===50000&&calls===2);
 assert(!JSON.stringify(result).includes('server-only'));
});
Deno.test('launch redeem ignores a claimed remaining balance and requires explicit consent',async()=>{
 const response=await books(req('bundle-redeem',{bundleRemaining:999}),n=>n==='WSN_LAUNCH_COMBO_ENABLED'?'true':env(n),(()=>{throw Error('network forbidden')}) as Fetch);
 assert(response.status===400);
});
Deno.test('launch redeem is server-authorized and returns the updated five-book ledger',async()=>{
 let calls=0;
 const response=await books(req('bundle-redeem',{consent:true,requestKey:'e'.repeat(32),snapshot:{segments:[]},bundleRemaining:999}),n=>n==='WSN_LAUNCH_COMBO_ENABLED'?'true':env(n),(async(url,init)=>{
  calls++;if(calls===1){const args=JSON.parse(init?.body as string);assert(args.p_kind==='bundle_book'&&!('bundleRemaining' in args));return fake({...o,state:'queued',amount_vnd:0,funding_bundle_id:'bundle'});}
  if(calls===2)return fake([{trials_used:0}]);
  return fake({offer:{active:true,amountVND:50000,books:5},bundle:{remaining:4,used:1},order:null});
 }) as Fetch);
 const result=await response.json();assert(result.order.fundingBundleId==='bundle'&&result.order.amountVND===0&&result.bundle.remaining===4&&calls===3);
});
Deno.test('profile reads do not register a device or expose secrets, and reject a wrong credential',async()=>{
 let calls=0;
 const request=()=>new Request('https://example.invalid/wsn-books/profile',{method:'POST',headers:{authorization:'Bearer wsn_book_'+'a'.repeat(64)},body:JSON.stringify({deviceCode:'SNAAAAAAAAAAAA'})});
 const fresh=await books(request(),env,(async(url,init)=>{calls++;assert(!init?.method||init.method==='GET');return fake([]);}) as Fetch);
 const info=await fresh.json();assert(fresh.status===200&&info.trialsRemaining===5&&info.trialCharacters===5000&&!info.registered&&calls===1);
 const mismatch=await books(request(),env,(async()=>fake([{secret_hash:'wrong',trials_used:3}])) as Fetch);assert(mismatch.status===401);
});

Deno.test('owner trial activation is device-scoped and never opens paid purchase',async()=>{
 const trialEnv=(n:string)=>n==='WSN_BOOKS_ENABLED'?'false':n==='WSN_BOOKS_TRIALS_ENABLED'?'true':n==='WSN_BOOKS_TEST_DEVICES'?'SNAAAAAAAAAAAA':n==='WSN_BANK_HOLDER'?undefined:env(n);
 const allowed=await books(req('trial',{consent:true,requestKey:'a'.repeat(32),snapshot:{segments:[]}}),trialEnv,(async(url)=>String(url).includes('/rpc/')?fake({...o,kind:'trial',state:'queued',amount_vnd:0}):fake([{trials_used:1}])) as Fetch);assert(allowed.status===200);
 const forbidden=(()=>{throw Error('Network forbidden')}) as Fetch;
 assert((await books(req('quote',{consent:true}),trialEnv,forbidden)).status===503);
 assert((await books(req('trial',{consent:true}),n=>n==='WSN_BOOKS_TEST_DEVICES'?'SNBBBBBBBBBBBB':trialEnv(n),forbidden)).status===503);
});

Deno.test('ready audio is signed with the server API key and bound to the authenticated order',async()=>{
 let calls=0;const response=await books(req('status',{orderId:o.id}),env,(async(url,init)=>{
  calls++;if(calls===1)return fake([{trials_used:1}]);if(calls===2)return fake([{...o,state:'ready',kind:'trial',amount_vnd:0,results:[{id:'a'.repeat(32),sha256:'c'.repeat(64),path:o.id+'/'+'a'.repeat(32)+'.wav'}]}]);
  const headers=init?.headers as Record<string,string>;assert(headers.apikey==='server-only'&&headers.authorization==='Bearer server-only');assert(String(url).endsWith('/object/sign/wsn-book-audio/'+o.id+'/'+'a'.repeat(32)+'.wav'));return fake({signedURL:'/object/sign/wsn-book-audio/'+o.id+'/sample.wav?token=short-lived'});
 }) as Fetch);const result=await response.json();assert(response.status===200&&calls===3&&result.audio.length===1&&result.audio[0].url.startsWith(vars.SUPABASE_URL+'/storage/v1/object/sign/wsn-book-audio/'+o.id));
});

Deno.test('capabilities describe trial-only activation without opening paid orders or leaking configuration',async()=>{
 const trialEnv=(n:string)=>n==='WSN_BOOKS_ENABLED'?'false':n==='WSN_BOOKS_TRIALS_ENABLED'?'true':n==='WSN_BOOKS_TEST_DEVICES'?'SNAAAAAAAAAAAA':env(n);
 const response=await books(req('profile'),trialEnv,(async()=>fake([])) as Fetch);
 const info=await response.json();assert(info.trialAvailable===true&&info.purchaseAvailable===false&&info.paymentRequired===true&&info.trialsRemaining===5);
 assert(!JSON.stringify(info).includes('server-only')&&!JSON.stringify(info).includes('SNAAAAAAAAAAAA'));
 assert(bookAvailability(trialEnv,'SNBBBBBBBBBBBB').trialAvailable===false);
 assert(bookAvailability(env,'SNAAAAAAAAAAAA').purchaseAvailable===true);
 assert(bookAvailability(n=>n==='WSN_BANK_HOLDER'?undefined:env(n),'SNAAAAAAAAAAAA').purchaseAvailable===false);
 assert(bookAvailability(n=>n==='WSN_BOOKS_COMMERCIAL_RIGHTS_CONFIRMED'?'false':env(n),'SNAAAAAAAAAAAA').purchaseAvailable===false);
});

Deno.test('checkout cannot quote before verified payment routing and paid dispatcher activation',async()=>{
 const forbidden=(()=>{throw Error('No database or provider call allowed')}) as Fetch;
 for(const flag of ['WSN_PAYMENTS_READY','WSN_HEYGEN_PAID_ENABLED']){
  const off=(n:string)=>n===flag?'false':env(n);
  assert(bookAvailability(off,'SNAAAAAAAAAAAA').purchaseAvailable===false);
  assert((await books(req('quote',{consent:true}),off,forbidden)).status===503);
 }
});
Deno.test('status returns the original receiving bank and never signs unpaid audio',async()=>{
 const bank={bin:'970423',account:'1234567890',holder:'QA ORIGINAL',name:'QA BANK'};
 let calls=0;
 const result=await books(req('status',{orderId:o.id}),env,(async()=>{calls++;return fake(calls===1?[{trials_used:1}]:[{...o,receiving_bank:bank}]);}) as Fetch);
 const body=await result.json();assert(result.status===200&&body.bank.account===bank.account&&body.order.bank.holder===bank.holder);
 calls=0;
 const blocked=await books(req('status',{orderId:o.id}),env,(async()=>{calls++;if(calls===1)return fake([{trials_used:1}]);if(calls===2)return fake([{...o,results:[{id:'a'.repeat(32),path:'must-not-sign.wav'}]}]);throw Error('Unpaid artifact signed');}) as Fetch);
 assert(blocked.status===409&&calls===2);
});
Deno.test('a forged successful callback must still match the independent SePay transaction',async()=>{
 const input={id:456,accountNumber:vars.WSN_BANK_ACCOUNT,transferType:'in',transferAmount:25000,content:o.payment_code,transactionDate:'2026-10-24 00:00:00'};
 for(const change of [{id:'other'},{account_number:'9999999999'},{amount_in:'1.00'},{amount_out:'1.00'},{transaction_content:'SB'+'B'.repeat(32)}]){
  let calls=0;const response=await webhook(new Request('https://fixture/webhook',{method:'POST',headers:{authorization:'Apikey hook-key'},body:JSON.stringify(input)}),env,(async()=>{calls++;assert(calls===1);return fake({status:200,transaction:{id:'456',account_number:vars.WSN_BANK_ACCOUNT,amount_in:'25000.00',amount_out:'0.00',transaction_content:o.payment_code,transaction_date:input.transactionDate,...change}});}) as Fetch);
  assert(response.status===200&&(await response.json()).status==='ignored'&&calls===1);
 }
});
Deno.test('direct results use provider link after device auth, never Storage signing',async()=>{
 let calls=0;
 const response=await books(req('status',{orderId:o.id}),env,(async(url)=>{
  calls++;if(calls===1)return fake([{trials_used:1}]);
  if(calls===2)return fake([{...o,kind:'trial',state:'ready',results:[{id:'a'.repeat(32),sha256:'c'.repeat(64),delivery:'provider'}]}]);
  assert(String(url).includes('wsn_heygen_tasks?select=segment_id,audio_url&order_id=eq.'+o.id));
  return fake([{segment_id:'a'.repeat(32),audio_url:'https://resource.heygen.ai/fixture.wav'}]);
 }) as Fetch);
 const body=await response.json();assert(response.status===200&&calls===3&&body.audio[0].delivery==='provider'&&body.audio[0].url==='https://resource.heygen.ai/fixture.wav'&&!JSON.stringify(body).includes('server-only'));
});
Deno.test('direct links never bypass order ownership, payment or provider host validation',async()=>{
 for(const variant of ['foreign','unpaid','evil']){
  let calls=0;
  const response=await books(req('status',{orderId:o.id}),env,(async()=>{
   calls++;if(calls===1)return fake([{trials_used:1}]);
   if(calls===2)return fake(variant==='foreign'?[]:[{...o,kind:variant==='unpaid'?'book':'trial',paid_at:null,state:'ready',results:[{id:'a'.repeat(32),delivery:'provider'}]}]);
   assert(variant==='evil');return fake([{segment_id:'a'.repeat(32),audio_url:'https://127.0.0.1/private'}]);
  }) as Fetch);assert(response.status!==200);
 }
});
