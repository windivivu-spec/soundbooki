import AppKit
import WebKit

// Real worker + PDFKit + WebKit. Playback clock events are fixtures: this verifies
// estimated tracking, not speech alignment. No TTS/cloud request is forwarded.
final class ReaderUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;var input=Pipe();var buffer=Data();let renderer=SourcePageRenderer()
 let started=CFAbsoluteTimeGetCurrent();var stage="start";var sourceCalls=0;var originalImage=""
 lazy var folder:URL={let meta=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/reader-ui/latest.json"))) as! [String:String];return URL(fileURLWithPath:meta["folder"]!)}()
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("fixture.json"))) as! [String:Any]
 var bid:String{fixture["bookID"] as! String};var page:Int{fixture["page"] as! Int};var first:Int{fixture["first"] as! Int};var next:Int{fixture["next"] as! Int}
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ s:String,_ next:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};next?(v)}}
 func require(_ s:String,_ next:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};next()}}
 func waitFor(_ expression:String,_ attempts:Int=40,_ next:@escaping()->Void){
  js(expression){value in if value as? Bool==true{next()}else if attempts>0{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){self.waitFor(expression,attempts-1,next)}}else{self.fail("Timed out: "+expression)}}
 }
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
  if event=="readerImage"||event=="readerImageError"{fputs("Image event: \(event) \(value["file"] ?? "")\n",stderr)}
  if event=="error"{fail(String(describing:value))}
  if event=="readerBook"{
   fputs("Reader payload received\n",stderr)
   send(value){
    if self.stage=="epubPage"{DispatchQueue.main.asyncAfter(deadline:.now()+0.5){self.require("ebookData.sentences.some(c=>c.text.includes('Sách có dấu'))&&!$('ebookFlow').textContent.includes('Không chạy mã')&&$('sourceOriginal').disabled&&ebookCount>=1"){self.snapshot("epub-spread.png"){self.command(["action":"shutdown"]);print("PASS: real worker + derived PDF EPUB/images; full-view two-page pagination, page-turn/reduced motion, source/audio highlight, font/TOC/bookmark, compact layout, return to creator and native EPUB");exit(0)}}}}else{self.ebookReady()}
   };return
  }
  if event=="readerPage"{
   renderer.receive(value,library:URL(fileURLWithPath:fixture["library"] as! String)){result in self.send(result){self.pageReady()}};return
  }
  send(value){
   if event=="init"{self.js("selectBook('\(self.bid)');")}
   if event=="book"&&self.stage=="start"{self.stage="first";self.send(["event":"buildInfo","version":"0.8.0","build":"16"]);self.js("$('theme').value='dark';applyAppearance();$('readingMode').click();")}
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
 func ebookReady(){
  guard stage=="first" else{return};stage="ebook"
  DispatchQueue.main.asyncAfter(deadline:.now()+0.8){
   fputs("Ebook first layout: \(CFAbsoluteTimeGetCurrent()-self.started) seconds\n",stderr)
   self.require("!!ebookData&&ebookColumns===2&&ebookCount>20&&$('ebookViewport').clientHeight>300&&getComputedStyle(document.querySelector('.library')).display==='none'&&$('readerBack').getBoundingClientRect().top>30&&document.documentElement.scrollWidth<=innerWidth&&$('ebookViewport').getBoundingClientRect().bottom<$('player').getBoundingClientRect().top&&ebookData.figures.length>0"){
    self.snapshot("ebook-dark.png"){
     self.js("window.qaSpread=ebookSpread;window.qaFlow=$('ebookFlow').firstChild;$('sourceNext').click();")
     self.require("ebookSpread===qaSpread+1&&!readerState.follow&&!flipbookTurn"){
      self.js("loaded=true;playing=true;window.receive({event:'playback',bookId:book.id,segment:index,seconds:9,duration:10,playing:true});")
      self.require("ebookSpread===qaSpread+1&&$('ebookFlow').firstChild===qaFlow&&!!$('ebookFlow').querySelector('.reading-now')"){
       self.js("$('readerPreferences').click();$('sourceFollow').click();$('sourceFont').value='27';$('sourceFont').oninput();$('closeReaderSettings').click();")
       self.require("readerState.follow&&getComputedStyle($('ebookFlow')).fontSize==='27px'&&Math.floor(ebookPositions.get(ebookActive).first/ebookColumns)===ebookSpread"){
        self.js("$('motion').value='off';$('theme').value='light';applyAppearance();cancelFlipbookTurn();turnEbook(1);")
        self.require("!flipbookTurn&&!readerState.follow"){
         self.snapshot("ebook-light-large.png"){
          self.js("$('readerContents').click();$('ebookContents').children[2].click();")
          self.require("!$('readerContentsDialog').open&&!readerState.follow&&readerState.anchor===ebookData.chapters[2].cue"){
           self.window.setContentSize(NSSize(width:1000,height:700))
           DispatchQueue.main.asyncAfter(deadline:.now()+0.4){
            self.require("ebookColumns===2&&document.documentElement.scrollWidth<=innerWidth&&$('ebookViewport').clientHeight>300&&$('sourcePlayPage').getBoundingClientRect().bottom<$('player').getBoundingClientRect().top"){
             self.snapshot("ebook-compact.png"){
              self.window.setContentSize(NSSize(width:1180,height:850))
              self.js("$('theme').value='dark';applyAppearance();readerState.fontSize=21;readerState.follow=false;")
              DispatchQueue.main.asyncAfter(deadline:.now()+0.3){
               self.js("layoutEbook(true);ebookSpread=Math.floor(ebookFigurePositions.get(ebookData.figures[0].file)/ebookColumns);applyEbookSpread();readerState.anchor=ebookFirstVisible()?.id;updateEbookHighlight();")
               DispatchQueue.main.asyncAfter(deadline:.now()+0.6){
                self.js("JSON.stringify({file:ebookData.figures[0].file,col:ebookFigurePositions.get(ebookData.figures[0].file),spread:ebookSpread,pending:[...ebookImagePending],src:ebookFigures.get(ebookData.figures[0].file).img.hasAttribute('src'),width:ebookFigures.get(ebookData.figures[0].file).img.naturalWidth})"){value in fputs("Image state: \(value ?? "")\n",stderr)}
                self.waitFor("ebookFigures.get(ebookData.figures[0].file).img.naturalWidth>0&&[...ebookFigures.values()].filter(v=>v.img.hasAttribute('src')).length<ebookData.figures.length"){
                 self.snapshot("ebook-illustration.png"){
                  self.stage="original";self.js("$('readerPreferences').click();$('sourceOriginal').click();$('closeReaderSettings').click();")
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
     }
    }
   }
  }
 }
 func pageReady(){
  guard stage=="original" else{return};stage="back"
  require("!$('sourcePaper').hidden&&$('sourceImage').naturalWidth>0&&$('ebookViewport').hidden"){
   self.js("$('readerBack').click();")
   self.require("readerState.mode==='create'&&!document.body.classList.contains('reading-mode')&&!$('contentWorkspace').hidden&&getComputedStyle(document.querySelector('.library')).display!=='none'&&document.activeElement===$('readingMode')"){
    self.snapshot("creation-retained.png"){
     self.stage="epubImport";self.js("awaitingImport=true;"){_ in self.command(["action":"import","paths":[self.fixture["epub"] as! String]])}
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
  if ["init","get","readerBook","readerImage","readerPage","readerSettings","deleteBook","restoreBook","position"].contains(action){command(r)}
 }
}
@main struct Main{static func main(){let a=NSApplication.shared;let d=ReaderUIQA();a.delegate=d;withExtendedLifetime(d){a.run()}}}
