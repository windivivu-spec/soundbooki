import AppKit
import WebKit

// Native WebKit fixture QA. No actual upload, generation or user-library writes.
final class ProcessingQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var web:WKWebView!;var window:NSWindow!;var started=false;var cancelled=false;var resumed=false
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/processing-ui/fixture.json"))) as! [String:Any]
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);exit(1)}
 func js(_ s:String,_ next:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};next?(v)}}
 func require(_ s:String,_ next:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};next()}}
 func send(_ o:Any){let data=try! JSONSerialization.data(withJSONObject:o);js("window.receive(\(String(data:data,encoding:.utf8)!))")}
 func snapshot(_ name:String,_ next:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.web.takeSnapshot(with:nil){img,error in
  guard let d=img?.tiffRepresentation,let p=NSBitmapImageRep(data:d)?.representation(using:.png,properties:[:]) else{self.fail("No UI snapshot")}
  try! p.write(to:self.root.appendingPathComponent(".qa/processing-ui/"+name));next()
 }}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app")
  c.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:c);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+40){self.fail("Processing UI timed out")}
 }
 func run(){
  js("$('theme').value='dark';$('motion').value='off';applyAppearance();book.status='importing';jobs.import=book.id;render();window.receive({event:'processing',bookId:book.id,phase:'extract',done:71,total:203,elapsedSeconds:7});")
  require("!$('importStatus').hidden&&$('importText').textContent==='Đang đọc chữ và bố cục'&&Math.abs($('importProgress').value-.8*71/203)<.001&&$('importDetail').textContent.includes('71/203')&&$('contentWorkspace').getAttribute('aria-busy')==='true'&&$('editor').disabled"){
   self.snapshot("extract-dark.png"){
    self.js("window.qaEditor=$('editor').value;window.qaPanel=$('importStatus');window.receive({event:'processing',bookId:book.id,phase:'layout',done:101,total:203,elapsedSeconds:22});")
    self.require("$('importText').textContent.includes('ghép dòng')&&$('importProgress').value>.89&&$('editor').value===qaEditor&&$('importStatus')===qaPanel&&document.querySelector('[data-phase=layout]').getAttribute('aria-current')==='step'"){
     self.js("window.receive({event:'processing',bookId:book.id,phase:'layout',done:130,total:203,elapsedSeconds:31});$('importAction').focus();")
     self.require("$('importDetail').textContent.includes('cần thêm thời gian')&&$('importElapsed').textContent.includes('31')&&document.activeElement===$('importAction')"){
      self.snapshot("layout-dark.png"){
       self.js("$('importAction').click();"){_ in
        guard self.cancelled else{self.fail("Cancel did not reach native bridge")}
        self.js("delete jobs.import;book.status='paused';render();")
        self.require("$('importAction').textContent==='Tiếp tục xử lý'&&$('importDetail').textContent.includes('Đã lưu')&&$('contentWorkspace').getAttribute('aria-busy')==='false'"){
         self.js("$('importAction').click();"){_ in
          guard self.resumed else{self.fail("Resume did not reach native bridge")}
          self.js("book.status='ready';render();$('theme').value='light';applyAppearance();selectChapter(book.sections[1].id);")
          self.require("$('importStatus').hidden&&!$('editor').disabled&&activeSection().number===1&&$('editor').value.startsWith('1')&&!$('editor').value.includes('Bắt đầu nào!')&&scopeIndices({type:'chapter',chapterId:activeSection().id}).join(',')===activeSection().indices.join(',')"){
           self.window.setContentSize(NSSize(width:1000,height:700))
           self.snapshot("chapter-light-compact.png"){
            self.require("document.documentElement.scrollWidth<=innerWidth&&$('editor').getBoundingClientRect().height>=55&&$('quickGenerate').getBoundingClientRect().bottom<=innerHeight"){
             print("PASS: native WebKit loading, actual progress, elapsed time, over-30s explanation, cancel/resume bridge, dark/light, compact window, exact mid-page chapter selection (fixtures only)");exit(0)
            }
           }
          }
         }
        }
       }
      }
     }
    }
   }
  }
 }
 func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage){
  guard let r=m.body as? [String:Any],let a=r["action"] as? String else{return}
  if a=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if a=="init"{send(fixture["models"]!);send(fixture["init"]!);send(["event":"buildInfo","version":"0.6.5","build":"14"])}
  if a=="get"{send(fixture["book"]!);if !started{started=true;DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.run()}}}
  if a=="cancel"&&r["kind"] as? String=="import"{cancelled=true}
  if a=="resume"{resumed=true}
 }
}
@main struct Main{static func main(){let a=NSApplication.shared;let d=ProcessingQA();a.delegate=d;withExtendedLifetime(d){a.run()}}}
