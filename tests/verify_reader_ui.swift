import AppKit
import WebKit

// Real worker + PDFKit + WebKit. Playback clock events are fixtures: this verifies
// estimated tracking, not speech alignment. No TTS/cloud request is forwarded.
final class ReaderUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;var input=Pipe();var buffer=Data();let renderer=SourcePageRenderer()
 var stage="start";var sourceCalls=0;var originalImage=""
 lazy var folder:URL={let meta=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/reader-ui/latest.json"))) as! [String:String];return URL(fileURLWithPath:meta["folder"]!)}()
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("fixture.json"))) as! [String:Any]
 var bid:String{fixture["bookID"] as! String};var page:Int{fixture["page"] as! Int};var first:Int{fixture["first"] as! Int};var next:Int{fixture["next"] as! Int}
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ s:String,_ next:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};next?(v)}}
 func require(_ s:String,_ next:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};next()}}
 func command(_ value:[String:Any]){var data=try! JSONSerialization.data(withJSONObject:value);data.append(10);try! input.fileHandleForWriting.write(contentsOf:data)}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ next:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.35){self.web.takeSnapshot(with:nil){img,error in guard let t=img?.tiffRepresentation,let png=NSBitmapImageRep(data:t)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.folder.appendingPathComponent(name));next()}}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);startWorker()
  let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app");c.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:c);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+50){self.fail("Reader QA timed out: "+self.stage)}
 }
 func startWorker(){
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":fixture["library"] as! String]){_,new in new};worker.standardInput=input
  let output=Pipe();worker.standardOutput=output;worker.standardError=FileHandle.standardError
  output.fileHandleForReading.readabilityHandler={h in let data=h.availableData;DispatchQueue.main.async{
   self.buffer.append(data);while let r=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<r.lowerBound);self.buffer.removeSubrange(0...r.lowerBound);if let obj=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{self.receive(obj)}}
  }}
  try! worker.run()
 }
 func receive(_ value:[String:Any]){
  let event=value["event"] as? String ?? ""
  if event=="error"{fail(String(describing:value))}
  if event=="readerPage"{
   renderer.receive(value,library:URL(fileURLWithPath:fixture["library"] as! String)){result in self.send(result){self.pageReady()}};return
  }
  send(value){
   if event=="book"&&self.stage=="start"{self.stage="first";self.send(["event":"buildInfo","version":"0.7.0","build":"15"]);self.js("$('theme').value='dark';applyAppearance();$('readingMode').click();")}
   if event=="bookDeleted"{self.deleted()}
   if event=="bookRestored"{self.stage="restored"}
   if event=="book"&&self.stage=="restored"{
    self.require("book?.id==='\(self.bid)'&&$('empty').hidden&&$('books').querySelectorAll('.book-entry').length===1"){
     self.stage="epubImport";self.js("awaitingImport=true;"){_ in self.command(["action":"import","paths":[self.fixture["epub"] as! String]])}
    }
   }
   if event=="book"&&self.stage=="epubImport",let b=value["book"] as? [String:Any],b["status"] as? String=="ready"{self.stage="epubPage";self.js("$('readingMode').click();")}
  }
 }
 func pageReady(){
  if stage=="epubPage"{
   stage="epubDone"
   require("readerData.format==='epub'&&$('sourceOriginal').disabled&&!$('sourceReflow').hidden&&$('sourcePaper').hidden&&$('sourceReflow').textContent.includes('Sách có dấu')&&!$('sourceReflow').textContent.includes('Không chạy mã')"){
    self.window.setContentSize(NSSize(width:1000,height:700))
    self.snapshot("epub-compact.png"){
     self.require("document.documentElement.scrollWidth<=innerWidth&&$('sourceViewport').clientHeight>80&&$('sourcePlayPage').getBoundingClientRect().bottom<=$('player').getBoundingClientRect().top"){
      self.command(["action":"shutdown"]);print("PASS: real worker + original PDF/highlight, estimated sentence tracking, cached/manual page turns, dark/light, text/font, creation view, delete/cancel/restore, real EPUB import/reflow and compact window (clock fixture only)");exit(0)
     }
    }
   }
  }else if stage=="first"{
   stage="highlight"
   require("readerData.page===\(page)&&!$('sourcePaper').hidden&&$('sourceImage').naturalWidth>0&&$('sourceHighlights').children.length>0&&$('sourceHighlights').firstElementChild.style.width!==''&&document.body.classList.contains('reading-mode')"){
    self.js("window.qaImage=$('sourceImage').src;window.qaCue=readerCue;loaded=true;playing=true;window.receive({event:'playback',bookId:book.id,segment:index,seconds:9,duration:10,playing:true});")
    self.require("readerCue!==qaCue&&$('sourceImage').src===qaImage&&$('sourceHighlights').querySelectorAll('.reading-now').length>0&&$('sourceTracking').textContent.includes('ước lượng')"){
     self.snapshot("original-dark.png"){
      self.stage="manual";self.js("$('sourceNext').click();")
     }
    }
   }
  }else if stage=="manual"{
   stage="follow"
   js("window.receive({event:'playback',bookId:book.id,segment:index,seconds:2,duration:10,playing:true});")
   require("readerState.page===\(page+1)&&readerState.follow===false&&$('sourceTracking').textContent.includes('trang khác')"){
    self.js("$('sourceFollow').click();")
    self.require("readerState.page===\(self.page)&&$('sourceImage').src===qaImage"){
     self.js("playSession='qa-clock';window.receive({event:'advanced',bookId:book.id,sessionId:playSession,fromSegment:index,segment:\(self.next),playing:true});$('sourceText').click();$('sourceFont').value='26';$('sourceFont').oninput();$('theme').value='light';applyAppearance();")
     self.require("readerState.page===\(self.page+1)&&!$('sourceReflow').hidden&&$('sourcePaper').hidden&&$('sourceReflow').style.fontSize==='26px'&&$('sourceReflow').querySelector('.reading-now')!==null"){
      self.snapshot("reflow-light.png"){
       self.js("$('creationMode').click();")
       self.require("!document.body.classList.contains('reading-mode')&&$('sourceReader').hidden&&!$('contentWorkspace').hidden&&$('editor').value.length>0"){
        self.js("$('books').querySelector('.delete-library-book').click();")
        self.require("$('deleteBookDialog').open&&$('deleteBookName').textContent===book.title&&document.activeElement===$('cancelDeleteBook')"){
         self.js("$('cancelDeleteBook').click();")
         self.require("!$('deleteBookDialog').open&&book!==null"){
          self.stage="delete";self.js("$('books').querySelector('.delete-library-book').click();$('confirmDeleteBook').click();")
         }
        }
       }
      }
     }
    }
   }
  }
 }
 func deleted(){
  guard stage=="delete" else{fail("Unexpected delete")};stage="undo"
  let library=URL(fileURLWithPath:fixture["library"] as! String)
  guard !FileManager.default.fileExists(atPath:library.appendingPathComponent(bid).path) else{fail("Deleted folder still in library")}
  require("book===null&&books.length===0&&!$('empty').hidden&&!$('deletedBookNotice').hidden&&$('books').children.length===0"){
   self.snapshot("deleted-light.png"){self.js("$('undoDeleteBook').click();")}
  }
 }
 func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage){
  guard let r=m.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="readerPage"{sourceCalls+=1}
  if ["init","get","readerPage","readerSettings","deleteBook","restoreBook","position"].contains(action){command(r)}
 }
}
@main struct Main{static func main(){let a=NSApplication.shared;let d=ReaderUIQA();a.delegate=d;withExtendedLifetime(d){a.run()}}}
