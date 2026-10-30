import AppKit
import WebKit

// Real worker + selected private PDF fixture. No inference or cloud actions.
final class ReaderPerformanceQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;let input=Pipe();var buffer=Data();var opened=false
 lazy var fixture: [String:Any] = {
  let meta=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/reader-ui/latest.json"))) as! [String:String]
  return try! JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:meta["folder"]!).appendingPathComponent("fixture.json"))) as! [String:Any]
 }()
 func fail(_ message:String)->Never{fputs(message+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
 func command(_ value:[String:Any]){var d=try! JSONSerialization.data(withJSONObject:value);d.append(10);try! input.fileHandleForWriting.write(contentsOf:d)}
 func send(_ value:[String:Any],_ done:(()->Void)?=nil){let d=try! JSONSerialization.data(withJSONObject:value);js("receive(\(String(data:d,encoding:.utf8)!))"){_ in done?()}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular)
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":fixture["library"] as! String]){_,new in new};worker.standardInput=input
  let output=Pipe();worker.standardOutput=output;worker.standardError=FileHandle.standardError
  output.fileHandleForReading.readabilityHandler={handle in let data=handle.availableData;DispatchQueue.main.async{
   self.buffer.append(data);while let r=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<r.lowerBound);self.buffer.removeSubrange(0...r.lowerBound);if let v=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{self.receive(v)}}
  }};try! worker.run()
  let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app")
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:config);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
  web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+45){self.fail("Reader performance QA timeout")}
 }
 func receive(_ value:[String:Any]){
  let event=value["event"] as? String ?? "";if event=="error"{fail(String(describing:value))}
  send(value){
   if event=="init"{self.js("selectBook('\(self.fixture["bookID"] as! String)')")}
   if event=="book" && !self.opened{self.opened=true;self.js("window.qaDrawMs=0;window.qaLayoutMs=0;const d=drawEbook,l=layoutEbook;drawEbook=function(v){const t=performance.now();d(v);qaDrawMs+=performance.now()-t};layoutEbook=function(v){const t=performance.now();l(v);qaLayoutMs+=performance.now()-t};$('readingMode').click();void 0;")}
   if event=="readerBook"{self.audit()}
  }
 }
 func audit(_ attempts:Int=80){js("!!ebookData&&ebookPositions.size>0&&!ebookRelayout"){value in
  guard value as? Bool==true else{if attempts>0{DispatchQueue.main.asyncAfter(deadline:.now()+0.1){self.audit(attempts-1)};return};self.fail("PDF did not paginate")}
  self.js("""
  (()=>{
   readerState.follow=false;document.documentElement.dataset.motion='off';
   const t=performance.now();for(let i=0;i<100;i++)renderReader();const ticks=performance.now()-t;
   const p=performance.now();for(let i=0;i<40;i++)commitEbookSpread(i%Math.min(10,Math.ceil(ebookCount/ebookColumns)),true,'');const turns=performance.now()-p;
   const segments=book.segments,key=ebookSignature(),originalText=$('ebookFlow').textContent;
   book.segments=segments.map((s,i)=>i?s:{...s,text:s.text+' QA correction'});const invalidated=ebookSignature()!==key;book.segments=segments;
   const restored=ebookSignature()===key;
   $('appLanguage').value='en';$('appLanguage').onchange();
   const translated=$('import').textContent.trim()==='Add a book',protectedText=$('ebookFlow').textContent===originalText;
   $('appLanguage').value='vi';$('appLanguage').onchange();
   return JSON.stringify({pages:book.pages.length,cues:ebookData.sentences.length,drawMs:qaDrawMs,layoutMs:qaLayoutMs,render100Ms:ticks,turn40Ms:turns,invalidated,restored,translated,protectedText});
  })()
  """){result in
   let json=result as! String,d=json.data(using:.utf8)!,report=try! JSONSerialization.jsonObject(with:d) as! [String:Any]
   for key in ["invalidated","restored","translated","protectedText"]{guard report[key] as? Bool==true else{self.fail("Failed "+key)}}
   try! d.write(to:self.root.appendingPathComponent(".qa/reader-performance/web-verified.json"));print(json);self.worker.terminate();exit(0)
  }
 }}
 func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage){guard let v=message.body as? [String:Any],let action=v["action"] as? String else{return};if ["init","get","readerBook","readerImage","readerSettings","position"].contains(action){command(v)}}
}
@main struct Main{static func main(){let app=NSApplication.shared,qa=ReaderPerformanceQA();app.delegate=qa;withExtendedLifetime(qa){app.run()}}}
