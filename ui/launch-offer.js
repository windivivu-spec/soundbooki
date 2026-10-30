'use strict';
const launchEndsAt='2026-11-01T17:00:00Z',launchStartsAt='2026-10-21T17:00:00Z';
let launchState={offer:{active:Date.now()>=Date.parse(launchStartsAt)&&Date.now()<Date.parse(launchEndsAt),endsAt:launchEndsAt},bundle:null,order:null,configured:false,available:false};
let launchBannerDismissed=false;
try{launchBannerDismissed=localStorage.getItem('windi-launch-banner-dismissed')==='1';}catch{}
let launchToken='',launchBusy=false,launchTimer=null,launchChecks=0,launchQuoteKey=null,launchTrigger=null,launchReturnBook=false,launchServerDelta=0;
function launchActive(){return launchState.offer?.active===true&&Date.now()+launchServerDelta<Date.parse(launchState.offer.endsAt||launchEndsAt);}
function clearLaunchPoll(){clearTimeout(launchTimer);launchTimer=null;}
function renderLaunch(){
 const active=launchActive(),grant=launchState.bundle,remaining=grant?.remaining||0,order=launchState.order;
 $('launchBanner').hidden=launchBannerDismissed||(!active&&!grant);
 $('launchBannerAction').textContent=grant?(active?`Còn ${remaining}/5 cuốn · Xem combo`:'Xem combo đã mua'):'Xem combo';
 $('launchBalance').hidden=!grant;$('launchRemaining').textContent=String(remaining);
 $('launchBalanceLabel').textContent=active?'cuốn còn lại trên Mac này':'lượt chưa dùng đã hết hạn';
 $('launchBalanceHint').textContent=active?'Dùng các lượt còn lại trước 23:59 ngày 01/11/2026.':'Các đơn đã đặt trước hạn vẫn được xử lý và nhận lại audio.';
 if(!active)$('launchStatus').textContent='Chương trình đã kết thúc. Bạn vẫn nhận lại audio của các đơn đã đặt hợp lệ.';
 $('launchBuy').hidden=!!grant||!active;$('launchBuy').disabled=launchBusy||!launchState.configured||!launchState.available;
 $('launchBuy').textContent=launchBusy?'Đang kiểm tra…':order?.state==='awaiting_payment'?'Kiểm tra đơn combo':'Lấy combo · 50.000đ';
 $('launchCheck').hidden=!order||order.state!=='awaiting_payment';$('launchCheck').disabled=launchBusy;
 $('launchUse').hidden=!grant||!active||remaining<=0;$('launchUse').disabled=launchBusy;
 const payment=order?.state==='awaiting_payment'&&Date.parse(order.expiresAt)>Date.now()+launchServerDelta;
 $('launchPayment').hidden=!payment;
 if(payment&&launchState.bank){$('launchPayAmount').textContent=moneyVND(order.amountVND);$('launchBank').textContent=`${launchState.bank.name} · ${launchState.bank.account} · ${launchState.bank.holder}`;$('launchPayCode').textContent=order.paymentCode;}
 renderBookCloudCombo();
}
function openLaunchOffer(){
 launchTrigger=document.activeElement;launchReturnBook=$('bookCloudDialog').open;
 if(launchReturnBook)$('bookCloudDialog').close();
 if($('licensePanel').open)$('licensePanel').close();
 if($('appInfoDialog').open)$('appInfoDialog').close();
 launchToken=requestToken();launchBusy=true;launchChecks=0;clearLaunchPoll();$('launchStatus').textContent='Đang kiểm tra combo trên Mac này…';$('launchQR').replaceChildren();
 $('launchDialog').showModal();renderLaunch();send({action:'launchInfo',token:launchToken});
}
function checkLaunch(){if(launchBusy||!$('launchDialog').open)return;launchBusy=true;renderLaunch();send({action:'launchCheck',token:launchToken});}
function pollLaunch(){
 clearLaunchPoll();if(!$('launchDialog').open||document.hidden||launchChecks>=30||launchState.order?.state!=='awaiting_payment')return;
 launchTimer=setTimeout(()=>{launchChecks++;checkLaunch();},10000);
}
function renderBookCloudCombo(){
 if(!$('bookCloudLaunch'))return;
 const grant=bookCloudInfo?.launchBundle||launchState.bundle,offer=bookCloudInfo?.launchOffer||launchState.offer;
 const active=offer?.active===true&&Date.now()+launchServerDelta<Date.parse(offer.endsAt||launchEndsAt);
 $('bookCloudLaunch').hidden=!active&&!grant;
 $('bookCloudLaunchLabel').textContent=grant?`Combo trên Mac này · Còn ${grant.remaining}/5 cuốn`:'Combo ra mắt · 50.000đ / 5 cuốn';
 $('bookCloudLaunchHint').textContent=active?'Mua và dùng hết trước 23:59 · 01/11/2026':'Combo đã hết hạn · Đơn đã nhận vẫn được xử lý';
 $('bookCloudCombo').hidden=!grant||!active||grant.remaining<=0;
 $('bookCloudCombo').disabled=bookCloudBusy||!bookCloudInfo?.configured||!$('bookCloudConsent').checked;
 $('bookCloudCombo').textContent=bookCloudOrder?.fundingBundleId?'Cập nhật cuốn đã dùng combo':'Dùng 1 lượt combo';
}
function receiveLaunch(e){
 if(e.event==='bookPaymentQR'&&$('launchDialog').open&&e.code===launchState.order?.paymentCode){
  if(!/^([M0-9 h v z-])+$/.test(e.qrPath)||!Number.isInteger(e.qrSize)||e.qrSize>200)return true;
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),path=document.createElementNS(svg.namespaceURI,'path');
  svg.setAttribute('viewBox',`0 0 ${e.qrSize} ${e.qrSize}`);svg.setAttribute('role','img');svg.setAttribute('aria-label','QR thanh toán combo '+moneyVND(launchState.order.amountVND));path.setAttribute('d',e.qrPath);svg.append(path);$('launchQR').replaceChildren(svg);return true;
 }
 if(e.event!=='launchResult')return false;
 if(e.token!==launchToken||!$('launchDialog').open)return true;
 launchBusy=false;
 if(!e.success){$('launchStatus').textContent=e.message;renderLaunch();return true;}
 launchState={...launchState,...e};if(e.offer?.serverTime)launchServerDelta=Date.parse(e.offer.serverTime)-Date.now();
 launchQuoteKey=e.pendingRequestKey||launchQuoteKey;
 const active=launchActive(),order=e.order;
 $('launchStatus').textContent=!active?'Chương trình đã kết thúc. Bạn vẫn nhận lại audio của các đơn đã đặt hợp lệ.':e.bundle?`Đã xác nhận combo. Còn ${e.bundle.remaining}/5 cuốn trên Mac này.`:!launchState.configured||!launchState.available?'Combo chưa mở thanh toán. Bạn vẫn có thể dùng Lite và tạo thử miễn phí.':order?.state==='awaiting_payment'?'Chuyển đúng 50.000đ và mã của đơn này. Đóng cửa sổ không làm mất đơn.':order?.state==='expired'?'QR cũ đã hết hạn. Nếu đã chuyển tiền, kiểm tra giao dịch trước khi tạo đơn mới.':'Một combo duy nhất trên Mac này. Chọn combo khi bạn sẵn sàng dùng cả 5 lượt trước hạn.';
 renderLaunch();
 if(order?.state==='awaiting_payment'&&e.bank)send({action:'bookPaymentQR',bank:e.bank,code:order.paymentCode,amount:order.amountVND});
 pollLaunch();return true;
}
$('dismissLaunchBanner').onclick=()=>{launchBannerDismissed=true;try{localStorage.setItem('windi-launch-banner-dismissed','1');}catch{}renderLaunch();$('appInfo').focus();};
$('openLaunchOffer').onclick=openLaunchOffer;$('bookCloudLaunchOpen').onclick=openLaunchOffer;
$('closeLaunchOffer').onclick=()=>$('launchDialog').close();
$('launchBuy').onclick=()=>{
 if(launchBusy||!launchState.available||!launchActive())return;
 if(launchState.order?.state==='awaiting_payment'&&Date.parse(launchState.order.expiresAt)>Date.now()+launchServerDelta){checkLaunch();return;}
 clearLaunchPoll();if(launchState.order?.state==='expired')launchQuoteKey=null;launchQuoteKey||=requestToken();launchBusy=true;renderLaunch();$('launchStatus').textContent='Đang tạo đơn combo 50.000đ…';send({action:'launchQuote',token:launchToken,requestKey:launchQuoteKey});
};
$('launchCheck').onclick=()=>{launchChecks=0;checkLaunch();};
$('launchUse').onclick=()=>{launchReturnBook=!!book;$('launchDialog').close();if(!book)toast('Chọn hoặc thêm sách trong thư viện, rồi chọn Pro để dùng lượt combo.');};
$('launchCopyCode').onclick=()=>{if(launchState.order)send({action:'copyBookPayment',value:launchState.order.paymentCode});};
$('launchDialog').addEventListener('close',()=>{clearLaunchPoll();launchToken='';const reopen=launchReturnBook;launchReturnBook=false;if(reopen&&book?.status==='ready')openBookCloud();else launchTrigger?.focus?.();});
const receiveBeforeLaunch=window.receive;
window.receive=e=>{
 if(receiveLaunch(e))return;
 receiveBeforeLaunch(e);
 if(e.event==='bookCloudInfo')renderBookCloudCombo();
 if(e.event==='bookCloudResult'&&e.success&&e.bundle){launchState.bundle=e.bundle;if(bookCloudInfo)bookCloudInfo.launchBundle=e.bundle;renderLaunch();}
};
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearLaunchPoll();else if($('launchDialog').open)pollLaunch();});
window.addEventListener('pagehide',clearLaunchPoll);
setInterval(renderLaunch,60000);renderLaunch();

$('launchWallet').onclick=openLaunchOffer;
