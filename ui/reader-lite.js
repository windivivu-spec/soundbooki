'use strict';
let readerFetchToken='',readerFetchKey='',readerLiteIntent=false,readerVoiceKey='',readerLiteCache=new Map(),readerQueued='',readerPauseTimer=null;
function cancelReaderLite(){clearTimeout(readerPauseTimer);readerPauseTimer=null;readerFetchToken='';readerFetchKey='';readerLiteIntent=false;readerQueued='';}
function liteVoice(){const voices=modelCatalog.find(m=>m.id==='nano')?.voices||[];return voices.some(v=>v.id===readerState.voice)?readerState.voice:voices.find(v=>v.default)?.id||voices[0]?.id||'Đức Trí';}
function renderReaderVoices(){
 const voices=modelCatalog.find(m=>m.id==='nano')?.voices||[];const key=JSON.stringify(voices);if(key!==readerVoiceKey){readerVoiceKey=key;$('readerVoiceChoice').replaceChildren();for(const voice of voices){const option=document.createElement('option');option.value=voice.id;option.textContent=voice.label;$('readerVoiceChoice').append(option);}}
 $('readerVoiceChoice').value=liteVoice();$('readerVoiceChoice').disabled=!voices.length;
}
function readerBuffer(){
 if(aux?.kind!=='reader')return;const at=aux.at,items=aux.segments.slice(at,at+12);if(items.every(s=>s.audio))return;
 // Keep a useful ahead buffer; don't cancel an in-flight window every sentence.
 if(readerFetchToken&&items.slice(0,5).every(s=>s.audio))return;
 const key=[book.id,aux.voice,aux.segments[at].id].join(':');if(readerFetchKey===key)return;readerFetchKey=key;readerFetchToken=requestToken();
 send({action:'readerListen',bookId:book.id,voice:aux.voice,cueId:aux.segments[at].id,token:readerFetchToken});
}
// Sentences are started after a short natural pause; audio cache stays unchanged.
function readerQueueNext(){}
function renderReaderPlayer(){
 if(aux?.kind!=='reader')return;const s=aux.segments[aux.at];$('player').hidden=false;$('playingTitle').textContent=`${pending?'Đang chuẩn bị Lite':playing?'Đang nghe':'Tạm dừng'} · ${unit(book,true)} ${s.page+1} · ${voiceLabel('nano',aux.voice)}`;
 $('positionLabel').textContent=`${aux.at+1} / ${aux.segments.length}`;$('prev').disabled=aux.at===0;$('next').disabled=aux.at>=aux.segments.length-1;
}
function readerRemember(){if(aux?.kind==='reader'){readerState.anchor=aux.segments[aux.at].id;readerState.page=aux.segments[aux.at].page;readerState.seconds=readerSeconds;saveReader();}}
function startReaderSentence(){
 if(aux?.kind!=='reader')return;readerSeconds=0;readerDuration=0;readerQueued='';const s=aux.segments[aux.at];if(!s)return;
 readerState.anchor=s.id;readerState.page=s.page;readerState.seconds=0;readerState.follow=true;saveReader();
 if(!s.audio){loaded=false;playing=false;pending=true;setPlay(true);renderReaderPlayer();renderReader();readerBuffer();return;}
 pending=false;loaded=true;playing=true;send({action:'auxPlay',path:s.audio,token:aux.token,speed:book.speed,music:{}});
 $('seek').value=0;$('seek').max=s.duration||1;$('time').textContent=`0:00 / ${fmt(s.duration||0)}`;renderReaderPlayer();setPlay(true);renderReader();readerQueueNext();readerBuffer();
}
function readerStartAt(cueId){
 if(!ebookData||readerState.mode!=='read'){toast('Chờ trang ebook mở xong để nghe Lite.');return;}
 const cues=ebookData.sentences.filter(s=>/[\p{L}\p{N}]/u.test(s.text)),at=cues.findIndex(s=>s.id===cueId);if(at<0)return;
 const voice=liteVoice();stop();readerLiteIntent=true;readerState.voice=voice;readerState.follow=true;
 aux={kind:'reader',voice,token:requestToken(),at,segments:cues.map(c=>({...c,...readerLiteCache.get(book.id+':'+!!book.bilingual+':'+voice+':'+c.id+':'+c.text)}))};startReaderSentence();
}
function readerJump(delta){if(aux?.kind!=='reader')return;clearTimeout(readerPauseTimer);readerPauseTimer=null;const at=aux.at+delta;if(at<0||at>=aux.segments.length)return;send({action:'stop'});readerFetchKey='';readerFetchToken='';aux.token=requestToken();aux.at=at;readerLiteIntent=true;startReaderSentence();}
function readerTogglePlay(){
 if(aux?.kind==='reader'){
  if(readerPauseTimer){readerRemember();stop();return;}
  if(pending){readerRemember();stop();renderReaderPlayer();return;}
  readerLiteIntent=!playing;send({action:playing?'pause':'continue'});return;
 }
 const cue=ebookData?.sentences.find(c=>c.id===readerState.anchor)||ebookFirstVisible();if(cue)readerStartAt(cue.id);else toast('Chờ trang ebook mở xong để nghe.');
}
function handleReaderLiteEvent(e){
 if(e.event==='readerAudioReady'){
  if(e.bookId!==book?.id||e.token!==readerFetchToken||aux?.kind!=='reader'||e.voice!==aux.voice)return true;
  const s=aux.segments.find(s=>s.id===e.cueId&&s.text===e.text);if(!s)return true;s.audio=e.path;s.duration=e.duration;
  readerLiteCache.set(book.id+':'+!!book.bilingual+':'+aux.voice+':'+s.id+':'+s.text,{audio:e.path,duration:e.duration});
  if(pending&&readerLiteIntent&&aux.segments[aux.at]===s)startReaderSentence();else readerQueueNext();return true;
 }
 if(e.event==='readerBuffer'){
  if(e.bookId!==book?.id||e.token!==readerFetchToken)return true;
  readerFetchToken='';readerFetchKey='';if(e.state==='error'){pending=false;readerLiteIntent=false;setPlay(playing);toast(e.message);}return true;
 }
 if(e.event==='auxPlayback'&&aux?.kind==='reader'&&aux.token===e.token){
  readerSeconds=e.seconds;readerDuration=e.duration;playing=e.playing;loaded=true;$('seek').max=e.duration;$('seek').value=e.seconds;$('time').textContent=`${fmt(e.seconds)} / ${fmt(e.duration)}`;renderReaderPlayer();setPlay(playing);renderReader();readerRemember();readerQueueNext();return true;
 }
 if(e.event==='auxAdvanced'&&aux?.kind==='reader'&&aux.token===e.token){
  if(e.segment!==aux.at+1)return true;aux.at=e.segment;readerSeconds=0;readerDuration=0;playing=true;pending=false;loaded=true;readerQueued='';renderReaderPlayer();renderReader();readerRemember();readerQueueNext();readerBuffer();return true;
 }
 if(e.event==='auxEnded'&&aux?.kind==='reader'&&aux.token===e.token){
  loaded=false;playing=false;readerQueued='';if(e.success&&readerLiteIntent&&aux.at+1<aux.segments.length){aux.at++;playing=true;setPlay(true);const token=aux.token;readerPauseTimer=setTimeout(()=>{readerPauseTimer=null;if(aux?.kind==='reader'&&aux.token===token&&readerLiteIntent)startReaderSentence();},350);}else{readerRemember();stop();setPlay(false);if(!e.success)toast('Câu đọc bị gián đoạn. Bấm Play để thử lại.');}return true;
 }
 return false;
}
window.addEventListener('DOMContentLoaded',()=>{
 const originalPlay=$('play').onclick;$('play').onclick=()=>readerState.mode==='read'?readerTogglePlay():originalPlay();
 const originalPrev=$('prev').onclick,originalNext=$('next').onclick;$('prev').onclick=()=>aux?.kind==='reader'?readerJump(-1):originalPrev();$('next').onclick=()=>aux?.kind==='reader'?readerJump(1):originalNext();
 $('readerVoiceChoice').onchange=()=>{const cue=aux?.kind==='reader'?aux.segments[aux.at].id:readerState.anchor,wasPlaying=playing||pending;stop();readerState.voice=$('readerVoiceChoice').value;saveReader();if(wasPlaying&&cue)readerStartAt(cue);};
 $('ebookFlow').addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)&&e.target.dataset.cue){e.preventDefault();e.stopPropagation();readerStartAt(e.target.dataset.cue);}});
 $('ebookFlow').addEventListener('click',e=>{const span=e.target.closest('[data-cue]');if(span&&!getSelection()?.toString())readerStartAt(span.dataset.cue);});
});
