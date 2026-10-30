'use strict';
const audio=document.getElementById('audio');
const book=window.windiBook;
const entries=book.segments;
const storageKey='windi-book:'+location.pathname;
const notice=document.getElementById('notice');
const english=book.language==='en';
let current=-1,lastSavedAt=0,restored=false,hasPlayed=false,lastKnownPosition=0,resumePosition=0;
try{resumePosition=Math.max(0,Number(localStorage.getItem(storageKey))||0);lastKnownPosition=resumePosition;}catch{notice.textContent=english?'This browser cannot save listening progress.':'Trình duyệt này chưa cho phép lưu vị trí nghe.';}
function stamp(seconds){return `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;}
function save(){
    if(!hasPlayed)return;
    try{localStorage.setItem(storageKey,String(lastKnownPosition));}catch{}
}
function update(){
    let at=0;
    for(let n=0;n<entries.length;n++)if(audio.currentTime>=entries[n].seconds)at=n;
    if(at===current||!entries.length)return;
    current=at;document.getElementById('text').textContent=entries[at].text;
    [...document.querySelectorAll('#chapters button')].forEach((b,n)=>b.setAttribute('aria-current',String(n===at)));
}
function restore(){
    if(restored||!Number.isFinite(audio.duration))return;
    restored=true;
    const position=Math.min(resumePosition,Math.max(0,audio.duration-.25));
    if(position>0){audio.currentTime=position;notice.textContent=english?`Resume from ${stamp(position)}.`:`Nghe tiếp từ ${stamp(position)}.`;}
    update();
}
for(const entry of entries){
    const button=document.createElement('button');button.textContent=entry.title;
    button.onclick=()=>{hasPlayed=true;lastKnownPosition=entry.seconds;audio.currentTime=entry.seconds;save();audio.play().catch(()=>{});};
    document.getElementById('chapters').append(button);
}
update();
audio.addEventListener('loadedmetadata',restore);
if(audio.readyState>=1)restore();
audio.addEventListener('play',()=>{hasPlayed=true;});
audio.addEventListener('timeupdate',()=>{
    update();
    if(!hasPlayed||!restored||audio.readyState<1||audio.seeking)return;
    lastKnownPosition=audio.currentTime;
    if(Date.now()-lastSavedAt>2000){save();lastSavedAt=Date.now();}
});
audio.addEventListener('seeked',()=>{update();if(hasPlayed){lastKnownPosition=audio.currentTime;save();}});
audio.addEventListener('pause',()=>{if(hasPlayed&&audio.readyState>=1&&audio.currentTime>0)lastKnownPosition=audio.currentTime;save();});
audio.addEventListener('ended',()=>{lastKnownPosition=0;save();});
window.addEventListener('pagehide',save);
document.getElementById('speed').onchange=e=>audio.playbackRate=Number(e.target.value);
