/* Soundbooki prelude sound: synthesized locally with Web Audio, no downloads.
   Nothing is audible until a user gesture calls unlock(); browsers block it otherwise. */
(()=>{
  'use strict';
  const AudioCtx=window.AudioContext||window.webkitAudioContext;
  let ctx=null,master=null,reverb=null,dry=null,noiseBuffer=null,pad=null,enabled=false;
  // D major pentatonic, rising: each phrase becomes the next note of a small melody.
  const melody=[587.33,659.25,739.99,880,987.77,1174.66,1318.51];

  function impulse(seconds=2.6,decay=3.2){
    const rate=ctx.sampleRate,length=Math.floor(rate*seconds),buffer=ctx.createBuffer(2,length,rate);
    for(let c=0;c<2;c++){const data=buffer.getChannelData(c);for(let i=0;i<length;i++)data[i]=(Math.random()*2-1)*Math.pow(1-i/length,decay);}
    return buffer;
  }
  function build(){
    if(ctx||!AudioCtx)return !!ctx;
    ctx=new AudioCtx();
    master=ctx.createGain();master.gain.value=0;master.connect(ctx.destination);
    const comp=ctx.createDynamicsCompressor();comp.threshold.value=-18;comp.ratio.value=3;comp.connect(master);
    dry=ctx.createGain();dry.gain.value=.8;dry.connect(comp);
    reverb=ctx.createConvolver();reverb.buffer=impulse();
    const wet=ctx.createGain();wet.gain.value=.55;reverb.connect(wet);wet.connect(comp);
    noiseBuffer=ctx.createBuffer(1,ctx.sampleRate*2,ctx.sampleRate);
    const data=noiseBuffer.getChannelData(0);for(let i=0;i<data.length;i++)data[i]=Math.random()*2-1;
    return true;
  }
  const live=()=>enabled&&ctx&&ctx.state==='running';
  function send(node,toReverb=.6){node.connect(dry);if(toReverb>0){const g=ctx.createGain();g.gain.value=toReverb;node.connect(g);g.connect(reverb);}}

  // Soft glassy bell: sine fundamental plus a quiet inharmonic partial.
  function chime(freq,{gain=.055,decay=2.2,delay=0}={}){
    if(!live())return;
    const t=ctx.currentTime+delay,out=ctx.createGain();
    out.gain.setValueAtTime(0,t);out.gain.linearRampToValueAtTime(gain,t+.012);out.gain.exponentialRampToValueAtTime(.0001,t+decay);
    send(out,.75);
    [[1,1],[2.76,.15],[5.4,.04]].forEach(([ratio,level])=>{
      const osc=ctx.createOscillator(),g=ctx.createGain();
      osc.type='sine';osc.frequency.value=freq*ratio;g.gain.value=level;
      osc.connect(g);g.connect(out);osc.start(t);osc.stop(t+decay+.1);
    });
  }
  // Paper: band-passed noise with a moving centre frequency.
  function rustle({duration=1.4,gain=.028,from=900,to=3200,delay=0}={}){
    if(!live())return;
    const t=ctx.currentTime+delay,src=ctx.createBufferSource(),bp=ctx.createBiquadFilter(),g=ctx.createGain();
    src.buffer=noiseBuffer;src.loop=true;
    bp.type='bandpass';bp.Q.value=.9;bp.frequency.setValueAtTime(from,t);bp.frequency.exponentialRampToValueAtTime(to,t+duration);
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(gain,t+duration*.25);g.gain.exponentialRampToValueAtTime(.0001,t+duration);
    src.connect(bp);bp.connect(g);send(g,.35);src.start(t);src.stop(t+duration+.05);
  }
  function flutter(count=4,spacing=.15,delay=0){
    for(let i=0;i<count;i++)rustle({duration:.2,gain:.016+(i%2)*.006,from:1800+i*250,to:4000,delay:delay+i*spacing+Math.random()*.03});
  }
  // A widening breath of air, used when the scene dissolves into the page.
  function swell({duration=1.5,gain=.024,delay=0}={}){
    if(!live())return;
    const t=ctx.currentTime+delay,src=ctx.createBufferSource(),lp=ctx.createBiquadFilter(),g=ctx.createGain();
    src.buffer=noiseBuffer;src.loop=true;lp.type='lowpass';
    lp.frequency.setValueAtTime(300,t);lp.frequency.exponentialRampToValueAtTime(4800,t+duration*.7);lp.frequency.exponentialRampToValueAtTime(800,t+duration);
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(gain,t+duration*.6);g.gain.exponentialRampToValueAtTime(.0001,t+duration);
    src.connect(lp);lp.connect(g);send(g,.5);src.start(t);src.stop(t+duration+.05);
  }
  function arpeggio(notes=[587.33,739.99,880,1174.66,1479.98],step=.085,gain=.028){notes.forEach((f,i)=>chime(f,{gain,decay:1.9,delay:i*step}));}

  // Warm, quiet pad that holds the scene together (D add9).
  function startPad(level=.016,fade=2.2){
    if(!live()||pad)return;
    const t=ctx.currentTime,out=ctx.createGain(),lp=ctx.createBiquadFilter();
    lp.type='lowpass';lp.frequency.value=1050;lp.Q.value=.4;
    out.gain.setValueAtTime(0,t);out.gain.linearRampToValueAtTime(level,t+fade);
    lp.connect(out);send(out,.7);
    const oscs=[146.83,220,329.63,369.99,440].flatMap((f,i)=>[-4,4].map(cents=>{
      const osc=ctx.createOscillator(),g=ctx.createGain();
      osc.type=i<2?'triangle':'sine';osc.frequency.value=f;osc.detune.value=cents;g.gain.value=i<2?.24:.15;
      osc.connect(g);g.connect(lp);osc.start(t);return osc;
    }));
    const lfo=ctx.createOscillator(),depth=ctx.createGain();lfo.frequency.value=.13;depth.gain.value=220;
    lfo.connect(depth);depth.connect(lp.frequency);lfo.start(t);
    pad={out,oscs:[...oscs,lfo]};
  }
  function stopPad(fade=1.2){
    if(!pad||!ctx)return;
    const t=ctx.currentTime,{out,oscs}=pad;pad=null;
    out.gain.cancelScheduledValues(t);out.gain.setValueAtTime(out.gain.value,t);out.gain.linearRampToValueAtTime(0,t+fade);
    oscs.forEach(o=>{try{o.stop(t+fade+.1);}catch{}});
  }

  window.SoundbookiPreludeSound={
    supported:!!AudioCtx,
    get ctx(){return ctx;},
    get enabled(){return live();},
    unlock(){
      if(!build())return false;
      enabled=true;
      try{
        const p=ctx.resume?.();
        if(p&&typeof p.catch==='function')p.catch(()=>{});
      }catch{}
      const t=ctx.currentTime;master.gain.cancelScheduledValues(t);master.gain.setValueAtTime(master.gain.value,t);master.gain.linearRampToValueAtTime(.24,t+.3);
      return true;
    },
    mute(){
      enabled=false;stopPad(.4);
      if(ctx){const t=ctx.currentTime;master.gain.cancelScheduledValues(t);master.gain.setValueAtTime(master.gain.value,t);master.gain.linearRampToValueAtTime(0,t+.4);}
    },
    suspend(){ctx?.suspend?.();},
    resume(){if(enabled)ctx?.resume?.();},
    startPad,stopPad,chime,rustle,flutter,swell,arpeggio,
    note(index,opts){chime(melody[index%melody.length],opts);}
  };
})();
