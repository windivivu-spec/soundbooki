const test=require('node:test');
const assert=require('node:assert/strict');
const PaymentWatcher=require('../ui/payment-watch.js');
function fixture(options={}){
 let clock=0,sequence=0;const timers=new Map(),requests=[],states=[],cancelled=[];let successes=0;
 const watch=new PaymentWatcher({now:()=>clock,setTimer:(fn,delay)=>{const id=++sequence;timers.set(id,{at:clock+delay,fn});return id;},clearTimer:id=>timers.delete(id),check:p=>requests.push(p),cancel:id=>cancelled.push(id),state:s=>states.push(s),success:()=>successes++,...options});
 function advance(ms){const end=clock+ms;for(;;){const next=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];if(!next||next[1].at>end)break;clock=next[1].at;timers.delete(next[0]);next[1].fn();}clock=end;}
 return {watch,requests,states,cancelled,advance,get successes(){return successes;}};
}
test('checks without a button, polls pending and stops on verified success',()=>{
 const f=fixture();f.watch.start();f.advance(0);assert.equal(f.requests.length,1);
 f.watch.result({...f.requests[0],state:'pending'});f.advance(4999);assert.equal(f.requests.length,1);f.advance(1);assert.equal(f.requests.length,2);
 f.watch.result({...f.requests[1],state:'success'});f.advance(60000);assert.equal(f.requests.length,2);assert.equal(f.successes,1);
});
test('closing, hiding and stale replies cannot continue a purchase session',()=>{
 const f=fixture();f.watch.start();f.advance(0);const old=f.requests[0];f.watch.stop();f.advance(10000);assert.equal(f.requests.length,1);assert.deepEqual(f.cancelled,[old.requestId]);
 f.watch.start({afterExpiresAt:'2027-10-20T00:00:00Z'});f.advance(0);assert.equal(f.watch.result({...old,state:'success'}),false);assert.equal(f.successes,0);
 assert.equal(f.requests[1].afterExpiresAt,'2027-10-20T00:00:00Z');f.watch.setVisible(false);f.advance(60000);assert.equal(f.requests.length,2);
 f.watch.setVisible(true);f.advance(0);assert.equal(f.requests.length,3);
});
test('network errors back off, missing replies time out and manual clicks do not overlap',()=>{
 const f=fixture();f.watch.start();f.advance(0);f.watch.checkNow();f.advance(0);assert.equal(f.requests.length,1);
 f.watch.result({...f.requests[0],state:'error'});f.advance(14999);assert.equal(f.requests.length,1);f.advance(1);assert.equal(f.requests.length,2);
 f.advance(25000);assert.equal(f.cancelled.length,1);f.advance(15000);assert.equal(f.requests.length,3);assert.equal(f.successes,0);
});
test('automatic checks expire and can only resume with an explicit action',()=>{
 const f=fixture({duration:10000});f.watch.start();f.advance(0);f.watch.result({...f.requests[0],state:'pending'});f.advance(5000);f.watch.result({...f.requests[1],state:'pending'});
 f.advance(5000);assert.equal(f.states.at(-1),'paused');f.advance(60000);assert.equal(f.requests.length,2);
 f.watch.checkNow();f.advance(0);assert.equal(f.requests.length,3);
});
test('a bad configuration never becomes success and reopening restores waiting feedback',()=>{
 const f=fixture();f.watch.start();f.advance(0);f.watch.result({...f.requests[0],state:'unavailable'});f.advance(60000);assert.equal(f.requests.length,1);assert.equal(f.successes,0);
 f.watch.start();assert.equal(f.states.at(-1),'pending');
});
