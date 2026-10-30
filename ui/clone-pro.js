'use strict';
const proMaxEnabled=false; // Deferred by the owner; no UI, polling or paid actions.
let cloudBusy=false,cloudRequest=null,cloudReturn=null,creditWallet=null,creditOrder=null,creditPoll=null,creditPolls=0,creditPurchaseKey=null;
function openCloud(){
 if(!proMaxEnabled)return;
 if(guardDirty())return;
 if($('licensePanel').open)$('licensePanel').close();
 renderCloud();$('cloudPanel').showModal();$('refreshCredits').focus();refreshCredits(true);
}
function refreshCredits(voices=false){
 if(!proMaxEnabled)return;
 if(cloudBusy)return;
 if(jobs.audio||jobs.export){$('cloudStatus').textContent='Hãy chờ hoặc hủy tạo/xuất audio trước khi cập nhật ví credit.';return;}
 cloudBusy=true;renderCloud();$('cloudStatus').textContent='Đang cập nhật ví credit trong app…';send({action:'creditWallet',voices});
}
function renderCloud(){
 if(!proMaxEnabled)return;
 const model=modelCatalog.find(m=>m.id==='clone-pro');
 $('refreshCredits').disabled=cloudBusy||!!jobs.audio||!!jobs.export;
 $('useCloud').disabled=cloudBusy||!model?.ready||!book||book.model==='clone-pro'||!!jobs.audio||!!jobs.export;
 $('creditBalance').textContent=creditWallet?creditWallet.balance.toLocaleString('vi-VN'):'—';
 const packs=creditWallet?.packs||[],selected=$('creditPack').value;
 $('creditPack').replaceChildren();for(const pack of packs){const opt=document.createElement('option');opt.value=pack.id;opt.textContent=`${pack.credits.toLocaleString('vi-VN')} credit · ${pack.amountVND.toLocaleString('vi-VN')}đ`;$('creditPack').append(opt);}
 if(packs.some(p=>p.id===selected))$('creditPack').value=selected;
 $('creditPack').disabled=cloudBusy||!packs.length;
 $('buyCredits').disabled=cloudBusy||!creditWallet?.salesReady||!packs.length||!!jobs.audio||!!jobs.export;
 $('creditPricingHint').textContent=packs.length?'Chọn gói và quét QR. Credit được cộng khi tiền vào được xác nhận.':'Giá gói credit sẽ được công bố sau. Chưa mở bán.';
 renderCreditOrder();
}
function renderCreditOrder(){
 if(!proMaxEnabled)return;
 $('creditOrder').hidden=!creditOrder;if(!creditOrder)return;
 const order=creditOrder,bank=order.bank||{};
 $('creditBankDetails').textContent=`${order.credits.toLocaleString('vi-VN')} credit · ${order.amountVND.toLocaleString('vi-VN')}đ · ${bank.name||''} · ${bank.account||''} · ${bank.holder||''}`;
 $('creditPaymentCode').textContent=order.content;
 $('creditOrderState').textContent=order.status==='paid'?'Đã xác nhận tiền vào. Credit đã được cộng vào ví.':'Đang chờ xác nhận tiền vào. Bạn có thể cập nhật số dư hoặc mở lại cửa sổ này sau.';
 if($('creditQR').dataset.order!==order.id){$('creditQR').dataset.order=order.id;$('creditQR').replaceChildren();send({action:'creditQR',order});}
}
function renderCreditQR(e){
 if(!proMaxEnabled)return;
 if(creditOrder?.id!==e.orderId||typeof e.qrPath!=='string'||!/^([M0-9 h v z-])+$/.test(e.qrPath)||!Number.isInteger(e.qrSize)||e.qrSize<20||e.qrSize>200)return;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),path=document.createElementNS(svg.namespaceURI,'path');svg.setAttribute('viewBox',`0 0 ${e.qrSize} ${e.qrSize}`);path.setAttribute('d',e.qrPath);svg.append(path);$('creditQR').replaceChildren(svg);
}
function scheduleCreditPoll(){
 if(!proMaxEnabled){clearTimeout(creditPoll);return;}
 clearTimeout(creditPoll);if(!$('cloudPanel').open||creditOrder?.status!=='pending'||creditPolls>=30)return;
 creditPoll=setTimeout(()=>{if($('cloudPanel').open&&!document.hidden){creditPolls++;refreshCredits();}else scheduleCreditPoll();},10000);
}
function handleCreditEvent(e){
 if(!proMaxEnabled)return;
 cloudBusy=e.running;
 if(e.wallet){creditWallet=e.wallet;const old=creditOrder;creditOrder=e.wallet.orders?.find(o=>o.id===old?.id)||e.wallet.orders?.find(o=>o.status==='pending')||null;}
 if(e.order){creditOrder=e.order;creditPurchaseKey=null;creditPolls=0;}
 renderCloud();if(e.message)$('cloudStatus').textContent=e.message;
 if(e.order&&$('cloudPanel').open)$('creditOrder').scrollIntoView({block:'start',behavior:'auto'});
 if(!e.running)scheduleCreditPoll();
}
function requestGenerate(request){
 if(book?.model==='pro-cloud'){openBookCloud({mode:'trial',chapterId:request.scope?.type==='chapter'?request.scope.chapterId:activeSection()?.id});return;}
 if(book?.model!=='clone-pro'){beginGeneration(request);send(request);return;}
 if(!proMaxEnabled){toast('Chọn giọng đọc local để tạo sách nói.');openModels();return;}
 if(cloudBusy){toast('Hãy chờ cập nhật ví credit hoàn tất.');return;}
 const indices=request.scope?scopeIndices(request.scope):book.segments.map((_,i)=>i).slice(request.start||0,request.all?undefined:(request.start||0)+3);
 const segments=indices.map(i=>book.segments[i]).filter(s=>/[\p{L}\p{N}]/u.test(s.text));if(!segments.length)return;
 const missing=segments.filter(s=>!s.audio);
 if(missing.length&&!modelCatalog.find(m=>m.id==='clone-pro')?.ready){openCloud();return;}
 cloudRequest={...request,cloudConsent:{voice:book.voice,language:book.language||'vi',segments:segments.map(s=>({id:s.id,text:s.text}))}};
 const pages=[...new Set(segments.map(s=>s.page+1))];
 $('cloudConfirmDetail').textContent=`${book.title} · ${voiceLabel(book.model,book.voice)} · ${unit()} ${pages[0]}–${pages.at(-1)} · ${segments.length} ${window.i18n?.language==='en'?'segments':'đoạn'}`;
 const credits=missing.reduce((sum,s)=>sum+Array.from(s.text.normalize('NFC').trim()).length,0);
 $('cloudCreditEstimate').textContent=missing.length?`${missing.length} đoạn cần tạo · Dự kiến ${credits.toLocaleString('vi-VN')} credit app. ${segments.length-missing.length} đoạn đã có được dùng lại.`:'Tất cả đoạn đã có audio. Không cần gửi chữ hoặc dùng credit.';
 $('confirmCloudGenerate').textContent=missing.length?'Gửi chữ và dùng credit app':'Dùng audio đã có';
 cloudReturn=document.activeElement;$('cloudConfirm').showModal();$('cancelCloudConfirm').focus();
}
document.addEventListener('DOMContentLoaded',()=>{
 if(!proMaxEnabled)return;
 const button=document.createElement('button');button.id='manageCloud';button.className='text';button.textContent='Pro Max · Mua credit';$('manageModels').after(button);button.onclick=openCloud;
 const offer=document.createElement('p'),title=document.createElement('strong'),copy=document.createElement('span'),open=document.createElement('button');
 title.textContent='Pro Max · Credit riêng trong app';copy.textContent='Tạo sách nói bằng Clone Pro 2.1. Không cần tài khoản web, không thêm phí gói.';
 open.className='text';open.textContent='Mua / quản lý credit';open.onclick=openCloud;offer.append(title,document.createElement('br'),copy,document.createElement('br'),open);$('purchaseHint').before(offer);
 $('closeCloud').onclick=()=>$('cloudPanel').close();$('refreshCredits').onclick=()=>refreshCredits(true);
 $('cloudPanel').addEventListener('close',()=>{clearTimeout(creditPoll);$('manageCloud').focus();});
 $('buyCredits').onclick=()=>{if(cloudBusy||!$('creditPack').value)return;cloudBusy=true;creditPurchaseKey=creditPurchaseKey||requestToken();renderCloud();$('cloudStatus').textContent='Đang tạo yêu cầu mua credit…';send({action:'creditPurchase',packId:$('creditPack').value,key:creditPurchaseKey});};
 $('creditPack').onchange=()=>{creditPurchaseKey=null;};
 $('copyCreditCode').onclick=()=>{if(creditOrder)send({action:'creditCopy',value:creditOrder.content});};
 $('useCloud').onclick=()=>{applyModel('clone-pro');$('cloudPanel').close();};
 for(const id of ['closeCloudConfirm','cancelCloudConfirm'])$(id).onclick=()=>$('cloudConfirm').close();
 $('cloudConfirm').addEventListener('close',()=>{cloudRequest=null;cloudReturn?.focus();});
 $('confirmCloudGenerate').onclick=()=>{const request=cloudRequest;if(request&&book?.id===request.bookId&&book.model==='clone-pro')send(request);$('cloudConfirm').close();};
});
