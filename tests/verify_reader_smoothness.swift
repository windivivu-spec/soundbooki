import AppKit
import WebKit

// Measures actual painted WebKit frames and the native snapshot round trip.
// Uses only the existing isolated 203-page PDF fixture; no speech or network.
final class SmoothnessQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;let input=Pipe();var buffer=Data();var opened=false;var audited=false
 let turn=EbookTurnBridge()
 lazy var fixture:[String:Any]={let meta=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/reader-ui/latest.json"))) as! [String:String];return try! JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:meta["folder"]!).appendingPathComponent("fixture.json"))) as! [String:Any]}()
 func fail(_ message:String)->Never{fputs(message+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
 func command(_ value:[String:Any]){var d=try! JSONSerialization.data(withJSONObject:value);d.append(10);try! input.fileHandleForWriting.write(contentsOf:d)}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let d=try! JSONSerialization.data(withJSONObject:value);js("receive(\(String(data:d,encoding:.utf8)!))"){_ in done?()}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular)
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":fixture["library"] as! String]){_,new in new};worker.standardInput=input
  let output=Pipe();worker.standardOutput=output;worker.standardError=FileHandle.standardError
  output.fileHandleForReading.readabilityHandler={handle in let data=handle.availableData;DispatchQueue.main.async{self.buffer.append(data);while let r=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<r.lowerBound);self.buffer.removeSubrange(0...r.lowerBound);if let v=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{self.receive(v)}}}}
  try! worker.run()
  let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);window.orderFrontRegardless()
  turn.web=web;turn.emit={[weak self] v in self?.send(v)}
  let ui=ProcessInfo.processInfo.environment["READER_BASELINE"] == "1" ? root.appendingPathComponent(".qa/reader-smoothness/before-ui"):root.appendingPathComponent("ui")
  web.loadFileURL(ui.appendingPathComponent("index.html"),allowingReadAccessTo:root);NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+60){self.fail("Smoothness QA timeout")}
 }
 func receive(_ value:[String:Any]){
  let event=value["event"] as? String ?? "";if event=="error"{fail(String(describing:value))}
  send(value){
   if event=="init"{self.js("selectBook('\(self.fixture["bookID"] as! String)')")}
   if event=="book" && !self.opened{self.opened=true;self.send(["event":"pageTurnSupport","supported":true]);self.js("window.qaLayouts=[];window.qaRectMs=0;window.qaBaseMs=0;window.qaReadyMs=null;const qaDraw=drawEbook;drawEbook=function(d){window.qaDrawAt=performance.now();return qaDraw(d)};const qaRect=Element.prototype.getClientRects;Element.prototype.getClientRects=function(){const t=performance.now(),r=qaRect.call(this);qaRectMs+=performance.now()-t;return r};const qaBase=Element.prototype.getBoundingClientRect;Element.prototype.getBoundingClientRect=function(){const t=performance.now(),r=qaBase.call(this);qaBaseMs+=performance.now()-t;return r};const qaLayout=layoutEbook;layoutEbook=function(v){const t=performance.now();qaLayout(v);const ms=performance.now()-t;if(ms>5)qaLayouts.push(ms);if(ebookPositions.size&&qaReadyMs===null)requestAnimationFrame(()=>{if(qaReadyMs===null)qaReadyMs=performance.now()-qaDrawAt})};$('motion').value='on';$('theme').value='dark';applyAppearance();$('readingMode').click();void 0;")}
   if event=="readerBook" && !self.audited{self.audited=true;self.audit()}
  }
 }
 func audit(_ attempts:Int=100){js("!!ebookData&&ebookPositions.size>0&&!ebookRelayout&&!ebookLayoutPending"){value in
  guard value as? Bool==true else{if attempts>0{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){self.audit(attempts-1)};return};self.fail("PDF did not paginate")}
  self.js("""
  (()=>{
   readerState.follow=false;cancelFlipbookTurn();if(\(ProcessInfo.processInfo.environment["READER_FAST"] == "1" ? "true":"false"))document.documentElement.dataset.motion='off';commitEbookSpread(4,false,'');
   window.qaSmooth={pages:book.pages.length,cues:ebookData.sentences.length,readyMs:qaReadyMs,layouts:qaLayouts,rectMs:qaRectMs,baseMs:qaBaseMs,turns:[],frames:[],start:performance.now(),base:ebookSpread};
   const handle=handleFlipbookEvent;handleFlipbookEvent=function(e){const q=qaSmooth.turns.at(-1);if(q&&e.event==='pageTurnCaptured')q.capture=performance.now()-q.start;if(q&&e.event==='pageTurnStaged')q.stage=performance.now()-q.start;return handle(e)};
   let last=0,waiting=false,nextAt=performance.now()+200;
   function frame(now){
    if(last)qaSmooth.frames.push(now-last);last=now;
    const q=qaSmooth.turns.at(-1);
    if(waiting&&!flipbookTurn){q.total=performance.now()-q.start;q.spread=ebookSpread;waiting=false;nextAt=now+180;}
    if(!waiting&&now>=nextAt){
     if(qaSmooth.turns.length===8){qaSmooth.elapsed=performance.now()-qaSmooth.start;qaSmooth.positions=ebookPositions.size;qaSmooth.domStable=$('ebookFlow').querySelectorAll('[data-cue]').length===ebookData.sentences.length;send({action:'qaDone',report:JSON.stringify(qaSmooth)});return;}
     if(qaSmooth.turns.length===4){commitEbookSpread(Math.floor(ebookCount/ebookColumns*.75),false,'');nextAt=now+180;qaSmooth.turns.push({start:performance.now(),jump:true});waiting=true;requestAnimationFrame(frame);return;}
     qaSmooth.turns.push({start:performance.now()});waiting=true;turnEbook(1);
    }
    requestAnimationFrame(frame);
   }
   requestAnimationFrame(frame);
  })();void 0;
  """)
 }}
 func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage){
  guard let v=message.body as? [String:Any],let action=v["action"] as? String else{return}
  if action=="qaError"{fail(v["message"] as? String ?? "JS error")}
  if action=="qaDone"{
   let report=v["report"] as! String,tag=ProcessInfo.processInfo.environment["READER_PERF_TAG"] ?? "after"
   let result=try! JSONSerialization.jsonObject(with:Data(report.utf8)) as! [String:Any]
   guard result["domStable"] as? Bool==true,result["positions"] as? Int==result["cues"] as? Int else{fail("Reader lost source cues")}
   if ProcessInfo.processInfo.environment["READER_BASELINE"] != "1" {
    let frames=result["frames"] as! [Double],turns=result["turns"] as! [[String:Any]]
    guard (frames.max() ?? 9999)<300,turns.allSatisfy({($0["total"] as? Double ?? 9999)<1500}) else{fail("Reader paint regression: "+report)}
   }
   try! report.write(to:root.appendingPathComponent(".qa/reader-smoothness/"+tag+".json"),atomically:true,encoding:.utf8)
   web.takeSnapshot(with:nil){image,_ in if let t=image?.tiffRepresentation,let p=NSBitmapImageRep(data:t)?.representation(using:.png,properties:[:]){try! p.write(to:self.root.appendingPathComponent(".qa/reader-smoothness/"+tag+".png"))};print(report);self.worker.terminate();exit(0)};return
  }
  if ["beginPageTurn","stagePageTurn","releasePageTurn","endPageTurn","cancelPageTurn"].contains(action){turn.handle(v);return}
  if ["init","get","readerBook","readerImage","readerSettings","position"].contains(action){command(v)}
 }
}
@main struct Main{static func main(){let app=NSApplication.shared,qa=SmoothnessQA();app.delegate=qa;withExtendedLifetime(qa){app.run()}}}
