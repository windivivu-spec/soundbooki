import AppKit
import WebKit

// Real WebKit + worker; isolated library. Speech inference is covered separately.
final class ReadingToolsQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,WKNavigationDelegate {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 var window:NSWindow!;var web:WKWebView!;var worker:Process!;let input=Pipe();var buffer=Data()
 func fail(_ text:String)->Never{fputs(text+"\n",stderr);worker?.terminate();exit(1)}
 func command(_ value:[String:Any]){var data=try! JSONSerialization.data(withJSONObject:value);data.append(10);try! input.fileHandleForWriting.write(contentsOf:data)}
 func applicationDidFinishLaunching(_ notification:Notification){
  NSApp.setActivationPolicy(.regular)
  let qa=root.appendingPathComponent(".qa/reading-features");try! FileManager.default.createDirectory(at:qa,withIntermediateDirectories:true)
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":qa.appendingPathComponent("ui-library").path]){_,new in new};worker.standardInput=input;let output=Pipe();worker.standardOutput=output;worker.standardError=FileHandle.standardError
  output.fileHandleForReading.readabilityHandler={h in let data=h.availableData;DispatchQueue.main.async{self.buffer.append(data);while let range=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<range.lowerBound);self.buffer.removeSubrange(0...range.lowerBound);if let obj=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{if obj["event"] as? String=="error"{self.fail(String(describing:obj))};let data=try! JSONSerialization.data(withJSONObject:obj);self.web.evaluateJavaScript("window.receive(\(String(data:data,encoding:.utf8)!))"){_,e in if let e=e{self.fail(e.localizedDescription)}}}}}}
  try! worker.run()
  let config=WKWebViewConfiguration();config.websiteDataStore = .nonPersistent();config.userContentController.add(self,name:"app");config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaFail',message:e.message}));window.addEventListener('unhandledrejection',e=>window.webkit.messageHandlers.app.postMessage({action:'qaFail',message:String(e.reason)}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:config);web.navigationDelegate=self;window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil);web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
  DispatchQueue.main.asyncAfter(deadline:.now()+90){self.fail("Reading tools QA timeout")}
 }
 func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaFail"{fail(r["message"] as? String ?? "JS failure")}
  if action=="qaPass"{command(["action":"shutdown"]);print("PASS: native WebKit + worker paste, search, edition-bound notes/highlights, reflow, bilingual setting and M4B controls; light/dark screenshots");exit(0)}
  if action=="qaSnapshot",let name=r["name"] as? String{DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.web.takeSnapshot(with:nil){img,e in guard let t=img?.tiffRepresentation,let png=NSBitmapImageRep(data:t)?.representation(using:.png,properties:[:])else{self.fail("snapshot failed")};try! png.write(to:self.root.appendingPathComponent(".qa/reading-features/"+name+".png"));self.web.evaluateJavaScript("window.qaSnapshotDone()",completionHandler:nil)}};return}
  if action=="qaCompact"{window.setContentSize(NSSize(width:1000,height:700));return}
  let allowed=["init","get","bookCover","models","readerBook","readerImage","readerPage","readerSettings","importText","readingSearch","readingNotes","readingAnnotation","settings","cancelListening","position"]
  if allowed.contains(action){command(r)}
 }
 func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){
  let script=#"""
  (async()=>{
   const check=(v,s)=>{if(!v)throw new Error(s)},wait=async fn=>{for(let n=0;n<200;n++){if(fn())return;await new Promise(r=>setTimeout(r,50));}throw new Error('timeout '+fn)},snap=name=>new Promise(r=>{window.qaSnapshotDone=r;send({action:'qaSnapshot',name})});
   await wait(()=>!!$('pasteTextDialog'));$('theme').value='light';applyAppearance();
   $('pasteTextDialog').showModal();$('pasteTextDialog').querySelector('input').value='Sách QA Việt–Anh';$('pasteTextDialog').querySelector('textarea').value='Đọc tiếng Việt thật dễ. It is a truth universally acknowledged. Chúc bạn đọc sách vui vẻ.\n\n'+('Một trang sách mở ra một khoảng trời. ').repeat(70);[...$('pasteTextDialog').querySelectorAll('button')].find(b=>b.textContent==='Thêm vào thư viện').click();
   await wait(()=>book?.title==='Sách QA Việt–Anh'&&!$('pasteTextDialog').open);check(book.segments.map(s=>s.text).join('').includes('Đọc tiếng Việt'),'paste text');
   $('readingMode').click();await wait(()=>ebookData&&readingEdition&&ebookElements.size>1);
   readingOpen('search');$('readingToolsQuery').value='doc tieng viet';$('readingToolsQuery').dispatchEvent(new Event('input'));await wait(()=>$('readingToolsResults').textContent.includes('Đọc tiếng Việt'));await snap('mac-search-light');$('readingToolsResults').querySelector('button').click();
   const cue=ebookData.sentences[0],el=ebookElements.get(cue.id),r=document.createRange();r.selectNodeContents(el);getSelection().removeAllRanges();getSelection().addRange(r);readingCapture();check($('readingNoteDialog').open,'annotation dialog');$('readingNoteText').value='Ghi chú tiếng Việt 🌍';[...$('readingNoteDialog').querySelectorAll('button')].find(b=>b.textContent==='Lưu').click();await wait(()=>readingNotes.some(n=>n.note==='Ghi chú tiếng Việt 🌍'));
   check(CSS.highlights.get('note-yellow').size===1,'actual highlight range');check(getComputedStyle($('readingNoteDialog')).borderRadius==='22px','local CSS loaded');let saved=readingNotes[0].id;
   readerState.fontSize=27;layoutEbook(true);readingPaint();check(CSS.highlights.get('note-yellow').size===1,'highlight after reflow');readingOpen('notes');await wait(()=>$('readingToolsResults').textContent.includes('Ghi chú tiếng Việt'));await snap('mac-notebook-light');$('readingToolsDialog').close();
   $('theme').value='dark';applyAppearance();send({action:'qaCompact'});await new Promise(r=>setTimeout(r,400));readingOpen('notes');await wait(()=>$('readingToolsResults').textContent.includes('Ghi chú tiếng Việt'));await snap('mac-notebook-dark-compact');check(document.documentElement.scrollWidth<=innerWidth,'compact overflow');$('readingToolsDialog').close();
   check($('exportFormat').querySelector('[value=m4b]')&&$('takeFormat').querySelector('[value=m4b]'),'M4B menus');$('bilingualReading').checked=true;$('bilingualReading').dispatchEvent(new Event('change'));await wait(()=>book.bilingual===true);check(book.segments[0].originalText.includes('Đọc tiếng Việt'),'original preserved');
   send({action:'get',bookId:book.id});await new Promise(r=>setTimeout(r,350));readingRequest('readingNotes');await wait(()=>readingNotes.some(n=>n.id===saved));send({action:'qaPass'});
  })().catch(e=>send({action:'qaFail',message:String(e.stack||e)}));
  """#
  web.evaluateJavaScript(script+";void 0;"){_,e in if let e=e{self.fail(e.localizedDescription)}}
 }
}
let app=NSApplication.shared;let delegate=ReadingToolsQA();app.delegate=delegate;app.run()
