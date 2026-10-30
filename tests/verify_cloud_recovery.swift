import AppKit
import WebKit

// A native WebKit fixture: no provider requests, payment or customer-library writes.
final class CloudRecoveryQA: NSObject, NSApplicationDelegate, WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var stage="trial";var creates=0;var checks=0;var requestKey=""
 let oid="11111111-1111-1111-1111-111111111111"
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ message:String)->Never{fputs(message+"\n",stderr);exit(1)}
 func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
 func require(_ source:String,_ done:@escaping()->Void){js(source){value in guard value as? Bool==true else{self.fail("Failed: "+source)};done()}}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ done:@escaping()->Void){web.takeSnapshot(with:nil){image,_ in guard let raw=image?.tiffRepresentation,let png=NSBitmapImageRep(data:raw)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/cloud-repair/"+name+".png"));done()}}
 func order(_ state:String)->[String:Any]{["id":oid,"kind":"trial","state":state,"amountVND":0,"done":state=="ready" ? 1:0,"total":1]}
 var audio:[[String:Any]]{[["audio":root.appendingPathComponent(".qa/book-ui/trial.wav").path,"duration":0.1]]}
 func result(_ request:[String:Any],_ state:String,_ local:Bool=false)->[String:Any]{["event":"bookCloudResult","token":request["token"]!,"bookId":request["bookId"]!,"success":true,"order":order(state),"localReady":local,"trialAudio":local ? audio:[],"trialsRemaining":4,"trialLimit":5,"trialCharacters":5000]}
 func applicationDidFinishLaunching(_ notification:Notification){
  NSApp.setActivationPolicy(.regular);let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+e.filename+':'+e.lineno+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1000,height:720),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"))
  DispatchQueue.main.asyncAfter(deadline:.now()+40){self.fail("Timeout: "+self.stage)}
 }
 func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
  guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
  fputs("bridge \(action) stage \(stage) checks \(checks)\n",stderr)
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="init"{send(fixture["models"] as! [String:Any]);send(fixture["init"] as! [String:Any]){let b=(self.fixture["book"] as! [String:Any])["book"] as! [String:Any];self.js("selectBook('\(b["id"] as! String)');")}}
  if action=="get"{send(fixture["book"] as! [String:Any]){self.js("$('theme').value='dark';applyAppearance();bookCloudPollInterval=500;openBookCloud({mode:'trial',chapterId:'one'});")}}
  if action=="bookCloudInfo"{
   var info=fixture["info"] as! [String:Any];info["event"]="bookCloudInfo";info["token"]=r["token"];info["bookId"]=r["bookId"];info["serviceCheckPending"]=true
   if stage=="cached"{info["savedTrialOrder"]=order("ready");info["trialAudio"]=audio}
   send(info)
  }
  if action=="bookCloudAvailability"{
   if stage=="cached"{
    require("!$('bookCloudTrialPlay').hidden&&$('bookCloudTrial').hidden&&bookCloudLocalReady&&$('bookCloudStatus').textContent.includes('Sách nói')"){
     self.snapshot("sample-ready"){self.stage="history";self.js("book.cloudOrders=[{kind:'trial',order:bookCloudOrder,snapshot:{voice:book.voice}}];$('bookCloudDialog').close();openBookCloud({mode:'trial',chapterId:'one'});")}
    };return
   }
   require("$('bookCloudTrial').disabled&&$('bookCloudBuy').disabled"){
    self.send(["event":"bookCloudAvailability","token":r["token"]!,"bookId":r["bookId"]!,"reachable":true,"trialAvailable":true,"purchaseAvailable":false,"trialsRemaining":4,"trialLimit":5]){
     if self.stage=="trial"{self.require("!$('bookCloudTrial').disabled&&$('bookCloudTrial').textContent.includes('Dùng 1 lượt')") {self.js("$('bookCloudTrial').click();")}}
     else if self.stage=="history"{self.require("!$('bookCloudHistoryWrap').hidden&&$('bookCloudHistoryWrap').getClientRects().length>0&&bookCloudOrder===null") {self.js("$('bookCloudHistory').value='\(self.oid)';$('bookCloudHistory').onchange();")}}
     else{
      self.require("$('bookCloudBuy').disabled&&$('bookCloudBuy').textContent==='Thanh toán sách chưa mở'&&$('bookCloudPayment').hidden&&$('bookCloudStatus').textContent.includes('chưa được mở')&&$('bookCloudDialog').scrollWidth<=$('bookCloudDialog').clientWidth"){
       self.snapshot("purchase-unavailable"){self.js("$('bookCloudConsent').checked=true;requestBookCloud('bookCloudQuote');$('bookCloudDialog').close();"){_ in
        guard self.creates==2,self.checks==4 else{self.fail("Unexpected generation/check count")};print("PASS: native WebKit capability check, timeout keeps request key, accepted/progress/receiving states, automatic audio receipt, cached sample immediately playable, older snapshot recoverable from visible history, paid-unavailable blocks quote (fixtures)");exit(0)
       }}
      }
     }
    }
   }
  }
  if action=="bookCloudQuote"{fail("Closed paid service accepted a quote")}
  if action=="bookCloudTrial"{
   creates+=1
   if creates==1{
    requestKey=r["requestKey"] as! String
    send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":false,"message":"Kết nối gián đoạn. Tiếp tục cùng yêu cầu."]){self.require("bookCloudPhase()==='error'&&$('bookCloudTrial').textContent==='Tiếp tục yêu cầu đã gửi'"){self.js("$('bookCloudTrial').click();")}}
   }else{
    guard creates==2,r["requestKey"] as? String==requestKey else{fail("Retry changed request or duplicated it")}
    send(result(r,"queued")){self.require("$('bookCloudProgressTitle').textContent==='Đang chờ tới lượt'&&!$('bookCloudProgress').hidden&&$('bookCloudTrialSummary').querySelector('fieldset').hidden&&$('bookCloudHeading').textContent==='Mẫu Pro của bạn'"){self.snapshot("sample-accepted") {self.js("checkBookCloud();")}}}
   }
  }
  if action=="bookCloudCheck"{
   checks+=1
   if checks==1{send(result(r,"processing")){self.require("$('bookCloudProgressTitle').textContent==='Đang tạo giọng đọc'&&!$('bookCloudProgressMeter').hidden") {self.js("checkBookCloud();")}}}
   else if checks==2{send(result(r,"ready")){self.require("$('bookCloudProgressTitle').textContent==='Đang nhận audio về Mac'&&$('bookCloudTrialPlay').hidden&&!bookCloudLocalReady") {self.js("if(document.hidden)checkBookCloud();")}}}
   else if checks==3{send(result(r,"ready",true)){self.require("$('bookCloudProgressTitle').textContent==='Mẫu Pro đã sẵn sàng'&&!$('bookCloudTrialPlay').hidden&&$('bookCloudTrial').hidden&&bookCloudTimer===null") {self.stage="cached";self.js("$('bookCloudDialog').close();openBookCloud({mode:'trial',chapterId:'one'});")}}}
   else if checks==4{send(result(r,"ready",true)){self.require("!$('bookCloudTrialPlay').hidden&&$('bookCloudConfirmText').textContent.includes(voiceLabel('pro-cloud',book.voice))") {self.stage="purchase";self.js("$('bookCloudDialog').close();openBookCloud();")}}}
   else{fail("Unbounded polling")}
  }
 }
}
let app=NSApplication.shared
let delegate=CloudRecoveryQA()
app.delegate=delegate
app.run()
