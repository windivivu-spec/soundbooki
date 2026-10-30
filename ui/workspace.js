'use strict';
let activeChapterId=null,editorKey='',workspaceTab='content',chapterSave=null;
let aux=null,previewToken=null,previewBusy=false,voiceListKey='',takesKey='',chapterListKey='';
function modelLabel(id){return modelCatalog.find(m=>m.id===id)?.label||({nano:'Lite',turbo:'VieNeu Turbo',kitten:'KittenTTS English','f5-private':'Bản đọc đã lưu','pro-cloud':'Pro · Tạo từ Cloud','clone-pro':'Bản đọc đã lưu'}[id]||'Giọng đọc');}
function voiceLabel(model,id){return modelCatalog.find(m=>m.id===model)?.voices?.find(v=>v.id===id)?.label||(model==='f5-private'&&/^voice-\d+$/.test(id)?'Giọng riêng '+String(Number(id.split('-')[1])).padStart(2,'0'):id);}
function requestToken(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');}
function activeSection(){return book?.sections?.find(c=>c.id===activeChapterId)||book?.sections?.[0];}
function prepareWorkspaceBook(next,changed){
 if(changed){activeChapterId=next.sections?.find(c=>c.indices.includes(next.position.segment))?.id||next.sections?.[0]?.id;editorKey='';workspaceTab='content';chapterSave=null;chapterListKey='';takesKey='';}
 if(chapterSave?.bookId===next.id){const c=next.sections.find(c=>c.id===chapterSave.chapterId);if(c?.text===chapterSave.text){dirty=false;index=next.position.segment;}}
 if(!next.sections?.some(c=>c.id===activeChapterId))activeChapterId=next.sections?.[0]?.id;
}
function setWorkspaceTab(tab){if(guardDirty())return;workspaceTab=tab;renderWorkspace();(tab==='content'?$('contentTab'):$('audiobooksTab')).focus();}
function selectChapter(id){
 if(guardDirty())return;const c=book.sections.find(c=>c.id===id);if(!c)return;
 stop();activeChapterId=id;editorKey='';index=c.indices[0]??book.segments.findIndex(s=>s.page>=c.startPage);if(index<0)index=0;
 if(book.segments[index]){book.position={segment:index,seconds:0};send({action:'position',bookId:book.id,segment:index,seconds:0});}
 render();prepareListening();
}
function renderWorkspace(){
 if(!book)return;const c=activeSection();if(!c)return;activeChapterId=c.id;
 $('contentWorkspace').hidden=workspaceTab!=='content';$('audiobooksPanel').hidden=workspaceTab!=='audio';
 $('contentTab').setAttribute('aria-selected',String(workspaceTab==='content'));$('audiobooksTab').setAttribute('aria-selected',String(workspaceTab==='audio'));
 $('contentTab').tabIndex=workspaceTab==='content'?0:-1;$('audiobooksTab').tabIndex=workspaceTab==='audio'?0:-1;
 $('takeCount').textContent=book.audiobooks?.length||0;
 const key=JSON.stringify([book.id,c.id,book.sections.map(s=>[s.id,s.title,s.characters,s.indices.filter(i=>book.segments[i]?.audio).length,s.indices.length])]);
 if(key!==chapterListKey){chapterListKey=key;$('segments').replaceChildren();for(const item of book.sections){
  const button=document.createElement('button');button.className='segment chapter-item'+(c.id===item.id?' active':'');button.setAttribute('aria-current',String(c.id===item.id));
  const title=document.createElement('strong');title.className='user-text';title.textContent=item.title;
  const meta=document.createElement('small');const ready=item.indices.filter(i=>book.segments[i]?.audio).length;meta.textContent=ready?`${ready}/${item.indices.length} phần đã tạo`:`${item.characters.toLocaleString('vi')} ký tự`;button.append(title,meta);button.onclick=()=>selectChapter(item.id);$('segments').append(button);
 }}
 const nextKey=book.id+':'+c.id;const editor=$('editor');
 if(editorKey!==nextKey){editorKey=nextKey;dirty=false;editor.value=c.text;editor.scrollTop=0;}
 else if(!dirty&&editor.value!==c.text)editor.value=c.text;
 document.querySelector('.document').hidden=!book.pages.length;$('pagePlaceholder').hidden=!!book.pages.length;
 $('pagePlaceholderText').textContent='Chưa có nội dung. Tiếp tục trích chữ để xem chương.';
 $('segmentLabel').classList.add('user-text');$('segmentLabel').textContent=c.title;
 const ready=c.indices.filter(i=>book.segments[i]?.audio).length;
 $('audioState').textContent=`${editor.value.length.toLocaleString('vi')} ký tự · `+(book.model==='pro-cloud'?'Bản Pro được lưu trong Sách nói của bạn':`${ready}/${c.indices.length} phần đã tạo`);
 const warnings=[...new Set(book.pages.slice(c.startPage,c.endPage+1).flatMap(p=>[p.warning,p.layoutWarning]).filter(Boolean))];
 $('warning').textContent=warnings.join(' ');$('warning').hidden=!warnings.length;
 const busy=!!chapterSave||jobs.audio===book.id||jobs.export===book.id||book.status!=='ready';editor.disabled=busy;
 $('saveEdit').disabled=!dirty||busy;$('discardEdit').disabled=!dirty||busy;$('restore').disabled=busy||editor.value===c.originalText;
 $('quickGenerate').disabled=busy||!!jobs.audio||!!jobs.export||!/[\p{L}\p{N}]/u.test(editor.value);
 const wholeBookIndices=scopeIndices({type:'all'});
 const wholeBookReady=wholeBookIndices.filter(i=>book.segments[i]?.audio).length;
 $('generateWholeBook').hidden=book.model==='clone-pro'||(book.model==='pro-cloud'&&book.language!=='vi');
 $('generateWholeBook').disabled=!!chapterSave||!!jobs.audio||!!jobs.export||book.status!=='ready'||!wholeBookIndices.length||(book.model!=='pro-cloud'&&wholeBookReady===wholeBookIndices.length);
 $('generateWholeBook').title=book.model==='pro-cloud'?'Xem giá và tạo Pro cho toàn bộ sách':'Tạo giọng đọc cho tất cả nội dung đã trích trong sách';
 $('quickGenerate').lastChild.textContent=chapterSave?'Đang lưu…':(book.model==='pro-cloud'?'Tạo Pro cho chương này':'Tạo bản đọc chương này');
 $('editHint').textContent=dirty?'Chưa lưu · Tạo bản đọc sẽ lưu nội dung bạn đang chỉnh sửa.':'Toàn bộ chương · có thể xóa bớt trước khi tạo.';
 renderTakes();if(!$('voicesPanel').hidden)renderVoiceDemos();
}
function edited(){clearTimeout(listeningTimer);listeningKey='';listeningToken='';send({action:'cancelListening'});dirty=$('editor').value!==activeSection().text;renderWorkspace();}
function saveChapter(generate=false){
 const c=activeSection();if(!c||chapterSave)return;
 if(!dirty){if(generate==='all')generateWholeBook();else if(generate)generateChapter(c);return;}
 stop();chapterSave={bookId:book.id,chapterId:c.id,text:$('editor').value,generate,token:requestToken()};
 send({action:'editChapter',...chapterSave,expected:c.text});renderWorkspace();
}
function generateWholeBook(){
 if(!book)return;
 if(dirty){saveChapter('all');return;}
 if(book.model==='pro-cloud'){openBookCloud();return;}
 if(book.status!=='ready'){toast('Chờ xử lý toàn bộ sách xong trước khi tạo.');return;}
 const scope={type:'all'},indices=scopeIndices(scope);if(!indices.length){toast('Sách chưa có nội dung để tạo giọng.');return;}
 if(indices.every(i=>book.segments[i]?.audio)){toast('Toàn bộ sách đã có giọng đọc.');return;}
 stop();index=indices[0];scopeDirty=false;book.generationScope=scope;$('scopeType').value='all';
 send({action:'settings',bookId:book.id,scope});requestGenerate({action:'generate',bookId:book.id,scope});render();
}
function generateChapter(c){
 if(book.model==='pro-cloud'){openBookCloud({mode:'trial',chapterId:c.id});return;}
 const indices=c.indices;if(!indices.length){toast('Nội dung này chưa có chữ để tạo giọng.');return;}
 stop();index=indices[0];scopeDirty=false;book.generationScope={type:'chapter',chapterId:c.id};$('scopeType').value='chapter';$('chapterSelect').value=c.id;
 send({action:'settings',bookId:book.id,scope:book.generationScope});requestGenerate({action:'generate',bookId:book.id,scope:book.generationScope});render();
}
function renderTakes(){
 const takes=book.audiobooks||[];$('takesEmpty').hidden=!!takes.length;
 const key=JSON.stringify([book.id,takes,modelCatalog.map(m=>[m.id,m.label,m.voices]),!!jobs.audio,!!jobs.export]);if(key===takesKey)return;takesKey=key;$('takeList').replaceChildren();
 for(const take of takes){
  const row=document.createElement('article');row.className='take-row';
  const copy=document.createElement('div');copy.className='take-copy';const title=document.createElement('h3');title.className='user-text take-title';title.textContent=take.title;
  const info=document.createElement('p');info.textContent=`${voiceLabel(take.model,take.voice)} · ${modelLabel(take.model)} · ${fmt(take.duration)}`;
  const date=document.createElement('small');date.className='user-text';date.textContent=new Date(take.createdAt).toLocaleString(window.i18n?.language==='en'?'en-GB':'vi-VN',{dateStyle:'short',timeStyle:'short'});
  const status=document.createElement('span');status.className='take-status';status.textContent=take.status==='ready'?'Đã tạo xong':`${take.readyCount}/${take.segments.length} phần sẵn sàng`;
  copy.append(title,info,date,status);const actions=document.createElement('div');actions.className='take-actions';
  const play=document.createElement('button');play.className='secondary';play.append(icon('play'),document.createTextNode('Nghe bản này'));play.disabled=!take.readyCount;
  play.onclick=()=>{if(guardDirty())return;playAux({kind:'take',takeId:take.id,title:take.title,segments:take.segments.filter(s=>s.audio),at:0,token:requestToken()});};
  const download=document.createElement('button');download.className='secondary';download.append(icon('export'),document.createTextNode('Tải về'));download.disabled=take.status!=='ready'||!!jobs.export;
  download.onclick=()=>send({action:'exportDialog',bookId:book.id,takeId:take.id,title:book.title+' — '+take.title,format:$('takeFormat').value});actions.append(play,download);
  for(const output of (take.exports||[]).slice(-2)){const file=document.createElement('button');file.className='text user-text';file.textContent=output.path.split('/').pop();file.title=output.path;file.onclick=()=>send({action:'revealExport',path:output.path});actions.append(file);}
  row.append(copy,actions);$('takeList').append(row);
 }
}
function openVoiceDemos(){if(guardDirty())return;closeProduction();$('modelsPanel').hidden=true;$('appearancePanel').hidden=true;$('appearance').setAttribute('aria-expanded','false');$('voicesPanel').hidden=false;document.querySelector('main').append($('voicesPanel'));renderVoiceDemos();$('closeVoices').focus();}
function renderVoiceDemos(){
 if(!book)return;const model=modelCatalog.find(m=>m.id===(book.model||'nano'));if(!model)return;
 $('voiceDemoHint').textContent=model.cloud?'Nghe thử mẫu giọng bạn thích trước khi tạo sách.':model.label;
 const key=JSON.stringify([book.id,book.model,book.voice,model.voices,previewBusy,previewToken,aux?.voice,!!jobs.audio]);
 if(key===voiceListKey)return;voiceListKey=key;$('voiceDemoList').replaceChildren();
 for(const voice of model.voices){
  const row=document.createElement('div');row.className='voice-demo-row';const copy=document.createElement('div');const title=document.createElement('strong');title.className='user-text';title.textContent=voice.label;const detail=document.createElement('small');detail.textContent=model.label;copy.append(title,detail);
  const sample=document.createElement('button');sample.className='secondary';sample.textContent=previewToken?.voice===voice.id&&previewBusy?'Đang chuẩn bị…':aux?.voice===voice.id&&playing?'Đang nghe':'Nghe thử';sample.disabled=previewBusy||(!model.ready&&!model.cloud)||!!jobs.audio;
  sample.onclick=()=>{stop();const token=requestToken();previewToken={token,voice:voice.id};send({action:'voicePreview',model:book.model,voice:voice.id,language:book.language,token});renderVoiceDemos();};
  const choose=document.createElement('button');choose.className='text';choose.textContent=book.voice===voice.id?'Đang chọn':'Chọn giọng';choose.disabled=book.voice===voice.id||!!jobs.audio||!!jobs.export;
  choose.onclick=()=>{stop();send({action:'settings',bookId:book.id,voice:voice.id});$('voicesPanel').hidden=true;$('voiceDemos').focus();};row.append(copy,sample,choose);$('voiceDemoList').append(row);
 }
}
function auxOffset(){return aux?.kind==='take'?aux.segments.slice(0,aux.at).reduce((sum,s)=>sum+(s.duration||0),0):0;}
function playAux(value){stop();aux=value;startAux();}
function queueAuxNext(){
 if(!aux||aux.kind==='reader')return;
 const next=aux.segments[aux.at+1];
 if(next?.audio)send({action:'auxQueue',token:aux.token,path:next.audio,segment:aux.at+1});
}
function startAux(){
 if(aux?.kind==='reader'){startReaderSentence();return;}
 readerSeconds=0;readerDuration=0;
 const s=aux?.segments[aux.at];if(!s)return;playing=true;loaded=true;pending=false;
 send({action:'auxPlay',token:aux.token,path:s.audio,speed:aux.kind==='voice'?1:book.speed,music:aux.kind==='voice'?{...musicPayload(),offset:0}:{...musicPayload(),offset:auxOffset()}});
 queueAuxNext();
 $('seek').value=0;$('seek').max=s.duration||1;$('time').textContent=`0:00 / ${fmt(s.duration||0)}`;renderAux();setPlay(true);renderVoiceDemos();
}
function moveAux(delta){if(aux&&aux.at+delta>=0&&aux.at+delta<aux.segments.length){aux.at+=delta;startAux();}}
function renderAux(){if(aux?.kind==='reader'){renderReaderPlayer();return;}if(!aux)return;$('player').hidden=false;$('playingTitle').textContent=(aux.kind==='voice'?'Nghe thử · ':'Sách nói · ')+aux.title;$('positionLabel').textContent=`${aux.at+1} / ${aux.segments.length}`;$('prev').disabled=aux.at===0;$('next').disabled=aux.at===aux.segments.length-1;}
function handleWorkspaceEvent(e){
 if(e.event==='chapterSaved'){
  const op=chapterSave;if(!op||op.token!==e.token)return true;chapterSave=null;dirty=false;render();if(op.generate&&book.id===op.bookId&&activeChapterId===op.chapterId){if(op.generate==='all')generateWholeBook();else generateChapter(activeSection());}return true;
 }
 if(e.event==='previewJob'){previewBusy=e.running;renderVoiceDemos();return true;}
 if(e.event==='voiceDemo'){
  if(previewToken?.token!==e.token)return true;playAux({kind:'voice',voice:e.voice,title:voiceLabel(book.model,e.voice),segments:[{audio:e.path,duration:0}],at:0,token:e.token});return true;
 }
 if(e.event==='auxPlayback'){
  if(aux?.token!==e.token)return true;playing=e.playing;loaded=true;$('seek').max=e.duration;$('seek').value=e.seconds;$('time').textContent=`${fmt(e.seconds)} / ${fmt(e.duration)}`;renderAux();setPlay(playing);return true;
 }
 if(e.event==='auxAdvanced'&&aux?.kind!=='reader'){
  if(aux?.token!==e.token)return true;
  if(!Number.isInteger(e.segment)||e.segment!==aux.at+1||!aux.segments[e.segment])return true;
  aux.at=e.segment;queueAuxNext();renderAux();return true;
 }
 if(e.event==='auxEnded'){
  if(aux?.token!==e.token)return true;if(e.success&&aux.at+1<aux.segments.length){aux.at++;startAux();}else{stop();render();renderVoiceDemos();if(!e.success)toast('Audio phát bị gián đoạn. Bấm nghe để thử lại.');}return true;
 }
 return false;
}
function bindWorkspace(){
 $('contentTab').onclick=()=>setWorkspaceTab('content');$('audiobooksTab').onclick=()=>setWorkspaceTab('audio');
 document.querySelector('.book-tabs').onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();setWorkspaceTab(workspaceTab==='content'?'audio':'content');}};
 $('editor').oninput=edited;$('saveEdit').onclick=()=>saveChapter();$('quickGenerate').onclick=()=>saveChapter(true);$('generateWholeBook').onclick=()=>saveChapter('all');
 $('restore').onclick=()=>{$('editor').value=activeSection().originalText;edited();};$('discardEdit').onclick=()=>{$('editor').value=activeSection().text;dirty=false;renderWorkspace();};
 $('voiceDemos').onclick=openVoiceDemos;$('closeVoices').onclick=()=>{$('voicesPanel').hidden=true;previewToken=null;send({action:'cancel',kind:'preview'});if(aux?.kind==='voice'){stop();render();}$('voiceDemos').focus();};
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('voicesPanel').hidden)$('closeVoices').click();});
}
