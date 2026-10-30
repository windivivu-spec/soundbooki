'use strict';
// Scheduling only. Requests go through the native bridge; success is supplied
// only by the worker after signature/device/expiry verification.
class PaymentWatcher {
 constructor({check,cancel=()=>{},state=()=>{},success=()=>{},now=()=>Date.now(),setTimer=(fn,delay)=>globalThis.setTimeout(fn,delay),clearTimer=id=>globalThis.clearTimeout(id),interval=5000,retry=15000,timeout=25000,duration=900000}){
  Object.assign(this,{check,cancel,onState:state,onSuccess:success,now,setTimer,clearTimer,interval,retry,timeout,duration});
  this.generation=0;this.sequence=0;this.visible=true;this.running=false;this.inflight=null;this.timer=null;this.guard=null;
 }
 start(context={}){this.stop();this.context={...context};this.running=true;this.deadline=this.now()+this.duration;this.lastState=null;this.lastMessage=null;this.report('pending');this.schedule(0);}
 report(state,message){if(this.lastState===state&&this.lastMessage===message)return;this.lastState=state;this.lastMessage=message;this.onState(state,message);}
 schedule(delay){this.clearTimer(this.timer);this.timer=null;if(this.running&&this.visible)this.timer=this.setTimer(()=>this.tick(),delay);}
 tick(){
  this.timer=null;if(!this.running||!this.visible||this.inflight)return;
  if(this.now()>=this.deadline){this.running=false;this.report('paused');return;}
  const requestId=`payment-${this.generation}-${++this.sequence}`;this.inflight=requestId;
  this.guard=this.setTimer(()=>{if(this.inflight!==requestId)return;this.cancel(requestId);this.result({requestId,state:'error'});},this.timeout);
  this.check({...this.context,requestId});
 }
 accepts(requestId){return this.running&&this.inflight===requestId;}
 result({requestId,state,message}){
  if(!this.accepts(requestId))return false;
  this.clearTimer(this.guard);this.guard=null;this.inflight=null;
  if(state==='success'){this.stop();this.onSuccess();return true;}
  if(state==='unavailable'){this.stop();this.report('unavailable',message);return true;}
  this.report(state==='error'?'retry':'pending',message);
  this.schedule(state==='error'?this.retry:this.interval);return true;
 }
 checkNow(){if(!this.context)return;if(!this.running){this.running=true;this.deadline=this.now()+this.duration;}if(!this.inflight){this.report('pending');this.schedule(0);}}
 setVisible(value){this.visible=value;this.clearTimer(this.timer);this.timer=null;if(!value&&this.inflight){this.cancel(this.inflight);this.clearTimer(this.guard);this.guard=null;this.inflight=null;}if(value)this.schedule(0);}
 stop(){this.running=false;this.generation++;this.clearTimer(this.timer);this.clearTimer(this.guard);this.timer=null;this.guard=null;if(this.inflight)this.cancel(this.inflight);this.inflight=null;}
}
if(typeof module!=='undefined'&&module.exports)module.exports=PaymentWatcher;
else globalThis.PaymentWatcher=PaymentWatcher;
