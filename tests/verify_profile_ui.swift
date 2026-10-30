import AppKit
import WebKit
final class ProfileQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var stage="profile";var name="";var gets=0
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/book-ui/fixture.json"))) as! [String:Any]
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);exit(1)}
 func js(_ s:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};done?(v)}}
 func require(_ s:String,_ done:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};done()}}
 func send(_ o:Any,_ done:(()->Void)?=nil){let d=try! JSONSerialization.data(withJSONObject:o);js("window.receive(\(String(data:d,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ file:String,_ done:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.15){self.web.takeSnapshot(with:nil){img,error in guard let data=img?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.root.appendingPathComponent(".qa/book-ui/"+file));done()}}}
 func applicationDidFinishLaunching(_ n:Notification){NSApp.setActivationPolicy(.regular);let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app");web=WKWebView(frame:NSRect(x:0,y:0,width:1000,height:720),configuration:c);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true);DispatchQueue.main.asyncAfter(deadline:.now()+30){self.fail("Timeout "+self.stage)}}
 func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage){guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="init"{send(fixture["models"]!);send(fixture["init"]!){self.js("$('theme').value='light';applyAppearance();$('openProfile').focus();$('openProfile').click();")}}
  if action=="profileInfo"||action=="profileSave"{
   if action=="profileSave"{name=r["name"] as! String}
   send(["event":"profileInfo","token":r["token"]!,"name":name,"deviceCode":"SNAAAAAAAAAAAA","trialLimit":5,"trialCharacters":5000,"trialsRemaining":2,"cached":true,"configured":false]){
    if self.stage=="profile"{self.require("$('profileDialog').open&&$('profileQuota').textContent.includes('2/5')&&$('profileState').textContent.includes('chưa mở')"){
     self.snapshot("profile-light.png"){self.stage="saved";self.js("$('profileName').value='Bạn đọc QA';$('saveProfile').click();")}
    }}else if self.stage=="saved"{self.require("$('profileName').value==='Bạn đọc QA'"){
     self.js("$('theme').value='dark';applyAppearance();"){_ in self.snapshot("profile-dark.png"){self.stage="combo";self.js("$('profileCombo').click();")}}
    }}
   }
  }
  if action=="launchInfo" {var e=fixture["launch"] as! [String:Any];e["event"]="launchResult";e["token"]=r["token"];e["success"]=true;send(e){self.require("$('launchDialog').open&&$('launchDialog').textContent.includes('50.000')"){
    let b=(self.fixture["book"] as! [String:Any])["book"] as! [String:Any];self.js("$('launchDialog').close();selectBook('\(b["id"] as! String)');")
   }}}
  if action=="get" {gets+=1;send(fixture["book"]!){if self.gets==1{self.stage="sample";self.js("openBookCloud();")}}}
  if action=="bookCloudInfo" {var info=fixture["info"] as! [String:Any];info["event"]="bookCloudInfo";info["token"]=r["token"];info["bookId"]=r["bookId"];send(info){
    if self.stage=="sample"{self.stage="chapter";self.js("$('bookCloudConsent').checked=true;$('bookCloudChapter').value='one';$('bookCloudChapter').onchange();")}
    else {guard r["chapterId"] as? String=="one" else{self.fail("Wrong sample chapter")};self.require("!$('bookCloudConsent').checked&&$('bookCloudTrial').disabled&&$('bookCloudSample').textContent.length===5000"){
     self.snapshot("pro-chapter-dark.png"){self.js("$('bookCloudConsent').checked=true;renderBookCloud();$('bookCloudTrial').click();")}
    }}
   }}
  if action=="bookCloudTrial"{guard r["chapterId"] as? String=="one",r["consent"] as? Bool==true else{fail("Wrong selected sample")};print("PASS: profile, saved name, cached 2/5 quota, combo entry, light/dark, selected chapter and renewed consent (native fixture)");exit(0)}
 }
}
let app=NSApplication.shared;let delegate=ProfileQA();app.delegate=delegate;app.run()
