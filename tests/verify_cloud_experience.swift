import AppKit
import WebKit

// Native WebKit transport fixtures; no cloud requests or customer-library writes.
final class CloudExperienceQA: NSObject, NSApplicationDelegate, WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var stage="confirm";var creates=0;var checks=0;var plays=0;var key=""
 let oid="11111111-1111-1111-1111-111111111111"
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 var audio:[[String:Any]]{Array(repeating:["audio":root.appendingPathComponent(".qa/book-ui/trial.wav").path,"duration":0.1],count:2)}
 func fail(_ message:String)->Never{fputs(message+"\n",stderr);exit(1)}
 func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
 func require(_ source:String,_ done:@escaping()->Void){js(source){value in guard value as? Bool==true else{self.fail("Failed: "+source)};done()}}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.15){self.web.takeSnapshot(with:nil){image,_ in guard let raw=image?.tiffRepresentation,let png=NSBitmapImageRep(data:raw)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/cloud-experience/"+name+".png"));done()}}}
 func order(_ state:String,_ done:Int=0)->[String:Any]{["id":oid,"kind":"trial","state":state,"amountVND":0,"characters":8462,"done":done,"total":2]}
 func result(_ r:[String:Any],_ state:String,_ done:Int=0,_ local:Bool=false)->[String:Any]{["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order(state,done),"localReady":local,"trialAudio":Array(audio.prefix(done)),"receivedSegments":done,"trialsRemaining":3,"trialLimit":5]}
 func applicationDidFinishLaunching(_ notification:Notification){
  NSApp.setActivationPolicy(.regular);let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1000,height:720),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"))
  DispatchQueue.main.asyncAfter(deadline:.now()+35){self.fail("Timeout: "+self.stage)}
 }
 func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
  guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="init"{send(fixture["models"] as! [String:Any]);send(fixture["init"] as! [String:Any]){let b=(self.fixture["book"] as! [String:Any])["book"] as! [String:Any];self.js("selectBook('\(b["id"] as! String)');")}}
  if action=="get"{send(fixture["book"] as! [String:Any]){self.js("$('theme').value='dark';applyAppearance();bookCloudPollInterval=200;openBookCloud({mode:'trial',chapterId:'one'});")}}
  if action=="bookCloudInfo"{
   var info=fixture["info"] as! [String:Any];info["event"]="bookCloudInfo";info["token"]=r["token"];info["bookId"]=r["bookId"];info["configured"]=true;info["serviceCheckPending"]=false
   if stage=="cached"{info["savedTrialOrder"]=order("ready",2);info["trialAudio"]=audio;info["trialsRemaining"]=0}
   send(info){
    if self.stage=="confirm"{
     self.require("!$('bookCloudTrial').disabled&&$('bookCloudConfirmLimit').textContent.length<100&&parseFloat(getComputedStyle($('bookCloudConfirmLimit')).fontSize)>=14&&$('bookCloudDialog').scrollWidth<=$('bookCloudDialog').clientWidth"){
      self.snapshot("confirm-dark"){self.js("$('bookCloudTrial').click();$('bookCloudTrial').click();")}
     }
    }else{
     self.require("bookCloudLocalReady&&!$('bookCloudTrialPlay').hidden&&$('bookCloudTrial').hidden&&bookCloudTimer===null"){
      self.snapshot("ready-light"){
       self.js("bookCloudOrder.state='processing';bookCloudLocalReady=false;bookCloudChecks=31;bookCloudPollUntil=Date.now()-1;pollBookCloud();") {_ in
        self.require("bookCloudTimer===null&&!$('bookCloudCheck').hidden&&$('bookCloudProgressNote').textContent.includes('Tạm dừng')"){
         self.stage="close";self.js("$('bookCloudCheck').click();")
        }
       }
      }
     }
    }
   }
  }
  if action=="bookCloudTrial"{
   creates+=1
   guard creates==1 else{fail("Repeated synthesis")};key=r["requestKey"] as! String
   send(result(r,"queued")){
    self.require("$('bookCloudTrial').hidden&&$('bookCloudCheck').hidden&&bookCloudTimer!==null"){
     self.js("bookCloudChecks=31;")
    }
   }
  }
  if action=="auxPlay"{plays+=1;guard plays==1 else{fail("Audio restarted when more files arrived")};return}
  if action=="bookCloudCheck"{
   checks+=1;guard r["orderId"] as? String==oid else{fail("Order changed")}
   if stage=="close"{
    guard checks==5,creates==1 else{fail("Unexpected requests")}
    send(result(r,"processing",1)){
     self.js("const oldCloudToken=bookCloudToken;$('bookCloudDialog').close();setTimeout(()=>window.webkit.messageHandlers.app.postMessage({action:'qaClosed',timer:bookCloudTimer===null}),500);")
    };return
   }
   if checks==1{
    send(result(r,"processing")){
     self.require("$('bookCloudTrial').hidden&&$('bookCloudCheck').hidden&&!$('bookCloudProgressMeter').hidden&&!$('bookCloudProgressMeter').hasAttribute('value')"){
      self.snapshot("processing-dark"){}
     }
    }
   }else if checks==2{
    send(result(r,"processing",1)){
     self.require("!$('bookCloudTrialPlay').hidden&&$('bookCloudTrialPlay').textContent==='Nghe phần đầu'&&bookCloudTimer!==null"){
      self.js("$('bookCloudTrialPlay').click();"){_ in self.require("$('bookCloudDialog').open&&$('bookCloudTrialPlay').textContent==='Tạm dừng'"){self.snapshot("partial-dark"){}}}
     }
    }
   }else if checks==3{
    send(["event":"bookCloudProgress","token":r["token"]!,"bookId":r["bookId"]!,"order":order("ready",2),"stage":"receiving","receivedSegments":1,"trialAudio":Array(audio.prefix(1))]){
     self.require("bookCloudPhase()==='receiving'&&!$('bookCloudTrialPlay').hidden"){
      self.send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":false,"message":"Kết nối gián đoạn."]){
       self.require("bookCloudTimer!==null&&!$('bookCloudTrialPlay').hidden&&$('bookCloudProgressNote').textContent.includes('tự kết nối')"){}
      }
     }
    }
   }else if checks==4{
    send(result(r,"ready",2,true)){
     self.require("bookCloudLocalReady&&bookCloudTimer===null&&$('bookCloudCheck').hidden&&$('bookCloudTrialPlay').textContent==='Tạm dừng'&&aux.segments.length===2"){
      self.stage="cached";self.js("$('bookCloudDialog').close();$('theme').value='light';applyAppearance();openBookCloud({mode:'trial',chapterId:'one'});")
     }
    }
   }else{fail("Unexpected polling")}
  }
  if action=="qaClosed"{
   guard r["timer"] as? Bool==true,checks==5,creates==1,plays==1 else{fail("Polling continued after close or audio replayed")}
   print("PASS: automatic receipt beyond 30 checks, indeterminate initial progress, early listening, transfer progress, transient failure recovery, cached audio at zero quota, bounded polling with explicit resume, close stops polling, readable compact dark/light UI (native WebKit fixtures)");exit(0)
  }
 }
}
let app=NSApplication.shared
let delegate=CloudExperienceQA()
app.delegate=delegate
app.run()
