'use strict';
// GulLabs core 3.2.2 (unmodified MPL-2.0 source in vendor/gul-flipbook/source).
// Only four HTML faces exist during a turn; live sentence DOM stays intact.
let flipbookSupported=false,flipbookTurn=null,flipbookQueued=null,flipbookWheel=null,flipbookWheelTimer=null,flipbookSuppressClick=0;
// Finish semantic navigation even if WebKit pauses animation frames in a covered window.
function flipbookPaint(done){let ran=false;const run=()=>{if(ran)return;ran=true;done();};requestAnimationFrame(()=>requestAnimationFrame(run));setTimeout(run,80);}
function disposeFlipbook(state){
 clearTimeout(state.timeout);cancelAnimationFrame(state.frame);state.engine?.destroy();state.overlay?.remove();state.oldImage='';
}
function cancelFlipbookTurn(){
 const state=flipbookTurn;flipbookTurn=null;flipbookQueued=null;flipbookWheel=null;clearTimeout(flipbookWheelTimer);
 if(state){disposeFlipbook(state);send({action:'cancelPageTurn'});}
}
function commitEbookSpread(next,manual,anchor){
 ebookSpread=next;applyEbookSpread();if(manual){readerState.anchor=anchor||ebookFirstVisible()?.id||'';saveReader();}updateEbookHighlight();
}
function requestEbookSpread(next,manual=false,anchor='',gesture=null){
 if(!ebookData)return;next=Math.max(0,Math.min(Math.ceil(ebookCount/ebookColumns)-1,next));
 if(manual)readerState.follow=false;
 if(flipbookTurn){if(next!==flipbookTurn.to)flipbookQueued={next,manual,anchor};return;}
 if(next===ebookSpread){if(manual&&anchor){readerState.anchor=anchor;saveReader();}return;}
 if(ebookRelayout||!ebookMotion()||!flipbookSupported||ebookColumns!==2||Math.abs(next-ebookSpread)!==1){commitEbookSpread(next,manual,anchor);return;}
 const rect=$('ebookViewport').getBoundingClientRect(),paper=getComputedStyle($('sourceReader')).backgroundColor,color=paper.match(/[\d.]+/g)||['32','40','53'];
 const state={token:requestToken(),from:ebookSpread,fromAnchor:readerState.anchor,to:next,manual,anchor,staged:false,gesture,settled:false,width:rect.width,height:rect.height,paper};flipbookTurn=state;
 send({action:'beginPageTurn',token:state.token,x:rect.x,y:rect.y,width:rect.width,height:rect.height,red:Number(color[0])/255,green:Number(color[1])/255,blue:Number(color[2])/255});
 state.timeout=setTimeout(()=>finishFlipbookFallback(state),1900);
}
function finishFlipbookFallback(state){
 if(flipbookTurn!==state)return;const committed=!(state.gesture?.ended&&!state.gesture.commit);
 if(committed&&ebookSpread!==state.to)commitEbookSpread(state.to,state.manual,state.anchor);
 finishFlipbookCurl(state,committed);
}
function finishFlipbookQueued(){const queued=flipbookQueued;flipbookQueued=null;if(queued)requestAnimationFrame(()=>requestEbookSpread(queued.next,queued.manual,queued.anchor));}
function finishFlipbookCurl(state,committed){
 if(flipbookTurn!==state||state.finishing)return;state.finishing=true;clearTimeout(state.timeout);
 if(!committed){flipbookQueued=null;commitEbookSpread(state.from,state.manual,state.fromAnchor||'');}
 // Keep the last curl frame until the semantic page underneath has painted.
 flipbookPaint(()=>{if(flipbookTurn!==state)return;flipbookTurn=null;disposeFlipbook(state);send({action:'endPageTurn',token:state.token});finishFlipbookQueued();});
}
function curlPoint(state,progress){
 const p=Math.max(.001,Math.min(.999,progress)),forward=state.to>state.from;
 return {x:state.width*(forward?1-p:p),y:state.height-2-Math.sin(Math.PI*p)*Math.min(state.height*.32,state.width*.23)};
}
function applyFlipbookProgress(state,progress){
 if(flipbookTurn!==state||!state.engine||state.finishing)return;
 const forward=state.to>state.from;
 if(!state.dragStarted){state.dragStarted=true;state.engine.startUserTouch({x:forward?state.width-1:1,y:state.height-2});state.engine.userMove({x:forward?state.width-9:9,y:state.height-3},true);}
 state.progress=progress;state.point=curlPoint(state,progress);state.engine.userMove(state.point,true);
}
function settleFlipbookGesture(){
 const state=flipbookTurn;if(!state?.staged||!state.gesture?.ended||state.settled)return;
 state.settled=true;const start=state.progress||0,target=state.gesture.commit?1:0,began=performance.now(),duration=Math.max(220,Math.min(560,260+Math.abs(target-start)*280-Math.abs(state.gesture.velocity||0)*25));
 const frame=now=>{if(flipbookTurn!==state||state.finishing)return;const t=Math.min(1,(now-began)/duration),ease=1-Math.pow(1-t,3);applyFlipbookProgress(state,start+(target-start)*ease);
  if(t<1)state.frame=requestAnimationFrame(frame);else state.engine.userStop(state.point,false);
 };state.frame=requestAnimationFrame(frame);
}
async function mountFlipbookCurl(state,image){
 if(!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(image)||!state.oldImage)throw Error('Missing local page face');
 const overlay=document.createElement('div'),root=document.createElement('div');overlay.className='ebook-curl-overlay';overlay.setAttribute('aria-hidden','true');overlay.inert=true;overlay.style.backgroundColor=state.paper;root.className='ebook-curl-engine';overlay.append(root);state.overlay=overlay;
 const forward=state.to>state.from,faces=[],images=[];
 for(let i=0;i<4;i++){
  const page=document.createElement('div'),face=document.createElement('div'),img=document.createElement('img');face.className='ebook-curl-face';img.className=i%2?'curl-right':'curl-left';img.alt='';img.draggable=false;
  img.src=(i<2)===forward?state.oldImage:image;face.append(img);page.append(face);page.dataset.density='soft';root.append(page);faces.push(page);images.push(img);
 }
 await Promise.all(images.map(img=>img.decode()));if(flipbookTurn!==state)return;
 $('ebookViewport').append(overlay);
 const engine=new GulFlipbook.PageFlip(root,{width:state.width/2,height:state.height,initialPage:forward?0:2,sizing:'fixed',autoSize:false,usePortrait:false,hardCovers:false,drawShadow:true,maxShadowOpacity:.32,flippingTime:420,pointerInput:[],flipOnClick:'never',foldCornerOnHover:false,pageBackground:state.paper,respectReducedMotion:true,injectStyles:false});state.engine=engine;
 engine.on('changeState',e=>{if(e.data.state==='read'&&state.settled)finishFlipbookCurl(state,engine.getCurrentPageIndex()===(forward?2:0));});
 engine.loadFromHTML(faces);
 // The engine's first frame must replace the capture cover without a flash.
 await new Promise(flipbookPaint);if(flipbookTurn!==state)return;
 state.staged=true;clearTimeout(state.timeout);state.timeout=setTimeout(()=>finishFlipbookFallback(state),state.gesture?30000:1400);send({action:'releasePageTurn',token:state.token});
 if(state.gesture){applyFlipbookProgress(state,state.gesture.progress);settleFlipbookGesture();}
 else{state.settled=true;if(!(forward?engine.flipNext(GulFlipbook.FlipCorner.BOTTOM):engine.flipPrev(GulFlipbook.FlipCorner.BOTTOM)))finishFlipbookFallback(state);}
}
function handleFlipbookEvent(e){
 if(e.event==='pageTurnSupport'){flipbookSupported=e.supported===true&&typeof GulFlipbook!=='undefined';return true;}
 if(!['pageTurnCaptured','pageTurnStaged','pageTurnFallback'].includes(e.event))return false;
 const state=flipbookTurn;if(!state||state.token!==e.token||state.finishing)return true;
 if(e.event==='pageTurnCaptured'){
  if(!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(e.image||'')){finishFlipbookFallback(state);return true;}
  state.oldImage=e.image;commitEbookSpread(state.to,state.manual,state.anchor);
  flipbookPaint(()=>{if(flipbookTurn===state)send({action:'stagePageTurn',token:state.token});});
 }else if(e.event==='pageTurnStaged')mountFlipbookCurl(state,e.image).catch(()=>finishFlipbookFallback(state));
 else finishFlipbookFallback(state);
 return true;
}
function moveFlipbookGesture(gesture,delta){
 const before=gesture.progress,now=performance.now();gesture.progress=Math.max(0,Math.min(1,gesture.progress+delta/Math.max(ebookWidth*.55,1)));
 if(gesture.time&&now>gesture.time)gesture.velocity=gesture.velocity*.7+(gesture.progress-before)/(now-gesture.time)*300;
 gesture.time=now;if(flipbookTurn?.gesture===gesture&&flipbookTurn.staged)applyFlipbookProgress(flipbookTurn,gesture.progress);
}
function endFlipbookGesture(gesture){
 gesture.ended=true;gesture.commit=gesture.progress>.3||gesture.velocity>1.1;flipbookSuppressClick=Date.now()+220;settleFlipbookGesture();
}
function flipbookWheelEvent(e){
 if(!flipbookSupported||!ebookMotion()||ebookColumns!==2||Math.abs(e.deltaY)>Math.abs(e.deltaX)*2)return false;
 e.preventDefault();if(flipbookTurn&&(!flipbookTurn.gesture||flipbookTurn.gesture.ended))return true;
 if(!flipbookWheel){if(Math.abs(e.deltaX)<4)return true;const direction=e.deltaX>0?1:-1,next=ebookSpread+direction;if(next<0||next*ebookColumns>=ebookCount)return true;
  flipbookWheel={progress:0,velocity:0,time:0,ended:false,commit:false,direction};requestEbookSpread(next,true,'',flipbookWheel);
 }
 if(flipbookWheel.ended)return true;moveFlipbookGesture(flipbookWheel,e.deltaX*flipbookWheel.direction);
 clearTimeout(flipbookWheelTimer);flipbookWheelTimer=setTimeout(()=>{if(flipbookWheel){endFlipbookGesture(flipbookWheel);flipbookWheel=null;}},120);return true;
}
window.addEventListener('DOMContentLoaded',()=>{
 let pointer=null;
 $('ebookViewport').addEventListener('pointerdown',e=>{const r=$('ebookViewport').getBoundingClientRect();if(!flipbookSupported||!ebookMotion()||ebookColumns!==2||e.button>0||(e.pointerType==='mouse'&&e.clientX>r.left+24&&e.clientX<r.right-24))return;pointer={x:e.clientX,y:e.clientY,last:e.clientX,gesture:null};});
 document.addEventListener('pointermove',e=>{if(!pointer)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;if(!pointer.gesture){if(Math.abs(dx)<8)return;if(Math.abs(dy)>Math.abs(dx)*2){pointer=null;return;}const direction=dx<0?1:-1,next=ebookSpread+direction;if(next<0||next*ebookColumns>=ebookCount){pointer=null;return;}
  pointer.gesture={progress:0,velocity:0,time:0,ended:false,commit:false,direction};requestEbookSpread(next,true,'',pointer.gesture);
 }e.preventDefault();moveFlipbookGesture(pointer.gesture,(pointer.last-e.clientX)*pointer.gesture.direction);pointer.last=e.clientX;});
 document.addEventListener('pointerup',()=>{if(pointer?.gesture)endFlipbookGesture(pointer.gesture);pointer=null;});document.addEventListener('pointercancel',()=>{if(pointer?.gesture){pointer.gesture.progress=0;pointer.gesture.velocity=0;endFlipbookGesture(pointer.gesture);}pointer=null;});
 $('ebookViewport').addEventListener('click',e=>{if(Date.now()<flipbookSuppressClick){e.preventDefault();e.stopImmediatePropagation();}},true);
});
