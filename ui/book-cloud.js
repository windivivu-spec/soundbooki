'use strict';
let bookCloudToken='',bookCloudInfo=null,bookCloudOrder=null,bookCloudBusy=false,bookCloudTimer=null,bookCloudChecks=0,bookCloudTrialKey=null,bookCloudQuoteKey=null,bookCloudTrigger=null,openCloudAfterBook=false,bookCloudBank=null;
let bookCloudComboKey=null,bookCloudChapterId=null;
let bookCloudMode='purchase',bookCloudOpenOptions={};
let bookCloudTrialUnits=1,bookCloudTrialChoice='single';
let bookCloudHistoryEntry=null;
let bookCloudService=null,bookCloudAudio=[],bookCloudLocalReady=false,bookCloudAction='',bookCloudProblem='';
let bookCloudPollInterval=3000,bookCloudRemaining=5,bookCloudTrialLimit=5,bookCloudTrialCharacters=5000;
let bookCloudPollUntil=0,bookCloudFailures=0,bookCloudReceiving=false,bookCloudReceived=0;
let bookCloudPreviewToken='';
function resumeBookCloudPoll(){bookCloudPollUntil=Date.now()+20*60*1000;bookCloudChecks=0;bookCloudFailures=0;}
function updateBookCloudQuota(e){
 bookCloudTrialLimit=5;
 if(Number.isInteger(e.trialCharacters))bookCloudTrialCharacters=e.trialCharacters;
 if(Number.isInteger(e.trialsRemaining))bookCloudRemaining=Math.max(0,5-Math.max(0,(Number.isInteger(e.trialLimit)?e.trialLimit:3)-e.trialsRemaining));
 $('bookCloudQuota').textContent=`Còn ${bookCloudRemaining}/${bookCloudTrialLimit} lượt · ${bookCloudTrialCharacters.toLocaleString('vi-VN')} ký tự/lượt`;
}
const moneyVND=n=>Number(n).toLocaleString('vi-VN')+'đ';
function clearBookCloudPoll(){clearTimeout(bookCloudTimer);bookCloudTimer=null;}
function cloudMessage(text){$('bookCloudStatus').textContent=text||'';$('bookCloudProgress').hidden=!text;}
function bookCloudPhase(){
 if(bookCloudProblem)return 'error';
 if(bookCloudBusy&&!bookCloudOrder&&['bookCloudTrial','bookCloudQuote','bookCloudCombo'].includes(bookCloudAction))return 'sending';
 if(!bookCloudOrder)return 'idle';
 return bookCloudReceiving||bookCloudOrder.state==='ready'&&!bookCloudLocalReady?'receiving':bookCloudOrder.state;
}
function configureBookCloudAudio(audio){
 bookCloudAudio=Array.isArray(audio)?audio:[];$('bookCloudTrialPlay').hidden=!bookCloudAudio.length;
 if(bookCloudPreviewToken&&aux?.token===bookCloudPreviewToken&&bookCloudAudio.length>aux.segments.length&&aux.segments.every((s,i)=>s.audio===bookCloudAudio[i]?.audio)){
  aux.segments=bookCloudAudio;queueAuxNext();renderAux();
 }
 renderBookCloudListen();
 $('bookCloudTrialPlay').onclick=()=>{
  if(!bookCloudAudio.length)return;
  if(bookCloudPreviewToken&&aux?.token===bookCloudPreviewToken){playing=!playing;send({action:playing?'continue':'pause'});setPlay(playing);renderBookCloudListen();return;}
  bookCloudPreviewToken=requestToken();playAux({kind:'trial',title:'Mẫu sách · Pro',segments:bookCloudAudio,at:0,token:bookCloudPreviewToken});
  if(bookCloudLocalReady)$('bookCloudDialog').close();else renderBookCloudListen();
 };
}
function renderBookCloudListen(){
 $('bookCloudTrialPlay').textContent=bookCloudPreviewToken&&aux?.token===bookCloudPreviewToken?(playing?'Tạm dừng':'Tiếp tục nghe'):bookCloudLocalReady?'Nghe ngay':'Nghe phần đầu';
}
function renderBookCloudProgress(){
 const phase=bookCloudPhase(),compact=bookCloudMode==='trial',order=bookCloudOrder;
 const headings={sending:'Đang gửi yêu cầu',queued:'Đang chờ tới lượt',processing:'Đang tạo giọng đọc',receiving:'Đang nhận audio về Mac',ready:order?.kind==='trial'?'Mẫu Pro đã sẵn sàng':'Sách nói đã sẵn sàng',awaiting_payment:'Chờ xác nhận thanh toán',failed:'Yêu cầu chưa hoàn tất',expired:'Đơn thanh toán đã hết hạn',error:'Chưa hoàn tất thao tác'};
 $('bookCloudProgressTitle').textContent=headings[phase]||'Thông tin dịch vụ';$('bookCloudProgress').dataset.state=phase;
 const paused=Date.now()>=bookCloudPollUntil;
 $('bookCloudProgressNote').textContent=bookCloudFailures&&!paused?'Đang tự kết nối lại. Yêu cầu vẫn được giữ.':['queued','processing','receiving'].includes(phase)?paused?'Tạm dừng cập nhật. Bấm tiếp tục để nhận kết quả.':'Tự nhận kết quả khi cửa sổ này mở.':phase==='sending'?'Chỉ gửi một lần. Vui lòng chờ.':'';
 const progress=$('bookCloudProgressMeter');progress.hidden=!['sending','queued','processing','receiving'].includes(phase);progress.max=order?.total||1;
 const done=phase==='receiving'?bookCloudReceived:order?.done||0;
 if(done>0)progress.value=Math.min(done,progress.max);else progress.removeAttribute('value');
 if(compact&&order)$('bookCloudHeading').textContent='Mẫu Pro của bạn';
 else if(compact)$('bookCloudHeading').textContent='Tạo Pro cho chương này?';
 else if(!compact)$('bookCloudHeading').textContent=phase==='awaiting_payment'?'Thanh toán sách nói':'Tạo sách nói Pro';
 const payment=order?.kind==='book'&&order.state==='awaiting_payment';$('bookCloudDialog').classList.toggle('is-payment',payment);$('bookCloudDialog').classList.toggle('has-order',!!order);
 $('bookCloudTrialSummary').querySelector('fieldset').hidden=!!order||bookCloudBusy;
 $('bookCloudTrialPlay').hidden=!bookCloudAudio.length;
 renderBookCloudListen();
 $('bookCloudTrial').hidden=!!order;
 $('bookCloudOpenAudio').hidden=order?.kind!=='book'||!bookCloudLocalReady;
 $('bookCloudOrderDetails').hidden=!order;
 $('bookCloudOrderId').textContent=order?.id||'';
 $('bookCloudCheck').hidden=!order||phase==='ready'||(['queued','processing','receiving'].includes(phase)&&!paused&&!bookCloudProblem);
 $('bookCloudCheck').textContent=phase==='awaiting_payment'?'Kiểm tra thanh toán':paused?'Tiếp tục nhận kết quả':bookCloudProblem?'Thử kết nối lại':'Cập nhật tiến độ';
 const canStartNew=!!order&&!bookCloudBusy&&(bookCloudLocalReady||['failed','expired'].includes(order.state));
 $('bookCloudNewTrial').hidden=!canStartNew||bookCloudRemaining<=0;
 $('bookCloudNewQuote').hidden=!canStartNew;
 if(compact&&order)$('bookCloudConfirmLimit').hidden=true;else $('bookCloudConfirmLimit').hidden=false;
}
function renderBookCloudPayment(){
 const order=bookCloudOrder,payment=order?.kind==='book'&&order.state==='awaiting_payment';$('bookCloudPayment').hidden=!payment;
 if(!payment)return;
 $('bookCloudPayAmount').textContent=moneyVND(order.amountVND);$('bookCloudPayCode').textContent=order.paymentCode;
 const bank=bookCloudBank;
 if(!bank?.account||!bank?.holder||!bank?.bin){$('bookCloudPayBank').textContent='Đang chờ thông tin ngân hàng của đơn.';$('bookCloudQR').textContent='Bấm kiểm tra thanh toán để nhận lại QR.';return;}
 $('bookCloudPayBank').textContent=`${bank.name} · ${bank.account} · ${bank.holder}`;
 const key=JSON.stringify([order.paymentCode,order.amountVND,bank.bin,bank.account]);
 if($('bookCloudQR').dataset.payment!==key){$('bookCloudQR').dataset.payment=key;$('bookCloudQR').textContent='Đang tạo mã QR…';send({action:'bookPaymentQR',bank,code:order.paymentCode,amount:order.amountVND});}
}
function openBookCloud(options={}){
 if(!book){toast('Thêm hoặc mở một cuốn sách trước khi chọn Pro.');return;}
 if(guardDirty())return;
 if(book.status!=='ready'){toast('Trích chữ xong trước khi tạo thử hoặc báo giá Pro.');return;}
 if(book.language!=='vi'){toast('Pro Cloud hiện hỗ trợ sách tiếng Việt. KittenTTS tiếng Anh vẫn miễn phí.');return;}
 bookCloudOpenOptions=options?.mode==='trial'?{mode:'trial',chapterId:options.chapterId||activeSection()?.id,trialChoice:options.trialChoice==='chapter'?'chapter':'single'}:{};
 if(book.model!=='pro-cloud'){openCloudAfterBook=true;applyModel('pro-cloud');return;}
 bookCloudMode=bookCloudOpenOptions.mode||'purchase';bookCloudTrialChoice=bookCloudOpenOptions.trialChoice||'single';
 $('bookCloudDialog').classList.toggle('is-trial-confirmation',bookCloudMode==='trial');
 $('bookCloudDialog').setAttribute('aria-describedby',bookCloudMode==='trial'?'bookCloudConfirmText bookCloudConfirmLimit':'bookCloudBenefit');
 $('bookCloudHeading').textContent=bookCloudMode==='trial'?'Tạo Pro cho chương này?':'Tạo sách nói Pro';
 $('bookCloudTrialSummary').hidden=bookCloudMode!=='trial';
 bookCloudTrigger=document.activeElement;bookCloudToken=requestToken();bookCloudInfo=null;bookCloudBusy=false;bookCloudOrder=null;bookCloudBank=null;bookCloudChecks=0;bookCloudHistoryEntry=null;bookCloudService=null;bookCloudAudio=[];bookCloudLocalReady=false;bookCloudAction='';bookCloudProblem='';clearBookCloudPoll();
 resumeBookCloudPoll();bookCloudReceiving=false;bookCloudReceived=0;bookCloudPreviewToken='';
 bookCloudQuoteKey=null;bookCloudTrialKey=null;bookCloudComboKey=null;bookCloudTrialUnits=1;
 $('bookCloudTitle').textContent=book.title;$('bookCloudPrice').textContent='Đang tính giá…';$('bookCloudEstimate').textContent='';$('bookCloudSample').textContent='';$('bookCloudConsent').checked=false;
 $('bookCloudPayment').hidden=true;$('bookCloudTrialPlay').hidden=true;cloudMessage('');
 const choices=book.sections||book.chapters||[];
 $('bookCloudChapter').replaceChildren(new Option('Đoạn mở đầu tự động',''),...choices.map(c=>new Option(c.title,c.id)));
 const scope=selectedScope(),chosen=bookCloudOpenOptions.chapterId||(scope.type==='chapter'?scope.chapterId:null);
 if(chosen&&!choices.some(c=>c.id===chosen)){toast('Chương đã thay đổi. Hãy chọn lại chương trước khi tạo Pro.');return;}
 bookCloudChapterId=chosen||null;
 $('bookCloudChapter').value=bookCloudChapterId||'';
 $('bookCloudDialog').showModal();renderBookCloud();send({action:'bookCloudInfo',bookId:book.id,token:bookCloudToken,chapterId:bookCloudChapterId||undefined,groupTrial:bookCloudMode==='trial'&&bookCloudTrialChoice==='chapter'});
}
function renderBookCloud(){
 const compact=bookCloudMode==='trial',consent=compact||$('bookCloudConsent').checked;
 const checking=bookCloudInfo?.serviceCheckPending&&!bookCloudService;
 const enabled=!!bookCloudInfo?.configured&&!bookCloudBusy&&!checking,existingTrial=bookCloudOrder?.kind==='trial';
 $('bookCloudTrial').disabled=!enabled||!consent||(!existingTrial&&!bookCloudTrialKey&&bookCloudRemaining<bookCloudTrialUnits);
 $('bookCloudTrial').disabled||=!existingTrial&&!bookCloudTrialKey&&bookCloudService?.trialAvailable===false;
 $('bookCloudBuy').disabled=!enabled||!$('bookCloudConsent').checked||bookCloudService?.purchaseAvailable===false||bookCloudOrder?.state==='awaiting_payment';
 $('bookCloudHistory').disabled=bookCloudBusy;$('bookCloudNewTrial').disabled=bookCloudBusy;$('bookCloudNewQuote').disabled=bookCloudBusy;
 $('bookCloudCheck').disabled=!bookCloudOrder||bookCloudBusy||!bookCloudInfo?.configured;
 $('bookCloudVoice').disabled=bookCloudBusy||!!bookCloudOrder;$('bookCloudChapter').disabled=bookCloudBusy||!!bookCloudOrder;
 $('bookCloudTrialSingle').checked=bookCloudTrialChoice==='single';$('bookCloudTrialChapter').checked=bookCloudTrialChoice==='chapter';
 $('bookCloudTrialSingle').disabled=bookCloudBusy||!!bookCloudOrder;$('bookCloudTrialChapter').disabled=bookCloudBusy||!!bookCloudOrder||!bookCloudChapterId;
 const choices=modelCatalog.find(m=>m.id==='pro-cloud')?.voices||[];
 if($('bookCloudVoice').dataset.catalog!==JSON.stringify(choices)){$('bookCloudVoice').dataset.catalog=JSON.stringify(choices);$('bookCloudVoice').replaceChildren(...choices.map(v=>new Option(v.label,v.id)));}
 $('bookCloudVoice').value=book?.voice||'';
 $('bookCloudTrial').textContent=bookCloudBusy?'Đang cập nhật…':existingTrial?'Kiểm tra mẫu đã tạo':bookCloudRemaining<=0?`Đã dùng hết ${bookCloudTrialLimit} lượt thử`:bookCloudChapterId?'Tạo thử chương này · Pro':'Tạo thử phần đầu · Pro';
 if(compact){
  const chapter=(book.sections||book.chapters||[]).find(c=>c.id===bookCloudChapterId),title=chapter?.title||'phần đầu sách';
  const voice=voiceLabel('pro-cloud',book.voice);
  $('bookCloudConfirmText').textContent=bookCloudHistoryEntry?voiceLabel('pro-cloud',bookCloudHistoryEntry.snapshot.voice):`“${title}” · ${voice}`;
  const count=bookCloudInfo?.trialSelectedCharacters,all=bookCloudInfo?.trialChapterCharacters;
  const limit=bookCloudInfo?.trialCompleteChapter?`Trọn chương · ${count.toLocaleString('vi-VN')} ký tự`:count&&all?`${count.toLocaleString('vi-VN')}/${all.toLocaleString('vi-VN')} ký tự đầu chương`:`Tối đa ${(bookCloudTrialCharacters*bookCloudTrialUnits).toLocaleString('vi-VN')} ký tự`;
  $('bookCloudConfirmLimit').textContent=limit+(bookCloudInfo?.configured?` · Còn ${bookCloudRemaining}/${bookCloudTrialLimit} lượt`:'');
  $('bookCloudTrial').textContent=bookCloudBusy?(bookCloudAction==='bookCloudTrial'?'Đang gửi yêu cầu…':'Đang kiểm tra…'):checking?'Đang kiểm tra dịch vụ…':existingTrial?'Kiểm tra / nhận mẫu':bookCloudTrialKey?'Tiếp tục yêu cầu đã gửi':bookCloudService?.trialAvailable===false?'Tạo thử Pro chưa mở':bookCloudRemaining<bookCloudTrialUnits?'Không đủ lượt Pro':`Xác nhận · Dùng ${bookCloudTrialUnits} lượt`;
 }
 $('bookCloudTrial').classList.toggle('primary',compact);$('bookCloudTrial').classList.toggle('secondary',!compact);
 $('bookCloudBuy').textContent=bookCloudOrder?.kind==='book'?bookCloudOrder.state==='awaiting_payment'?'Đang chờ thanh toán':'Cập nhật bản đọc đã mua':checking?'Đang kiểm tra thanh toán…':bookCloudService?.purchaseAvailable===false?'Thanh toán sách chưa mở':'Thanh toán & tạo cả sách'+(bookCloudInfo?' · '+moneyVND(bookCloudInfo.amountVND):'');
 $('bookCloudCheck').textContent=bookCloudOrder?.state==='awaiting_payment'?'Kiểm tra thanh toán':'Kiểm tra / nhận audio';
 const history=[...new Map((book?.cloudOrders||[]).filter(o=>o.order&&(!compact||o.kind==='trial')).map(o=>[o.order.id,o])).values()].reverse();
 $('bookCloudHistoryWrap').hidden=!history.length;
 const historyKey=JSON.stringify([compact,history.map(o=>[o.order.id,o.order.state,o.snapshot.voice])]);
 if($('bookCloudHistory').dataset.entries!==historyKey){
  $('bookCloudHistory').dataset.entries=historyKey;
  const states={ready:'Sẵn sàng',awaiting_payment:'Chờ thanh toán',queued:'Đang chờ',processing:'Đang tạo',failed:'Chưa hoàn tất',expired:'Hết hạn'};
  $('bookCloudHistory').replaceChildren(new Option(compact?'Chương đang chọn':'Nội dung hiện tại',''),...history.map((o,i)=>new Option(`${o.kind==='trial'?'Mẫu':'Sách'} ${history.length-i} · ${voiceLabel('pro-cloud',o.snapshot.voice).split(' · ')[0]} · ${states[o.order.state]||'Đang cập nhật'}`,o.order.id)));
 }
 $('bookCloudHistory').value=bookCloudOrder?.id||'';
 if(typeof renderBookCloudCombo==='function')renderBookCloudCombo();
 renderBookCloudProgress();
}
function requestBookCloud(action){
 if(bookCloudBusy||(!(bookCloudMode==='trial')&&!$('bookCloudConsent').checked)||!bookCloudInfo?.configured)return;
 if(bookCloudMode==='trial'&&action!=='bookCloudTrial')return;
 if(bookCloudInfo.serviceCheckPending&&!bookCloudService)return;
 if(action==='bookCloudQuote'&&bookCloudOrder?.kind!=='book'&&bookCloudService?.purchaseAvailable===false)return;
 if(action==='bookCloudTrial'&&!bookCloudOrder&&!bookCloudTrialKey&&bookCloudService?.trialAvailable===false)return;
 clearBookCloudPoll();
 if(action==='bookCloudQuote'&&bookCloudOrder?.kind==='book'){checkBookCloud();return;}
 if(action==='bookCloudTrial'&&bookCloudOrder?.kind==='trial'){checkBookCloud();return;}
 if(action==='bookCloudCombo'&&bookCloudOrder?.fundingBundleId){checkBookCloud();return;}
 if(action==='bookCloudTrial')bookCloudTrialKey||=requestToken();else if(action==='bookCloudCombo')bookCloudComboKey||=requestToken();else bookCloudQuoteKey||=requestToken();
 resumeBookCloudPoll();bookCloudBusy=true;bookCloudAction=action;bookCloudProblem='';renderBookCloud();cloudMessage(action==='bookCloudTrial'?'Đang gửi nội dung đã chọn…':'Đang lấy giá và mã thanh toán…');
 send({action,bookId:book.id,token:bookCloudToken,chapterId:action==='bookCloudTrial'?(bookCloudChapterId||undefined):undefined,trialUnits:action==='bookCloudTrial'?bookCloudTrialUnits:undefined,requestKey:action==='bookCloudCombo'?bookCloudComboKey:action==='bookCloudTrial'?bookCloudTrialKey:bookCloudQuoteKey,consent:true});
}
function checkBookCloud(){if(bookCloudBusy||!bookCloudOrder||!$('bookCloudDialog').open)return;clearBookCloudPoll();bookCloudBusy=true;bookCloudAction='check';bookCloudProblem='';renderBookCloud();send({action:'bookCloudCheck',bookId:book.id,token:bookCloudToken,orderId:bookCloudOrder.id});}
function pollBookCloud(soon=false){
 clearBookCloudPoll();
 if(!$('bookCloudDialog').open||document.hidden||bookCloudBusy||!bookCloudOrder||(['failed','expired'].includes(bookCloudOrder.state))||(bookCloudOrder.state==='ready'&&bookCloudLocalReady&&!bookCloudOrder.hasMoreAudio))return;
 if(Date.now()>=bookCloudPollUntil){renderBookCloudProgress();return;}
 const delay=bookCloudFailures?Math.min(30000,bookCloudPollInterval*2**bookCloudFailures):soon?Math.min(500,bookCloudPollInterval):bookCloudPollInterval;
 bookCloudTimer=setTimeout(()=>{bookCloudChecks++;checkBookCloud();},delay);
}
function drawBookQR(e){
 if(bookCloudOrder?.state!=='awaiting_payment'||e.code!==bookCloudOrder?.paymentCode||!/^([M0-9 h v z-])+$/.test(e.qrPath)||!Number.isInteger(e.qrSize)||e.qrSize>200)return;
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),path=document.createElementNS(svg.namespaceURI,'path');svg.setAttribute('viewBox',`0 0 ${e.qrSize} ${e.qrSize}`);svg.setAttribute('role','img');svg.setAttribute('aria-label','QR thanh toán '+moneyVND(bookCloudOrder.amountVND));path.setAttribute('d',e.qrPath);svg.append(path);$('bookCloudQR').replaceChildren(svg);
}
function handleBookCloudEvent(e){
 if(e.event==='bookPaymentQR'){drawBookQR(e);return true;}
 if(!['bookCloudInfo','bookCloudAvailability','bookCloudBusy','bookCloudProgress','bookCloudResult'].includes(e.event))return false;
 if(e.token!==bookCloudToken||e.bookId!==book?.id||!$('bookCloudDialog').open)return true;
 if(e.event==='bookCloudProgress'){
  if(bookCloudOrder&&bookCloudOrder.id!==e.order?.id)return true;
  bookCloudOrder=e.order;bookCloudReceiving=true;bookCloudProblem='';bookCloudReceived=e.receivedSegments||0;
  configureBookCloudAudio(e.trialAudio);
  cloudMessage(bookCloudReceived?`Đã lưu ${bookCloudReceived}/${e.order.total} phần trên Mac.`:'Đang tải audio về Mac…');
  renderBookCloud();return true;
 }
 if(e.event==='bookCloudAvailability'){
  bookCloudService=e;if(Number.isInteger(e.trialsRemaining))updateBookCloudQuota(e);
  if(!bookCloudOrder&&!bookCloudBusy){
   if(!e.reachable)cloudMessage(e.message||'Chưa kết nối được dịch vụ Pro. Mở lại cửa sổ để kiểm tra.');
   else if(bookCloudMode==='purchase'&&!e.purchaseAvailable)cloudMessage('Thanh toán cả sách chưa được mở. Bạn vẫn có thể dùng mẫu Pro đã có hoặc Lite miễn phí; chưa có yêu cầu thanh toán nào được tạo.');
   else if(bookCloudMode==='trial'&&!e.trialAvailable)cloudMessage('Tạo thử Pro chưa mở trên Mac này. Các lượt đã dùng và mẫu đã có vẫn được giữ.');
   else cloudMessage('');
  }
  renderBookCloud();return true;
 }
 if(e.event==='bookCloudInfo'){
  bookCloudInfo=e;bookCloudTrialUnits=Number.isInteger(e.trialUnits)&&e.trialUnits>=1&&e.trialUnits<=4?e.trialUnits:1;bookCloudComboKey=e.pendingComboKey||null;updateBookCloudQuota(e);bookCloudTrialKey=e.pendingTrialKey||null;bookCloudQuoteKey=e.pendingQuoteKey||null;bookCloudOrder=bookCloudMode==='trial'?(e.savedTrialOrder||null):(e.savedOrder||null);bookCloudBank=e.bank||null;$('bookCloudPrice').textContent=moneyVND(e.amountVND)+' / cuốn';$('bookCloudEstimate').textContent=`${e.characters.toLocaleString('vi-VN')} ký tự · khoảng ${e.estimatedMinutes} phút ở tốc độ 1×`;$('bookCloudSample').textContent=e.sampleText;
  bookCloudLocalReady=bookCloudOrder?.kind==='trial'&&bookCloudOrder.state==='ready'&&(e.trialAudio?.length||0)>=(bookCloudOrder.total||1);configureBookCloudAudio(bookCloudMode==='trial'?e.trialAudio:[]);
  if(bookCloudLocalReady)cloudMessage('Đã lưu trong Sách nói của bạn.');
  else if(!e.configured)cloudMessage(bookCloudMode==='trial'?'Tạo Pro chưa sẵn sàng trên bản Mac này. Chưa sử dụng lượt của bạn.':'Pro Cloud chưa kết nối dịch vụ. Bạn vẫn có thể tạo sách bằng Lite miễn phí.');
  else if(e.serviceCheckPending&&!bookCloudOrder)cloudMessage('Đang kết nối Pro…');
  else if(bookCloudOrder)cloudMessage(bookCloudOrder.state==='processing'?'Đang tạo audio…':'Đang cập nhật kết quả…');
  else if(bookCloudRemaining<bookCloudTrialUnits&&!bookCloudOrder&&!bookCloudTrialKey)cloudMessage(`Cần ${bookCloudTrialUnits} lượt để tạo phần đã chọn, hiện còn ${bookCloudRemaining} lượt.`);
  renderBookCloud();renderBookCloudPayment();if(bookCloudOrder)pollBookCloud(true);if(e.configured&&e.serviceCheckPending)send({action:'bookCloudAvailability',bookId:book.id,token:bookCloudToken});return true;
 }
 if(e.event==='bookCloudBusy'){bookCloudBusy=e.running;renderBookCloud();if(!e.running&&!bookCloudTimer)pollBookCloud(true);return true;}
 bookCloudBusy=false;
 bookCloudReceiving=false;
 if(!e.success){bookCloudFailures++;bookCloudProblem=e.message||'Chưa nhận được kết quả. Yêu cầu vẫn được giữ.';cloudMessage(bookCloudProblem);renderBookCloud();pollBookCloud();return true;}
 bookCloudOrder=e.order;bookCloudOrder.hasMoreAudio=e.hasMoreAudio===true;
 bookCloudFailures=0;bookCloudProblem='';bookCloudReceived=e.receivedSegments||0;bookCloudLocalReady=e.localReady===true||(e.order.kind==='trial'&&e.order.state==='ready'&&(e.trialAudio?.length||0)>=(e.order.total||1));
 configureBookCloudAudio(e.trialAudio);
 updateBookCloudQuota(e);
 // A successful trial consumes a new explicit attempt; failed transport keeps its key.
 if(e.order.kind==='trial')bookCloudTrialKey=null;
 const labels={awaiting_payment:'Quét QR và giữ nguyên nội dung chuyển khoản.',queued:e.order.kind==='trial'?'Đã nhận yêu cầu. Đang chờ bắt đầu.':'Đã thanh toán. Đang chờ bắt đầu.',processing:e.order.done?`Đã tạo ${e.order.done}/${e.order.total} phần${bookCloudAudio.length?' · Có thể nghe phần đầu.':'.'}`:'Phần đầu đang được tạo. Audio dài có thể mất vài phút.',ready:bookCloudLocalReady?'Đã lưu trong Sách nói của bạn.':'Đang tải audio về Mac…',failed:'Yêu cầu chưa hoàn tất. Bạn có thể cập nhật lại đơn này.',expired:'Đơn đã hết hạn. Nếu đã chuyển tiền, hãy kiểm tra giao dịch.'};
 cloudMessage(e.hasMoreAudio?'Đang nhận các phần audio đã tạo về Mac…':labels[e.order.state]||'Đang cập nhật yêu cầu.');
 $('bookCloudOrderId').textContent=e.order.id;
 if(e.bank)bookCloudBank=e.bank;
 renderBookCloud();renderBookCloudPayment();pollBookCloud(e.hasMoreAudio||(e.order.state==='ready'&&!bookCloudLocalReady));
 if(e.order.kind==='book'&&e.order.state==='awaiting_payment')$('bookCloudPayment').scrollIntoView({block:'nearest',behavior:'auto'});
 return true;
}
$('closeBookCloud').onclick=()=>$('bookCloudDialog').close();
$('bookCloudOpenAudio').onclick=()=>{$('bookCloudDialog').close();setWorkspaceTab('audio');};
$('bookCloudDialog').addEventListener('close',()=>{if($('bookCloudDialog').open)return;clearBookCloudPoll();bookCloudToken='';bookCloudTrigger?.focus?.();});
$('bookCloudConsent').onchange=renderBookCloud;
$('bookCloudTrial').onclick=()=>requestBookCloud('bookCloudTrial');$('bookCloudBuy').onclick=()=>requestBookCloud('bookCloudQuote');$('bookCloudCheck').onclick=()=>{resumeBookCloudPoll();checkBookCloud();};
$('copyBookCloudCode').onclick=()=>send({action:'copyBookPayment',value:bookCloudOrder.paymentCode});
$('bookCloudVoice').onchange=()=>{const voice=$('bookCloudVoice').value;$('bookCloudDialog').close();openCloudAfterBook=true;send({action:'settings',bookId:book.id,voice});};
$('bookCloudNewTrial').onclick=()=>{bookCloudPreviewToken='';clearBookCloudPoll();resumeBookCloudPoll();bookCloudReceiving=false;bookCloudReceived=0;bookCloudHistoryEntry=null;bookCloudTrialKey=null;bookCloudOrder=null;bookCloudLocalReady=false;bookCloudProblem='';configureBookCloudAudio([]);$('bookCloudPayment').hidden=true;cloudMessage('');renderBookCloud();};
$('bookCloudNewQuote').onclick=()=>{bookCloudPreviewToken='';bookCloudHistoryEntry=null;clearBookCloudPoll();bookCloudOrder=null;bookCloudQuoteKey=null;bookCloudLocalReady=false;bookCloudProblem='';configureBookCloudAudio([]);$('bookCloudConsent').checked=false;$('bookCloudPayment').hidden=true;renderBookCloud();cloudMessage(bookCloudService?.purchaseAvailable===false?'Thanh toán cả sách chưa được mở. Chưa có yêu cầu thanh toán nào được tạo.':'Bấm Thanh toán & tạo cả sách để lấy báo giá của nội dung hiện tại. Đơn đã mua vẫn được giữ trong lịch sử.');};
const receiveBeforeBookCloud=window.receive;
window.receive=e=>{if(handleBookCloudEvent(e))return;receiveBeforeBookCloud(e);if(['auxPlayback','auxAdvanced','auxEnded'].includes(e.event)&&$('bookCloudDialog').open)renderBookCloudListen();if(e.event==='book'&&openCloudAfterBook&&book?.model==='pro-cloud'){openCloudAfterBook=false;openBookCloud(bookCloudOpenOptions);}};
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearBookCloudPoll();else if($('bookCloudDialog').open)pollBookCloud(true);});
window.addEventListener('pagehide',clearBookCloudPoll);

$('bookCloudHistory').onchange=()=>{bookCloudPreviewToken='';clearBookCloudPoll();resumeBookCloudPoll();bookCloudReceiving=false;bookCloudReceived=0;const entry=book.cloudOrders.find(o=>o.order?.id===$('bookCloudHistory').value);bookCloudHistoryEntry=entry||null;bookCloudOrder=entry?.order||null;bookCloudBank=entry?.bank||null;bookCloudLocalReady=false;bookCloudProblem='';configureBookCloudAudio([]);$('bookCloudPayment').hidden=true;cloudMessage('');renderBookCloud();if(bookCloudOrder)checkBookCloud();};

$('bookCloudCombo').onclick=()=>requestBookCloud('bookCloudCombo');

function reloadBookCloudTrial(){
 bookCloudPreviewToken='';
 resumeBookCloudPoll();bookCloudReceiving=false;bookCloudReceived=0;
 clearBookCloudPoll();bookCloudChecks=0;bookCloudToken=requestToken();bookCloudInfo=null;bookCloudOrder=null;bookCloudBank=null;bookCloudTrialKey=null;bookCloudQuoteKey=null;bookCloudComboKey=null;bookCloudTrialUnits=1;bookCloudHistoryEntry=null;bookCloudService=null;bookCloudLocalReady=false;bookCloudProblem='';configureBookCloudAudio([]);
 $('bookCloudConsent').checked=false;$('bookCloudPayment').hidden=true;$('bookCloudTrialPlay').hidden=true;cloudMessage('');renderBookCloud();
 send({action:'bookCloudInfo',bookId:book.id,token:bookCloudToken,chapterId:bookCloudChapterId||undefined,groupTrial:bookCloudMode==='trial'&&bookCloudTrialChoice==='chapter'});
}
$('bookCloudChapter').onchange=()=>{if(bookCloudBusy)return;bookCloudChapterId=$('bookCloudChapter').value||null;reloadBookCloudTrial();};
for(const [id,choice] of [['bookCloudTrialSingle','single'],['bookCloudTrialChapter','chapter']])$(id).onchange=()=>{
 if(bookCloudBusy||bookCloudTrialChoice===choice)return;
 bookCloudTrialChoice=choice;bookCloudOpenOptions.trialChoice=choice;reloadBookCloudTrial();
};
