import AppKit
import WebKit
import CoreImage

final class LaunchQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var stage="home";var quoteCalls=0;var comboCalls=0;var checkCalls=0;var launchCalls=0
 let orderID="22222222-2222-2222-2222-222222222222",bookOrderID="33333333-3333-3333-3333-333333333333",code="SB"+String(repeating:"B",count:32)
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ message:String)->Never{fputs(message+"\n",stderr);exit(1)}
 func js(_ code:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(code){v,e in if let e=e{self.fail(e.localizedDescription)};done?(v)}}
 func require(_ code:String,_ done:@escaping()->Void){js(code){v in guard v as? Bool==true else{self.fail("Failed: "+code)};done()}}
 func send(_ value:Any,_ done:(()->Void)?=nil){let d=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:d,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.25){self.web.takeSnapshot(with:nil){image,error in guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("No image")};try! png.write(to:self.root.appendingPathComponent(".qa/book-ui/"+name));done()}}}
 func order(_ kind:String,_ state:String)->[String:Any]{["id":kind=="bundle" ? orderID:bookOrderID,"kind":kind,"state":state,"paymentCode":code,"amountVND":kind=="bundle" ? 50000:0,"characters":kind=="bundle" ? 1:5954,"expiresAt":ISO8601DateFormatter().string(from:Date().addingTimeInterval(600)),"done":0,"total":kind=="bundle" ? 0:1,"fundingBundleId":kind=="bundle" ? "":"bundle-qa"]}
 func launch(_ r:[String:Any],paid:Bool){
  var e=fixture["launch"] as! [String:Any];e["event"]="launchResult";e["token"]=r["token"];e["success"]=true
  if stage != "offer"{e["order"]=order("bundle",paid ? "ready":"awaiting_payment")}
  if paid{e["bundle"]=["id":"bundle-qa","used":0,"remaining":5,"expiresAt":"2026-11-01T17:00:00Z"]}
  send(e)
 }
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app");config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));DispatchQueue.main.asyncAfter(deadline:.now()+45){self.fail("Timeout "+self.stage)}
 }
 func verifyQR(_ done:@escaping()->Void){js("(()=>{const r=$('launchQR').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()"){v in
  let r=v as! [String:Double],config=WKSnapshotConfiguration();config.rect=NSRect(x:r["x"]!,y:r["y"]!,width:r["w"]!,height:r["h"]!)
  self.web.takeSnapshot(with:config){image,error in guard let data=image?.tiffRepresentation,let cg=NSBitmapImageRep(data:data)?.cgImage else{self.fail("No QR")}
   let detector=CIDetector(ofType:CIDetectorTypeQRCode,context:nil,options:[CIDetectorAccuracy:CIDetectorAccuracyHigh])!
   let values=detector.features(in:CIImage(cgImage:cg)).compactMap{($0 as? CIQRCodeFeature)?.messageString}
   guard values.contains(VietQR.payload(bin:"970423",account:"0000000000",amount:50000,content:self.code)) else{self.fail("QR amount/code mismatch")};done()
  }
 }}
 func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage){
  guard let r=m.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="init"{send(fixture["models"]!);send(fixture["init"]!){self.js("$('theme').value='light';applyAppearance();")
   self.require("!$('launchBanner').hidden&&$('launchBanner').textContent.includes('50.000')&&!$('launchBanner').textContent.includes('01/11/2026')"){
    guard self.launchCalls==0 else{self.fail("Unexpected automatic network")}
    self.snapshot("launch-home-light.png"){self.js("$('dismissLaunchBanner').click();renderLaunch();");self.require("$('launchBanner').hidden&&localStorage.getItem('windi-launch-banner-dismissed')==='1'"){self.stage="offer";self.js("$('appInfo').click();$('launchWallet').click();")}}
   }
  }}
  if action=="launchInfo"{launchCalls+=1;launch(r,paid:false)
   require("$('launchDialog').open&&!$('launchBuy').disabled&&$('launchDialog').textContent.includes('Lượt chưa dùng sẽ hết hạn')&&$('launchDialog').textContent.includes('01 combo')&&$('launchDialog').scrollWidth<=$('launchDialog').clientWidth"){
    self.snapshot("launch-offer-light.png"){
     self.window.setContentSize(NSSize(width:1000,height:720))
     DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.require("$('launchDialog').scrollWidth<=$('launchDialog').clientWidth&&$('launchBuy').getBoundingClientRect().bottom<=innerHeight"){
      self.snapshot("launch-offer-compact.png"){self.stage="payment";self.js("$('launchBuy').click();")}
     }}
    }
   }
  }
  if action=="launchQuote"{quoteCalls+=1;guard r["requestKey"] as? String != nil,r["snapshot"]==nil,r["amount"]==nil else{fail("Client sent price/book for bundle")};launch(r,paid:false)}
  if action=="bookPaymentQR"&&stage=="payment"{
   guard r["amount"] as? Int==50000 else{fail("Wrong price")}
   let payload=VietQR.payload(bin:"970423",account:"0000000000",amount:50000,content:code),qr=VietQR.vector(VietQR.payload(bin:"970423",account:"0000000000",amount:50000,content:code))!
   guard !payload.isEmpty else{fail("No payload")}
   send(["event":"bookPaymentQR","code":code,"qrPath":qr.path,"qrSize":qr.size])
   js("$('theme').value='dark';applyAppearance();$('launchPayment').scrollIntoView({block:'center'});")
   require("!$('launchPayment').hidden&&$('launchPayAmount').textContent==='50.000đ'&&$('launchQR').querySelector('svg')!==null&&$('launchDialog').contains(document.activeElement)"){
    self.verifyQR{self.snapshot("launch-payment-dark.png"){self.stage="paid";self.js("$('launchCheck').click();")}}
   }
  }
  if action=="launchCheck"{launchCalls+=1;launch(r,paid:true)
   require("$('launchPayment').hidden&&!$('launchBalance').hidden&&$('launchRemaining').textContent==='5'&&$('launchBuy').hidden&&!$('launchUse').hidden"){
    self.snapshot("launch-owned-dark.png"){self.stage="book";self.js("$('launchDialog').close();selectBook('\(((self.fixture["book"] as! [String:Any])["book"] as! [String:Any])["id"] as! String)');")}
   }
  }
  if action=="get"{send(fixture["book"]!){self.js("openBookCloud();")}}
  if action=="bookCloudInfo"{var e=fixture["info"] as! [String:Any];e["event"]="bookCloudInfo";e["token"]=r["token"];e["bookId"]=r["bookId"];e["launchBundle"]=["id":"bundle-qa","used":0,"remaining":5];send(e)
   require("!$('bookCloudCombo').hidden&&$('bookCloudCombo').disabled"){
    self.js("$('bookCloudConsent').checked=true;$('bookCloudConsent').onchange();$('bookCloudCombo').click();")
   }
  }
  if action=="bookCloudCombo"{comboCalls+=1;guard r["consent"] as? Bool==true else{fail("No consent")}
   send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("book","queued"),"bundle":["id":"bundle-qa","used":1,"remaining":4],"trialsRemaining":10,"trialLimit":10])
   require("$('bookCloudLaunchLabel').textContent.includes('4/5')&&$('bookCloudPayment').hidden"){
    self.js("$('bookCloudCombo').click();")
   }
  }
  if action=="bookCloudCheck"{checkCalls+=1;send(["event":"bookCloudResult","token":r["token"]!,"bookId":r["bookId"]!,"success":true,"order":order("book","queued"),"trialsRemaining":10,"trialLimit":10])
   js("$('bookCloudDialog').close();launchState.offer.active=false;renderLaunch();")
   DispatchQueue.main.asyncAfter(deadline:.now()+0.08){self.require("$('launchBuy').hidden&&$('launchUse').hidden&&bookCloudTimer===null&&launchTimer===null"){
    let before=self.launchCalls;DispatchQueue.main.asyncAfter(deadline:.now()+0.4){guard self.quoteCalls==1,self.comboCalls==1,self.checkCalls==1,self.launchCalls==before else{self.fail("Duplicate purchase/redemption/poll")};print("PASS: launch banner, truthful deadline, 50k QR scanned, paid five-book balance, explicit one-slot redemption, repeat checks existing order, expiry, dark/light, focus and zero background requests (native fixtures)");exit(0)}
   }}
  }
 }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=LaunchQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
