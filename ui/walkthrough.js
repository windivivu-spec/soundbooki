'use strict';
// Local-only discovery. No provider, payment or synthesis action runs during navigation.
const walkthroughKey='windi-walkthrough-v1';
let walkthroughAudioToken='',walkthroughMuted=preference('walkthrough-muted','false')==='true';
let walkthroughPage=0,walkthroughTrigger=null,walkthroughInitialized=false;
const walkthroughPages=[
 {label:'Sách nói miễn phí',tag:'MIỄN PHÍ · NGAY TRÊN MAC',title:'Sách của bạn.\nNghe hoàn toàn miễn phí.',body:'Biến PDF, EPUB thành sách nói với Lite. Tạo và nghe ngay trên máy của bạn, không cần mạng sau khi có gói giọng.',points:[],tip:'Lite tiếng Việt · 8 giọng Kitten tiếng Anh',scene:'import'},
 {label:'Giọng Pro trên cloud',tag:'PRO CLOUD · TỪ 10.000Đ / CUỐN',title:'Giọng đọc giàu cảm xúc.\nTự nhiên như người kể.',body:'Để Pro kể lại cuốn sách bạn yêu thích bằng giọng đọc tự nhiên, giàu cảm xúc. Tạo trên cloud, chỉ từ 10.000đ/cuốn.',points:[],tip:'Thử miễn phí 5 lượt / Mac · Tối đa 5.000 ký tự / lượt',scene:'cloud'},
 {label:'Đọc như ebook',tag:'KHÔNG GIAN ĐỌC SÁCH RIÊNG',title:'Một ứng dụng ebook.\nNgay trong góc nghe của bạn.',body:'Lật trang, chọn chương, chỉnh cỡ chữ và đọc kết hợp nghe. Tự lưu dấu trang đang đọc để lần sau tiếp tục đúng chỗ.',points:[],tip:'Đọc EPUB · Xem PDF gốc · Tự nhớ vị trí đọc',scene:'reader'},
 {label:'Nghe offline',tag:'LƯU VỀ MÁY · NGHE MỌI LÚC',title:'Tắt mạng. Thả lỏng.\nĐể câu chuyện tiếp tục.',body:'Lưu bản nghe về máy, thêm nhạc nền thư giãn và chỉnh âm lượng theo ý thích. Mang sách theo bạn, kể cả khi offline.',points:[],tip:'Xuất WAV hoặc M4A kèm nhạc nền',scene:'export'},
 {label:'Combo mở bán',tag:'COMBO MỞ BÁN · MỘT LẦN / MAC',title:'5 cuốn sách Pro.\nChỉ 50.000đ.',body:'Chọn 5 cuốn bạn muốn nghe nhất. Một combo dành riêng cho mỗi Mac, để bắt đầu thư viện sách nói Pro của bạn.',points:[],tip:'Mua và dùng đủ 5 lượt trước 23:59 · 01/11/2026 (giờ Việt Nam). Lượt chưa dùng sẽ hết hạn.',scene:'pro'}
];
const tourIcon=name=>`<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const tourWave=()=>`<div class="tour-wave">${Array.from({length:29},()=>`<i></i>`).join('')}</div>`;
function walkthroughScene(kind){
 const book=`<div class="tour-book"><span>WINDI<br>SÁCH NÓI</span>${tourIcon('wave')}<strong>Một trang sách.<br>Một thế giới.</strong></div>`;
 if(kind==='import')return `<div class="tour-orbit"></div><div class="tour-file tour-file-back">PDF<span>Bản gốc</span></div>${book}<div class="tour-file tour-file-front">EPUB<span>Sẵn sàng để đọc</span></div>`;
 if(kind==='reader')return `<div class="tour-reader"><div class="tour-mini-toolbar">${tourIcon('book')} CHƯƠNG 01 <span>Đã lưu vị trí đọc</span></div><h3>Chậm lại một chút</h3><p>Mở một trang sách, bạn mở thêm một khoảng trời.</p><p><mark>Có những câu chuyện đáng để ta lắng nghe thật chậm.</mark></p><div class="tour-text-lines"></div><div class="tour-mini-player">${tourIcon('pause')}<span>Đang đọc cùng bạn</span><b>1.0×</b></div></div>`;
 if(kind==='cloud')return `<div class="tour-cloud-symbol">${tourIcon('headphones')}<span>PRO</span></div>${tourWave()}<div class="tour-cloud-price"><small>GIỌNG ĐỌC TRÊN CLOUD</small><strong>Từ 10.000<span>đ</span></strong><p>Cho một cuốn sách của bạn</p></div>`;
 if(kind==='export')return `<div class="tour-export-disc">${tourIcon('music')}</div><div class="tour-export-card"><span>BẢN NGHE CỦA BẠN</span><h3>Câu chuyện, luôn bên mình.</h3><div class="tour-mix">${tourIcon('wave')} Giọng đọc <i></i></div><div class="tour-mix">${tourIcon('music')} Nhạc nền <i></i></div><div class="tour-formats"><b>WAV</b><b>M4A</b><b>WEB</b></div></div>`;
 return `<div class="tour-ticket"><span>COMBO RA MẮT · MỘT LẦN / MAC</span><div class="tour-five">${Array.from({length:5},(_,i)=>`<div>${tourIcon('book')}<small>0${i+1}</small></div>`).join('')}</div><div class="tour-price">50.000<small>đ</small></div><strong>5 cuốn sách nói Pro</strong><div class="tour-ticket-rule"></div><p>Mua và dùng đủ 5 lượt trước<br><b>23:59 · 01/11/2026</b></p></div>`;
}
function renderWalkthrough(){
 const page=walkthroughPages[walkthroughPage],expired=walkthroughPage===4&&Date.now()>=Date.parse(launchEndsAt);
 $('walkthroughTitle').textContent=expired?'Giọng đọc Pro.\nChọn theo từng cuốn.':page.title;
 $('walkthroughTag').textContent=expired?'GIỌNG ĐỌC PRO':page.tag;
 $('walkthroughBody').textContent=expired?'Chương trình combo ra mắt đã kết thúc. Bạn vẫn có thể xem giọng Pro, giá thường theo cuốn và nhận lại audio của các đơn đã đặt.':page.body;
 $('walkthroughPoints').replaceChildren(...(page.points).map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
 $('walkthroughTip').textContent=expired?'Xem trạng thái dịch vụ và các đơn hiện có trong phần Pro.':page.tip;
 $('walkthroughDialog').dataset.page=String(walkthroughPage);
 $('walkthroughScene').className=`tour-scene tour-scene-${page.scene}`;
 $('walkthroughScene').innerHTML=expired?`<div class="tour-ticket">${tourIcon('headphones')}<h3>Pro theo từng cuốn</h3><p>Chọn giọng. Xem giá.<br>Tạo bản nghe cho cuốn sách của bạn.</p></div>`:walkthroughScene(page.scene);
 $('walkthroughCount').textContent=`${walkthroughPage+1} / 5`;
 $('walkthroughBack').disabled=walkthroughPage===0;
 $('walkthroughNext').textContent=walkthroughPage===4?'Nghe Sách của bạn Ngay':'Tiếp theo';
 $('walkthroughPro').hidden=walkthroughPage!==4;
 $('walkthroughPro').textContent=expired?'Xem các đơn Pro':'Xem chương trình Pro';
 document.querySelectorAll('.tour-step').forEach((b,i)=>{b.setAttribute('aria-current',i===walkthroughPage?'step':'false');b.classList.toggle('is-complete',i<walkthroughPage);});
 $('walkthroughScroll').scrollTop=0;
}
function openWalkthrough(){
 if($('appInfoDialog').open)$('appInfoDialog').close();
 if(document.querySelector('dialog[open]'))return;
 walkthroughTrigger=document.activeElement;if(playing||pending||musicPreview||previewToken)stop();walkthroughPage=0;renderWalkthrough();$('walkthroughDialog').showModal();$('walkthroughNext').focus();animateWalkthrough(1,true);walkthroughAudioToken=requestToken();renderWalkthroughSound();send({action:'walkthroughAudio',operation:'start',token:walkthroughAudioToken,muted:walkthroughMuted});
}
function finishWalkthrough(){send({action:'walkthroughAudio',operation:'stop',token:walkthroughAudioToken});resetTourDrag();clearTimeout(tourWheelTimer);tourWheelX=0;tourWheelLocked=false;$('walkthroughDialog').getAnimations({subtree:true}).forEach(a=>a.cancel());try{localStorage.setItem(walkthroughKey,'seen');}catch{}$('walkthroughDialog').close();if(walkthroughTrigger?.isConnected&&walkthroughTrigger.matches('button:not(:disabled),a[href],input,select,textarea,[tabindex]')&&!walkthroughTrigger.closest('dialog:not([open])'))walkthroughTrigger.focus();else $('openWalkthroughHome').focus();}
function walkthroughReducedMotion(){return document.documentElement.dataset.motion==='off'||(document.documentElement.dataset.motion!=='on'&&matchMedia('(prefers-reduced-motion: reduce)').matches);}
function animateWalkthrough(direction=1,opening=false){
 const dialog=$('walkthroughDialog');dialog.getAnimations({subtree:true}).forEach(a=>a.cancel());
 if(walkthroughReducedMotion())return;
 const ease='cubic-bezier(.22,.61,.36,1)';
 if(opening)dialog.animate([{opacity:0,transform:'translateY(10px) scale(.985)'},{opacity:1,transform:'none'}],{duration:1250,easing:ease});
 $('walkthroughScene').animate([{opacity:0,transform:`translateX(${direction*18}px) scale(.985)`},{opacity:1,transform:'none'}],{duration:1400,easing:ease});
 [$('walkthroughTag'),$('walkthroughTitle'),$('walkthroughBody'),$('walkthroughTip')].forEach((el,i)=>el.animate([{opacity:0,transform:`translateY(${7+i}px)`},{opacity:1,transform:'none'}],{duration:1100,delay:100+i*140,easing:ease,fill:'backwards'}));
}
function setWalkthroughPage(next){
 next=Math.max(0,Math.min(walkthroughPages.length-1,next));if(next===walkthroughPage)return;
 const direction=next>walkthroughPage?1:-1;resetTourDrag();walkthroughPage=next;renderWalkthrough();animateWalkthrough(direction);
}
function renderWalkthroughSound(){const b=$('walkthroughSound');b.textContent=walkthroughMuted?'Bật âm':'Tắt âm';b.setAttribute('aria-pressed',String(walkthroughMuted));b.setAttribute('aria-label',walkthroughMuted?'Bật lời chào và nhạc nền':'Tắt lời chào và nhạc nền');}
$('walkthroughSound').onclick=()=>{walkthroughMuted=!walkthroughMuted;try{localStorage.setItem('windi-walkthrough-muted',String(walkthroughMuted));}catch{}renderWalkthroughSound();send({action:'walkthroughAudio',operation:'mute',token:walkthroughAudioToken,muted:walkthroughMuted});};
$('walkthroughSkip').onclick=finishWalkthrough;
$('walkthroughBack').onclick=()=>setWalkthroughPage(walkthroughPage-1);
$('walkthroughNext').onclick=()=>{if(walkthroughPage<4)setWalkthroughPage(walkthroughPage+1);else{finishWalkthrough();if(!book){showHome();pick();}}};
$('walkthroughPro').onclick=()=>{finishWalkthrough();openLaunchOffer();};
$('walkthroughDialog').addEventListener('cancel',event=>{event.preventDefault();finishWalkthrough();});
$('walkthroughSteps').replaceChildren(...walkthroughPages.map((page,i)=>{const b=document.createElement('button');b.type='button';b.className='tour-step';b.innerHTML='<span></span>';b.setAttribute('aria-label',`Trang ${i+1}: ${page.label}`);b.title=page.label;b.onclick=()=>setWalkthroughPage(i);return b;}));
$('walkthroughDialog').addEventListener('keydown',e=>{if(e.altKey||e.metaKey||e.ctrlKey)return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();setWalkthroughPage(walkthroughPage+(e.key==='ArrowRight'?1:-1));}});
// Native trackpad horizontal gestures and pointer/touch drags share the same bounded pager.
let tourDrag=null,tourWheelX=0,tourWheelLocked=false,tourWheelTimer=null;
function resetTourDrag(){tourDrag=null;const el=$('walkthroughScroll');el.classList.remove('is-dragging');el.style.removeProperty('--tour-drag');}
const tourSurface=$('walkthroughScroll');
tourSurface.addEventListener('pointerdown',e=>{
 if(!e.isPrimary||e.button!==0||e.target.closest('button,a,input,select,textarea'))return;
 tourDrag={id:e.pointerId,x:e.clientX,y:e.clientY,horizontal:false};
});
tourSurface.addEventListener('pointermove',e=>{
 if(!tourDrag||tourDrag.id!==e.pointerId)return;
 const dx=e.clientX-tourDrag.x,dy=e.clientY-tourDrag.y;
 if(!tourDrag.horizontal&&Math.abs(dy)>12&&Math.abs(dy)>Math.abs(dx)){resetTourDrag();return;}
 if(Math.abs(dx)>10&&Math.abs(dx)>Math.abs(dy)*1.25){tourDrag.horizontal=true;try{tourSurface.setPointerCapture(e.pointerId);}catch{}tourSurface.classList.add('is-dragging');}
 if(tourDrag.horizontal){e.preventDefault();const edge=(walkthroughPage===0&&dx>0)||(walkthroughPage===4&&dx<0);if(!walkthroughReducedMotion())tourSurface.style.setProperty('--tour-drag',`${Math.max(-95,Math.min(95,dx*(edge ? .14 : .4)))}px`);}
});
tourSurface.addEventListener('pointerup',e=>{
 if(!tourDrag||tourDrag.id!==e.pointerId)return;
 const dx=e.clientX-tourDrag.x,dy=e.clientY-tourDrag.y,swipe=tourDrag.horizontal&&Math.abs(dx)>=55&&Math.abs(dx)>Math.abs(dy)*1.25;
 resetTourDrag();if(swipe)setWalkthroughPage(walkthroughPage+(dx<0?1:-1));
});
tourSurface.addEventListener('pointercancel',resetTourDrag);
tourSurface.addEventListener('lostpointercapture',resetTourDrag);
tourSurface.addEventListener('wheel',e=>{
 if(e.ctrlKey||Math.abs(e.deltaX)<=Math.abs(e.deltaY)*1.2)return;
 e.preventDefault();clearTimeout(tourWheelTimer);tourWheelTimer=setTimeout(()=>{tourWheelX=0;tourWheelLocked=false;},220);
 if(tourWheelLocked)return;const dx=e.deltaX*(e.deltaMode===1?16:e.deltaMode===2?tourSurface.clientWidth:1);
 if(tourWheelX*dx<0)tourWheelX=0;tourWheelX+=dx;
 if(Math.abs(tourWheelX)>=65){tourWheelLocked=true;setWalkthroughPage(walkthroughPage+(tourWheelX>0?1:-1));}
},{passive:false});
$('openWalkthroughHome').onclick=openWalkthrough;$('openWalkthroughInfo').onclick=openWalkthrough;
const receiveBeforeWalkthrough=window.receive;
window.receive=e=>{if(e.event==='walkthroughAudio'){if(e.token===walkthroughAudioToken&&e.success===false&&$('walkthroughDialog').open){$('walkthroughSound').textContent='Âm thanh chưa sẵn sàng';$('walkthroughSound').title='Không mở được file chào mừng hoặc nhạc nền trên máy.';}return;}receiveBeforeWalkthrough(e);if(e.event==='init'&&!walkthroughInitialized){walkthroughInitialized=true;let seen=false;try{seen=localStorage.getItem(walkthroughKey)==='seen';}catch{}if(!seen&&Array.isArray(e.books)&&e.books.length===0&&!awaitingImport)openWalkthrough();}};
