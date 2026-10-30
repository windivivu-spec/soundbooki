import AppKit
import WebKit

// Real local worker, covers and EPUB import; no inference or cloud is forwarded.
final class AppShellQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;var input=Pipe();var buffer=Data();var stage="home";var oldBook:[String:Any]?
 lazy var folder=root.appendingPathComponent(".qa/app-shell")
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("fixture.json"))) as! [String:String]
 func fail(_ message:String)->Never{fputs("FAIL [\(stage)] \(message)\n",stderr);worker?.terminate();exit(1)}
 func js(_ source:String,_ next:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};next?(value)}}
 func require(_ source:String,_ next:@escaping()->Void){js(source){value in guard value as? Bool == true else{self.fail(source)};next()}}
 func command(_ value:[String:Any]){var data=try! JSONSerialization.data(withJSONObject:value);data.append(10);try! input.fileHandleForWriting.write(contentsOf:data)}
 func send(_ value:[String:Any],_ next:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in next?()}}
 func snapshot(_ name:String,_ next:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.web.takeSnapshot(with:nil){image,error in guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("snapshot")};try! png.write(to:self.folder.appendingPathComponent(name+".png"));next()}}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular)
  let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:config)
  window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.title="Windi UI QA";window.contentView=web;window.makeKeyAndOrderFront(nil)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":fixture["library"]!]){_,new in new};worker.standardInput=input
  let output=Pipe();worker.standardOutput=output;worker.standardError=FileHandle.standardError
  output.fileHandleForReading.readabilityHandler={h in let data=h.availableData;DispatchQueue.main.async{self.buffer.append(data);while let range=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<range.lowerBound);self.buffer.removeSubrange(0...range.lowerBound);if let value=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{self.receive(value)}}}}
  try! worker.run();DispatchQueue.main.asyncAfter(deadline:.now()+50){self.fail("timeout")}
 }
 func receive(_ value:[String:Any]){
  let event=value["event"] as? String ?? ""
  if event=="error"{fail(String(describing:value))}
  send(value){
   if event=="init"&&self.stage=="home"{
    self.stage="opening"
    self.require("book===null&&!$('empty').hidden&&$('reader').hidden&&books.length>0&&$('home').getAttribute('aria-current')==='page'&&!document.querySelector('.import-options')&&!$('pasteTextDialog')"){
     self.js("$('theme').value='dark';applyAppearance();")
     self.snapshot("home-dark"){self.js("$('books').querySelector('.book-item').click();")}
    }
   }
   if event=="book"&&self.stage=="opening"{self.oldBook=value;self.stage="cover";self.checkCover()}
   if event=="bookCover"&&self.stage=="cover"{self.checkCover()}
   if event=="readerBook"&&self.stage=="reading"{
    self.stage="back"
    self.require("document.body.classList.contains('reading-mode')&&$('ebookFlow').textContent.includes('Tiếng Việt')"){
     self.snapshot("reader-dark"){self.js("$('readerBack').click();$('home').click();"){_ in
      self.send(self.oldBook!){self.require("book===null&&!$('empty').hidden&&!document.body.classList.contains('reading-mode')"){
       self.js("window.receive({event:'job',kind:'audio',bookId:'\(self.fixture["bookID"]!)',running:false});$('appInfo').click();")
       self.require("$('appInfoDialog').open&&$('appBuildBadge').textContent.includes('Build 18')&&$('appInfoDialog').contains($('manageModels'))&&document.activeElement===$('closeAppInfo')"){
        self.snapshot("info-dark"){self.js("$('manageModels').click();")
         self.require("!$('appInfoDialog').open&&!$('modelsPanel').hidden"){
          self.js("$('closeModels').click();$('theme').value='light';applyAppearance();$('motion').value='off';applyAppearance();document.documentElement.dataset.contrast='more';document.documentElement.dataset.transparency='reduced';")
          self.window.setContentSize(NSSize(width:860,height:660))
          self.snapshot("home-light-compact"){self.importEpub()}
         }
        }
       }
      }}
     }}
    }
   }
   if event=="book"&&self.stage=="importing",let book=value["book"] as? [String:Any],book["status"] as? String=="ready"{self.stage="epubCover";self.finishCover()}
   if event=="bookCover"&&self.stage=="epubCover"{self.finishCover()}
  }
 }
 func checkCover(){
  js("!!$('titleCover').querySelector('img')&&$('titleCover').querySelector('img').complete&&$('titleCover').querySelector('img').naturalWidth>0"){value in
   guard self.stage=="cover" else{return};guard value as? Bool==true else{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){if self.stage=="cover"{self.checkCover()}};return}
   self.stage="creation"
   self.send(["event":"buildInfo","version":"0.8.2","build":"18"])
   self.require("!$('reader').hidden&&!$('modelHint').textContent.includes('kHz')&&$('readingLocation')===null&&$('creationMode').textContent.includes('Tạo sách nói')&&$('readingMode').textContent.includes('Đọc sách')&&$('home').getAttribute('aria-current')==='false'"){
    self.js("dirty=true;$('home').click();")
    self.require("book!==null&&$('empty').hidden"){
     self.js("dirty=false;$('toast').hidden=true;")
     self.snapshot("creation-dark"){self.stage="reading";self.js("$('readingMode').click();")}
    }
   }
  }
 }
 func importEpub(){
  require("document.documentElement.scrollWidth<=innerWidth&&$('emptyImport').getBoundingClientRect().bottom<innerHeight"){
   self.js("window.receive({event:'fileDrag',active:true});")
   self.require("document.body.classList.contains('is-file-dragging')&&$('emptyImportLabel').textContent.includes('Thả')"){
    self.stage="importing";self.js("window.receive({event:'fileDrag',active:false});awaitingImport=true;"){_ in self.command(["action":"import","paths":[self.fixture["epub"]!]])}
   }
  }
 }
 func finishCover(){
  js("book?.format==='epub'&&!!$('titleCover').querySelector('img')&&$('titleCover').querySelector('img').naturalWidth>0"){value in
   guard self.stage=="epubCover" else{return};guard value as? Bool==true else{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){if self.stage=="epubCover"{self.finishCover()}};return}
   self.stage="done"
   self.js("$('reader').scrollTop=$('reader').scrollHeight;")
   self.require("$('empty').hidden&&document.documentElement.scrollWidth<=innerWidth&&$('editor').getBoundingClientRect().height>70&&$('player').getBoundingClientRect().bottom<=innerHeight&&$('saveEdit').getBoundingClientRect().bottom<=$('player').getBoundingClientRect().top"){
    self.snapshot("imported-epub-compact"){self.command(["action":"shutdown"]);print("PASS: home selection, stale background update guard, unsaved edit guard, PDF/EPUB native covers, read/back/home, info/model handoff, real EPUB import, dark/light/860x660/reduced motion/contrast");exit(0)}
   }
  }
 }
 func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage){
  guard let value=message.body as? [String:Any],let action=value["action"] as? String else{return}
  if action=="qaError"{fail(value["message"] as? String ?? "JavaScript")}
  if ["init","get","bookCover","readerBook","readerSettings","position","models","cancelListening"].contains(action){command(value)}
 }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=AppShellQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
