'use strict';
let ebookData=null,ebookKey='',ebookToken='',ebookSpread=0,ebookCount=1,ebookColumns=2,ebookStep=0,ebookWidth=0,ebookLayout='',ebookPositions=new Map(),ebookElements=new Map(),ebookActive='',ebookResizeTimer=null,ebookRelayout=false,ebookFigures=new Map(),ebookFigurePositions=new Map(),ebookImagePending=new Set();
let ebookSignatureCache=null,ebookCueIndex=new Map(),ebookSegmentCues=new Map(),ebookColumnFirst=[],ebookTabStop=null,ebookChapterIndex=[],ebookLayoutPending=false;
function readerText(id,value){const el=$(id);if(el.textContent!==value)el.textContent=value;}
function resetEbook(){if(globalThis.CSS?.highlights)for(const color of ['yellow','green','blue','pink'])CSS.highlights.delete('note-'+color);ebookSignatureCache=null;ebookCueIndex.clear();ebookSegmentCues.clear();ebookColumnFirst=[];ebookTabStop=null;ebookChapterIndex=[];cancelFlipbookTurn();ebookToken='';ebookKey='';ebookData=null;ebookLayout='';ebookSpread=0;ebookPositions.clear();ebookElements.clear();ebookFigures.clear();ebookFigurePositions.clear();ebookImagePending.clear();ebookActive='';$('ebookFlow').replaceChildren();$('ebookContents').replaceChildren();}
function ebookSignature(){
 const segments=aux?.kind==='take'?aux.segments:book.segments,takeId=aux?.kind==='take'?aux.takeId:'';
 const cache=ebookSignatureCache;
 if(cache&&cache.id===book.id&&cache.status===book.status&&cache.segments===segments&&cache.sections===book.sections&&cache.takeId===takeId)return cache.key;
 const key=JSON.stringify([book.id,takeId,book.status,segments.map(s=>[s.id,s.text]),book.sections?.map(c=>[c.id,c.title,c.indices])]);
 ebookSignatureCache={id:book.id,status:book.status,segments,sections:book.sections,takeId,key};return key;
}
function renderEbook(current){
 $('ebookViewport').hidden=false;$('sourceViewport').hidden=true;$('sourcePaper').hidden=true;$('sourceReflow').hidden=true;
 $('sourceOriginal').disabled=book.format==='epub';$('sourceOriginal').setAttribute('aria-pressed','false');$('sourceText').setAttribute('aria-pressed','true');$('sourceFontLabel').hidden=false;$('sourceFontFamilyLabel').hidden=false;$('sourceZoomLabel').hidden=true;$('sourceFont').value=readerState.fontSize;$('sourceFontFamily').value=readerState.fontFamily||'svn-nexa';$('readerTheme').value=readerState.paperTheme==='paper'?'paper':$('theme').value;
 $('sourceFollow').setAttribute('aria-pressed',String(readerState.follow));readerText('sourceFollow',readerState.follow?'Đang bám theo giọng đọc':'Về vị trí đang đọc');
 if(document.activeElement!==$('sourcePageNumber'))$('sourcePageNumber').value=readerState.page+1;$('sourcePageNumber').max=book.pages.length;$('sourcePageTotal').textContent='/ '+book.pages.length;$('sourceUnit').textContent=unit();
 if(book.status!=='ready'){$('sourceLoading').hidden=false;$('sourceLoading').textContent='Đang xử lý sách. Ebook sẽ mở sau khi hoàn tất…';return;}
 const key=ebookSignature();
 if(key!==ebookKey){
  ebookKey=key;ebookToken=requestToken();ebookData=null;ebookLayout='';ebookActive='';$('ebookFlow').replaceChildren();$('sourceLoading').hidden=false;$('sourceLoading').textContent='Đang dàn trang ebook trên Mac…';
  send({action:'readerBook',bookId:book.id,token:ebookToken,...(current.takeId?{takeId:current.takeId}:{})});
 }
 if(ebookData){$('sourceLoading').hidden=true;layoutEbook();updateEbookHighlight();}
}
function drawEbook(data){
 // Prepare column metrics before attaching the long book. Reading viewport
 // geometry after insertion, then changing it, lays out the whole book twice.
 const viewport=$('ebookViewport'),width=viewport.clientWidth,height=viewport.clientHeight;
 ebookData=data;ebookElements.clear();ebookPositions.clear();ebookFigures.clear();ebookFigurePositions.clear();ebookImagePending.clear();ebookActive='';const flow=document.createDocumentFragment();ebookCueIndex.clear();ebookSegmentCues.clear();ebookColumnFirst=[];ebookTabStop=null;
 for(let i=0;i<data.sentences.length;i++){const cue=data.sentences[i];ebookCueIndex.set(cue.id,{cue,index:i});if(!ebookSegmentCues.has(cue.segmentId))ebookSegmentCues.set(cue.segmentId,[]);ebookSegmentCues.get(cue.segmentId).push(cue);}
 ebookChapterIndex=(data.chapters||[]).map(chapter=>({chapter,index:ebookCueIndex.get(chapter.cue)?.index??-1})).filter(c=>c.index>=0).sort((a,b)=>a.index-b.index);
 const images=new Map();for(const f of data.figures||[]){if(!images.has(f.before))images.set(f.before,[]);images.get(f.before).push(f);}
 let paragraph=null,lastPage=-1;
 const chapterCues=new Map((data.chapters||[]).map(c=>[c.cue,c])),chapterTitles=new Set((data.chapters||[]).map(c=>c.title.trim().replace(/\s+/g,' ').toLocaleLowerCase()));
 for(const cue of data.sentences){
  for(const f of images.get(cue.id)||[]){
   if(!/^(p\d+-\d+|epub-\d+)\.jpg$/.test(f.file))continue;
   const figure=document.createElement('figure'),img=document.createElement('img');if(f.image)img.src=f.image;img.alt='Ảnh minh họa · '+unit(book,true)+' '+(f.page+1);if(f.width&&f.pixelsHigh){img.width=f.width;img.height=f.pixelsHigh;}figure.append(img);figure.dataset.file=f.file;flow.append(figure);ebookFigures.set(f.file,{figure,img,width:f.width||800,height:f.pixelsHigh||600});paragraph=null;
  }
  const chapter=chapterCues.get(cue.id),isHeading=chapterTitles.has(cue.text.trim().replace(/\s+/g,' ').toLocaleLowerCase());
  if(isHeading){paragraph=document.createElement('h2');flow.append(paragraph);}
  if(!paragraph){paragraph=document.createElement('p');flow.append(paragraph);}
  if(lastPage!==-1&&lastPage!==cue.page&&paragraph.hasChildNodes()&&!/\s$/.test(paragraph.lastChild.textContent)&&!/^\s/.test(cue.text))paragraph.append(document.createTextNode(' '));
  const span=document.createElement('span');span.dataset.cue=cue.id;span.dataset.page=cue.page;span.dataset.segmentId=cue.segmentId;span.tabIndex=-1;span.setAttribute('role','button');span.setAttribute('aria-label','Nghe từ câu: '+cue.text.trim().slice(0,180));
  // One wrapper keeps source identity even when a sentence flows over columns.
  const parts=cue.text.split(/(\n\s*\n)/);
  for(let i=0;i<parts.length;i++){const part=parts[i];
   if(/^\n\s*\n$/.test(part)){if(parts.slice(i+1).join('').trim())span.append(document.createElement('br'),document.createElement('br'));}else span.append(document.createTextNode(part));
  }
  if(chapter&&/^\s*\d+\s*$/.test(cue.text))paragraph.classList.add('ebook-chapter-number');
  paragraph.append(span);ebookElements.set(cue.id,span);lastPage=cue.page;
  if(/\n\s*\n\s*$/.test(cue.text)||isHeading)paragraph=null;
 }
 if(!data.sentences.length){const p=document.createElement('p');p.textContent='Chưa có nội dung chữ để dàn trang. Chọn PDF / ảnh gốc để xem tài liệu.';flow.append(p);}
 prepareEbookFlow(width,height);if(globalThis.CSS?.highlights)for(const color of ['yellow','green','blue','pink'])CSS.highlights.delete('note-'+color);$('ebookFlow').replaceChildren(flow);if(typeof readingPaint==='function')readingPaint();
 $('ebookContents').replaceChildren();$('readerContentsBook').textContent=book.title;
 for(const c of data.chapters||[]){const button=document.createElement('button');button.className='ebook-chapter user-text';const title=document.createElement('strong'),meta=document.createElement('small');title.textContent=c.title;meta.textContent=unit(book,true)+' '+(c.page+1);button.append(title,meta);button.dataset.cue=c.cue;button.onclick=()=>{readerState.follow=false;ebookGoCue(c.cue,true);$('readerContentsDialog').close();$('ebookViewport').focus();};$('ebookContents').append(button);}
 ebookLayout='';setTimeout(()=>{if(ebookData!==data)return;layoutEbook(true);if(readerState.follow)updateEbookHighlight();else if(readerState.anchor)ebookGoCue(readerState.anchor);else ebookGoSource(readerState.page);},0);
}
function scheduleEbookLayout(){ebookLayoutPending=true;clearTimeout(ebookResizeTimer);ebookResizeTimer=setTimeout(()=>{ebookLayoutPending=false;if(readerState.mode==='read'&&readerState.variant==='text')layoutEbook(true);},120);}
function ebookColumnGap(w,columns){return columns===2?Math.min(144,Math.max(96,w*.085,readerState.fontSize*4)):32;}
function prepareEbookFlow(w,h){
 if(w<100||h<80)return;
 const flow=$('ebookFlow'),columns=w>=700?2:1,gap=ebookColumnGap(w,columns);
 flow.style.columnCount=String(columns);flow.style.columnGap=gap+'px';flow.style.fontSize=readerState.fontSize+'px';flow.style.fontFamily=readerFontFamily(readerState.fontFamily||'svn-nexa');
 for(const value of ebookFigures.values()){const ratio=value.width/value.height,width=Math.min((w+gap)/columns-gap,h*.65*ratio);value.img.style.width=width+'px';value.img.style.height=width/ratio+'px';}
 $('ebookViewport').classList.toggle('single-page',columns===1);
}
function layoutEbook(force=false){
 if(!ebookData||$('ebookViewport').hidden||ebookLayoutPending&&!force)return;
 const viewport=$('ebookViewport'),flow=$('ebookFlow'),w=viewport.clientWidth,h=viewport.clientHeight;if(w<100||h<80)return;
 const columns=w>=700?2:1,gap=ebookColumnGap(w,columns);
 const font=readerState.fontFamily||'svn-nexa';
 const key=[w,h,readerState.fontSize,font,columns].join(':');if(key===ebookLayout&&ebookPositions.size)return;
 cancelFlipbookTurn();ebookRelayout=true;const anchor=readerState.follow?ebookActive:readerState.anchor||ebookFirstVisible()?.id;ebookLayout=key;ebookColumns=columns;ebookWidth=w;ebookStep=(w+gap)/columns;
 prepareEbookFlow(w,h);flow.style.transform='none';
 viewport.classList.toggle('single-page',columns===1);viewport.setAttribute('aria-label',columns===2?'Nội dung ebook, hai trang':'Nội dung ebook, một trang');
 ebookPositions.clear();ebookColumnFirst=[];const base=flow.getBoundingClientRect();
 for(const [id,element] of ebookElements){const rects=[...element.getClientRects()].filter(r=>r.width>0);const cols=rects.map(r=>Math.max(0,Math.floor((r.left-base.left+1)/ebookStep)));if(cols.length){const first=Math.min(...cols),last=Math.max(...cols);ebookPositions.set(id,{first,last});for(let col=first;col<=last;col++)if(!ebookColumnFirst[col])ebookColumnFirst[col]=ebookCueIndex.get(id)?.cue;}}
 ebookFigurePositions.clear();for(const [file,{figure}] of ebookFigures){const r=figure.getBoundingClientRect();ebookFigurePositions.set(file,Math.max(0,Math.floor((r.left-base.left+1)/ebookStep)));}
 const last=Math.max(0,...[...ebookPositions.values()].map(p=>p.last),...[...ebookFigurePositions.values()]);ebookCount=Math.max(1,last+1);ebookSpread=Math.min(ebookSpread,Math.ceil(ebookCount/ebookColumns)-1);
 if(anchor&&ebookPositions.has(anchor))ebookSpread=Math.floor(ebookPositions.get(anchor).first/ebookColumns);
 applyEbookSpread();updateEbookHighlight();ebookRelayout=false;
}
function ebookFirstVisible(){const first=ebookSpread*ebookColumns;for(let col=first;col<first+ebookColumns;col++)if(ebookColumnFirst[col])return ebookColumnFirst[col];}
function loadEbookImages(){
 if(!ebookData)return;const first=ebookSpread*ebookColumns;
 for(const [file,col] of ebookFigurePositions){const item=ebookFigures.get(file);if(col>=first-2&&col<first+ebookColumns+2&&!item.img.hasAttribute('src')&&!ebookImagePending.has(file)){ebookImagePending.add(file);send({action:'readerImage',bookId:book.id,contentKey:ebookData.contentKey,file});}
  if(Math.abs(col-first)>12&&item.img.hasAttribute('src')){item.img.removeAttribute('src');ebookImagePending.delete(file);}
 }
}
function applyEbookSpread(){
 // A 3D transform promotes the entire multicolumn book to a huge texture in
 // WebKit. A clipped 2D translation paints only the visible spread instead.
 $('ebookFlow').style.transform=`translateX(${-ebookSpread*ebookColumns*ebookStep}px)`;
 const first=ebookSpread*ebookColumns+1,last=Math.min(ebookCount,first+ebookColumns-1);
 $('ebookSpreadLabel').textContent=`${ebookColumns===2?'Trang đọc':'Trang đọc'} ${first}${last>first?'–'+last:''} / ${ebookCount}`;
 $('sourcePrevious').disabled=ebookSpread<=0;$('sourceNext').disabled=(ebookSpread+1)*ebookColumns>=ebookCount;
 const visible=ebookFirstVisible();if(visible){if(ebookTabStop)ebookTabStop.tabIndex=-1;ebookTabStop=ebookElements.get(visible.id);if(ebookTabStop)ebookTabStop.tabIndex=0;readerState.page=visible.page;const cueIndex=ebookCueIndex.get(visible.id)?.index??0;const chapter=ebookChapterIndex.findLast(c=>c.index<=cueIndex)?.chapter;$('ebookChapter').textContent=chapter?.title||'';for(const button of $('ebookContents').children)button.setAttribute('aria-current',String(button.dataset.cue===chapter?.cue));}
 if(document.activeElement!==$('sourcePageNumber'))$('sourcePageNumber').value=readerState.page+1;loadEbookImages();
}
function ebookMotion(){const mode=document.documentElement.dataset.motion;return mode!=='off'&&(mode==='on'||!matchMedia('(prefers-reduced-motion: reduce)').matches);}
function turnEbook(direction,manual=true){
 if(!ebookData)return;const base=flipbookQueued?.next??flipbookTurn?.to??ebookSpread,next=base+direction;if(next<0||next*ebookColumns>=ebookCount)return;
 requestEbookSpread(next,manual);
}
function ebookGoCue(id,manual=false){
 const position=ebookPositions.get(id);if(!position)return;const next=Math.floor(position.first/ebookColumns);
 if(next!==ebookSpread)requestEbookSpread(next,manual,id);else if(manual){readerState.anchor=id;saveReader();}updateEbookStatus();
}
function ebookGoSource(page){const cue=ebookData?.sentences.find(c=>c.page>=page);if(cue){readerState.anchor=cue.id;ebookGoCue(cue.id,true);}}
function updateEbookStatus(){
 if(!ebookData)return;const current=readerCurrent(),s=current.segment;
 readerText('sourceTracking',current.generating?`Đang tạo · ${unit(book,true)} ${(s?.page??0)+1}`:`Nguồn: ${unit(book,true)} ${readerState.page+1} · ${current.lite?'Lite · Bấm câu để nghe từ đây':'Bấm câu để nghe bằng Lite'}`);
 readerText('sourceNotice','');
}
function updateEbookHighlight(){
 if(!ebookData||readerState.mode!=='read'||readerState.variant!=='text')return;
 const current=readerCurrent(),s=current.segment;const cues=ebookSegmentCues.get(s?.id)||[];
 const fraction=current.duration>0?Math.min(.999999,Math.max(0,current.seconds/current.duration)):0;
 const cue=current.cueId?ebookCueIndex.get(current.cueId)?.cue:current.generating?null:cues.find(c=>c.startFraction<=fraction&&fraction<c.endFraction)||cues[0],id=cue?.id||'';
 if(id!==ebookActive){ebookElements.get(ebookActive)?.classList.remove('reading-now');ebookActive=id;ebookElements.get(id)?.classList.add('reading-now');if(readerState.follow&&id){ebookGoCue(id);readerState.anchor=id;}}
 if(readerState.follow&&id){const p=ebookPositions.get(id);if(p&&(p.first<ebookSpread*ebookColumns||p.first>=(ebookSpread+1)*ebookColumns))ebookGoCue(id);}
 if(current.generating&&readerState.follow&&cues[0])ebookGoCue(cues[0].id);
 updateEbookStatus();
}
function handleEbookEvent(e){
 if(e.event==='readerImage'||e.event==='readerImageError'){
  if(e.bookId!==book?.id||e.contentKey!==ebookData?.contentKey)return true;
  const item=ebookFigures.get(e.file);if(item&&/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(e.image||''))item.img.src=e.image;return true;
 }
 if(e.event==='readerBook'||e.event==='readerBookError'){
  if(e.bookId!==book?.id||e.token!==ebookToken)return true;
  if(e.event==='readerBookError'){$('sourceLoading').hidden=false;$('sourceLoading').textContent=e.message||'Chưa dàn được trang ebook.';return true;}
  $('sourceLoading').hidden=true;drawEbook(e);return true;
 }
 if(e.event==='ebookExported'){if(e.bookId===book?.id){$('readerExportStatus').textContent='Đã lưu bản EPUB.';toast('Đã lưu bản EPUB vào vị trí bạn chọn.');}return true;}
 return false;
}
window.addEventListener('DOMContentLoaded',()=>{
 $('readerTheme').onchange=()=>{const value=$('readerTheme').value;readerState.paperTheme=value==='paper'?'paper':'system';document.body.classList.toggle('reader-paper',readerState.mode==='read'&&value==='paper');if(value!=='paper'){$('theme').value=value;applyAppearance();}saveReader();};
 $('readerBack').onclick=()=>setReaderMode('create');$('readerFullscreen').onclick=()=>send({action:'readerFullscreen'});
 for(const [button,dialog,close] of [['readerPreferences','readerSettingsDialog','closeReaderSettings'],['readerContents','readerContentsDialog','closeReaderContents']]){
  $(button).onclick=()=>{if(button==='readerPreferences')$('readerTheme').value=readerState.paperTheme==='paper'?'paper':$('theme').value;$(dialog).showModal();$(close).focus();};$(close).onclick=()=>$(dialog).close();$(dialog).addEventListener('click',e=>{if(e.target===$(dialog)){const r=$(dialog).getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$(dialog).close();}});$(dialog).onclose=()=>$(button).focus();
 }
 $('readerExportEpub').onclick=()=>{if(!book)return;$('readerExportStatus').textContent='Chọn nơi lưu bản EPUB.';send({action:'exportEbookDialog',bookId:book.id,title:book.title,...(aux?.kind==='take'?{takeId:aux.takeId}:{})});};
 document.fonts.addEventListener('loadingdone',()=>{ebookLayout='';scheduleEbookLayout();});
 new ResizeObserver(scheduleEbookLayout).observe($('ebookViewport'));
 document.addEventListener('keydown',e=>{
  if(readerState.mode!=='read'||document.querySelector('dialog[open]'))return;
  if(e.key==='Escape'){e.preventDefault();setReaderMode('create');return;}
  if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;
  if(readerState.variant==='text'&&['ArrowLeft','ArrowRight','PageUp','PageDown'].includes(e.key)){e.preventDefault();turnEbook(['ArrowRight','PageDown'].includes(e.key)?1:-1);}
 });
 let wheel=0,last=0;
 $('ebookViewport').addEventListener('wheel',e=>{if(flipbookWheelEvent(e))return;e.preventDefault();if(Date.now()-last<480)return;wheel+=Math.abs(e.deltaX)>Math.abs(e.deltaY)?e.deltaX:e.deltaY;if(Math.abs(wheel)>65){turnEbook(wheel>0?1:-1);wheel=0;last=Date.now();}},{passive:false});

});
