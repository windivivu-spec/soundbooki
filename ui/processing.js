'use strict';
const importRuns=new Map();
let processingClock=null;
function receiveProcessing(e){
 const run=importRuns.get(e.bookId)||{};
 importRuns.set(e.bookId,{...run,...e,receivedAt:performance.now()});
 if(book?.id===e.bookId)renderImportProcessing();
}
function renderImportProcessing(){
 if(!book)return;
 $('processPDF').hidden=book.status!=='ready'||book.format==='epub'||!book.sources?.every(s=>s.file.endsWith('.pdf'))||!!book.layoutProcessing;
 const running=jobs.import===book.id,run=importRuns.get(book.id)||book.processing||{};
 const visible=book.status!=='ready';$('importStatus').hidden=!visible;
 // Keep the live progress announcement outside the busy document subtree.
 $('contentWorkspace').setAttribute('aria-busy',String(running));
 if(!visible){clearInterval(processingClock);processingClock=null;return;}
 const phase=run.phase||'extract',done=run.done??book.pages.length,total=run.total||book.totalPages;
 const label=running?(phase==='ready'?'Đã xử lý xong sách':phase==='layout'?'Đang tự dọn chữ và ghép dòng':'Đang đọc chữ và bố cục'):(book.error?'Chưa xử lý xong':'Đã tạm dừng xử lý sách');
 if($('importText').textContent!==label)$('importText').textContent=label;
 $('importAction').textContent=running?'Hủy xử lý':'Tiếp tục xử lý';
 const progress=$('importProgress');
 // Percentage measures completed work, never elapsed time. Unknown totals use
 // the native indeterminate bar until the extractor reports a page count.
 if(phase==='ready')progress.value=1;
 else if(total){progress.value=phase==='layout'?.8+.2*Math.min(1,done/total):.8*Math.min(1,done/total);}else progress.removeAttribute('value');
 for(const step of document.querySelectorAll('.processing-steps [data-phase]'))step.setAttribute('aria-current',step.dataset.phase===phase?'step':'false');
 $('importDetail').textContent=book.error||(!running?`Đã lưu ${book.pages.length} ${unit()}. Bạn có thể tiếp tục từ phần đã lưu.`:phase==='ready'?'Đã lưu kết quả. Đang mở nội dung sách…':`${done}/${total||'?'} ${unit()} · ${phase==='layout'?'Tự nối dòng, bỏ ký hiệu trang trí và nhận diện chương.':'Xử lý trên Mac · Trang có chữ được đọc trực tiếp; trang scan dùng OCR.'}`);
 function tick(){
  const elapsed=Math.floor((run.elapsedSeconds||0)+(running&&run.receivedAt?(performance.now()-run.receivedAt)/1000:0));
  $('importElapsed').textContent=elapsed?`${elapsed} giây`:'';
  if(running&&phase!=='ready'&&elapsed>=30)$('importDetail').textContent=`${done}/${total||'?'} ${unit()} · Sách này cần thêm thời gian, nhất là các trang scan. Phần đã xử lý vẫn được lưu.`;
 }
 tick();clearInterval(processingClock);processingClock=running?setInterval(tick,1000):null;
}
window.addEventListener('DOMContentLoaded',()=>{
 $('processPDF').onclick=()=>{if(guardDirty())return;stop();send({action:'processPDF',bookId:book.id});};
});
