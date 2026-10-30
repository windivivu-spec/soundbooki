/* The supplied recording is the only clock. Audio starts on an explicit click. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const stage = $('ink-stage');
  if (!stage) return;
  const paper=$('ink-paper'), copy=$('ink-copy');
  const effects=$('ink-effects'), media=$('ink-audio'), music=$('ink-music');
  const toggle=$('ink-toggle'), replay=$('ink-replay'), seek=$('ink-seek');
  const phase=$('ink-phase'), caption=$('ink-caption'), time=$('ink-time'), status=$('ink-status');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const segmenter=typeof Intl.Segmenter==='function'?new Intl.Segmenter('vi',{granularity:'grapheme'}):null;
  const glyphs=text=>segmenter?[...segmenter.segment(text)].map(g=>g.segment):Array.from(text.normalize('NFC'));
  const normalize=text=>text.normalize('NFC').toLocaleLowerCase('vi').replace(/[^\p{L}\p{N}]+/gu,'');
  const clamp=n=>Math.max(0,Math.min(1,n));
  const smooth=n=>{n=clamp(n);return n*n*(3-2*n);};
  const hash=(a,b)=>((Math.sin(a*127.1+b*311.7)*43758.5453123)%1+1)%1;
  const label=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  const prelude=$('book-prelude'), particlesHost=$('prelude-particles'), motesHost=$('prelude-motes');
  const preludeSoundBtn=$('prelude-sound'), preludeSoundLabel=$('prelude-sound-label'), bookWrap=$('prelude-book-wrap');
  const doorReplay=$('ink-door-replay');
  let preludeStartFrame=0, preludeFinished=false, silentVisualMode=false;
  const words=[], active=new Map();
  let scoreRows=[];
  let cues=[], descriptors=[], geometry=[], ready=false, frame=0, pending=false, revision=0;
  let voiceStarted=false, leadInTimer=0, musicFadeFrame=0;
  const musicGain=.18;
  let musicFinished=false, musicOutro=false;
  const musicLimit=60, musicOutroLength=3;
  let lastTime=-1, duration=18.08;
  const visual=copy.cloneNode(true);
  visual.removeAttribute('id');visual.setAttribute('aria-hidden','true');visual.classList.add('ink-visual');
  copy.after(visual);copy.classList.add('sr-only');
  function split(node){
    for(const child of [...node.childNodes]){
      if(child.nodeType!==Node.TEXT_NODE){split(child);continue;}
      const fragment=document.createDocumentFragment();
      for(const part of child.textContent.split(/(\s+)/u)){
        if(!part)continue;
        if(/^\s+$/u.test(part)){fragment.append(document.createTextNode(part));continue;}
        const span=document.createElement('span');span.className='ink-word';
        const text=document.createElement('span');text.className='ink-word-text';
        const score=document.createElement('span');score.className='ink-word-score';
        const characters=glyphs(part).map(char=>{const el=document.createElement('span');el.className='ink-char';el.textContent=char;text.append(el);return el;});
        span.append(text,score);
        words.push({node:span,text:part,textLayer:text,score,characters,emphasis:!!node.closest('em')});fragment.append(span);
      }
      child.replaceWith(fragment);
    }
  }
  split(visual);
  const notePaths=[
    '<path d="M16 2v20.5c-1.2-.7-3-.6-4.6.1-2.5 1-3.9 3.2-3.1 4.9s3.4 2.3 5.9 1.2c2.1-.9 3.3-2.5 3.3-4V9c3.7 1.4 5.7 3.1 4.3 7.3C28 10.1 22 6.4 16 2Z"/>',
    '<path d="m7 9 18-5v17c0 2.5-2.8 4.4-5.2 4.4-2.2 0-3.8-1.3-3.8-2.9 0-2.2 3.7-4.4 7-3.2V10L9 14v12c0 2.5-2.8 4.4-5.2 4.4C1.6 30.4 0 29.1 0 27.5c0-2.2 3.7-4.4 7-3.2V9Z"/>',
    '<path d="M18 3v20c0 2.9-3.6 5.5-6.8 5.5-2.6 0-4.5-1.4-4.5-3.4 0-2.8 4.7-5.5 9.2-4.1V3H18Z"/>'
  ];
  const clefs={
    treble:'<path d="M12 32C5 33 2 27 4 22C6 17 18 14 17 7C16 1 12 0 10 5C7 12 11 22 14 33L16 42C17 49 6 51 5 44C4 40 9 38 11 41" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 28C4 20 13 17 17 22C21 27 15 34 9 31" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/><circle cx="8" cy="43" r="2" fill="currentColor"/>',
    bass:'<path d="M5 14C5 5 21 4 18 15C16 23 10 28 4 31" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/><circle cx="6" cy="14" r="3.3" fill="currentColor"/><circle cx="24" cy="12" r="1.6" fill="currentColor"/><circle cx="24" cy="20" r="1.6" fill="currentColor"/>'
  };
  function notation(kind){
    if(kind==='treble')return `<svg class="score-clef" viewBox="0 0 24 52" aria-hidden="true">${clefs.treble}</svg>`;
    if(kind==='bass')return `<svg class="score-bass" viewBox="0 0 28 36" aria-hidden="true">${clefs.bass}</svg>`;
    if(kind==='bar')return '<svg class="score-bar" viewBox="0 0 12 34" aria-hidden="true"><path d="M4 5v25M8 5v25" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>';
    return `<svg viewBox="0 0 30 34" aria-hidden="true">${notePaths[{eighth:0,beamed:1,quarter:2}[kind]]}</svg>`;
  }
  function arrangeScore(){
    scoreRows=[];
    geometry.forEach((p,i)=>{
      let row=scoreRows[scoreRows.length-1];
      if(!row||Math.abs(row.top-p.top)>3){
        row={top:p.top,left:p.x,indices:[]};scoreRows.push(row);
      }
      row.indices.push(i);
    });
    // Allocate a sparse score, then stagger each row across its own text width.
    const budget=Math.min(12,words.length);
    const allocations=scoreRows.map((row,i)=>({row,i,count:Math.floor(budget*row.indices.length/words.length),remainder:(budget*row.indices.length)%words.length}));
    let remaining=budget-allocations.reduce((n,a)=>n+a.count,0);
    for(const item of [...allocations].sort((a,b)=>b.remainder-a.remainder||a.i-b.i)){if(remaining--<=0)break;item.count++;}
    words.forEach(word=>{word.score.dataset.kind='empty';word.score.replaceChildren();});
    allocations.forEach(({row,i:rowIndex,count})=>{
      const available=row.indices.filter(index=>normalize(words[index].text));
      const left=geometry[row.indices[0]].x;
      const last=geometry[row.indices.at(-1)];
      const right=last.x+last.width;
      for(let slot=0;slot<count&&available.length;slot++){
        const fraction=count===1
          ? .5+(hash(rowIndex+1,slot+11)-.5)*.72
          : .05+(slot+.5+(hash(rowIndex+1,slot+11)-.5)*.8)*(.9/count);
        const target=left+(right-left)*fraction;
        const index=available.reduce((best,index)=>Math.abs(geometry[index].x+geometry[index].width/2-target)<Math.abs(geometry[best].x+geometry[best].width/2-target)?index:best,available[0]);
        available.splice(available.indexOf(index),1);
        const word=words[index],p=geometry[index];
        const kind=rowIndex===0&&slot===0?'treble':['eighth','quarter','beamed'][(rowIndex+slot)%3];
        word.score.dataset.kind=kind;
        word.score.innerHTML=`<span class="ink-score-glyph">${notation(kind)}</span>`;
        word.score.style.setProperty('--float-duration',(10+((index*7)%5)*.7)+'s');
        word.score.style.setProperty('--float-delay',(-((index*3)%9)*.9)+'s');
        word.score.style.setProperty('--score-offset-x',(target-p.x-p.width/2).toFixed(2)+'px');
        word.score.style.setProperty('--score-offset-y',((hash(rowIndex+7,slot+3)-.5)*16).toFixed(2)+'px');
        word.score.style.setProperty('--score-tilt',((hash(rowIndex+19,slot+5)-.5)*7).toFixed(2)+'deg');
        word.score.style.setProperty('--score-size',(kind==='beamed'?20:16)+'px');
        word.score.style.setProperty('--score-pitch','0px');
      }
    });
  }

  function clearEffects(){for(const item of active.values())item.node.remove();active.clear();}
  function stopMusic(reset=false){
    if(musicFadeFrame){cancelAnimationFrame(musicFadeFrame);musicFadeFrame=0;}
    musicOutro=false;music.pause();music.volume=0;
    if(reset&&Number.isFinite(music.duration))music.currentTime=0;
  }
  function fadeMusicIn(token){
    if(musicFadeFrame){cancelAnimationFrame(musicFadeFrame);musicFadeFrame=0;}
    music.volume=0;
    const started=performance.now();
    const step=now=>{
      if(token!==revision||music.paused){musicFadeFrame=0;return;}
      const amount=clamp((now-started)/500);
      music.volume=musicGain*smooth(amount);
      if(amount<1)musicFadeFrame=requestAnimationFrame(step);else musicFadeFrame=0;
    };
    musicFadeFrame=requestAnimationFrame(step);
  }
  function fadeMusicOut(){
    if(musicOutro||music.paused||musicFinished)return;
    if(musicFadeFrame)cancelAnimationFrame(musicFadeFrame);
    musicOutro=true;
    const step=()=>{
      if(music.paused){musicFadeFrame=0;musicOutro=false;return;}
      const amount=clamp((music.currentTime-musicLimit)/musicOutroLength);
      music.volume=musicGain*(1-smooth(amount));
      if(amount<1){musicFadeFrame=requestAnimationFrame(step);return;}
      musicFadeFrame=0;musicFinished=true;stopMusic();status.textContent='Đã nghe hết lời chào và đoạn piano.';sync();
    };
    musicFadeFrame=requestAnimationFrame(step);
  }
  music.addEventListener('timeupdate',()=>{if(music.currentTime>=musicLimit)fadeMusicOut();});
  function scheduleVoiceStart(token,delayMs=1000){
    if(leadInTimer)clearTimeout(leadInTimer);
    leadInTimer=window.setTimeout(()=>{
      leadInTimer=0;
      if(token!==revision||media.paused||media.ended)return;
      // The silent pre-roll preserves Safari's user-gesture permission; rewind
      // before unmuting so the supplied word cues still begin at media time 0.
      media.currentTime=0;media.muted=false;voiceStarted=true;status.textContent='Đang nghe lời chào Sound Booki.';sync();
    },delayMs);
  }
  function measure(){
    const rect=paper.getBoundingClientRect();
    const sx=paper.offsetWidth?rect.width/paper.offsetWidth:1,sy=paper.offsetHeight?rect.height/paper.offsetHeight:1;
    geometry=words.map(({node})=>{const r=node.getBoundingClientRect();return {x:(r.left-rect.left)/sx,top:(r.top-rect.top)/sy,y:(r.top-rect.top+r.height*.79)/sy+4,width:r.width/sx,height:r.height/sy};});
    arrangeScore();clearEffects();lastTime=-1;render();
  }
  function makeDescriptors(){
    descriptors=[];
    const spoken=cues.map((cue,index)=>({cue,index})).filter(({cue})=>normalize(cue.word));
    // Emit after 2–4 spoken words. Overlapping, long-lived notes make a quiet
    // continuous atmosphere, without a per-syllable bounce or flashing pulse.
    let previous=-1;
    while(previous+2<spoken.length){
      const from=previous+2,to=Math.min(previous+4,spoken.length-1);
      let chosen=from,best=-Infinity;
      for(let ordinal=from;ordinal<=to;ordinal++){
        const {cue,index}=spoken[ordinal];
        const score=(words[index].emphasis?3:0)+(/[.,!?]$/u.test(cue.word)?2:0)-Math.abs(ordinal-previous-3)*.25;
        if(score>best){best=score;chosen=ordinal;}
      }
      const {cue,index}=spoken[chosen];
      const born=cue.start+.08;
      descriptors.push({id:`b${index}`,type:'bloom',index,born,life:4.5});
      descriptors.push({id:`r${index}`,type:'ring',index,born:born+.18,life:4.8});
      descriptors.push({id:`n${index}`,type:'note',index,born:born+.12,life:4.2+(chosen%3)*.2,ordinal:chosen+1});
      previous=chosen;
    }
  }
  function createEffect(d){
    const p=geometry[d.index];if(!p)return;
    const node=document.createElement('span');node.className=`ink-${d.type==='bloom'?'bloom':d.type==='ring'?'ring':'note'}`;
    node.dataset.word=cues[d.index].word;
    if(d.ordinal)node.dataset.wordOrdinal=String(d.ordinal);
    node.style.left=(p.x+p.width*.5)+'px';node.style.top=(p.y+(d.type==='note'?-22:0))+'px';
    if(d.type==='note')node.innerHTML=`<svg viewBox="0 0 30 34">${notePaths[d.index%3]}</svg>`;
    effects.append(node);
    const item={node};active.set(d.id,item);return item;
  }
  function renderEffects(t){
    const live=new Set();
    for(const d of descriptors){
      const age=t-d.born;if(age<0||age>=d.life)continue;
      live.add(d.id);const item=active.get(d.id)||createEffect(d);if(!item)continue;
      const u=clamp(age/d.life),flow=smooth(u),breath=Math.sin(u*Math.PI);
      // Inline transforms keep paused/seeking frames painted consistently in
      // WebKit, including effects first created by a backwards or forwards seek.
      if(d.type==='note'){
        const drift=d.index%2?14:-16;
        item.node.style.transform=`translate3d(${drift*flow-6}px,${3-32*flow}px,0) scale(${.7+.2*breath}) rotate(${-2+4*flow}deg)`;
        item.node.style.opacity=String(.72*breath);
      }else{
        const sx=.35+(d.type==='bloom'?2.15:2.35)*flow;
        const sy=.35+(d.type==='bloom'?.95:1.5)*flow;
        item.node.style.transform=`scale(${sx},${sy})`;
        item.node.style.opacity=String((d.type==='bloom'?.38:.24)*breath);
      }
    }
    for(const [id,item] of active){if(!live.has(id)){item.node.remove();active.delete(id);}}
  }
  function render(force=false){
    if(!ready)return;
    const t=voiceStarted?media.currentTime:0;if(!force&&t===lastTime)return;lastTime=t;
    let spoken=-1;
    words.forEach((word,i)=>{
      const cue=cues[i],age=t-cue.start,entered=age>=0;
      if(entered)spoken=i;
      // A slow, one-way lift out of a soft veil; no spring, squash or rapid wipe.
      // Onsets follow the supplied cue, while the long settle overlaps the next
      // words and keeps the movement calm even for short spoken syllables.
      const reveal=media.ended||reduced.matches?1:smooth(age/.95);
      const light=entered&&!media.ended?Math.exp(-Math.pow((age-.55)/.8,2))*(word.emphasis?1:.58):0;
      const scoreFade=media.ended||reduced.matches?1:smooth(age/.82);
      word.textLayer.style.opacity=String(reveal);
      word.textLayer.style.transform=`translate3d(0,${(1-reveal)*4}px,0)`;
      word.textLayer.style.filter=reveal>.995?'none':`blur(${(1-reveal)*1.15}px)`;
      word.score.style.opacity=String((1-scoreFade)*.72);
      word.score.style.transform=`translate3d(var(--score-offset-x),calc(var(--score-offset-y) - ${scoreFade*3}px),0) rotate(var(--score-tilt))`;
      word.node.classList.toggle('is-unheard',!entered);
      word.node.style.setProperty('--word-light',String(light));
      word.node.classList.toggle('is-revealing',entered&&age<.95);
      word.characters.forEach(char=>char.classList.toggle('is-written',entered));
    });
    stage.dataset.activeWord=spoken>=0?cues[spoken].word:'';
    stage.dataset.audioTime=t.toFixed(3);
    if(reduced.matches)clearEffects();else renderEffects(t);
    seek.value=String(t);seek.setAttribute('aria-valuetext',`${label(t)} trên ${label(duration)}`);time.textContent=`${label(t)} / ${label(duration)}`;
    phase.textContent=t<2.44?'01 / LỜI CHÀO':t<14.597?'02 / THANH ÂM':'03 / CẢM XÚC';
    caption.textContent=media.ended?(musicFinished?'Một lời chào. Một khoảng để lắng nghe.':'Lời chào khép lại. Piano vẫn ngân nga.'):silentVisualMode?'Chữ và nốt nhạc đang lan tỏa · Bấm Bật tiếng để nghe giọng kể.':t>0?'Lời kể chậm. Câu chữ ngân nga.':'Bật lời chào, để bản nhạc hóa thành lời.';
  }
  function tick(){frame=0;render();if(!media.paused&&!media.ended&&!reduced.matches)frame=requestAnimationFrame(tick);}
  function sync(){
    const playing=(!media.paused&&!media.ended)||!music.paused;
    const musicOnly=media.ended&&!musicFinished&&!silentVisualMode;
    stage.classList.toggle('is-playing',playing);stage.classList.toggle('is-paused',!playing&&media.currentTime>0&&!media.ended);stage.classList.toggle('is-finished',media.ended);
    toggle.textContent=silentVisualMode?'Bật tiếng':playing?'Tạm dừng':musicOnly?'Tiếp tục nhạc':media.ended?'Nghe lại':media.currentTime>0?'Tiếp tục':'Nghe lời chào';
    toggle.setAttribute('aria-label',silentVisualMode?'Bật tiếng lời chào':playing?(musicOnly?'Tạm dừng nhạc nền':'Tạm dừng lời chào'):musicOnly?'Tiếp tục nhạc nền':media.ended?'Nghe lại lời chào':media.currentTime>0?'Tiếp tục lời chào':'Nghe lời chào');
    toggle.setAttribute('aria-pressed',String(playing&&!silentVisualMode));
    if(frame){cancelAnimationFrame(frame);frame=0;}
    render(true);if(playing&&!reduced.matches)frame=requestAnimationFrame(tick);
  }
  async function startSilentVisualGreeting(){
    const request=++revision;
    if(!ready){try{await readyPromise;}catch{return;}if(!ready||request!==revision)return;}
    silentVisualMode=true;
    voiceStarted=true;
    media.currentTime=0;
    media.muted=true;
    clearEffects();
    try{
      await media.play();
      if(request===revision){
        status.textContent='Đang hiển thị lời chào. Bấm Bật tiếng để nghe giọng đọc.';
        sync();
      }
    }catch{
      silentVisualMode=false;
      voiceStarted=false;
      media.muted=false;
      sync();
    }
  }
  async function play(fromStart=false,leadInMs=0,allowSilentFallback=false,keepMusicRunning=false){
    const request=++revision;
    if(leadInTimer){clearTimeout(leadInTimer);leadInTimer=0;}
    if(!ready){try{await readyPromise;}catch{return;}if(!ready||request!==revision)return;}
    if(silentVisualMode){
      silentVisualMode=false;
      fromStart=true;
    }
    if(media.ended&&!fromStart&&!musicFinished){
      document.dispatchEvent(new CustomEvent('soundbooki:audio-start',{detail:{source:'welcome'}}));
      try{await music.play();fadeMusicIn(request);if(music.currentTime>=musicLimit)fadeMusicOut();}catch(error){status.textContent='Chưa phát tiếp được nhạc nền.';}
      sync();return;
    }
    const musicAlreadyPlaying=keepMusicRunning&&!music.paused&&!music.ended;
    if(fromStart||media.ended){
      media.pause();media.currentTime=0;voiceStarted=false;clearEffects();
      if(!musicAlreadyPlaying){stopMusic(true);music.currentTime=0;musicFinished=false;}
    }
    const needsLeadIn=!voiceStarted&&leadInMs>0&&!musicAlreadyPlaying;
    if(needsLeadIn){
      media.currentTime=0;media.muted=true;
    }else{
      if(!voiceStarted)media.currentTime=0;
      voiceStarted=true;media.muted=false;
    }
    document.dispatchEvent(new CustomEvent('soundbooki:audio-start',{detail:{source:'welcome'}}));
    pending=true;status.textContent=needsLeadIn?'Nhạc nền đang dạo nhẹ…':'Đang nghe lời chào Sound Booki.';
    let musicRequest=Promise.resolve();
    if(musicAlreadyPlaying){
      if(!musicFadeFrame&&!musicOutro)music.volume=musicGain;
    }else{
      music.volume=0;
      musicRequest=music.play().then(()=>{
        if(request!==revision)return;
        fadeMusicIn(request);
        if(needsLeadIn)scheduleVoiceStart(request,leadInMs);
      }).catch(error=>{
        if(request!==revision||error.name==='AbortError')return;
        if(allowSilentFallback){
          if(leadInTimer){clearTimeout(leadInTimer);leadInTimer=0;}
          startSilentVisualGreeting();
          return;
        }
        console.warn('Welcome music:',error);
        if(needsLeadIn)scheduleVoiceStart(request,leadInMs);
      });
    }
    try{await media.play();if(request===revision&&!needsLeadIn)status.textContent='Đang nghe lời chào Sound Booki.';}
    catch(error){
      if(request===revision&&error.name!=='AbortError'){
        if(leadInTimer){clearTimeout(leadInTimer);leadInTimer=0;}
        if(allowSilentFallback){
          await startSilentVisualGreeting();
          return;
        }
        media.muted=false;voiceStarted=false;if(!musicAlreadyPlaying)stopMusic(true);status.textContent='Chưa phát được lời chào. Bấm Nghe lời chào để thử lại.';
      }
    }
    finally{if(request===revision){pending=false;sync();}}
    void musicRequest;
  }
  function pause(){
    revision++;pending=false;silentVisualMode=false;
    if(leadInTimer){clearTimeout(leadInTimer);leadInTimer=0;}
    media.pause();media.muted=false;
    if(!voiceStarted)media.currentTime=0;
    stopMusic(!voiceStarted);sync();
  }

  // Articulated covers and curved page shells open around a shared 3D spine.
  const phraseCopy=[...document.querySelectorAll('.prelude-phrase')];
  const constrained=matchMedia('(max-width:760px)').matches||navigator.connection?.saveData||!!(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<=4);
  prelude?.classList.toggle('prelude-lite',constrained);
  // A few quiet notes live outside the book's center, independently of the
  // synchronized word flights. They never participate in the audio timeline.
  const ambientHost=$('prelude-ambient-notes');
  const ambientNotes=[
    {x:8,y:22,kind:'treble',size:24,dx:7,dy:-12,duration:15,tint:'ice'},
    {x:17,y:65,kind:'eighth',size:17,dx:-9,dy:-15,duration:13,tint:'ice'},
    {x:9,y:85,kind:'quarter',size:14,dx:6,dy:-10,duration:16,tint:'warm'},
    {x:91,y:24,kind:'beamed',size:20,dx:-7,dy:-13,duration:14,tint:'ice'},
    {x:81,y:72,kind:'quarter',size:16,dx:8,dy:-11,duration:16,tint:'warm'},
    {x:94,y:50,kind:'eighth',size:17,dx:-6,dy:-16,duration:12,tint:'ice'}
  ];
  if(ambientHost&&!reduced.matches){
    (constrained?[ambientNotes[0],ambientNotes[2],ambientNotes[3],ambientNotes[5]]:ambientNotes).forEach((item,index)=>{
      const note=document.createElement('span');note.className=`ambient-note ambient-note-${item.tint}`;
      note.style.setProperty('--note-x',item.x+'%');note.style.setProperty('--note-y',item.y+'%');
      note.style.setProperty('--note-size',item.size+'px');note.style.setProperty('--note-dx',item.dx+'px');
      note.style.setProperty('--note-dy',item.dy+'px');note.style.setProperty('--note-duration',item.duration+'s');
      note.style.setProperty('--note-delay',(-index*1.7)+'s');
      const glyph=document.createElement('span');glyph.className='ambient-note-glyph';glyph.innerHTML=notation(item.kind);
      note.append(glyph);ambientHost.append(note);
    });
    prelude.classList.toggle('prelude-motion-paused',document.hidden);
  }
  const origins=[[340,250],[650,250],[380,300],[640,300],[320,355],[680,355],[420,380]];
  const preludeFlights=[], preludeMotes=[];
  if(particlesHost&&!reduced.matches){
    phraseCopy.forEach((source,index)=>{
      const root=document.createElement('span');root.className='prelude-flight';
      root.style.setProperty('--px',origins[index][0]/10+'%');
      root.style.setProperty('--py',origins[index][1]/5.8+'%');
      const word=document.createElement('span');word.className='particle-word';word.textContent=source.textContent;
      const ring=document.createElement('span');ring.className='particle-ring';
      const note=document.createElement('span');note.className='particle-note';
      note.innerHTML=notation(['eighth','beamed','quarter','eighth','quarter','beamed','eighth'][index]);
      root.append(word,ring,note);particlesHost.append(root);preludeFlights.push({root,word,ring,note});
    });
  }
  if(motesHost&&!reduced.matches){
    const moteCount=constrained?10:18;
    for(let i=0;i<moteCount;i++){
      const mote=document.createElement('span');
      mote.className=`prelude-mote ${i%3===0?'mote-ice':'mote-gold'}`;
      const mx=21+hash(i,1)*58;
      const my=32+hash(i,2)*38;
      const size=(3.8+hash(i,3)*4.2).toFixed(1)+'px';
      mote.style.setProperty('--mx',mx.toFixed(1)+'%');
      mote.style.setProperty('--my',my.toFixed(1)+'%');
      mote.style.setProperty('--ms',size);
      motesHost.append(mote);
      preludeMotes.push({node:mote,driftX:(hash(i,4)-.5)*(constrained?44:76),rise:82+hash(i,5)*(constrained?68:118),delay:.55+(i%6)*.34+hash(i,6)*.25,duration:2.6+hash(i,7)*1.4});
    }
  }
  const preludeSound=window.SoundbookiPreludeSound||null;
  let preludeMuted=false, mediaPrimed=false;
  if(preludeSound?.supported&&preludeSoundBtn)preludeSoundBtn.hidden=false;
  function syncPreludeSoundUi(){
    if(!preludeSoundBtn)return;
    const active=!preludeMuted&&!!((preludeSound?.enabled&&preludeSound?.ctx?.state==='running')||(!music.paused&&!music.ended));
    preludeSoundBtn.setAttribute('aria-pressed',String(active));
    preludeSoundBtn.classList.toggle('is-active',active);
    preludeSoundBtn.classList.toggle('sound-invite',!active&&!preludeMuted);
    if(preludeSoundLabel)preludeSoundLabel.textContent=active?'Đang phát âm thanh':'Bật âm thanh';
  }
  function startPreludeMusic(reset=false){
    if(!music||preludeMuted)return;
    if(reset){
      if(musicFadeFrame){cancelAnimationFrame(musicFadeFrame);musicFadeFrame=0;}
      musicOutro=false;musicFinished=false;
      try{music.currentTime=0;}catch{}
    }
    if(!music.paused&&!music.ended){
      if(!musicFadeFrame&&music.volume<musicGain*.8)fadeMusicIn(revision);
      syncPreludeSoundUi();
      return;
    }
    music.volume=0;
    document.dispatchEvent(new CustomEvent('soundbooki:audio-start',{detail:{source:'welcome'}}));
    music.play().then(()=>{
      fadeMusicIn(revision);
      syncPreludeSoundUi();
    }).catch(()=>{
      syncPreludeSoundUi();
    });
  }
  function primeVoiceForHero(){
    if(mediaPrimed||!media||!media.paused||voiceStarted)return;
    mediaPrimed=true;
    media.muted=true;
    media.play().then(()=>{
      if(!preludeFinished&&prelude&&!prelude.classList.contains('is-hidden')){
        media.pause();
        media.currentTime=0;
      }
    }).catch(()=>{mediaPrimed=false;});
  }
  function unlockPreludeSound(withImmediateChime=false){
    preludeMuted=false;
    preludeFromClick=true;
    if(preludeSound?.supported){
      try{
        preludeSound.unlock();
        if(preludeSound.ctx&&preludeSound.ctx.state!=='running'){
          preludeSound.ctx.resume().then(syncPreludeSoundUi).catch(()=>{});
        }
      }catch{}
    }
    if(prelude&&!prelude.classList.contains('is-hidden')){
      startPreludeMusic(false);
      primeVoiceForHero();
      if(withImmediateChime&&preludeSound?.supported){
        preludeSound.startPad(.015,1.2);
        preludeSound.chime(587.33,{gain:.035,decay:1.7});
      }
    }
    syncPreludeSoundUi();
  }
  function mutePreludeSound(){
    preludeMuted=true;
    preludeFromClick=false;
    preludeSound?.mute();
    if(prelude&&!prelude.classList.contains('is-hidden'))stopMusic(true);
    syncPreludeSoundUi();
  }
  let preludeTl=null,preludeFromClick=false,preludePrepared=false,preludeRevealed=false;
  let preparation=0,bookModel=null;
  function positionPageForReveal(){
    let target=null;
    try{target=location.hash?$(decodeURIComponent(location.hash.slice(1))):null;}catch{/* Ignore a malformed fragment. */}
    if(target)target.scrollIntoView({behavior:'auto',block:'start'});
    else window.scrollTo({top:0,left:0,behavior:'auto'});
    preludeRevealed=true;
  }
  function cancelPreludeStart(){
    if(preludeStartFrame){cancelAnimationFrame(preludeStartFrame);preludeStartFrame=0;}
  }
  function finishPrelude(){
    preludeFinished=true;
    preludeSound?.stopPad(.45);
    document.body.classList.add('prelude-entered');
    if(!preludeRevealed)positionPageForReveal();
    prelude?.classList.add('is-hidden');
    document.documentElement.classList.remove('prelude-pending');
    if(prelude)prelude.dataset.phase='complete';
    for(const {root} of preludeFlights)root.style.willChange='';
    for(const {node} of preludeMotes)node.style.willChange='';
    if(bookWrap)bookWrap.style.transform='';
    document.dispatchEvent(new CustomEvent('soundbooki:prelude-end'));
    measure();
  }
  function skipPrelude(){
    preparation++;cancelPreludeStart();preludeTl?.kill();preludeTl=null;
    preludeSound?.stopPad(.2);
    finishPrelude();
    if(!document.hidden&&!preludeMuted)play(true,0,true,true);
  }
  function tryOpportunisticPreludeAudio(){
    if(preludeMuted)return;
    try{
      preludeSound?.unlock();
      if(preludeSound?.ctx?.state==='running')preludeFromClick=true;
    }catch{}
    startPreludeMusic(true);
    syncPreludeSoundUi();
  }
  function buildPreludeTimeline(){
    if(!window.gsap||!prelude)return null;
    preludeTl?.kill();
    const gsap=window.gsap;
    prelude.classList.remove('is-hidden');prelude.dataset.phase='ready';
    document.body.classList.remove('prelude-entered');
    document.documentElement.classList.add('prelude-pending');
    document.dispatchEvent(new CustomEvent('soundbooki:prelude-start'));
    // Keep initialization unpainted; never reveal the open pose before closing.
    gsap.set(prelude,{autoAlpha:1});
    gsap.set('#prelude-book-wrap',{autoAlpha:0,y:14,scale:.95,rotation:0});
    if(!bookModel&&window.SoundbookiBookOpening)bookModel=window.SoundbookiBookOpening.mount($('book-model'),{lowPower:constrained});
    bookModel?.draw(0);
    gsap.set('.prelude-light-blue',{xPercent:0,yPercent:0,scale:1});
    gsap.set('.prelude-light-ice',{xPercent:0,yPercent:0,scale:1});
    gsap.set('.prelude-horizon',{rotation:-13,scale:.9});
    gsap.set('#prelude-book-shadow',{scaleX:.5,autoAlpha:.65});
    gsap.set('.spine-beam',{autoAlpha:0,scaleY:.38,scaleX:.72});
    gsap.set('.spine-bloom',{autoAlpha:0,scale:.55});
    preludeFlights.forEach(({root,word,ring,note})=>{
      root.style.transform='none';word.style.opacity='0';ring.style.opacity='0';note.style.opacity='0';
    });
    preludeMotes.forEach(({node})=>{
      gsap.set(node,{x:0,y:0,scale:.4,autoAlpha:0});
    });
    const book=$('prelude-book-wrap').getBoundingClientRect();
    preludeRevealed=false;
    preludeTl=gsap.timeline({paused:true,onComplete:()=>{
      finishPrelude();
      if(!document.hidden&&!preludeMuted)play(true,0,true,true);
    }});
    preludeTl
      .call(()=>{
        prelude.dataset.phase='opening';
        startPreludeMusic(false);
        preludeSound?.startPad(.015,1.8);
        preludeSound?.rustle({duration:1.35,gain:.026});
      },[],.06)
      .call(()=>{preludeSound?.flutter(4,.16);},[],.72)
      .call(()=>{preludeSound?.arpeggio([587.33,739.99,880,1174.66],.09,.024);},[],2.1)
      .to({open:0},{open:1,duration:2.35,ease:'power2.inOut',onUpdate:function(){bookModel?.draw(this.targets()[0].open);}},.06)
      .to('#prelude-book-wrap',{y:0,scale:1,duration:2.35,ease:'power2.out'},.06)
      .to('#prelude-book-wrap',{y:-10,scale:1.024,rotation:-.45,duration:2.9,ease:'sine.inOut'},2.45)
      .to('#prelude-book-wrap',{y:-3,scale:1.046,rotation:.35,duration:2.7,ease:'sine.inOut'},5.35)
      .to('#prelude-book-shadow',{scaleX:1.05,autoAlpha:1,duration:2.4,ease:'sine.inOut'},0)
      .to('#prelude-book-shadow',{scaleX:.92,autoAlpha:.82,duration:2.9,ease:'sine.inOut'},2.45)
      .to('.spine-beam',{autoAlpha:.92,scaleY:1,scaleX:1,duration:1.95,ease:'sine.out'},.48)
      .to('.spine-bloom',{autoAlpha:.88,scale:1.08,duration:2.1,ease:'sine.out'},.48)
      .to('.spine-beam',{autoAlpha:.62,scaleY:1.12,scaleX:1.18,duration:3.2,yoyo:true,repeat:1,ease:'sine.inOut'},2.45)
      .to('.spine-bloom',{autoAlpha:1,scale:1.24,duration:2.8,yoyo:true,repeat:1,ease:'sine.inOut'},2.45)
      .to('.prelude-horizon',{rotation:-9,scale:1.05,duration:8.2,ease:'sine.inOut'},0)
      .to('.prelude-light-blue',{xPercent:4,yPercent:-3,scale:1.08,duration:8,ease:'sine.inOut'},0);
    if(!constrained)preludeTl.to('.prelude-light-ice',{xPercent:-4,yPercent:3,scale:1.06,duration:8,ease:'sine.inOut'},0);
    preludeMotes.forEach(({node,driftX,rise,delay,duration:moteDur},i)=>{
      preludeTl.fromTo(node,
        {x:0,y:8,scale:.35,autoAlpha:0},
        {
          x:driftX,y:-rise,scale:1.15+(i%3)*.18,autoAlpha:.86,
          duration:moteDur,ease:'sine.out',
          onStart:()=>{node.style.willChange='transform, opacity';},
          onComplete:()=>{node.style.willChange='';}
        },
        delay
      ).to(node,{autoAlpha:0,y:-rise-28,scale:.45,duration:.95,ease:'sine.in'},delay+moteDur-.65);
    });
    preludeFlights.forEach(({root,word,ring,note},index)=>{
      const driver={progress:0},direction=index%2?1:-1;
      const desiredTravel=Math.min(330,book.height*.78)*(1+(index%3-1)*.07);
      const availableRise=Math.max(24,book.top+book.height*origins[index][1]/580-28);
      const travel=Math.min(desiredTravel,availableRise);
      const bend=Math.min(102,book.width*.13);
      const points=[[direction*bend*.85,-travel*.26],[-direction*bend*.34,-travel*.7],[direction*bend*.64,-travel]];
      const startAt=2.4+index*.32;
      preludeTl.call(()=>{
        preludeSound?.note(index,{gain:.042,decay:2.1});
      },[],startAt+.64);
      preludeTl.to(driver,{
        progress:1,duration:3.6+(index%3)*.18,ease:'sine.inOut',
        onStart:()=>{root.style.willChange='transform';},
        onUpdate:function(){
          const t=driver.progress,m=1-t;
          const elapsed=this.time()/this.duration();
          const sway=Math.sin(t*Math.PI*2.4+index)*direction*7*smooth((t-.18)/.25);
          const x=3*m*m*t*points[0][0]+3*m*t*t*points[1][0]+t*t*t*points[2][0]+sway;
          const y=3*m*m*t*points[0][1]+3*m*t*t*points[1][1]+t*t*t*points[2][1];
          root.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0) rotate(${(direction*5.5*t).toFixed(2)}deg)`;
          word.style.opacity=String(smooth(elapsed/.06)*(1-smooth((t-.21)/.17))*.96);
          const ringProgress=clamp((t-.18)/.26);
          const ringAlpha=smooth((t-.18)/.08)*(1-smooth((t-.26)/.2));
          ring.style.opacity=String((ringAlpha*.78).toFixed(3));
          ring.style.transform=`translate(-50%,-50%) scale(${(.35+ringProgress*1.85).toFixed(3)})`;
          const noteEnter=smooth((t-.22)/.17);
          const noteExit=1-smooth((t-.74)/.26);
          const notePop=1+.22*Math.sin(clamp((t-.22)/.24)*Math.PI);
          note.style.opacity=String((noteEnter*noteExit*.92).toFixed(3));
          note.style.transform=`translate(-50%,-50%) scale(${((.62+.42*noteEnter)*notePop).toFixed(3)}) rotate(${(Math.sin(t*9+index)*8).toFixed(1)}deg)`;
        },
        onComplete:()=>{root.style.willChange='';}
      },startAt);
    });
    preludeTl
      .call(()=>{prelude.dataset.phase='unfolding';},[],1.15)
      .call(()=>{prelude.dataset.phase='flying';},[],2.4)
      .call(()=>{prelude.dataset.phase='morphing';},[],3.4)
      .call(()=>{prelude.dataset.phase='notes';},[],5.4)
      .call(()=>{
        preludeSound?.swell({duration:1.1,gain:.022});
        preludeSound?.stopPad(1.0);
      },[],7.7)
      .call(()=>{prelude.dataset.phase='reveal';positionPageForReveal();},[],8.05)
      .to(prelude,{autoAlpha:0,duration:.85,ease:'sine.inOut'},8.05);
    gsap.set('#prelude-book-wrap',{autoAlpha:1});
    preludePrepared=true;
    return preludeTl;
  }
  function queuePreludeStart(){
    cancelPreludeStart();
    if(document.hidden)return;
    preludeStartFrame=requestAnimationFrame(()=>{
      preludeStartFrame=0;
      startPrelude(preludeFromClick);
    });
  }
  function preparePrelude(fromClick=false){
    const token=++preparation;preludeFromClick=fromClick;preludePrepared=false;
    if(reduced.matches||!window.gsap){finishPrelude();return;}
    if(fromClick)unlockPreludeSound(false);
    else tryOpportunisticPreludeAudio();
    if(token!==preparation||preludeFinished)return;
    buildPreludeTimeline();
    queuePreludeStart();
  }
  function startPrelude(fromClick=false){
    if(fromClick)unlockPreludeSound(true);
    if(preludeFinished||document.hidden)return;
    if(!preludePrepared){preparePrelude(fromClick);return;}
    cancelPreludeStart();preludeFinished=true;preludeFromClick=fromClick||preludeFromClick;
    preludeTl.play(0);
  }
  function replayPrelude(){
    preparation++;cancelPreludeStart();preludeTl?.kill();pause();clearEffects();lastTime=-1;render(true);
    preludeFinished=false;preludeRevealed=false;preludeMuted=false;mediaPrimed=false;
    prelude.classList.remove('is-hidden');
    document.documentElement.classList.add('prelude-pending');
    window.scrollTo({top:0,left:0,behavior:'auto'});
    preparePrelude(true);
  }
  if(prelude){
    if(reduced.matches||!window.gsap)finishPrelude();else preparePrelude(false);
    const unlockOnFirstGesture=event=>{
      if(preludeMuted)return;
      if(event.target?.closest?.('#prelude-sound')||event.target?.closest?.('#prelude-skip'))return;
      if(!prelude.classList.contains('is-hidden')){
        unlockPreludeSound(false);
      }else if(silentVisualMode){
        play(true,0,false,!music.paused);
      }
    };
    for(const evt of ['pointerdown','touchstart','keydown'])document.addEventListener(evt,unlockOnFirstGesture,{passive:true});
    preludeSoundBtn?.addEventListener('click',event=>{
      event.stopPropagation();
      const active=!preludeMuted&&!!((preludeSound?.enabled&&preludeSound?.ctx?.state==='running')||(!music.paused&&!music.ended));
      if(active)mutePreludeSound();
      else unlockPreludeSound(true);
    });
    prelude.addEventListener('click',event=>{
      if(event.target.closest('#prelude-skip')||event.target.closest('#prelude-sound'))return;
      unlockPreludeSound(false);
      if(!preludeFinished)startPrelude(true);
    });
    if(!constrained&&bookWrap){
      prelude.addEventListener('pointermove',event=>{
        if(prelude.classList.contains('is-hidden')||reduced.matches)return;
        const nx=(event.clientX/Math.max(1,window.innerWidth)-.5)*2;
        const ny=(event.clientY/Math.max(1,window.innerHeight)-.5)*2;
        window.gsap?.to(bookWrap,{x:nx*12,rotationY:nx*3.2,rotationX:-ny*2.4,duration:.65,overwrite:'auto',ease:'sine.out'});
      },{passive:true});
    }
    $('prelude-skip')?.addEventListener('click',skipPrelude);
    doorReplay?.addEventListener('click',replayPrelude);
    document.addEventListener('keydown',event=>{
      if(prelude.classList.contains('is-hidden'))return;
      if(event.key==='Escape')skipPrelude();
      else if(event.key==='m'||event.key==='M')unlockPreludeSound(true);
    });
    document.addEventListener('visibilitychange',()=>{
      prelude.classList.toggle('prelude-motion-paused',document.hidden);
      if(prelude.classList.contains('is-hidden'))return;
      if(document.hidden){cancelPreludeStart();preludeTl?.pause();preludeSound?.suspend();}
      else if(preludeFinished&&preludeTl){preludeTl.resume();preludeSound?.resume();}
      else if(preludePrepared)queuePreludeStart();
    });
    reduced.addEventListener('change',()=>{if(reduced.matches&&!prelude.classList.contains('is-hidden'))skipPrelude();});
  }
  paper?.addEventListener('click',()=>{if(silentVisualMode)play(true,0,false,!music.paused);});
  toggle.addEventListener('click',()=>{if(silentVisualMode)play(true,0,false,!music.paused);else if(!media.paused||!music.paused||pending)pause();else play(false,0,false,!music.paused);});
  replay.addEventListener('click',()=>play(true,0,false,false));
  seek.addEventListener('input',()=>{if(Number.isFinite(media.duration)){media.currentTime=Number(seek.value);clearEffects();render(true);}});
  media.playbackRate=.95;media.preservesPitch=true;
  for(const event of ['play','pause','ended','seeking','seeked','loadedmetadata'])media.addEventListener(event,()=>{
    if(Number.isFinite(media.duration)){duration=media.duration;seek.max=String(duration);seek.disabled=!ready;}
    if(event==='ended'){
      if(silentVisualMode){silentVisualMode=false;media.muted=false;musicFinished=true;status.textContent='Lời chào đã hiện đầy đủ. Bấm Nghe lại để nghe giọng đọc và piano.';}
      else status.textContent='Đã nghe hết lời chào. Piano tiếp tục đến một phút rồi dịu dần.';
    }
    else if((event==='pause'||event==='seeked')&&media.paused&&!media.ended)status.textContent=media.currentTime>0?'Đã tạm dừng lời chào.':'Lời chào sẵn sàng.';
    sync();
  });
  media.addEventListener('timeupdate',()=>{if(reduced.matches||media.paused)render(true);});
  media.addEventListener('error',()=>{pause();status.classList.remove('sr-only');status.textContent='Chưa tải được lời chào. Hãy thử lại khi kết nối sẵn sàng.';});
  document.addEventListener('soundbooki:audio-start',event=>{if(event.detail?.source!=='welcome')pause();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  window.addEventListener('pagehide',pause);
  if('IntersectionObserver' in window)new IntersectionObserver(entries=>{if(!entries[0].isIntersecting&&(!media.paused||!music.paused))pause();},{threshold:.1}).observe(stage);
  new MutationObserver(()=>{if(document.querySelector('dialog[open]')&&(!media.paused||!music.paused))pause();}).observe(document.body||document.documentElement,{subtree:true,attributes:true,attributeFilter:['open']});
  reduced.addEventListener('change',()=>{stage.classList.toggle('ink-static',reduced.matches);clearEffects();sync();});
  if('ResizeObserver' in window)new ResizeObserver(measure).observe(paper);else window.addEventListener('resize',measure);
  const readyPromise=Promise.all([document.fonts.ready,fetch('assets/audio/welcome-cues.json').then(r=>{if(!r.ok)throw Error('Missing welcome timing');return r.json();})]).then(([,data])=>{
    if(!Array.isArray(data.words)||data.words.length!==words.length)throw Error('Welcome timing word count mismatch');
    data.words.forEach((cue,i)=>{
      if(normalize(cue.word)!==normalize(words[i].text)||!Number.isFinite(cue.start)||!Number.isFinite(cue.end)||cue.end<cue.start||(i&&cue.start<data.words[i-1].start))throw Error('Invalid welcome cue at '+i);
    });
    cues=data.words;duration=Number.isFinite(media.duration)?media.duration:data.duration;
    ready=true;toggle.disabled=false;replay.disabled=false;seek.disabled=!Number.isFinite(media.duration);seek.max=String(duration);
    makeDescriptors();measure();stage.classList.add('ink-ready');stage.classList.toggle('ink-static',reduced.matches);status.textContent='Lời chào sẵn sàng. Bấm Nghe lời chào để bắt đầu.';sync();
  }).catch(error=>{
    stage.classList.add('ink-static');status.classList.remove('sr-only');status.textContent='Chưa chuẩn bị được phần nghe lời chào. Vui lòng tải lại trang.';console.error('Welcome animation:',error);
  });
})();
