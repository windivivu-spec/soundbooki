import AppKit
import WebKit
final class WalkthroughQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler{
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var network=0;var reloading=false;var explicitPro=false;var allowPick=false;var pickCalls=0;var audioStarts=0;var audioStops=0;var audioMutes=0
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);exit(1)}
 func js(_ s:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(String(describing:e))};done?(v)}}
 func check(_ s:String,_ done:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("FAIL: "+s)};done()}}
 func send(_ e:Any,_ done:@escaping()->Void){let d=try! JSONSerialization.data(withJSONObject:e);js("window.receive(\(String(data:d,encoding:.utf8)!))"){_ in done()}}
 func snapshot(_ name:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+1.8){self.web.takeSnapshot(with:nil){image,error in guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:])else{self.fail("snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/book-ui/tour-"+name+".png"));done()}}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app");config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+e.filename+':'+e.lineno+':'+e.colno+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));DispatchQueue.main.asyncAfter(deadline:.now()+75){self.fail("Timeout")}
 }
 func pages(_ i:Int,_ dark:Bool){
  if i==5{if !dark{js("$('theme').value='dark';applyAppearance();");window.setContentSize(NSSize(width:1000,height:720));pages(0,true)}else{gestures()};return}
  js("walkthroughPage=\(i);renderWalkthrough();")
  check("$('walkthroughDialog').open&&$('walkthroughCount').textContent==='\(i+1) / 5'&&document.querySelectorAll('.tour-step[aria-current=step]').length===1&&$('walkthroughDialog').scrollWidth<=$('walkthroughDialog').clientWidth&&$('walkthroughNext').getBoundingClientRect().bottom<=innerHeight&&$('walkthroughDialog').contains(document.activeElement)"){
   self.snapshot("\(i+1)-\(dark ? "dark":"light")"){self.pages(i+1,dark)}
  }
 }
 func gestures(){
  guard audioStarts==1,audioStops==0 else{fail("Paging restarted welcome audio")}
  js("$('walkthroughSound').click();")
  check("walkthroughMuted&&$('walkthroughSound').getAttribute('aria-pressed')==='true'&&localStorage.getItem('windi-walkthrough-muted')==='true'"){}
  js("$('walkthroughSound').click();")
  js("setWalkthroughPage(0);document.querySelectorAll('.tour-step')[2].click();")
  check("walkthroughPage===2&&$('walkthroughDialog').getAnimations({subtree:true}).length>0"){
   self.js("$('walkthroughBack').click();$('walkthroughNext').click();")
   self.check("walkthroughPage===2"){
    self.js("window.tourPointer=(type,x,y)=>tourSurface.dispatchEvent(new PointerEvent(type,{pointerId:9,isPrimary:true,button:0,clientX:x,clientY:y,bubbles:true}));tourPointer('pointerdown',300,100);tourPointer('pointermove',200,103);tourPointer('pointerup',200,103);")
    self.check("walkthroughPage===3"){
     self.js("tourPointer('pointerdown',300,100);tourPointer('pointermove',290,210);tourPointer('pointerup',290,210);")
     self.check("walkthroughPage===3"){
      self.js("tourPointer('pointerdown',200,100);tourPointer('pointermove',300,101);tourPointer('pointerup',300,101);tourSurface.dispatchEvent(new WheelEvent('wheel',{deltaX:80,deltaY:2,cancelable:true}));tourSurface.dispatchEvent(new WheelEvent('wheel',{deltaX:80,deltaY:2,cancelable:true}));")
      self.check("walkthroughPage===3"){
       self.js("document.documentElement.dataset.motion='off';setWalkthroughPage(4);")
       self.check("walkthroughPage===4&&$('walkthroughNext').textContent==='Nghe Sách của bạn Ngay'&&$('walkthroughDialog').getAnimations({subtree:true}).length===0"){
        self.js("setWalkthroughPage(5);document.documentElement.dataset.motion='system';")
        self.check("walkthroughPage===4"){self.finish()}
       }
      }
     }
    }
   }
  }
 }
 func finish(){
  js("walkthroughPage=2;renderWalkthrough();$('walkthroughDialog').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));")
  check("walkthroughPage===3"){
   self.js("$('walkthroughSkip').click();")
   self.check("!$('walkthroughDialog').open&&localStorage.getItem(walkthroughKey)==='seen'&&document.activeElement===$('openWalkthroughHome')"){
    self.allowPick=true;self.js("$('openWalkthroughHome').click();$('walkthroughDialog').dispatchEvent(new Event('cancel',{cancelable:true}));openWalkthrough();walkthroughPage=4;renderWalkthrough();$('walkthroughNext').click();")
    self.check("!$('walkthroughDialog').open&&awaitingImport"){
     self.js("openAppInfo();$('openWalkthroughInfo').click();")
     self.check("$('walkthroughDialog').open&&!$('appInfoDialog').open"){
      self.js("finishWalkthrough();const oldNow=Date.now;Date.now=()=>Date.parse('2026-11-03T00:00:00Z');openWalkthrough();walkthroughPage=4;renderWalkthrough();Date.now=oldNow;void 0;")
      self.check("!$('walkthroughBody').textContent.includes('50.000')&&$('walkthroughBody').textContent.includes('đã kết thúc')"){
       self.snapshot("expired-dark"){
        self.js("finishWalkthrough();");self.reloading=true;self.web.reload()
       }
      }
     }
    }
   }
  }
 }
 func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage){
  guard let r=m.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaError"{fail(r["message"] as? String ?? "error")}
  if action=="walkthroughAudio"{
   let op=r["operation"] as? String ?? ""
   if op=="start"{audioStarts+=1}else if op=="stop"{audioStops+=1}else if op=="mute"{audioMutes+=1}else{fail("Unknown welcome command")}
   guard r["path"]==nil,r["volume"]==nil else{fail("UI cannot send arbitrary media or gains")}
   send(["event":"walkthroughAudio","token":r["token"] ?? "","success":true,"active":op != "stop","muted":r["muted"] ?? false]){};return
  }
  if action=="pick"&&allowPick{pickCalls+=1;guard pickCalls==1 else{fail("Duplicate picker")};return}
  if action=="launchInfo"&&explicitPro{network+=1;check("$('launchDialog').open&&!$('walkthroughDialog').open"){
   guard self.network==1,self.pickCalls==1,self.audioStarts==6,self.audioStops==6,self.audioMutes==2 else{self.fail("Unexpected request count")};print("PASS: five concise pages light/dark, native WebKit compact layout, entrance animations, dots, pointer swipes both directions, vertical scroll retained, trackpad debounce, reduced motion, keyboard, final explicit file picker, skip/reopen/persistence/expiry, no automatic cloud/payment/generation; explicit Pro CTA; local welcome starts once per opening, mute preference, stop on every exit");exit(0)
  };return}
  if action.hasPrefix("launch")||action.hasPrefix("bookCloud")||["generate","readerListen","voicePreview","pick"].contains(action){network+=1;fail("Unexpected action: "+action)}
  if action=="init"{
   send(fixture["models"]!){var e=self.fixture["init"] as! [String:Any];e["books"]=[];self.send(e){
    if self.reloading{self.check("!$('walkthroughDialog').open"){
      guard self.network==0 else{self.fail("Network")};self.explicitPro=true;self.js("openWalkthrough();walkthroughPage=4;renderWalkthrough();$('walkthroughPro').click();")
    }}else{self.js("$('theme').value='light';applyAppearance();");self.check("$('walkthroughDialog').open&&walkthroughPage===0"){self.pages(0,false)}}
   }}
  }
 }
}
@main struct Main{static func main(){let app=NSApplication.shared;let d=WalkthroughQA();app.delegate=d;withExtendedLifetime(d){app.run()}}}
