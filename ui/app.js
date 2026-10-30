'use strict';
const $=id=>document.getElementById(id);
const send=value=>window.webkit?.messageHandlers.app.postMessage(value);
let books=[], book=null, index=0, dirty=false, playing=false, loaded=false, pending=false, waitingNext=false;
let jobs={}, toastTimer, awaitingImport=false, selectedId=null, renderedContentKey='', libraryKey='', musicCatalog=[], musicPreview=false, scopeBookId=null, scopeDirty=false, saveMusicTimer, productionTrigger=null;
let modelCatalog=[], machine={}, freeBytes=0, modelDownload=null, modelProgress=null;
let homeActive=true,infoTrigger=null;
const bookCovers=new Map(),coverRequests=new Set();
function requestCover(id){if(coverRequests.has(id))return;coverRequests.add(id);send({action:'bookCover',bookId:id});}
function drawCover(element,value){
 const image=bookCovers.get(value.id),key=JSON.stringify([value.id,value.title,!!image]);
 if(element.dataset.cover===key)return;element.dataset.cover=key;element.replaceChildren();
 element.classList.toggle('has-cover',!!image);
 if(image){const img=document.createElement('img');img.src=image;img.alt='';element.append(img);}
 else{const name=document.createElement('span');name.className='cover-monogram user-text';name.textContent=(value.title||'S').trim().slice(0,1).toLocaleUpperCase('vi');element.append(name);}
 requestCover(value.id);
}
function showHome(){
 if(guardDirty())return;
 flushReader();stop();homeActive=true;selectedId=null;awaitingImport=false;book=null;libraryKey='';resetReader(null);
 closeProduction();$('modelsPanel').hidden=true;$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');
 render();$('emptyImport').focus();
}
function openAppInfo(){
 if(document.querySelector('dialog[open]'))return;infoTrigger=document.activeElement;
 $('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');$('appInfoDialog').showModal();$('closeAppInfo').focus();
}
function closeAppInfo(){$('appInfoDialog').close();}
const audioRuns=new Map();
let listeningTimer=null,listeningKey='',listeningToken='',nativeQueueKey='',playSession='',preparedKey='';
function listeningIndices(){
 return scopeIndices(selectedScope()).filter(i=>i>=index&&/[\p{L}\p{N}]/u.test(book.segments[i]?.text||''));
}
function prepareListening(immediate=false){
 clearTimeout(listeningTimer);
 const run=()=>{
  if(readerState.mode==='read'||!book||book.status!=='ready'||book.model!=='nano'||dirty||aux||jobs.audio||!modelCatalog.find(m=>m.id==='nano')?.ready)return;
  const indices=listeningIndices().slice(0,12);if(!indices.length)return;
  const key=JSON.stringify([book.id,book.model,book.voice,book.speed,indices.map(i=>[i,book.segments[i].id,book.segments[i].text])]);
  if(key===listeningKey)return;listeningKey=key;
  if(indices.every(i=>book.segments[i].audio))return;
  listeningToken=requestToken();
  send({action:'prepareListening',bookId:book.id,start:index,scope:selectedScope(),seconds:60*book.speed,token:listeningToken});
 };
 if(immediate)run();else listeningTimer=setTimeout(run,250);
}
function prepareCurrent(){
 if(!book||loaded||pending||aux)return;const s=book.segments[index];if(!s?.audio)return;
 const key=JSON.stringify([book.id,index,s.audio]);if(key===preparedKey)return;preparedKey=key;
 send({action:'prepareCurrent',path:s.audio,bookId:book.id,segment:index});
}
function nanoBufferReady(){
 const indices=listeningIndices();let seconds=0,count=0;
 for(const i of indices){const s=book.segments[i];if(!s.audio)break;count++;seconds+=Math.max(0,s.duration-(i===index?book.position.seconds:0))/book.speed;}
 return seconds>=2||count===indices.length||count>=12;
}
function queueUpcoming(){
 if(!book||!loaded||aux||!playSession)return;
 const segments=[];
 for(const i of listeningIndices().filter(i=>i>index).slice(0,12)){const s=book.segments[i];if(!s.audio)break;segments.push({segment:i,path:s.audio});}
 const key=JSON.stringify([playSession,index,segments]);if(key===nativeQueueKey)return;nativeQueueKey=key;
 send({action:'queueNext',bookId:book.id,fromSegment:index,sessionId:playSession,segments});
}
function beginGeneration(request){
 audioRuns.set(request.bookId,{phase:'preparing',done:0,total:null});
 $('toast').hidden=true;closeProduction();renderGeneration();$('generationStatus').scrollIntoView({block:'nearest',behavior:'auto'});
}
function renderGeneration(){
 const run=book&&audioRuns.get(book.id),panel=$('generationStatus');panel.hidden=!run;if(!run)return;
 const active=['preparing','generating'].includes(run.phase),total=run.total||0,done=Math.min(run.done||0,total);
 panel.dataset.phase=run.phase;$('cancelAudio').hidden=!active;$('closeGeneration').hidden=active;
 const labels={preparing:'Đang chuẩn bị giọng đọc…',generating:'Đang tạo bản đọc',complete:'Đã tạo xong bản đọc',cancelled:'Đã dừng · giữ phần đã tạo',error:'Tạo bản đọc bị gián đoạn'};
 $('generationText').textContent=labels[run.phase];
 $('generationCount').textContent=total?`${done}/${total} đoạn · ${Math.floor(done/total*100)}%`:'';
 const bar=$('generationProgress');bar.max=total||1;if(total)bar.value=done;else bar.removeAttribute('value');
 bar.hidden=!total&&!active;
 $('generationDetail').classList.toggle('user-text',!!run.title&&run.phase!=='error');
 $('generationDetail').textContent=run.phase==='error'?run.message||'Hãy thử tạo lại phần chưa hoàn tất.':run.title||'Bản đọc được lưu trong Sách nói của bạn.';
}
$('closeGeneration').onclick=()=>{if(book)audioRuns.delete(book.id);renderGeneration();$('generateAll').focus();};
let entitlement={tier:'development',label:'Bản dùng thử'},licenseChecking=false,manualLicenseID=null;
const licenseFeedback=document.createElement('p');licenseFeedback.id='licenseFeedback';licenseFeedback.setAttribute('role','status');licenseFeedback.setAttribute('aria-live','polite');licenseFeedback.hidden=true;$('purchaseHint').after(licenseFeedback);
const deviceRow=document.createElement('p'),deviceCode=document.createElement('code'),copyDevice=document.createElement('button'),checkLicense=document.createElement('button');
deviceRow.append('Mã kích hoạt cho Mac này: ',deviceCode);deviceCode.id='licenseDevice';copyDevice.id='copyDevice';copyDevice.className='text';copyDevice.textContent='Sao chép mã';deviceRow.append(copyDevice);$('licenseState').after(deviceRow);
checkLicense.id='checkLicense';checkLicense.className='secondary';checkLicense.textContent='Cập nhật Pro đã mua';$('importLicense').before(checkLicense);
copyDevice.onclick=()=>send({action:'copyDeviceCode'});checkLicense.onclick=()=>{licenseChecking=true;manualLicenseID=requestToken();checkLicense.disabled=true;licenseFeedback.textContent='Đang cập nhật Pro…';licenseFeedback.hidden=false;send({action:'checkLicense',requestId:manualLicenseID,bookId:book?.id});};
const licenseButton=document.createElement('button');licenseButton.id='manageLicense';licenseButton.className='text';licenseButton.textContent='Gói Free / Pro';$('manageModels').after(licenseButton);
function offerPro(){if(entitlement.checkoutURL)openPayment();else openLicense();}
function openLicense(){closeAppInfo();if(!licenseChecking)licenseFeedback.hidden=true;renderLicense();$('licensePanel').showModal();}
function renderLicense(){
 licenseButton.textContent='Lite / Pro · Giá theo cuốn';
 $('buyPro').textContent='Chọn Pro cho cuốn sách';$('buyPro').disabled=!book;
 $('licenseState').textContent=entitlement.tier==='pro'?'Bản quyền cũ của bạn vẫn được giữ.':'Lite miễn phí · Pro thanh toán theo cuốn';
 deviceRow.hidden=!entitlement.deviceCode;deviceCode.textContent=entitlement.deviceCode||'';
 checkLicense.textContent='Kiểm tra bản quyền cũ';checkLicense.disabled=!entitlement.licenseBaseURL||licenseChecking;
 $('proFeatures').textContent='Giọng đọc giàu ngữ điệu. Tạo thử 5 lượt, tối đa 5.000 ký tự/lượt; tự lấy đoạn đầu sách.';
 $('purchaseHint').textContent='Mỗi đơn dành cho đúng một cuốn sách và giọng đã chọn. Không cần tài khoản hoặc email.';
}

licenseButton.onclick=openLicense;$('closeLicense').onclick=()=>$('licensePanel').close();
let paymentFromLicense=false,paymentCompleted=false,paymentTrigger=null;
function paymentMessage(message,state='pending'){$('paymentPanel').dataset.state=state;$('paymentStatus').textContent=message;}
function paymentSucceeded(){
 paymentCompleted=true;$('paymentContent').hidden=true;$('paymentFooter').hidden=true;$('paymentNotice').hidden=true;$('paymentSuccess').hidden=false;$('paymentPanel').dataset.state='success';
 $('paymentPanel').setAttribute('aria-labelledby','paymentSuccessTitle');$('paymentPanel').setAttribute('aria-describedby','paymentExpiry');
 $('paymentExpiry').textContent=entitlement.expiresAt?'Pro dùng đến '+new Date(entitlement.expiresAt).toLocaleDateString('vi-VN')+'.':'Pro đã được mở cho Mac này.';$('finishPayment').focus();
}
const paymentWatcher=new PaymentWatcher({
 check:payload=>{$('checkPayment').disabled=true;send({action:'checkLicense',...payload});},
 cancel:requestId=>send({action:'cancelLicenseCheck',requestId}),
 success:paymentSucceeded,
 state:(state,message)=>{
  const texts={pending:'Đang chờ thanh toán · Tự động cập nhật',retry:'Chưa kết nối được. App đang thử lại…',paused:'Đã tạm dừng cập nhật. Nếu đã chuyển khoản, bấm Kiểm tra ngay; không cần chuyển lại.',unavailable:'Thanh toán tạm thời chưa sẵn sàng. Hãy đóng cửa sổ và thử lại sau.'};
  paymentMessage(state==='pending'?texts.pending:message||texts[state],state);
  $('checkPayment').disabled=state==='unavailable'||!entitlement.licenseBaseURL;
 }
});
document.addEventListener('visibilitychange',()=>paymentWatcher.setVisible(!document.hidden));
window.addEventListener('pagehide',()=>paymentWatcher.stop());
function openPayment(){
 paymentTrigger=document.activeElement;
 paymentWatcher.stop();
 $('paymentPanel').setAttribute('aria-labelledby','paymentTitle');$('paymentPanel').setAttribute('aria-describedby','paymentDescription');
 paymentFromLicense=$('licensePanel').open;paymentCompleted=false;
 if(paymentFromLicense)$('licensePanel').close();
 $('paymentContent').hidden=false;$('paymentFooter').hidden=false;$('paymentNotice').hidden=false;$('paymentSuccess').hidden=true;
 for(const id of ['paymentBank','paymentAccount','paymentHolder','paymentCode'])$(id).textContent='—';
 $('paymentQR').setAttribute('hidden','');$('paymentQR').removeAttribute('src');$('paymentQRLoading').hidden=false;$('paymentQRLoading').textContent='Đang tạo mã QR…';
 $('checkPayment').disabled=true;$('copyPaymentAccount').disabled=true;$('copyPaymentCode').disabled=true;
 paymentMessage('Đang chuẩn bị thanh toán…');$('paymentPanel').showModal();$('closePayment').focus();send({action:'purchase'});
}
function closePayment(){$('paymentPanel').close();}
$('buyPro').onclick=()=>{$('licensePanel').close();openBookCloud();};$('closePayment').onclick=closePayment;
$('paymentPanel').addEventListener('close',()=>{paymentWatcher.stop();if(paymentFromLicense&&!paymentCompleted){openLicense();$('buyPro').focus();}else{const target=paymentTrigger?.isConnected&&paymentTrigger.getClientRects().length?paymentTrigger:licenseButton;target.focus();}});
$('finishPayment').onclick=closePayment;
$('copyPaymentAccount').onclick=()=>send({action:'copyPaymentAccount'});
$('copyPaymentCode').onclick=()=>send({action:'copyDeviceCode'});
$('checkPayment').onclick=()=>paymentWatcher.checkNow();
$('importLicense').onclick=()=>send({action:'licenseDialog',bookId:book?.id});
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('aria-hidden','true');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href','#i-'+name);svg.append(use);return svg;}
function setPlay(active){$('play').querySelector('use').setAttribute('href',active?'#i-pause':'#i-play');$('play').setAttribute('aria-label',active?'Tạm dừng':'Phát');document.body.classList.toggle('is-playing',playing);document.body.classList.toggle('is-preparing',pending&&!loaded);$('previewMusic').disabled=playing||$('musicTrack').value==='none'||!!book?.musicUnavailable;}
function animateContent(key){
 if(key===renderedContentKey)return;renderedContentKey=key;
 if(document.documentElement.dataset.motion==='off'||(document.documentElement.dataset.motion!=='on'&&matchMedia('(prefers-reduced-motion: reduce)').matches))return;
 // Keep semantic document contents fully opaque for WebKit accessibility.
 const el=book?document.querySelector('.document'):$('empty');
 el.classList.remove('content-enter');void el.offsetWidth;el.classList.add('content-enter');
 el.addEventListener('animationend',()=>el.classList.remove('content-enter'),{once:true});
}
function preference(name,fallback){try{return localStorage.getItem('windi-'+name)||fallback;}catch{return fallback;}}
function applyAppearance(){cancelFlipbookTurn();document.querySelectorAll('.content-enter,.library-enter').forEach(el=>el.classList.remove('content-enter','library-enter'));for(const name of ['theme','motion']){const value=$(name).value;document.documentElement.dataset[name]=value;try{localStorage.setItem('windi-'+name,value);}catch{}}send({action:'appearance',theme:$('theme').value,motion:$('motion').value});}
const unit=(value=book,capital=false)=>{const name=value?.unitLabel||'trang';return capital?name[0].toLocaleUpperCase('vi')+name.slice(1):name;};
const fmt=n=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
function toast(message){if($('licensePanel').open){licenseFeedback.textContent=message;licenseFeedback.hidden=false;}$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,7000);}
function stop(){cancelReaderLite();clearTimeout(listeningTimer);listeningKey='';listeningToken='';nativeQueueKey='';playSession='';preparedKey='';send({action:'cancelListening'});aux=null;previewToken=null;musicPreview=false;send({action:'stop'});playing=false;loaded=false;pending=false;waitingNext=false;setPlay(false);}
function guardDirty(){if(dirty){toast('Lưu nội dung hoặc hủy sửa trước khi đổi chương hay bắt đầu nghe.');return true;}return false;}
function selectBook(id){if(guardDirty())return;flushReader();stop();homeActive=false;selectedId=id;send({action:'get',bookId:id});}
function renderBooks(){
 $('bookCount').textContent=books.length;
 const query=$('librarySearch').value.trim().toLocaleLowerCase('vi');
 const filtered=books.filter(b=>b.title.toLocaleLowerCase('vi').includes(query));
 const key=JSON.stringify([book?.id,filtered.map(b=>[b.id,b.title,b.pages,b.segments,b.finished])]);
 $('searchEmpty').hidden=!query||!!filtered.length;
 if(key===libraryKey)return;libraryKey=key;
 const nav=$('books');nav.replaceChildren();
 for(const b of filtered){
  const btn=document.createElement('button');btn.className='book-item'+(book?.id===b.id?' active':'');btn.setAttribute('aria-current',book?.id===b.id?'true':'false');
  const thumb=document.createElement('span');thumb.className='book-thumb';thumb.setAttribute('aria-hidden','true');drawCover(thumb,b);
  const copy=document.createElement('span');copy.className='book-copy';const title=document.createElement('strong');title.textContent=b.title;const meta=document.createElement('small');meta.textContent=`${b.pages} ${unit(b)} · ${b.segments} đoạn${b.finished?' · Đã nghe xong':''}`;copy.append(title,meta);btn.append(thumb,copy);btn.onclick=()=>selectBook(b.id);const entry=document.createElement('div');entry.className='book-entry';const remove=document.createElement('button');remove.className='delete-library-book';remove.textContent='×';remove.setAttribute('aria-label','Xóa '+b.title+' khỏi thư viện');remove.title='Xóa khỏi thư viện';remove.onclick=()=>openDeleteBook(b,remove);entry.append(btn,remove);nav.append(entry);
 }
}
function render(){
 $('home').setAttribute('aria-current',book?'false':'page');
 $('breadcrumbTitle').classList.toggle('user-text',!!book);
 $('empty').hidden=!!book;$('reader').hidden=!book;$('player').hidden=!book?.segments.length;
 if(!book){$('breadcrumbTitle').textContent='Trang chủ';document.body.classList.remove('is-generating');renderReader();renderBooks();animateContent('empty');return;}
 index=Math.min(index,Math.max(0,book.segments.length-1));
 $('title').textContent=book.title;$('breadcrumbTitle').textContent=book.title;
 $('meta').textContent=`${book.pages.length} ${unit()} · ${book.segments.length} đoạn · `+(book.model==='pro-cloud'?`${(book.audiobooks||[]).filter(t=>t.model==='pro-cloud'&&t.status==='ready').length} bản Pro đã lưu`:`${book.readyCount} đoạn đã tạo`);
 drawCover($('titleCover'),book);
 if(book.layoutProcessing?.chapterCount)$('meta').textContent+=` · ${book.layoutProcessing.chapterCount} chương`;
 document.body.classList.toggle('is-generating',jobs.audio===book.id);
 renderModelControls();$('voice').value=book.voice;$('speed').value=String(book.speed);
 renderImportProcessing();
 $('voice').disabled=jobs.audio===book.id||jobs.export===book.id;$('bookLanguage').value=book.language||'vi';$('bookLanguage').disabled=jobs.audio===book.id||jobs.export===book.id||book.status!=='ready';
 $('generateAll').disabled=!book.segments.length||dirty;
 $('export').disabled=!book.segments.length||dirty;
 renderGeneration();
 renderWorkspace();renderReader();
 const s=book.segments[index];
 if(s&&!aux){
  $('playingTitle').textContent=`${pending?'Đang chuẩn bị':playing?'Đang nghe':loaded?'Tạm dừng':'Sẵn sàng nghe'} · Đoạn ${index+1}`;
  $('positionLabel').textContent=`${index+1} / ${book.segments.length}`;
  if(!loaded&&!playing){const saved=book.position.segment===index?book.position.seconds:0;$('seek').max=s.duration||1;$('seek').value=saved;$('time').textContent=`${fmt(saved)} / ${fmt(s.duration||0)}`;}
 }
 $('prev').disabled=index===0;$('next').disabled=index>=book.segments.length-1;
 if(!$('modelsPanel').hidden)renderModels();renderChapters();renderBooks();renderProduction();animateContent(`${book.id}:${activeChapterId}:${workspaceTab}`);if(aux)renderAux();setPlay(playing||pending);
}
function renderChapters(){}
function selectIndex(i,autoplay=false){if(guardDirty()||!book?.segments[i])return;stop();readerSeconds=0;readerDuration=0;activeChapterId=book.sections?.find(c=>c.indices.includes(i))?.id||activeChapterId;book.finished=false;const summary=books.find(b=>b.id===book.id);if(summary)summary.finished=false;index=i;book.position={segment:i,seconds:0};send({action:'position',bookId:book.id,segment:i,seconds:0});$('seek').value=0;$('time').textContent='0:00 / 0:00';render();prepareCurrent();prepareListening();if(autoplay)startPlay();}
function startPlay(){
 if(guardDirty()||!book?.segments[index])return;
 if(book.status!=='ready'){toast('Chờ xử lý sách xong để nghe bản đã sắp xếp.');return;}
 if(!scopeIndices(selectedScope()).includes(index)){openProduction('scope');toast('Chọn phạm vi có đoạn đang đọc trước khi nghe.');return;}
 const s=book.segments[index];if(!/[\p{L}\p{N}]/u.test(s.text)){const next=scopeIndices(selectedScope()).find(i=>i>index);if(next!==undefined)selectIndex(next,true);else toast('Phần này chỉ có ký hiệu trang trí. Dọn nội dung trước khi tạo.');return;}musicPreview=false;pending=true;
 if(book.model==='nano'&&s.audio&&!nanoBufferReady()){prepareListening(true);$('playingTitle').textContent='Đang chuẩn bị giọng đọc…';setPlay(true);return;}
 if(s.audio){pending=false;loaded=true;preparedKey='';playSession=requestToken();nativeQueueKey='';send({action:'play',sessionId:playSession,path:s.audio,bookId:book.id,segment:index,speed:book.speed,seconds:book.position.segment===index?book.position.seconds:0,music:musicPayload()});queueUpcoming();prepareListening(true);}
 else if(book.model==='pro-cloud'){pending=false;setPlay(false);openBookCloud({mode:'trial',chapterId:activeSection()?.id});return;}
 else if(book.model==='clone-pro'){pending=false;setPlay(false);openModels();toast('Chọn giọng đọc local để tạo sách nói.');return;}
 else if(book.model==='nano'){if(!modelCatalog.find(m=>m.id==='nano')?.ready){pending=false;setPlay(false);openModels();return;}prepareListening(true);}
 else if(!jobs.audio){const selection=selectedScope();send({action:'generate',bookId:book.id,scope:selection});}
 $('playingTitle').textContent=s.audio?`Đang nghe · Đoạn ${index+1}`:'Đang chuẩn bị giọng đọc…';
 setPlay(true);
}
let fileDragActive=false;
function setFileDrag(active){
 active=!!active&&!document.querySelector('dialog[open]');
 if(active===fileDragActive)return;
 fileDragActive=active;
 document.body.classList.toggle('is-file-dragging',active);
 $('importInvitation').textContent=active?'Thả EPUB, PDF hoặc ảnh vào đây':'Sách của bạn. Giọng đọc của bạn.';
 $('emptyImportLabel').textContent=active?'Thả để mở sách':'Chọn EPUB, PDF hoặc ảnh';
}
window.receive=function(e){
 if(handleLibraryEvent(e)||handleReaderEvent(e))return;
 if(e.event==='processing'){receiveProcessing(e);return;}
 if(handleWorkspaceEvent(e))return;
 if(e.event==='buildInfo'){$('appBuildBadge').textContent=`v${e.version} · Build ${e.build}`;}
 else if(e.event==='showAppInfo'){openAppInfo();}
 else if(e.event==='showHome'){showHome();}
 else if(e.event==='bookCover'){
  if(typeof e.image==='string'&&e.image.length<400000&&/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(e.image)){
   bookCovers.set(e.bookId,e.image);libraryKey='';renderBooks();if(book?.id===e.bookId)drawCover($('titleCover'),book);
  }
 }
 else if(e.event==='fileDrag'){setFileDrag(e.active);}
 else if(e.event==='requestImport'){pick();}
 else if(e.event==='filesSelected'){
  setFileDrag(false);
  if(guardDirty())return;
  if(document.querySelector('dialog[open]')){toast('Đóng cửa sổ đang mở trước khi thêm sách.');return;}
  awaitingImport=true;send({action:'importSelection',selectionToken:e.selectionToken,forceOCR:false,language:'vi'});
 }else if(e.event==='accessibility'){
 document.documentElement.dataset.transparency=e.reduceTransparency?'reduced':'normal';
 document.documentElement.dataset.contrast=e.increaseContrast?'more':'normal';
}else if(e.event==='init'){
  musicCatalog=e.music||[];
  books=e.books;$('resourceState').textContent=e.ready?'Lite sẵn sàng · Không cần mạng':'Chọn một gói giọng để bắt đầu nghe';
  $('voice').replaceChildren();for(const v of e.voices){let opt=document.createElement('option');opt.value=v.id;opt.textContent=v.label;$('voice').append(opt);}
  render();
 }else if(e.event==='purchaseReady'){
  if(!$('paymentPanel').open)return;
  $('paymentBank').textContent=e.bank;$('paymentAccount').textContent=e.account;$('paymentHolder').textContent=e.holder;$('paymentCode').textContent=e.content;
  if(typeof e.qrPath==='string'&&/^([M0-9 h v z-])+$/.test(e.qrPath)&&Number.isInteger(e.qrSize)&&e.qrSize>20&&e.qrSize<200){
   const qr=document.createElementNS('http://www.w3.org/2000/svg','svg'),path=document.createElementNS(qr.namespaceURI,'path');
   qr.id='paymentQR';qr.setAttribute('viewBox',`0 0 ${e.qrSize} ${e.qrSize}`);qr.setAttribute('role','img');qr.setAttribute('aria-label','Mã QR chuyển khoản 189.000 đồng cho Windi Sách Nói Pro');
   path.setAttribute('d',e.qrPath);qr.append(path);$('paymentQR').replaceWith(qr);$('paymentQRLoading').hidden=true;
  }else{$('paymentQRLoading').textContent='Chưa hiển thị được QR. Bạn có thể chuyển khoản bằng thông tin bên cạnh.';}
  $('copyPaymentAccount').disabled=false;$('copyPaymentCode').disabled=false;
  paymentWatcher.setVisible(!document.hidden);
  if(entitlement.licenseBaseURL)paymentWatcher.start({bookId:book?.id,...(entitlement.tier==='pro'&&entitlement.expiresAt?{afterExpiresAt:entitlement.expiresAt}:{})});
  else paymentMessage('Thanh toán tạm thời chưa sẵn sàng. Hãy đóng cửa sổ và thử lại sau.','unavailable');
 }else if(e.event==='purchaseError'){$('paymentQRLoading').textContent=e.message;paymentMessage(e.message,'error');}
 else if(e.event==='paymentAccountCopied'){toast('Đã sao chép số tài khoản.');}
 else if(e.event==='cloudConnection'){handleCreditEvent(e);}
 else if(e.event==='creditQR'){renderCreditQR(e);}
 else if(e.event==='models'){const previous=entitlement.tier;entitlement=e.entitlement||entitlement;if(previous==='pro'&&entitlement.tier!=='pro'){stop();if(book)send({action:'get',bookId:book.id});}modelCatalog=e.models.filter(m=>!['turbo','f5-private'].includes(m.id)&&(proMaxEnabled||m.id!=='clone-pro'));if(e.credits)creditWallet=e.credits;machine=e.hardware;freeBytes=e.freeBytes;renderLicense();renderModels();renderModelControls();renderCloud();prepareListening();}
 else if(e.event==='licenseCheck'){
  if(paymentWatcher.result(e)){$('checkPayment').disabled=e.state==='unavailable'||!entitlement.licenseBaseURL;}
  else if(e.requestId===manualLicenseID){manualLicenseID=null;licenseChecking=false;renderLicense();licenseFeedback.textContent=e.message||'Chưa có thay đổi với Pro trên Mac này. Nếu đã chuyển khoản, mở cửa sổ mua Pro để tự cập nhật.';licenseFeedback.hidden=false;}
 }
 else if(e.event==='licenseImported'){
  if(e.requestId&&paymentWatcher.result({...e,state:'success'}))return;
  if(e.requestId&&e.requestId!==manualLicenseID)return;
  manualLicenseID=null;licenseChecking=false;
  if($('paymentPanel').open){paymentWatcher.stop();paymentSucceeded();}
  else{toast('Pro đã sẵn sàng. Bạn có thể chọn giọng riêng F5.');$('licensePanel').close();}
 }
 else if(e.event==='deviceCopied'){toast('Đã sao chép mã máy.');}
 else if(e.event==='modelJob'){modelDownload=e.running?e.modelId:null;if(!e.running)modelProgress=null;renderModels();}
 else if(e.event==='modelProgress'){modelProgress=e;renderModels();}
 else if(e.event==='musicEnded'){if(musicPreview){musicPreview=false;renderMusicControls();}}
 else if(e.event==='library'){books=e.books;renderBooks();}
 else if(e.event==='book'){
  if((!homeActive&&e.book.id===selectedId)||(awaitingImport&&!books.some(b=>b.id===e.book.id))){
   homeActive=false;
   const changed=book?.id!==e.book.id;if(changed){stop();dirty=false;index=e.book.position.segment;awaitingImport=false;}else if(book?.model!==e.book.model||book?.voice!==e.book.voice||book?.language!==e.book.language){stop();}
   prepareWorkspaceBook(e.book,changed);book=e.book;selectedId=book.id;render();prepareCurrent();queueUpcoming();prepareListening();
   if(pending&&book.segments[index]?.audio)startPlay();
   if(waitingNext&&book.segments[index+1])selectIndex(index+1,true);
  }
 }else if(e.event==='listeningReady'){
  if(book?.id!==e.bookId||e.token!==listeningToken||book.model!==e.model||book.voice!==e.voice)return;
  const s=book.segments[e.index];if(!s||s.id!==e.segmentId||s.text!==e.text)return;
  if(!s.audio)book.readyCount++;s.audio=e.path;s.duration=e.duration;
  if(pending&&book.segments[index]?.audio)startPlay();else {prepareCurrent();queueUpcoming();}
  renderWorkspace();
 }else if(e.event==='listeningBuffer'){
  if(e.token===listeningToken&&e.state==='error'){listeningKey='';if(pending){pending=false;setPlay(false);toast(e.message);}}
 }else if(e.event==='advanced'){
  if(book?.id!==e.bookId||e.sessionId!==playSession||e.fromSegment!==index)return;
  index=e.segment;loaded=true;playing=e.playing!==false;pending=false;nativeQueueKey='';book.position={segment:index,seconds:0};
  activeChapterId=book.sections?.find(c=>c.indices.includes(index))?.id||activeChapterId;
  render();queueUpcoming();prepareListening(true);
 }else if(e.event==='job'){
  if(e.kind==='import'&&e.running&&e.bookId===book?.id)stop();
  if(e.kind==='audio'){const run=audioRuns.get(e.bookId);if(e.running)audioRuns.set(e.bookId,{phase:'preparing',done:0,total:null});else if(run)run.phase=e.cancelled?'cancelled':run.phase==='error'?'error':'complete';}
  if(e.running)jobs[e.kind]=e.bookId;else delete jobs[e.kind];render();
  if(e.kind==='audio'&&!e.running){listeningKey='';if(!e.cancelled||playing||pending)prepareListening();if(pending&&!book?.error&&!e.cancelled)startPlay();}
 }else if(e.event==='error'){if(e.bookId&&(e.kind==='audio'||e.action==='generate')){const run=audioRuns.get(e.bookId)||{};run.phase='error';run.message=e.message;audioRuns.set(e.bookId,run);renderGeneration();}chapterSave=null;previewToken=null;renderWorkspace();awaitingImport=false;pending=false;waitingNext=false;setPlay(playing);toast(e.message);}
 else if(e.event==='progress'){
  if(e.kind==='audio'){audioRuns.set(e.bookId,{phase:e.phase||'generating',done:e.done,total:e.total,title:e.title,page:e.page,index:e.index});if(book?.id===e.bookId)renderGeneration();}
  else if(book?.id===e.bookId&&e.kind==='export'){$('exportProgress').hidden=false;$('exportProgress').textContent=e.done===e.total?'Đang hoàn tất tệp âm thanh…':`Đang lưu bản đọc · ${Math.round(e.done/e.total*100)}%`;}
 }
 else if(e.event==='playback'&&e.bookId===book?.id&&e.segment===index){
  playing=e.playing;book.position={segment:index,seconds:e.seconds};$('seek').max=e.duration;$('seek').value=e.seconds;$('time').textContent=`${fmt(e.seconds)} / ${fmt(e.duration)}`;
  setPlay(playing);$('playingTitle').textContent=`${playing?'Đang nghe':'Tạm dừng'} · ${unit(book,true)} ${book.segments[index].page+1} · Đoạn ${index+1}`;if(playing){queueUpcoming();prepareListening();}
 }else if(e.event==='ended'&&e.bookId===book?.id){
  loaded=false;playing=false;setPlay(false);
  if(!e.success){render();toast('Audio phát bị gián đoạn. Bấm nghe để thử lại.');return;}
  const selected=scopeIndices(selectedScope());
  const next=selected.find(i=>i>index&&/[\p{L}\p{N}]/u.test(book.segments[i]?.text||''));
  if(next!==undefined)selectIndex(next,true);
  else if(selectedScope().type!=='all'){book.position={segment:index,seconds:0};send({action:'position',bookId:book.id,segment:index,seconds:0});render();toast('Đã nghe hết phạm vi đang chọn.');}
  else if(book.status!=='ready'){waitingNext=true;$('playingTitle').textContent=`Đang chờ ${unit()} tiếp theo…`;}
  else{send({action:'position',bookId:book.id,segment:index,seconds:0,finished:true});book.position={segment:index,seconds:0};book.finished=true;const summary=books.find(b=>b.id===book.id);if(summary)summary.finished=true;render();toast('Bạn đã nghe hết sách.');}
 }else if(e.event==='pickCancelled'){awaitingImport=false;}else if(e.event==='exported'){if(book?.id===e.bookId)send({action:'get',bookId:book.id});$('exportProgress').hidden=false;$('exportProgress').textContent='Đã lưu file có nhạc nền theo thiết lập hiện tại.';toast('Đã tải về: '+e.path);}
};
function pick(){if(guardDirty())return;if(document.querySelector('dialog[open]')){toast('Đóng cửa sổ đang mở trước khi thêm sách.');return;}awaitingImport=true;send({action:'pick',forceOCR:false,language:'vi',uiLanguage:window.i18n?.language||'vi'});}
$('import').onclick=pick;$('emptyImport').onclick=pick;$('reveal').onclick=()=>send({action:'reveal'});
$('home').onclick=showHome;$('breadcrumbHome').onclick=showHome;$('appInfo').onclick=openAppInfo;$('closeAppInfo').onclick=closeAppInfo;
$('appInfoDialog').addEventListener('close',()=>{if(document.querySelector('dialog[open]')||!$('modelsPanel').hidden)return;const target=infoTrigger?.isConnected&&infoTrigger.getClientRects().length?infoTrigger:$('appInfo');target.focus();});
bindWorkspace();
$('voice').onchange=()=>{if(guardDirty()){render();return;}stop();send({action:'settings',bookId:book.id,voice:$('voice').value});};
$('speed').onchange=()=>{if(!book)return;const speed=Number($('speed').value);book.speed=speed;send({action:'rate',speed});send({action:'settings',bookId:book.id,speed});};
$('play').onclick=()=>{if(aux){if(playing)send({action:'pause'});else send({action:'continue'});return;}if(playing){send({action:'pause'});}else if(pending){pending=false;setPlay(false);}else if(loaded){send({action:'continue'});}else startPlay();};
$('prev').onclick=()=>aux?moveAux(-1):selectIndex(index-1,playing);$('next').onclick=()=>aux?moveAux(1):selectIndex(index+1,playing);
$('seek').oninput=()=>{if(loaded)send({action:'seek',seconds:Number($('seek').value),musicOffset:(aux?auxOffset():musicOffset())+Number($('seek').value)});};
$('original').onclick=()=>{if(!book)return;const page=book.pages[book.segments[index]?.page||0];const source=book.sources[page?.source||0];send({action:'original',bookId:book.id,file:source.file});};
$('importAction').onclick=()=>{if(jobs.import===book.id)send({action:'cancel',kind:'import'});else send({action:'resume',bookId:book.id});};
$('generateAll').onclick=()=>openProduction('scope');
$('musicButton').onclick=()=>openProduction('music');
$('cancelAudio').onclick=()=>{pending=false;send({action:'cancel',kind:'audio'});setPlay(playing);};
$('export').onclick=()=>openProduction('download');
document.addEventListener('keydown',e=>{if(e.code==='Space'&&!['TEXTAREA','INPUT','SELECT','BUTTON'].includes(e.target.tagName)&&book){e.preventDefault();$('play').click();}});
function selectedScope(){
 if(book?.model==='pro-cloud')return {type:'all'};
 const type=$('scopeType').value;
 if(type==='page')return {type,page:(book?.segments[index]?.page||0)+1};
 if(type==='range')return {type,fromPage:Number($('fromPage').value),toPage:Number($('toPage').value)};
 if(type==='chapter')return {type,chapterId:$('chapterSelect').value};
 return {type:'all'};
}
function scopeIndices(scope){
 if(!book)return [];let first=0,last=book.pages.length-1;
 if(scope.type==='page')first=last=scope.page-1;
 if(scope.type==='range'){first=scope.fromPage-1;last=scope.toPage-1;}
 if(scope.type==='chapter'){const c=(book.sections||book.chapters).find(c=>c.id===scope.chapterId);if(!c)return [];if(c.indices)return c.indices;first=c.startPage;last=c.endPage;}
 if(!Number.isInteger(first)||!Number.isInteger(last)||first<0||last<first||last>=book.pages.length)return [];
 return book.segments.map((s,i)=>s.page>=first&&s.page<=last?i:-1).filter(i=>i>=0&&/[\p{L}\p{N}]/u.test(book.segments[i].text));
}
function scopeLabel(scope){if(scope.type==='page')return `${unit(book,true)} ${scope.page}`;if(scope.type==='range')return `${unit(book,true)} ${scope.fromPage}–${scope.toPage}`;if(scope.type==='chapter')return (book.sections||book.chapters).find(c=>c.id===scope.chapterId)?.title||'Chưa chọn chương';return 'Toàn bộ sách';}
function renderProduction(){
 if(!book)return;
 $('scopeType').querySelector('[value=page]').textContent=`${unit(book,true)} đang đọc`;
 $('scopeType').querySelector('[value=range]').textContent=`Khoảng ${unit()}`;
 $('fromUnit').textContent=`Từ ${unit()}`;$('toUnit').textContent=`Đến ${unit()}`;
 $('markChapter').textContent=`Lưu mốc ở ${unit()} này`;
 const changed=scopeBookId!==book.id;
 if(changed){scopeBookId=book.id;scopeDirty=false;const scope=book.generationScope||{type:'all'};$('scopeType').value=scope.type;$('fromPage').value=scope.fromPage||1;$('toPage').value=scope.toPage||book.pages.length||1;}
 const old=$('chapterSelect').value;const key=JSON.stringify(book.sections||book.chapters);
 if($('chapterSelect').dataset.catalog!==key){$('chapterSelect').dataset.catalog=key;$('chapterSelect').replaceChildren();for(const c of book.sections||book.chapters){const opt=document.createElement('option');opt.value=c.id;opt.textContent=`${c.title} · ${unit()} ${c.startPage+1}–${c.endPage+1}`;$('chapterSelect').append(opt);}const saved=book.generationScope||{};$('chapterSelect').value=changed?saved.chapterId||(book.sections||book.chapters).find(c=>c.indices?.includes(index))?.id||(book.sections||book.chapters)[0]?.id:old||(book.sections||book.chapters)[0]?.id;if(!$('chapterSelect').value&&(book.sections||book.chapters).length)$('chapterSelect').value=(book.sections||book.chapters)[0].id;}
 if(changed&&book.generationScope?.chapterId)$('chapterSelect').value=book.generationScope.chapterId;
 if(!scopeDirty&&!changed&&book.generationScope?.type==='chapter'){$('scopeType').value='chapter';$('chapterSelect').value=book.generationScope.chapterId;}
 for(const id of ['scopeType','fromPage','toPage','chapterSelect'])$(id).disabled=jobs.export===book.id;
 $('fromPage').max=book.pages.length;$('toPage').max=book.pages.length;
 const scope=selectedScope(),indices=scopeIndices(scope),ready=indices.filter(i=>book.segments[i].audio).length;
 $('rangeFields').hidden=scope.type!=='range';$('chapterField').hidden=scope.type!=='chapter';
 $('scopeSummary').textContent=scope.type==='chapter'&&!(book.sections||book.chapters).length?`Sách chưa có mục lục chương. Đặt mốc chương ở bên dưới hoặc chọn theo ${unit()}.`:`${scopeLabel(scope)} · ${indices.length} đoạn · ${ready} đã có giọng đọc`;
 $('createScope').textContent=indices.length&&ready===indices.length?'Đã tạo đủ giọng đọc':`Tạo ${indices.length||''} đoạn trong phạm vi`;
 $('createScope').disabled=!indices.length||ready===indices.length||!!jobs.audio||!!jobs.export||dirty;
 $('downloadScope').textContent=`${scopeLabel(scope)} · ${ready}/${indices.length} đoạn sẵn sàng. Phạm vi được chọn ở tab Phạm vi.`;
 $('downloadScopeButton').disabled=!indices.length||ready!==indices.length||!!jobs.audio||!!jobs.export||dirty||(scope.type==='all'&&book.status!=='ready');
 $('cancelExport').hidden=jobs.export!==book.id;
 $('chapterHelp').textContent=`Mốc chương bắt đầu từ ${unit()} ${(book.segments[index]?.page||0)+1}. Có thể đặt lại tên tại cùng ${unit()}.`;
 $('markChapter').disabled=!!jobs.audio||!!jobs.export||!book.pages.length;
 $('removeChapter').disabled=!$('chapterSelect').value||$('chapterSelect').value==='preface'||!!jobs.audio||!!jobs.export;
 if(book.model==='pro-cloud'){$('scopeSummary').textContent='Chọn tạo thử 1 lượt hoặc tạo chương bằng tối đa 4 lượt (20.000 ký tự).';$('createScope').textContent='Tạo Pro cho chương này';$('createScope').disabled=dirty||!!jobs.audio||!!jobs.export;$('scopePane').classList.add('cloud-scope');}else $('scopePane').classList.remove('cloud-scope');
 renderMusicControls();
}
function openProduction(tab){if(guardDirty()||!book)return;productionTrigger=tab==='scope'?'generateAll':tab==='music'?'musicButton':'export';$('voicesPanel').hidden=true;$('modelsPanel').hidden=true;$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');$('productionPanel').hidden=false;for(const id of ['generateAll','musicButton','export'])$(id).setAttribute('aria-expanded',String(id===productionTrigger));for(const name of ['scope','music','download']){const active=tab===name;$(name+'Pane').hidden=!active;$(name+'Pane').setAttribute('aria-hidden',String(!active));if(active)$('productionPanel').append($(name+'Pane'));$(name+'Tab').setAttribute('aria-selected',String(active));$(name+'Tab').tabIndex=active?0:-1;}renderProduction();$(tab+'Tab').focus();}
function closeProduction(){if(musicPreview){musicPreview=false;send({action:'musicPreview',...musicPayload(),playing:false});} $('productionPanel').hidden=true;for(const id of ['generateAll','musicButton','export'])$(id).setAttribute('aria-expanded','false');if(productionTrigger)$(productionTrigger).focus();}
function musicOffset(){return book?book.segments.slice(0,index).reduce((sum,s)=>sum+(s.duration||0),0):0;}
function chosenMusic(){return book?.music||{track:'none',volume:.12};}
function musicOrder(settings=chosenMusic()){return settings.track==='none'?[]:settings.mode==='shuffle'?(settings.playlist||[]):[settings.track];}
function musicPayload(){
 const settings=chosenMusic(),items=musicOrder(settings).map(id=>musicCatalog.find(m=>m.id===id));
 const available=items.length&&items.every(Boolean);
 return {path:available?items[0].path:'',playlist:available?items.map(m=>m.path):[],loop:settings.loop!==false,volume:Number($('musicVolume').value)/100,offset:aux?auxOffset()+Number($('seek').value||0):musicOffset()+(book?.position.segment===index?book.position.seconds:0)};
}
function saveMusic(){clearTimeout(saveMusicTimer);if(!book)return;const music={...chosenMusic(),volume:Number($('musicVolume').value)/100};book.music=music;book.musicUnavailable=musicOrder(music).some(id=>!musicCatalog.some(m=>m.id===id));send({action:'settings',bookId:book.id,music});}
function commitMusic(music){
 if(!book||jobs.export===book.id)return;
 if(musicPreview){send({action:'musicPreview',...musicPayload(),playing:false});musicPreview=false;}
 book.music=music;renderMusicControls();saveMusic();send({action:'music',...musicPayload(),seek:true});
}
function musicTitle(m){return window.i18n?.language==='en'?m.title.replace(/^Bài (\d+)$/,'Track $1'):m.title;}
function categoryTracks(category){return musicCatalog.filter(m=>(m.category||'Thư giãn')===category);}
function shuffleMusic(category){
 const ids=categoryTracks(category).map(m=>m.id);
 for(let i=ids.length-1;i>0;i--){const data=new Uint32Array(1);crypto.getRandomValues(data);const j=Math.floor(data[0]/4294967296*(i+1));[ids[i],ids[j]]=[ids[j],ids[i]];}
 // With several tracks, an explicit reshuffle should visibly change the order.
 if(ids.length>1&&JSON.stringify(ids)===JSON.stringify(musicOrder()))ids.push(ids.shift());
 return ids;
}
let renderedMusicKey='';
function renderMusicControls(){
 if(!book)return;
 const music=chosenMusic(),item=musicCatalog.find(m=>m.id===music.track),category=music.track==='none'?'none':music.category||item?.category||'Thư giãn';
 const unavailable=musicOrder(music).some(id=>!musicCatalog.some(m=>m.id===id));book.musicUnavailable=unavailable;
 const categories=[...new Set(musicCatalog.map(m=>m.category||'Thư giãn'))];
 const key=JSON.stringify([book.id,category,music.mode,musicOrder(music),musicCatalog.map(m=>m.id),window.i18n?.language]);
 if(key!==renderedMusicKey){
  renderedMusicKey=key;
  $('musicCategory').replaceChildren(new Option('Không dùng nhạc nền','none'),...categories.map(c=>new Option(c,c)));
  if(category!=='none'&&!categories.includes(category))$('musicCategory').add(new Option('Nhạc đã chọn · Chưa có trên máy này',category));
  $('musicCategory').value=category;
  const tracks=categoryTracks(category);
  $('musicTrack').replaceChildren(...tracks.map(m=>new Option(`${musicTitle(m)} · ${fmt(m.duration)}`,m.id)));
  if(!tracks.some(m=>m.id===music.track))$('musicTrack').add(new Option(music.track==='none'?'Không dùng nhạc nền':'Nhạc đã chọn · Chưa có trên máy này',music.track));
  $('musicTrack').value=music.track;
  $('musicQueue').replaceChildren(...musicOrder(music).map(id=>{
   const m=musicCatalog.find(m=>m.id===id),li=document.createElement('li'),title=document.createElement('span'),duration=document.createElement('small');
   title.className='user-text';title.textContent=m?musicTitle(m):'—';duration.textContent=m?fmt(m.duration):'—';li.append(title,duration);return li;
  }));
 }
 $('musicChoices').hidden=music.track==='none';$('musicTrackLabel').hidden=music.mode==='shuffle';$('musicQueueWrap').hidden=music.mode!=='shuffle';
 $('musicSingle').setAttribute('aria-pressed',String(music.mode!=='shuffle'));$('musicShuffle').setAttribute('aria-pressed',String(music.mode==='shuffle'));
 $('musicLoop').checked=music.loop!==false;
 if(document.activeElement!==$('musicVolume'))$('musicVolume').value=Math.round(music.volume*100);
 $('musicVolumeLabel').textContent=`${$('musicVolume').value}%`;
 $('musicDescription').textContent=unavailable?'Nhạc đã chọn không có trên máy này. Chọn nhạc khác trước khi nghe kèm hoặc xuất file.':music.track==='none'?'Chỉ phát lời đọc, không kèm nhạc.':music.mode==='shuffle'?'Phát các bài theo thứ tự ngẫu nhiên đã chọn.':item?.description||'Nhạc được trộn vào cả bản nghe và file tải về.';
 const locked=jobs.export===book.id;
 for(const id of ['musicCategory','musicTrack','musicSingle','musicShuffle','reshuffleMusic','musicLoop'])$(id).disabled=locked;
 $('musicVolume').disabled=locked||music.track==='none'||unavailable;
 $('previewMusic').disabled=music.track==='none'||playing||unavailable;
 $('previewMusic').querySelector('span').textContent=musicPreview?'Dừng nghe thử':'Nghe thử nhạc';
 $('previewMusic').querySelector('use').setAttribute('href',musicPreview?'#i-pause':'#i-play');
}
for(const name of ['scope','music','download'])$(name+'Tab').onclick=()=>openProduction(name);
$('closeProduction').onclick=closeProduction;
$('productionPanel').addEventListener('keydown',e=>{if(e.target.getAttribute('role')==='tab'&&['ArrowRight','ArrowLeft'].includes(e.key)){e.preventDefault();const tabs=['scope','music','download'];const at=tabs.findIndex(n=>$(n+'Tab')===e.target);openProduction(tabs[(at+(e.key==='ArrowRight'?1:2))%3]);}});
for(const id of ['scopeType','fromPage','toPage','chapterSelect'])$(id).onchange=()=>{scopeDirty=true;renderProduction();listeningKey='';listeningToken='';send({action:'cancelListening'});queueUpcoming();prepareListening();if(scopeIndices(selectedScope()).length)send({action:'settings',bookId:book.id,scope:selectedScope()});};
$('createScope').onclick=()=>{if(guardDirty())return;if(book.model==='pro-cloud'){openBookCloud({mode:'trial',chapterId:activeSection()?.id});return;}const scope=selectedScope(),indices=scopeIndices(scope);if(!indices.length)return;selectIndex(indices[0]);requestGenerate({action:'generate',bookId:book.id,scope});};
$('markChapter').onclick=()=>{if(!$('chapterTitle').value.trim()){toast('Nhập tên chương trước khi lưu mốc.');return;}scopeDirty=false;send({action:'chapter',bookId:book.id,page:(book.segments[index]?.page||0)+1,title:$('chapterTitle').value});$('chapterTitle').value='';};
$('removeChapter').onclick=()=>{scopeDirty=false;send({action:'chapter',bookId:book.id,remove:$('chapterSelect').value});};
$('musicCategory').onchange=()=>{const category=$('musicCategory').value,tracks=categoryTracks(category);commitMusic({...chosenMusic(),category,mode:'single',track:tracks[0]?.id||'none',playlist:tracks[0]?[tracks[0].id]:[],loop:chosenMusic().loop!==false});};
$('musicTrack').onchange=()=>commitMusic({...chosenMusic(),mode:'single',track:$('musicTrack').value,playlist:[$('musicTrack').value]});
$('musicSingle').onclick=()=>commitMusic({...chosenMusic(),mode:'single',playlist:[chosenMusic().track]});
function selectShuffle(){const category=$('musicCategory').value,playlist=shuffleMusic(category);if(playlist.length)commitMusic({...chosenMusic(),category,mode:'shuffle',track:playlist[0],playlist});}
$('musicShuffle').onclick=selectShuffle;$('reshuffleMusic').onclick=selectShuffle;
$('musicLoop').onchange=()=>commitMusic({...chosenMusic(),loop:$('musicLoop').checked});
$('musicVolume').oninput=()=>{$('musicVolumeLabel').textContent=`${$('musicVolume').value}%`;send({action:musicPreview?'musicPreview':'music',...musicPayload(),playing:musicPreview,seek:false});clearTimeout(saveMusicTimer);saveMusicTimer=setTimeout(saveMusic,180);};
$('musicVolume').onchange=saveMusic;
$('previewMusic').onclick=()=>{musicPreview=!musicPreview;send({action:'musicPreview',...musicPayload(),offset:0,playing:musicPreview});renderProduction();};
$('exportFormat').onchange=()=>{$('exportDescription').textContent=$('exportFormat').value==='zip'?'Gồm bản đọc, nhạc nền, nội dung sách và trình nghe. Bạn có thể mang sang máy khác hoặc đưa lên website của mình.':'Một file gồm lời đọc và nhạc nền đã chọn. M4A dễ mang sang điện thoại và máy tính khác.';};
$('downloadScopeButton').onclick=()=>{saveMusic();send({action:'exportDialog',bookId:book.id,title:book.title+' — '+(window.i18n?.language==='en'&&selectedScope().type!=='chapter'?window.i18n.english(scopeLabel(selectedScope())):scopeLabel(selectedScope())),format:$('exportFormat').value,scope:selectedScope()});};
$('cancelExport').onclick=()=>send({action:'cancel',kind:'export'});
document.addEventListener('pointerdown',e=>{if(!$('productionPanel').hidden&&!$('productionPanel').contains(e.target)&&!['generateAll','musicButton','export'].some(id=>$(id).contains(e.target)))closeProduction();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('productionPanel').hidden){closeProduction();}});
$('librarySearch').oninput=renderBooks;
$('appearance').onclick=()=>{$('modelsPanel').hidden=true;const open=$('appearancePanel').hidden;$('appearancePanel').hidden=!open;$('appearance').setAttribute('aria-expanded',String(open));if(open)$('theme').focus();};
document.addEventListener('pointerdown',e=>{if(!$('appearancePanel').hidden&&!$('appearancePanel').contains(e.target)&&!$('appearance').contains(e.target)){$('voicesPanel').hidden=true;$('modelsPanel').hidden=true;$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('appearancePanel').hidden){$('voicesPanel').hidden=true;$('modelsPanel').hidden=true;$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');$('appearance').focus();}});
for(const name of ['theme','motion']){$(name).value=preference(name,'system');$(name).onchange=applyAppearance;}
function renderModelControls(){
 if(!book||!modelCatalog.length)return;
 const choice=$('modelChoice'),key=JSON.stringify([book.model,modelCatalog.map(m=>[m.id,m.ready,m.supported,m.entitled])]);
 if(choice.dataset.catalog!==key){choice.dataset.catalog=key;choice.replaceChildren();for(const m of modelCatalog){const opt=document.createElement('option');opt.value=m.id;opt.textContent=m.label+(m.entitled===false?' · Mở khóa Pro':m.ready?'':m.cloud?' · Tính giá theo cuốn':' · Chưa tải');opt.disabled=!m.supported;choice.append(opt);}}
 if(!modelCatalog.some(m=>m.id===(book.model||'nano'))){const opt=document.createElement('option');opt.value=book.model;opt.textContent=modelLabel(book.model)+' · Chưa có trong gói này';opt.disabled=true;if(![...choice.options].some(o=>o.value===opt.value))choice.append(opt);}
 choice.value=book.model||'nano';choice.disabled=jobs.audio===book.id||jobs.export===book.id;
 const model=modelCatalog.find(m=>m.id===choice.value);
 const voice=$('voice'),voiceKey=JSON.stringify([choice.value,model?.voices]);if(voice.dataset.catalog!==voiceKey){voice.dataset.model=choice.value;voice.dataset.catalog=voiceKey;voice.replaceChildren();for(const v of model?.voices||[]){const opt=document.createElement('option');opt.value=v.id;opt.textContent=v.label;voice.append(opt);}}
 if(book.voice&&![...voice.options].some(o=>o.value===book.voice)){const opt=document.createElement('option');opt.value=book.voice;opt.textContent='Giọng trước đây · Chọn giọng khác';opt.disabled=true;voice.append(opt);}
 voice.value=book.voice;$('modelHint').textContent='';$('modelHint').hidden=true;
 $('resourceState').textContent=model?.cloud?'Pro Cloud · Trả theo cuốn, nghe trên Mac':model?.ready?`${model.label} sẵn sàng · Không cần mạng`:'Chọn một gói giọng để bắt đầu nghe';

}
function renderModels(){
 $('hardwareInfo').textContent=`Mac ${machine.architecture==='arm64'?'Apple Silicon':machine.architecture||''} · ${machine.memoryGB?machine.memoryGB+' GB RAM':'Chưa đọc được RAM'} · Trống ${(freeBytes/1024**3).toFixed(1)} GB`;
 const list=$('modelList'),key=JSON.stringify([modelCatalog.map(m=>[m.id,m.ready,m.canDownload,m.supported,m.entitled]),book?.id,book?.model,modelDownload,!!jobs.audio,!!jobs.export]);
 if(list.dataset.catalog!==key){list.dataset.catalog=key;list.replaceChildren();const ordered=[...modelCatalog].sort((a,b)=>book?.language==='en'?Number(b.id==='kitten')-Number(a.id==='kitten'):0);for(const m of ordered){
  const row=document.createElement('section');row.className='model-row';row.dataset.model=m.id;row.classList.toggle('model-locked',m.entitled===false);
  const title=document.createElement('h3');title.textContent=m.label;const desc=document.createElement('p');desc.textContent=m.description;
  if(m.entitled===false){const badge=document.createElement('span');badge.className='pro-badge';badge.textContent='Pro';title.append(badge);}
  const details=document.createElement('small');details.textContent=m.cloud?'Từ 10.000đ/cuốn · 5 lượt tạo thử':`${Math.round(m.bytes/1000000)} MB · ${m.sampleRate/1000} kHz · ${m.languages?.join(' / ').toUpperCase()} · Nên có ${m.recommendedRAM} GB RAM`;
  const note=document.createElement('p');note.className='model-status';note.textContent=!m.supported?'Cần Mac Apple Silicon, RAM từ 8 GB':m.hardwareNote;
  const progress=document.createElement('p');progress.className='model-progress';progress.setAttribute('role','status');
  const button=document.createElement('button');button.className=m.id==='nano'?'secondary':'primary';
  if(m.cloud){button.textContent='Tạo thử / xem giá cuốn sách';button.onclick=openBookCloud;note.textContent=m.hardwareNote;}
  else if(m.entitled===false){button.className='pro-button';button.append(icon('shield'),document.createTextNode('Mua Pro · 189.000đ/năm'));button.setAttribute('aria-label','Mua Pro để mở '+m.label+' · 189.000đ/năm');button.onclick=offerPro;note.textContent='Nano và tiếng Anh vẫn miễn phí.';}
  else if(modelDownload===m.id){button.textContent='Hủy tải · giữ phần đã tải';button.onclick=()=>send({action:'cancel',kind:'model'});}
  else if(m.ready){button.textContent=book?.model===m.id?'Đang dùng cho sách này':book?'Dùng cho sách này':'Đã tải';button.disabled=!book||book.model===m.id||!!jobs.audio||!!jobs.export;button.onclick=()=>applyModel(m.id);}
  else{button.textContent=m.localOnly?'Gói giọng riêng chưa có trên máy':`Tải / tiếp tục tải · ${Math.round(m.bytes/1000000)} MB`;button.disabled=!!modelDownload||!m.canDownload;button.onclick=()=>{modelProgress=null;send({action:'downloadModel',model:m.id});};}
  if(!m.cloud&&m.entitled!==false&&!m.ready&&!m.canDownload&&m.supported)note.textContent=m.localOnly?'Gói giọng riêng chưa đầy đủ. Vui lòng cài lại gói giọng Pro đã nhận.':'Cần thêm dung lượng trống trước khi tải.';
  row.append(title,desc,details,note,progress,button);list.append(row);
 }}
 for(const m of modelCatalog){const row=list.querySelector(`[data-model="${m.id}"]`);if(!row)continue;const p=modelProgress?.modelId===m.id?modelProgress:null;row.querySelector('.model-progress').textContent=p?`${p.phase==='verify'?'Kiểm tra tệp':p.phase==='ready'?'Đã tải và xác minh':'Đang tải'} · ${Math.min(100,Math.round(p.done/p.total*100))}% · ${Math.round(p.done/1000000)}/${Math.round(p.total/1000000)} MB`:m.cloud?(m.ready?'Đã kết nối':'Chưa kết nối'):m.ready?'Đã tải trên máy':'';}
}
function openModels(modelId){if(guardDirty())return;closeAppInfo();$('voicesPanel').hidden=true;closeProduction();$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');$('modelsPanel').hidden=false;document.querySelector('main').append($('modelsPanel'));renderModels();const row=typeof modelId==='string'?[...$('modelList').children].find(r=>r.dataset.model===modelId):null;if(row){row.scrollIntoView({block:'center'});row.querySelector('button')?.focus();}else $('closeModels').focus();send({action:'models'});}
function applyModel(id){if(!book||guardDirty())return;stop();send({action:'settings',bookId:book.id,model:id});$('modelsPanel').hidden=true;}
$('manageModels').onclick=openModels;$('modelDetails').onclick=openModels;
$('closeModels').onclick=()=>{$('modelsPanel').hidden=true;(book?$('modelDetails'):$('appInfo')).focus();};
$('modelChoice').onchange=()=>{const id=$('modelChoice').value,m=modelCatalog.find(m=>m.id===id);if(m?.entitled===false){$('modelChoice').value=book.model||'nano';openModels(id);return;}if(m?.cloud){applyModel(id);return;}if(!m?.ready){$('modelChoice').value=book.model||'nano';openModels();}else applyModel(id);};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('modelsPanel').hidden){$('modelsPanel').hidden=true;(book?$('modelDetails'):$('appInfo')).focus();}});
$('bookLanguage').onchange=()=>{if(guardDirty()){render();return;}stop();send({action:'settings',bookId:book.id,language:$('bookLanguage').value});};
window.addEventListener('localechange',()=>{if(book)render();});
applyAppearance();document.querySelector('.library').classList.add('library-enter');animateContent('empty');
send({action:'init'});
