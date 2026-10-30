'use strict';
let readerState={mode:'create',variant:'text',page:0,fontSize:22,fontFamily:'svn-nexa',paperTheme:'system',follow:true};
function readerFontFamily(name){
 switch(name){
  case 'svn-georgia':return "'SVN Georgia', Georgia, serif";
  case 'svn-book-antiqua':return "'SVN Book Antiqua', 'Book Antiqua', Palatino, serif";
  case 'svn-linux-libertine':return "'SVN Linux Libertine', 'Linux Libertine', serif";
  case 'svn-arial':return "'SVN Arial', Arial, sans-serif";
  case 'svn-avo':return "'SVN Avo', sans-serif";
  case 'svn-gotham':return "'SVN Gotham', sans-serif";
  case 'sf-pro-rounded':return "'SF Pro Rounded', -apple-system, sans-serif";
  case 'system':return "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  case 'svn-nexa':
  default:return "var(--font-reading), sans-serif";
 }
}
let readerBook=null,readerData=null,readerToken='',readerKey='',readerCue='',readerSeconds=0,readerDuration=0,readerSaveTimer=null,readerGeneration=null;
const readerCache=new Map();
let readerPaintKey=[];
function readerCurrent(){
 if(aux?.kind==='reader'){const s=aux.segments[aux.at];return {segment:{id:s.segmentId,page:s.page},cueId:s.id,seconds:readerSeconds,duration:readerDuration||s.duration||0,lite:true};}
 if(aux?.kind==='take')return {segment:aux.segments[aux.at],takeId:aux.takeId,seconds:readerSeconds,duration:readerDuration||aux.segments[aux.at]?.duration||0};
 if(!book)return {};
 const generation=jobs.audio===book.id&&!playing&&!loaded&&readerGeneration;
 return {segment:book.segments[generation?readerGeneration.index:index],seconds:generation?0:readerSeconds,duration:generation?0:readerDuration||book.segments[index]?.duration||0,generating:!!generation};
}
function resetReader(next){
 readerPaintKey=[];
 clearTimeout(readerSaveTimer);readerBook=next?.id||null;readerState={mode:'create',variant:'text',page:0,fontSize:22,fontFamily:'svn-nexa',paperTheme:'system',follow:true,...next?.reader};
 if(next?.reader?.ebookVersion!==1)readerState.variant='text';readerState.ebookVersion=1;
 readerState.page=Math.min(Math.max(0,readerState.page),Math.max(0,(next?.pages.length||1)-1));
 resetEbook();readerData=null;readerKey='';readerToken='';readerCue='';readerSeconds=next?.position?.seconds||0;readerDuration=0;readerGeneration=null;readerCache.clear();
 $('sourceImage').removeAttribute('src');$('sourceHighlights').replaceChildren();$('sourceReflow').replaceChildren();
}
function saveReader(){
 if(!book)return;book.reader={...readerState};const id=book.id,value={...readerState};clearTimeout(readerSaveTimer);
 readerSaveTimer=setTimeout(()=>{readerSaveTimer=null;send({action:'readerSettings',bookId:id,reader:value});},250);
}
function flushReader(){if(readerSaveTimer&&book){clearTimeout(readerSaveTimer);readerSaveTimer=null;send({action:'readerSettings',bookId:book.id,reader:{...readerState}});}}
function setReaderMode(mode){cancelFlipbookTurn();if(guardDirty())return;if(aux?.kind==='reader')readerRemember();stop();readerState.mode=mode;if(mode==='read')readerState.variant='text';saveReader();renderReader();if(mode==='create')$('readingMode').focus();else $('readerBack').focus();}
function setReaderPage(page,manual=true){
 if(!book||!Number.isInteger(page)||page<0||page>=book.pages.length)return;
 if(manual)readerState.follow=false;
 readerState.page=page;if(readerState.variant==='text')ebookGoSource(page);saveReader();renderReader();
}
function readerRequestKey(){
 const current=readerCurrent(),segments=aux?.kind==='take'?aux.segments:book.segments;
 return JSON.stringify([book.id,readerState.page,current.takeId||'',segments.filter(s=>s.page===readerState.page).map(s=>[s.id,s.text])]);
}
function renderReader(){
 if(!book){document.body.classList.remove('reading-mode');$('sourceReader').hidden=true;return;}
 if(readerBook!==book.id)resetReader(book);
 const current=readerCurrent(),s=current.segment,activePage=s?.page??0;
 // Playback clocks only update a highlight. Do not invalidate the whole
 // multicolumn book by rewriting header/visibility controls on every tick.
 const paint=[book,book.status,book.title,readerState.mode,readerState.variant,readerState.page,readerState.fontSize,readerState.fontFamily,readerState.paperTheme,readerState.follow,modelCatalog,current.takeId,!!current.lite,!!current.generating,readerState.variant==='original'&&readerState.follow?s?.page:null];
 if(paint.length===readerPaintKey.length&&paint.every((value,i)=>value===readerPaintKey[i])){updateReaderHighlight();return;}
 readerPaintKey=paint;
 const reading=readerState.mode==='read';document.body.classList.toggle('reading-mode',reading);document.body.classList.toggle('reader-paper',reading&&readerState.paperTheme==='paper');$('sourceReader').hidden=!reading;
 $('creationMode').setAttribute('aria-pressed',String(!reading));$('readingMode').setAttribute('aria-pressed',String(reading));
 if(!reading)return;
 $('ebookTitle').textContent=book.title;renderReaderVoices();
 if(readerState.variant==='text'){renderEbook(current);return;}
 $('ebookViewport').hidden=true;$('sourceViewport').hidden=false;$('ebookSpreadLabel').textContent='';
 if(readerState.follow&&s&&!(aux&&!['take','reader'].includes(aux.kind)))readerState.page=Math.min(s.page,Math.max(0,book.pages.length-1));
 const page=readerState.page;
 if(document.activeElement!==$('sourcePageNumber'))$('sourcePageNumber').value=page+1;$('sourcePageNumber').max=book.pages.length;$('sourcePageTotal').textContent='/ '+book.pages.length;
 $('sourceUnit').textContent=unit();$('sourcePrevious').disabled=page<=0;$('sourceNext').disabled=page>=book.pages.length-1;
 $('sourceFollow').setAttribute('aria-pressed',String(readerState.follow));$('sourceFollow').textContent=readerState.follow?'Đang bám theo giọng đọc':'Về vị trí đang đọc';
 $('sourceOriginal').disabled=book.format==='epub';
 const key=readerRequestKey();
 if(key!==readerKey){
  readerKey=key;readerToken=requestToken();readerData=null;readerCue='';$('sourceLoading').hidden=false;$('sourceLoading').textContent='Đang mở trang sách…';$('sourcePaper').hidden=true;$('sourceReflow').hidden=true;
  if(readerCache.has(key)){readerData=readerCache.get(key);drawReaderPage();}
  else if(book.pages.length)send({action:'readerPage',bookId:book.id,page,token:readerToken,...(current.takeId?{takeId:current.takeId}:{})});
  else $('sourceLoading').textContent='Trang sách sẽ xuất hiện sau khi nhập xong.';
 }else if(readerData)showReaderVariant();
 updateReaderHighlight();
}
function showReaderVariant(){
 if(!readerData)return;
 const text=readerState.variant==='text'||readerData.format==='epub'||!readerData.image;
 $('sourcePaper').hidden=text;$('sourceReflow').hidden=!text;$('sourceFontLabel').hidden=!text;$('sourceFontFamilyLabel').hidden=!text;$('sourceZoomLabel').hidden=text;
 $('sourceOriginal').setAttribute('aria-pressed',String(!text));$('sourceText').setAttribute('aria-pressed',String(text));
 $('sourceFont').value=readerState.fontSize;$('sourceReflow').style.fontSize=readerState.fontSize+'px';
 $('sourceFontFamily').value=readerState.fontFamily||'svn-nexa';$('sourceReflow').style.fontFamily=readerFontFamily(readerState.fontFamily);
 $('sourcePaper').style.width=$('sourceZoom').value==='fit'?'100%':$('sourceZoom').value+'%';
 const notice=readerData.imageError?'Chưa mở được ảnh trang gốc. Bạn vẫn có thể đọc bản chữ.':readerState.follow?(readerCurrent().lite?'Trang tự chuyển theo câu đang đọc bằng Lite.':'Trang tự chuyển theo đoạn audio. Highlight câu là ước lượng.'):'Đang lật trang tự do. Bấm “Về vị trí đang đọc” để tiếp tục theo audio.';
 if($('sourceNotice').textContent!==notice)$('sourceNotice').textContent=notice;
}
function drawReaderPage(){
 const data=readerData;$('sourceLoading').hidden=true;readerCue='';
 if(data.image&&/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(data.image)){$('sourceImage').src=data.image;$('sourceImage').alt=`${unit(book,true)} ${data.page+1} · ${book.title}`;}else $('sourceImage').removeAttribute('src');
 $('sourceHighlights').replaceChildren();$('sourceReflow').replaceChildren();
 let paragraph=document.createElement('p');$('sourceReflow').append(paragraph);
 for(const cue of data.sentences){
  for(const part of cue.text.split(/(\n\s*\n)/)){
   if(/^\n\s*\n$/.test(part)){if(paragraph.textContent){paragraph=document.createElement('p');$('sourceReflow').append(paragraph);}continue;}
   if(!part)continue;const span=document.createElement('span');span.textContent=part;span.dataset.cue=cue.id;span.dataset.segmentId=cue.segmentId;paragraph.append(span);
  }
  for(const rect of data.highlights?.[cue.id]||[]){
   if(!['x','y','w','h'].every(k=>Number.isFinite(rect[k])&&rect[k]>=0&&rect[k]<=1))continue;
   const mark=document.createElement('div');mark.className='source-highlight';mark.dataset.cue=cue.id;
   for(const [property,value] of [['left',rect.x],['top',rect.y],['width',rect.w],['height',rect.h]])mark.style[property]=value*100+'%';
   $('sourceHighlights').append(mark);
  }
 }
 if(!data.sentences.length){const p=document.createElement('p');p.textContent=data.rawText||'Trang này không có chữ để đọc.';$('sourceReflow').append(p);}
 $('sourceViewport').scrollTop=0;showReaderVariant();updateReaderHighlight();
}
function updateReaderHighlight(){
 if(readerState.mode==='read'&&readerState.variant==='text'){updateEbookHighlight();return;}
 if(readerState.mode!=='read'||!readerData||!book)return;
 const current=readerCurrent(),s=current.segment;
 const visible=s?.page===readerData.page&&!(aux&&!['take','reader'].includes(aux.kind));
 const cues=visible?readerData.sentences.filter(c=>c.segmentId===s.id):[];
 const fraction=current.duration>0?Math.max(0,Math.min(.999999,current.seconds/current.duration)):0;
 const cue=current.cueId?cues.find(c=>c.id===current.cueId):current.generating?null:cues.find(c=>c.startFraction<=fraction&&fraction<c.endFraction)||cues[0];
 const id=cue?.id||'';
 if(readerCue!==id){
  readerCue=id;
  for(const span of $('sourceReflow').querySelectorAll('[data-cue]'))span.classList.toggle('reading-now',span.dataset.cue===id);
  for(const mark of $('sourceHighlights').children)mark.classList.toggle('reading-now',mark.dataset.cue===id);
  if(readerState.follow&&id){
   const target=(!$('sourceReflow').hidden?$('sourceReflow'):$('sourceHighlights')).querySelector('.reading-now');
   if(target){const viewport=$('sourceViewport'),a=target.getBoundingClientRect(),b=viewport.getBoundingClientRect();if(a.top<b.top+20||a.bottom>b.bottom-20)viewport.scrollTop+=a.top-b.top-Math.max(20,b.height*.35);}
  }
 }
 for(const p of $('sourceReflow').children)p.classList.toggle('source-generating',!!current.generating&&[...p.querySelectorAll('[data-segment-id]')].some(span=>span.dataset.segmentId===s?.id));
 $('sourceTracking').textContent=current.generating?`Đang tạo giọng cho ${unit()} ${(s?.page??0)+1}. Highlight câu xuất hiện khi phát audio.`:visible&&cue?(readerData.image&&!(readerData.highlights?.[id]?.length)&&readerState.variant==='original'?'Câu đã sửa hoặc chưa khớp chữ gốc · Chuyển “Ebook” để theo dõi.':(current.lite?'Lite · Câu đang được phát.':'Đúng trang theo đoạn đọc · Vị trí câu ước lượng theo thời lượng audio.')):'Bạn đang xem trang khác với vị trí phát.';
}
function handleReaderEvent(e){
 if(handleFlipbookEvent(e)||handleReaderLiteEvent(e)||handleEbookEvent(e))return true;
 if(e.event==='job'&&e.kind==='audio'&&e.bookId===book?.id){
  if(e.running)readerGeneration=null;
  else if(readerGeneration&&readerState.mode==='read'&&!playing&&!loaded){readerState.follow=false;saveReader();}
 }
 if(e.event==='readerPage'||e.event==='readerPageError'){
  if(!book||e.bookId!==book.id||e.token!==readerToken)return true;
  if(e.event==='readerPageError'){$('sourceLoading').textContent='Chưa mở được trang này. Lật sang trang khác hoặc thử lại.';readerKey='';return true;}
  readerData=e;readerCache.set(readerKey,e);if(readerCache.size>5)readerCache.delete(readerCache.keys().next().value);drawReaderPage();return true;
 }
 if(e.event==='playback'&&e.bookId===book?.id&&e.segment===index){readerSeconds=e.seconds;readerDuration=e.duration;renderReader();}
 if(e.event==='auxPlayback'&&aux?.token===e.token){readerSeconds=e.seconds;readerDuration=e.duration;renderReader();}
 if(e.event==='advanced'&&e.bookId===book?.id&&e.sessionId===playSession){readerSeconds=0;readerDuration=0;}
 if(e.event==='progress'&&e.kind==='audio'&&e.bookId===book?.id&&Number.isInteger(e.index)){readerGeneration={index:e.index,page:e.page};renderReader();}
 return false;
}
window.addEventListener('DOMContentLoaded',()=>{
 $('creationMode').onclick=()=>setReaderMode('create');$('readingMode').onclick=()=>setReaderMode('read');
 $('sourcePrevious').onclick=()=>readerState.variant==='text'?turnEbook(-1):setReaderPage(readerState.page-1);$('sourceNext').onclick=()=>readerState.variant==='text'?turnEbook(1):setReaderPage(readerState.page+1);
 $('sourcePageNumber').onchange=()=>setReaderPage(Number($('sourcePageNumber').value)-1);
 $('sourceFollow').onclick=()=>{readerState.follow=!readerState.follow;saveReader();renderReader();};
 $('sourceOriginal').onclick=()=>{cancelFlipbookTurn();readerState.variant='original';readerCue='';saveReader();renderReader();};$('sourceText').onclick=()=>{readerState.variant='text';readerCue='';saveReader();renderReader();};
 $('sourceFont').oninput=()=>{readerState.fontSize=Number($('sourceFont').value);saveReader();if(readerState.variant==='text')scheduleEbookLayout();else showReaderVariant();readerCue='';updateReaderHighlight();};
 $('sourceFontFamily').onchange=()=>{readerState.fontFamily=$('sourceFontFamily').value;saveReader();if(readerState.variant==='text')scheduleEbookLayout();else showReaderVariant();readerCue='';updateReaderHighlight();};
 $('sourceZoom').onchange=()=>{showReaderVariant();readerCue='';updateReaderHighlight();};
 $('sourceImage').onload=()=>{readerCue='';requestAnimationFrame(updateReaderHighlight);};
 $('sourceViewport').addEventListener('wheel',()=>{if(readerState.follow){readerState.follow=false;saveReader();renderReader();}},{passive:true});
 $('sourcePlayPage').onclick=()=>{
  if(guardDirty())return;if(readerState.mode==='read'&&ebookData){const cue=ebookFirstVisible();if(cue)readerStartAt(cue.id);return;}const saved=aux?.kind==='take',segments=saved?aux.segments:book?.segments;
  const cue=readerState.variant==='text'?ebookFirstVisible():null;
  const i=segments?.findIndex(s=>(cue?s.id===cue.segmentId:s.page===readerState.page)&&/[\p{L}\p{N}]/u.test(s.text));
  if(i>=0){readerState.follow=true;saveReader();if(saved){aux.at=i;startAux();renderReader();}else selectIndex(i,true);}else toast('Trang này không có chữ để nghe.');
 };
 $('sourceViewport').onkeydown=e=>{
  if(e.target!==$('sourceViewport'))return;
  if(['ArrowUp','ArrowDown','PageUp','PageDown','Home','End'].includes(e.key)&&readerState.follow){readerState.follow=false;saveReader();renderReader();}
  if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();setReaderPage(readerState.page+(e.key==='ArrowRight'?1:-1));
 };
});
