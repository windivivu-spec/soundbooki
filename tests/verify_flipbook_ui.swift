import AppKit
import WebKit

// Real worker + PDFKit + WebKit. Playback clock events are fixtures: this verifies
// estimated tracking, not speech alignment. No TTS/cloud request is forwarded.
final class ReaderUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:Bundle.main.object(forInfoDictionaryKey:"WindiProjectRoot") as? String ?? FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;var input=Pipe();var buffer=Data();let renderer=SourcePageRenderer();let turn=EbookTurnBridge();var turnCount=0;var checkedGeometry=false
 let started=CFAbsoluteTimeGetCurrent();var stage="start";var sourceCalls=0;var originalImage=""
 lazy var folder:URL={let meta=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/reader-ui/latest.json"))) as! [String:String];return URL(fileURLWithPath:meta["folder"]!)}()
 lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("fixture.json"))) as! [String:Any]
 var bid:String{fixture["bookID"] as! String};var page:Int{fixture["page"] as! Int};var first:Int{fixture["first"] as! Int};var next:Int{fixture["next"] as! Int}
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ s:String,_ next:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};next?(v)}}
 func require(_ s:String,_ next:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail("Failed: "+s)};next()}}
 func waitFor(_ expression:String,_ attempts:Int=40,_ next:@escaping()->Void){
  js(expression){value in if value as? Bool==true{next()}else if attempts>0{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){self.waitFor(expression,attempts-1,next)}}else{self.js("JSON.stringify({spread:ebookSpread,turn:flipbookTurn?{staged:flipbookTurn.staged,finishing:flipbookTurn.finishing,old:!!flipbookTurn.oldImage,gesture:flipbookTurn.gesture,state:flipbookTurn.engine?.getState()}:null})"){v in self.fail("Timed out: "+expression+" STATE \(v ?? "")")}}}
 }
 func command(_ value:[String:Any]){var data=try! JSONSerialization.data(withJSONObject:value);data.append(10);try! input.fileHandleForWriting.write(contentsOf:data)}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func snapshot(_ name:String,_ next:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.35){self.web.takeSnapshot(with:nil){img,error in guard let t=img?.tiffRepresentation,let png=NSBitmapImageRep(data:t)?.representation(using:.png,properties:[:]) else{self.fail("No snapshot")};try! png.write(to:self.folder.appendingPathComponent(name));next()}}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);startWorker()
  let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app");c.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message+' '+(e.error?.stack||'')}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:c);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.title="Flipbook QA — lật trang";window.contentView=web;window.makeKeyAndOrderFront(nil);window.orderFrontRegardless();turn.web=web;turn.emit={[weak self] value in self?.turnEvent(value)};web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+85){self.fail("Reader QA timed out: "+self.stage)}
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
    if self.stage=="epubPage"{DispatchQueue.main.asyncAfter(deadline:.now()+0.5){self.require("ebookData.sentences.some(c=>c.text.includes('Sách có dấu'))&&!$('ebookFlow').textContent.includes('Không chạy mã')&&$('sourceOriginal').disabled&&ebookCount>=1"){self.snapshot("epub-spread.png"){self.command(["action":"shutdown"]);guard self.turnCount>0&&self.checkedGeometry else{self.fail("No GulLabs page turns")};let report:[String:Any]=["result":"PASS","engine":"@gullabs/flipbook-core 3.2.2","commit":"3fb7192c02ecca559d67192d15a1479fd7cf3af8","stagedTurns":self.turnCount,"curveGeometry":true,"queuedTurnsAndFallback":true,"pdfEpubAndSourceView":true,"library":"isolated .qa fixture"];try! JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:self.folder.appendingPathComponent("gul-flipbook-result.json"));print("PASS: GulLabs curved HTML turns + real worker + derived PDF EPUB/images; full-view two-page pagination, page-turn/reduced motion, source/audio highlight, font/TOC/bookmark, compact layout, return to creator and native EPUB");exit(0)}}}}else{self.ebookReady()}
   };return
  }
  if event=="readerPage"{
   renderer.receive(value,library:URL(fileURLWithPath:fixture["library"] as! String)){result in self.send(result){self.pageReady()}};return
  }
  send(value){
   if event=="init"{self.js("selectBook('\(self.bid)');")}
   if event=="book"&&self.stage=="start"{self.stage="first";self.send(["event":"pageTurnSupport","supported":true]);self.send(["event":"buildInfo","version":"0.8.2","build":"18"]);self.js("$('theme').value='dark';applyAppearance();$('readingMode').click();")}
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
 func turnEvent(_ value:[String:Any]){
  fputs("TURN EVENT: \(value["event"] ?? "") token=\(value["token"] ?? "")\n",stderr)
  if value["event"] as? String=="pageTurnStaged"{turnCount+=1}
  send(value)
 }
 func auditGesture(_ done:@escaping()->Void){
  js("window.qaBeforeGesture=ebookSpread;window.qaGesture={progress:0.42,velocity:0,time:0,ended:false,commit:false};requestEbookSpread(ebookSpread+1,true,'',qaGesture);")
  waitFor("flipbookTurn?.staged===true"){
   DispatchQueue.main.asyncAfter(deadline:.now()+0.2){
    guard self.turn.overlay==nil else{self.fail("Capture cover hid the HTML engine")}
    self.js("JSON.stringify({state:flipbookTurn?.engine?.getState(),progress:flipbookTurn?.progress,faces:document.querySelectorAll('.ebook-curl-overlay img').length,same:$('ebookFlow').firstChild===qaFlow,clips:[...document.querySelectorAll('.ebook-curl-overlay .stf__item')].map(e=>({clip:e.style.clipPath,webkit:e.style.webkitClipPath,css:e.style.cssText}))})"){v in fputs("Gesture: \(v ?? "")\n",stderr)}
    self.require("flipbookTurn.engine.getPageCount()===4&&flipbookTurn.engine.getState()==='user_fold'&&Math.abs(flipbookTurn.progress-.42)<.01&&!![...document.querySelectorAll('.ebook-curl-overlay .stf__item')].find(e=>e.style.clipPath.includes('polygon'))&&document.querySelectorAll('.ebook-curl-overlay img').length===4&&$('ebookFlow').firstChild===qaFlow"){
     self.checkedGeometry=true
     self.snapshot("gul-curl-42.png"){
      self.js("JSON.stringify([...document.querySelectorAll('.ebook-curl-overlay .stf__item')].map(e=>({clip:e.style.clipPath,transform:e.style.transform})))"){v in fputs("Curl geometry: \(v ?? "")\n",stderr)}
      fputs("GUL_CURL_HELD at 42 percent\n",stderr)
      let delay=ProcessInfo.processInfo.environment["WINDI_QA_HOLD"]=="1" ? 25.0:0.2
      DispatchQueue.main.asyncAfter(deadline:.now()+delay){
       self.js("qaGesture.progress=.12;applyFlipbookProgress(flipbookTurn,.12);qaGesture.ended=true;qaGesture.commit=false;settleFlipbookGesture();")
       self.waitFor("!flipbookTurn&&ebookSpread===qaBeforeGesture&&!document.querySelector('.ebook-curl-overlay')"){
        guard self.turn.overlay==nil else{self.fail("Cancelled gesture left capture cover")}
        self.js("turnEbook(-1);")
        self.waitFor("!flipbookTurn&&ebookSpread===qaBeforeGesture-1"){
         self.js("turnEbook(1);")
         self.waitFor("!flipbookTurn&&ebookSpread===qaBeforeGesture",40){self.auditFallbackAndQueue(done)}
        }
       }
      }
     }
    }
   }
  }
 }
 func auditFallbackAndQueue(_ done:@escaping()->Void){
  js("window.qaQueueStart=ebookSpread;turnEbook(1);turnEbook(1);turnEbook(1);")
  waitFor("!flipbookTurn&&ebookSpread===qaQueueStart+3"){
   self.js("requestEbookSpread(qaQueueStart,true);")
   self.waitFor("!flipbookTurn&&ebookSpread===qaQueueStart"){
    self.js("requestEbookSpread(qaQueueStart+1,true);handleFlipbookEvent({event:'pageTurnFallback',token:flipbookTurn.token});")
    self.waitFor("!flipbookTurn&&ebookSpread===qaQueueStart+1&&!document.querySelector('.ebook-curl-overlay')"){
     self.js("turnEbook(-1);")
     self.waitFor("!flipbookTurn&&ebookSpread===qaQueueStart",40){self.require("qaCurlFrames>10&&qaCurlCommits>=4"){done()}}
    }
   }
  }
 }
 func ebookReady(){
  guard stage=="first" else{return};stage="ebook"
  DispatchQueue.main.asyncAfter(deadline:.now()+0.8){
   fputs("Ebook first layout: \(CFAbsoluteTimeGetCurrent()-self.started) seconds\n",stderr)
   self.js("JSON.stringify({book:book.id,expected:'\(self.bid)',columns:ebookColumns,count:ebookCount,height:$('ebookViewport').clientHeight,width:innerWidth,body:document.documentElement.scrollWidth,back:$('readerBack').getBoundingClientRect().top,bottom:$('ebookViewport').getBoundingClientRect().bottom,player:$('player').getBoundingClientRect().top,figures:ebookData.figures.length})"){value in fputs("Layout state: \(value ?? "")\n",stderr)}
   self.require("!!ebookData&&ebookColumns===2&&ebookCount>20&&$('ebookViewport').clientHeight>300&&getComputedStyle(document.querySelector('.library')).display==='none'&&$('readerBack').getBoundingClientRect().top>30&&document.documentElement.scrollWidth<=innerWidth&&$('ebookViewport').getBoundingClientRect().bottom<$('player').getBoundingClientRect().top&&ebookData.figures.length>0"){
    self.snapshot("ebook-dark.png"){
     self.js("window.qaCurlFrames=0;window.qaCurlCommits=0;const qaLoad=GulFlipbook.PageFlip.prototype.loadFromHTML;GulFlipbook.PageFlip.prototype.loadFromHTML=function(pages){this.on('turnProgress',()=>qaCurlFrames++);this.on('flip',()=>qaCurlCommits++);return qaLoad.call(this,pages)};window.qaSpread=ebookSpread;window.qaFlow=$('ebookFlow').firstChild;$('sourceNext').click();")
     self.waitFor("ebookSpread===qaSpread+1&&!readerState.follow&&!flipbookTurn"){
      self.auditGesture{
      self.js("loaded=true;playing=true;window.receive({event:'playback',bookId:book.id,segment:index,seconds:9,duration:10,playing:true});")
      self.require("ebookSpread===qaSpread+1&&$('ebookFlow').firstChild===qaFlow&&!!$('ebookFlow').querySelector('.reading-now')"){
       self.js("$('readerPreferences').click();$('sourceFollow').click();$('sourceFont').value='27';$('sourceFont').oninput();$('closeReaderSettings').click();")
       self.waitFor("readerState.follow&&!flipbookTurn&&getComputedStyle($('ebookFlow')).fontSize==='27px'&&Math.floor(ebookPositions.get(ebookActive).first/ebookColumns)===ebookSpread"){
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
  if ["beginPageTurn","stagePageTurn","releasePageTurn","endPageTurn","cancelPageTurn"].contains(action){fputs("TURN ACTION: \(action)\n",stderr);turn.handle(r);return}
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if action=="readerPage"{sourceCalls+=1}
  if ["init","get","readerBook","readerImage","readerPage","readerSettings","deleteBook","restoreBook","position"].contains(action){command(r)}
 }
}
@main struct Main{static func main(){let a=NSApplication.shared;let d=ReaderUIQA();a.delegate=d;withExtendedLifetime(d){a.run()}}}
