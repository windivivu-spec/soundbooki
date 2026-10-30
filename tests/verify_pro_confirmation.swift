import AppKit
import WebKit

final class ProConfirmationQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var stage="offline";var trialCalls=0;var checks=0
 let orderID="11111111-1111-1111-1111-111111111111"
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ text:String)->Never{fputs(text+"\n",stderr);exit(1)}
 func js(_ text:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(text){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
 func require(_ text:String,_ done:@escaping()->Void){js(text){value in guard value as? Bool==true else{self.fail("Failed: "+text)};done()}}
 func send(_ value:Any,_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.web.takeSnapshot(with:nil){image,error in guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/book-ui/"+name));done()}}}
 func order(_ state:String)->[String:Any]{["id":orderID,"kind":"trial","trialUnits":2,"state":state,"amountVND":0,"done":state=="ready" ? 1:0,"total":1]}
 func applicationDidFinishLaunching(_ note:Notification){
  NSApp.setActivationPolicy(.regular);let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1000,height:720),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+35){self.fail("Timeout: "+self.stage)}
 }
 func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
  guard let request=message.body as? [String:Any],let action=request["action"] as? String else{return}
  if action=="qaError"{fail(request["message"] as? String ?? "JS error")}
  if action=="init"{send(fixture["models"]!);send(fixture["init"]!){let b=(self.fixture["book"] as! [String:Any])["book"] as! [String:Any];self.js("selectBook('\(b["id"] as! String)');")}}
  if action=="get"{send(fixture["book"]!){self.js("$('theme').value='dark';applyAppearance();selectChapter('one');$('quickGenerate').click();")}}
  if action=="bookCloudInfo"{
   guard request["chapterId"] as? String=="one",request["groupTrial"] as? Bool==(stage != "offline" && stage != "single") else{fail("Create did not use the active chapter/group plan")}
   var info=fixture[(stage=="offline" || stage=="single") ? "info":"groupInfo"] as! [String:Any];info["event"]="bookCloudInfo";info["token"]=request["token"];info["bookId"]=request["bookId"];info["configured"]=stage != "offline"
   if stage=="insufficient"{info["trialsRemaining"]=1}
   if stage=="partial"{info["trialUnits"]=4;info["trialChapterCharacters"]=25000;info["trialSelectedCharacters"]=20000;info["trialCompleteChapter"]=false}
   if stage=="saved"{info["savedTrialOrder"]=order("ready");info["trialsRemaining"]=0}
   send(info){
    self.require("$('bookCloudDialog').classList.contains('is-trial-confirmation')&&$('bookCloudDialog').open&&$('bookCloudConfirmText').textContent.includes('Chương 1')&&$('bookCloudConfirmText').textContent.includes(voiceLabel('pro-cloud',book.voice))&&$('bookCloudSample').getClientRects().length===0&&$('bookCloudPrice').getClientRects().length===0&&$('bookCloudBuy').getClientRects().length===0&&$('bookCloudConsent').getClientRects().length===0&&$('bookCloudVoice').getClientRects().length===0&&$('bookCloudDialog').getBoundingClientRect().height<560&&$('bookCloudDialog').scrollWidth<=$('bookCloudDialog').clientWidth"){
     if self.stage=="offline"{
      self.require("$('bookCloudTrial').disabled&&$('bookCloudStatus').textContent.includes('Chưa sử dụng lượt')"){
       self.snapshot("pro-confirm-unavailable.png"){self.stage="single";self.js("$('bookCloudDialog').close();$('theme').value='light';applyAppearance();$('quickGenerate').click();")}
      }
     }else if self.stage=="single"{
      self.require("!$('bookCloudTrial').disabled&&$('bookCloudTrialSingle').checked&&!$('bookCloudTrialChapter').checked&&$('bookCloudTrial').textContent==='Xác nhận · Dùng 1 lượt'&&$('bookCloudConfirmLimit').textContent.includes('Còn 5/5')"){
       self.snapshot("pro-confirm-single.png"){self.stage="insufficient";self.js("$('bookCloudTrialChapter').click();")}
      }
     }else if self.stage=="insufficient"{
      self.require("$('bookCloudTrial').disabled&&$('bookCloudStatus').textContent.includes('Cần 2 lượt')") {self.stage="partial";self.js("$('bookCloudDialog').close();openBookCloud({mode:'trial',chapterId:'one',trialChoice:'chapter'});")}
     }else if self.stage=="partial"{
      self.require("!$('bookCloudTrial').disabled&&$('bookCloudTrial').textContent.includes('Dùng 4 lượt')&&$('bookCloudConfirmLimit').textContent.includes('20.000/25.000')&&!$('bookCloudConfirmLimit').textContent.includes('trọn chương')"){
       self.snapshot("pro-confirm-four-unit-cap.png"){self.stage="connected";self.js("$('bookCloudDialog').close();openBookCloud({mode:'trial',chapterId:'one',trialChoice:'chapter'});")}
      }
     }else if self.stage=="connected"{
      guard self.trialCalls==0 else{self.fail("Opening confirmation spent a trial")}
      self.require("!$('bookCloudTrial').disabled&&!$('bookCloudConsent').checked&&$('bookCloudTrial').textContent==='Xác nhận · Dùng 2 lượt'&&$('bookCloudConfirmLimit').textContent.includes('Trọn chương')"){
       self.snapshot("pro-confirm-ready.png"){self.js("$('bookCloudTrial').click();$('bookCloudTrial').click();")}
      }
     }else if self.stage=="saved"{
      self.require("$('bookCloudTrial').hidden&&bookCloudTimer!==null"){self.js("checkBookCloud();")}
     }
    }
   }
  }
  if action=="bookCloudTrial"{
   trialCalls+=1;guard trialCalls==1,request["chapterId"] as? String=="one",request["trialUnits"] as? Int==2,request["consent"] as? Bool==true,(request["requestKey"] as? String)?.count==32 else{fail("Wrong/duplicate trial submission")}
   send(["event":"bookCloudResult","token":request["token"]!,"bookId":request["bookId"]!,"success":true,"order":order("queued"),"trialsRemaining":3,"trialLimit":5,"trialCharacters":5000]){self.js("checkBookCloud();")}
  }
  if action=="bookCloudCheck"{
   checks+=1;guard trialCalls==1,request["orderId"] as? String==orderID else{fail("Retry did not reuse the order")}
   send(["event":"bookCloudResult","token":request["token"]!,"bookId":request["bookId"]!,"success":true,"order":order("ready"),"trialAudio":[["audio":root.appendingPathComponent(".qa/book-ui/trial.wav").path,"duration":0.1]],"trialsRemaining":3,"trialLimit":5,"trialCharacters":5000]){
    if self.stage=="connected"{self.stage="saved";self.js("$('bookCloudDialog').close();openBookCloud({mode:'trial',chapterId:'one',trialChoice:'chapter'});")}
    else {self.require("!$('bookCloudTrialPlay').hidden") {self.js("$('bookCloudTrialPlay').click();")}}
   }
  }
  if action=="auxPlay"{guard trialCalls==1,checks==2 else{fail("Unexpected calls")};print("PASS: default one-unit choice, explicit grouped choice, five-unit policy, compact confirmation, 2-unit full chapter, 4-unit partial cap, insufficient quota, active chapter/voice, no offline spend, double-click protection, saved group reuse at zero quota (fixtures)");exit(0)}
 }
}
let application=NSApplication.shared
let delegate=ProConfirmationQA()
application.delegate=delegate
application.run()
