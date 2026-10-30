import AppKit
import WebKit
import CoreImage
final class BookUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,WKNavigationDelegate {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var started=false;var stage="trial";var checks=0;var calls=0;var paymentSeen=false
 let orderID="11111111-1111-1111-1111-111111111111",paymentCode="SB"+String(repeating:"A",count:32)
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);exit(1)}
 func js(_ s:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};done?(v)}}
 func require(_ s:String,_ done:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};done()}}
 func send(_ o:Any,_ done:(()->Void)?=nil){let d=try! JSONSerialization.data(withJSONObject:o);js("window.receive(\(String(data:d,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ file:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.web.takeSnapshot(with:nil){image,error in guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/book-ui/"+file));done()}}}
 func verifyQR(_ done:@escaping()->Void){
  js("(()=>{const r=$('bookCloudQR').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()") {v in
   guard let r=v as? [String:Double] else{self.fail("No QR rect")}
   let config=WKSnapshotConfiguration();config.rect=NSRect(x:r["x"]!,y:r["y"]!,width:r["w"]!,height:r["h"]!)
   self.web.takeSnapshot(with:config){img,error in
    guard let data=img?.tiffRepresentation,let cg=NSBitmapImageRep(data:data)?.cgImage else{self.fail("No QR image")}
    let detector=CIDetector(ofType:CIDetectorTypeQRCode,context:nil,options:[CIDetectorAccuracy:CIDetectorAccuracyHigh])!
    let codes=detector.features(in:CIImage(cgImage:cg)).compactMap{($0 as? CIQRCodeFeature)?.messageString}
    guard codes.contains(VietQR.payload(bin:"970423",account:"0000000000",amount:25000,content:self.paymentCode)) else{self.fail("Rendered QR does not scan")};done()
   }
  }
 }
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app")
  c.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+e.filename+':'+e.lineno+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:860),configuration:c);web.navigationDelegate=self;window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+30){self.fail("Timed out stage "+self.stage)}
 }
 func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){fputs("UI loaded\n",stderr);js("({book:book?.id,selected:selectedId,books:books.length})"){v in fputs("State: \(String(describing:v))\n",stderr)}}
 func run(){js("$('theme').value='dark';applyAppearance();bookCloudPollInterval=80;openBookCloud();")}
 func order(_ kind:String,_ state:String)->[String:Any]{return ["id":orderID,"kind":kind,"state":state,"paymentCode":paymentCode,"amountVND":25000,"characters":40000,"done":state=="ready" ? 1:0,"total":1]}
 func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage){
  guard let r=m.body as? [String:Any],let action=r["action"] as? String else{return}
  fputs("bridge \(action) stage \(stage)\n",stderr)
  if action=="generate"{fail("Generation requested before verified checkout")};if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="init"{send(fixture["models"]!);send(fixture["init"]!){
   let book=(self.fixture["book"] as! [String:Any])["book"] as! [String:Any]
   self.js("selectBook('\(book["id"] as! String)');")
  }}
  if action=="get"{send(fixture["book"]!);if !started{started=true;DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.run()}}}
  if action=="bookCloudInfo"{
   var info=fixture["info"] as! [String:Any];info["event"]="bookCloudInfo";info["token"]=r["token"];info["bookId"]=r["bookId"];send(info)
   if stage=="trial"{require("getComputedStyle($('bookCloudDialog')).backgroundColor==='rgb(32, 42, 57)'&&$('bookCloudDialog').open&&$('bookCloudTrial').disabled&&$('bookCloudBuy').disabled&&$('bookCloudVoice').selectedIndex>=0&&$('bookCloudDialog').querySelectorAll('#chapterSelect,#scopeType').length===0&&$('bookCloudSample').textContent.length===bookCloudInfo.trialSelectedCharacters&&$('bookCloudSample').textContent.startsWith('Chương 1.')"){
    self.snapshot("pro-dark.png"){self.js("$('bookCloudConsent').checked=true;$('bookCloudConsent').onchange();$('bookCloudTrial').click();")}
   }}else if stage=="quote"{js("bookCloudPollInterval=1000;$('theme').value='light';applyAppearance();$('bookCloudConsent').checked=true;$('bookCloudConsent').onchange();$('bookCloudBuy').click();")}
  }
  if action=="bookCloudTrial"{
   calls+=1;guard r["consent"] as? Bool==true,r["scope"]==nil,r["chapterId"]==nil else{fail("Trial selection leaked")}
   send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("trial","queued"),"trialsRemaining":4,"trialLimit":5,"trialCharacters":5000])
   js("({hidden:document.hidden,busy:bookCloudBusy,order:bookCloudOrder,modal:$('bookCloudDialog').open,timer:bookCloudTimer})"){v in fputs("Trial state: \(String(describing:v))\n",stderr);self.js("$('bookCloudCheck').click();")}

  }
  if action=="bookCloudCheck"{
   checks+=1
   if stage=="trial"{
    send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("trial","ready"),"trialAudio":[["audio":root.appendingPathComponent(".qa/book-ui/trial.wav").path,"duration":0.1]],"trialsRemaining":4,"trialLimit":5,"trialCharacters":5000])
    require("!$('bookCloudTrialPlay').hidden&&$('bookCloudPayment').hidden&&$('bookCloudQuota').textContent.includes('4/5')&&$('bookCloudQuota').textContent.includes('5.000')") {self.js("$('bookCloudTrialPlay').click();")}
   }else{send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("book",stage=="paid" ? "queued":"awaiting_payment"),"trialsRemaining":4,"trialLimit":5,"trialCharacters":5000])}
  }
  if action=="auxPlay"&&stage=="trial"{stage="quote";DispatchQueue.main.asyncAfter(deadline:.now()+0.15){self.js("stop();openBookCloud();")}}
  if action=="bookCloudQuote"{
   calls+=1;send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("book","awaiting_payment"),"bank":["bin":"970423","name":"QA BANK","account":"0000000000","holder":"QA ONLY"],"trialsRemaining":4,"trialLimit":5,"trialCharacters":5000])
  }
  if action=="bookPaymentQR"{
   if paymentSeen{return};paymentSeen=true
   guard r["amount"] as? Int==25000 else{fail("QR trusted local estimate instead of server quote")}
   let payload=VietQR.payload(bin:"970423",account:"0000000000",amount:25000,content:paymentCode)
   guard let qr=VietQR.vector(payload) else{fail("Invalid QR")}
   send(["event":"bookPaymentQR","code":paymentCode,"qrPath":qr.path,"qrSize":qr.size])
   require("!$('bookCloudPayment').hidden&&$('bookCloudBuy').disabled&&bookCloudOrder.state==='awaiting_payment'&&$('bookCloudPayAmount').textContent==='25.000đ'&&$('bookCloudQR').querySelector('svg')!==null&&getComputedStyle($('bookCloudQR').querySelector('path')).stroke==='none'&&$('bookCloudDialog').scrollWidth<=$('bookCloudDialog').clientWidth&&getComputedStyle($('bookCloudDialog')).backgroundColor==='rgb(247, 249, 252)'&&$('bookCloudDialog').contains(document.activeElement)"){
    self.js("$('bookCloudPayment').scrollIntoView({block:'center'});")
    self.verifyQR{self.snapshot("payment-light.png"){
     self.stage="paid"
     self.js("clearBookCloudPoll();bookCloudPollInterval=60000;window.receive({event:'bookCloudResult',token:bookCloudToken,bookId:book.id,success:true,order:{id:'\(self.orderID)',kind:'book',state:'queued',amountVND:25000,done:0,total:1},trialsRemaining:4,trialLimit:5});") { _ in
      self.require("$('bookCloudPayment').hidden&&$('bookCloudProgressTitle').textContent==='Đang chờ tới lượt'&&$('bookCloudStatus').textContent.includes('Đã thanh toán')") {
       self.js("$('bookCloudDialog').close();"){_ in
      self.stage="closed"
      DispatchQueue.main.asyncAfter(deadline:.now()+0.05){let before=self.checks
       DispatchQueue.main.asyncAfter(deadline:.now()+0.5){guard self.checks==before,self.calls==2 else{self.fail("Unexpected background poll/generation")};self.require("bookCloudTimer===null&&!$('bookCloudDialog').open") {print("PASS: native WebKit, explicit consent, opening sample, trial listen only, scanned 25k QR, paid confirmation before queue, no premature generation, dark/light, focus and stop polling on close (fixtures only)");exit(0)}}
      }
     }
     }}
    }}
   }
  }
 }
}
@main struct Main{static func main(){let a=NSApplication.shared;let d=BookUIQA();a.delegate=d;withExtendedLifetime(d){a.run()}}}
