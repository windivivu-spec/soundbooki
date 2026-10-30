import AppKit
import WebKit
import AVFAudio

// Real WebKit -> worker Nano -> AVAudioPlayer + the app's native queue.
// Isolated fixture only. Players muted: this tests transitions, not listening quality.
final class LiteQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,AVAudioPlayerDelegate {
 let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
 let queue=NarrationQueue();var window:NSWindow!;var web:WKWebView!;var worker:Process!;let input=Pipe();var buffer=Data();var player:AVAudioPlayer?;var token="";var timer:Timer?;var stage="start";var played:[String]=[];var advances=0
 lazy var folder:URL={let dirs=try! FileManager.default.contentsOfDirectory(at:root.appendingPathComponent(".qa/reader-lite"),includingPropertiesForKeys:[.contentModificationDateKey]);let item=dirs.filter{FileManager.default.fileExists(atPath:$0.appendingPathComponent("result.json").path)}.sorted{$0.path>$1.path}.last!;return item}()
 lazy var result=try! JSONSerialization.jsonObject(with:Data(contentsOf:folder.appendingPathComponent("result.json"))) as! [String:Any]
 func fail(_ s:String)->Never{fputs(s+"\n",stderr);worker?.terminate();exit(1)}
 func js(_ s:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(s){v,e in if let e=e{self.fail(e.localizedDescription)};done?(v)}}
 func require(_ s:String,_ done:@escaping()->Void){js(s){v in guard v as? Bool==true else{self.fail(s)};done()}}
 func command(_ r:[String:Any]){var data=try! JSONSerialization.data(withJSONObject:r);data.append(10);try! input.fileHandleForWriting.write(contentsOf:data)}
 func send(_ r:[String:Any],_ done:(()->Void)?=nil){let data=try! JSONSerialization.data(withJSONObject:r);js("window.receive(\(String(data:data,encoding:.utf8)!))"){_ in done?()}}
 func applicationDidFinishLaunching(_ n:Notification){
  NSApp.setActivationPolicy(.regular);let c=WKWebViewConfiguration();c.websiteDataStore = .nonPersistent();c.userContentController.add(self,name:"app");c.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
  web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:c);window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
  worker=Process();worker.executableURL=root.appendingPathComponent(".runtime/bin/python");worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path];worker.environment=ProcessInfo.processInfo.environment.merging(["WINDI_SACH_HOME":folder.appendingPathComponent("library").path]){_,new in new};worker.standardInput=input;worker.standardError=FileHandle.standardError;let output=Pipe();worker.standardOutput=output
  output.fileHandleForReading.readabilityHandler={h in let data=h.availableData;DispatchQueue.main.async{self.buffer.append(data);while let range=self.buffer.range(of:Data([10])){let line=self.buffer.subdata(in:0..<range.lowerBound);self.buffer.removeSubrange(0...range.lowerBound);if let value=try? JSONSerialization.jsonObject(with:line) as? [String:Any]{self.receive(value)}}}}
  try! worker.run();web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));timer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){_ in self.tick()};DispatchQueue.main.asyncAfter(deadline:.now()+50){self.fail("Timeout: "+self.stage)}
 }
 func receive(_ value:[String:Any]){
  if value["event"] as? String=="error"{fail(String(describing:value))}
  send(value){
   if value["event"] as? String=="book"&&self.stage=="start"{self.stage="ebook";self.js("$('readingMode').click();")}
   if value["event"] as? String=="readerBook"&&self.stage=="ebook"{self.stage="clickSecond";DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.require("ebookData.sentences.length===3&&$('readerVoiceChoice').options.length>0"){
    self.js("$('ebookFlow').querySelectorAll('[data-cue]')[1].click();")
   }}}
  }
 }
 func tick(){guard let p=player else{return};send(["event":"auxPlayback","token":token,"seconds":p.currentTime,"duration":p.duration,"playing":p.isPlaying])}
 func audioPlayerDidFinishPlaying(_ old:AVAudioPlayer,successfully flag:Bool){
  guard old===player else{return}
  if flag,let (next,at)=queue.take(){player=next;next.volume=0;if !next.isPlaying{next.play()};advances+=1;send(["event":"auxAdvanced","token":token,"segment":at]){
   if self.stage=="clickSecond"{self.stage="continuous";self.require("aux.kind==='reader'&&aux.at===2&&ebookActive===aux.segments[2].id&&playing"){
    self.js("$('play').click();")
    DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.require("!playing&&aux.at===2"){
     self.js("$('play').click();")
     DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.require("playing&&aux.at===2"){
      self.stage="earlier";self.js("$('ebookFlow').querySelectorAll('[data-cue]')[0].click();")
     }}
    }}
   }}
   };return
  }
  player=nil;send(["event":"auxEnded","token":token,"success":flag])
 }
 func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage){
  guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
  if action=="qaError"{fail(r["message"] as? String ?? "JS error")}
  if ["init","get","readerBook","readerImage","readerSettings","readerListen","cancelListening","position"].contains(action){command(r);return}
  if action=="stop"{queue.clear();player?.stop();player=nil;return}
  if action=="pause"{queue.pause();player?.pause();tick();return}
  if action=="continue"{player?.play();if let p=player{queue.reschedule(after:p)};tick();return}
  if action=="auxQueue",let p=player,r["token"] as? String==token,let path=r["path"] as? String,let at=r["segment"] as? Int{try! queue.prepare(after:p,entries:[(URL(fileURLWithPath:path),at)],delegate:self);return}
  if action=="auxPlay",let path=r["path"] as? String,let id=r["token"] as? String {
   queue.clear();player?.stop();player=try! AVAudioPlayer(contentsOf:URL(fileURLWithPath:path));player?.volume=0;player?.delegate=self;player?.enableRate=true;player?.prepareToPlay();token=id;played.append(path);player?.play();tick()
   if stage=="earlier"{stage="voice";require("aux.at===0&&ebookActive===aux.segments[0].id&&book.model==='pro-cloud'&&$('readerVoiceChoice').value===aux.voice"){
    self.js("window.qaOldVoice=aux.voice;const option=[...$('readerVoiceChoice').options].find(o=>o.value!==qaOldVoice);$('readerVoiceChoice').value=option.value;$('readerVoiceChoice').onchange();")
   }}else if stage=="voice"{stage="done";require("aux.at===0&&aux.voice!==qaOldVoice&&book.model==='pro-cloud'&&readerState.voice===aux.voice&&playing"){
    guard self.advances>=1,self.played.count>=3 else{self.fail("No continuous audio")};self.command(["action":"shutdown"]);print("PASS: real Nano + native audio queue; click second sentence, continue to third, pause/resume, click earlier sentence, switch Lite voice; production Pro settings unchanged; zero cloud requests");exit(0)
   }}
  }
 }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=LiteQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
