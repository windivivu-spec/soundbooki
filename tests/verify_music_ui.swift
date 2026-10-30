import AppKit
import WebKit

// Real WebKit with an isolated library fixture. No uploads or user-library writes.
final class MusicUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,WKNavigationDelegate {
    let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
    var window:NSWindow!;var web:WKWebView!;var started=false
    var settings:[[String:Any]]=[];var payload:[String:Any]?
    lazy var fixture=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/music-ui/fixture.json"))) as! [String:Any]
    func fail(_ text:String)->Never{fputs(text+"\n",stderr);exit(1)}
    func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
    func require(_ source:String,_ next:@escaping()->Void){js(source){ok in guard ok as? Bool==true else{self.fail("Failed: "+source)};next()}}
    func send(_ value:Any){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))")}
    func applicationDidFinishLaunching(_ notification:Notification){
        NSApp.setActivationPolicy(.regular)
        let config=WKWebViewConfiguration();config.userContentController.add(self,name:"app")
        config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
        web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:850),configuration:config);web.navigationDelegate=self
        window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
        web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
        DispatchQueue.main.asyncAfter(deadline:.now()+25){self.fail("Music UI timed out")}
    }
    func snapshot(_ name:String,_ next:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+0.5){self.web.takeSnapshot(with:nil){image,error in
        guard let data=image?.tiffRepresentation,let png=NSBitmapImageRep(data:data)?.representation(using:.png,properties:[:]) else{self.fail("Snapshot failed")}
        try! png.write(to:self.root.appendingPathComponent(".qa/music-ui/"+name));next()
    }}}
    func run(){
        js("$('appLanguage').value='vi';$('appLanguage').onchange();$('theme').value='dark';applyAppearance();openProduction('music');$('musicCategory').value='Jazz Morning';$('musicCategory').onchange();$('musicShuffle').click();")
        DispatchQueue.main.asyncAfter(deadline:.now()+0.3){
            self.require("$('musicCategory').options.length===6&&$('musicQueue').children.length===4&&$('musicShuffle').getAttribute('aria-pressed')==='true'&&$('musicLoop').checked&&musicPayload().playlist.length===4&&$('previewMusic').getBoundingClientRect().bottom<=$('productionPanel').getBoundingClientRect().bottom"){
                self.js("window.qaOrder=JSON.stringify(book.music.playlist);$('musicVolume').value='18';$('musicVolume').onchange();closeProduction();openProduction('music');")
                self.require("JSON.stringify(book.music.playlist)===qaOrder&&$('musicVolume').value==='18'&&$('musicVolumeLabel').textContent==='18%'"){
                    self.snapshot("music-shuffle-dark-vi.png"){
                        self.js("$('reshuffleMusic').click();")
                        self.require("JSON.stringify(book.music.playlist)!==qaOrder"){
                            self.js("$('musicLoop').checked=false;$('musicLoop').onchange();$('previewMusic').click();")
                            DispatchQueue.main.asyncAfter(deadline:.now()+0.1){
                                guard let payload=self.payload,payload["loop"] as? Bool==false,(payload["playlist"] as? [String])?.count==4 else{self.fail("Native preview payload lost order/loop")}
                                self.js("$('previewMusic').click();$('musicSingle').click();$('appLanguage').value='en';$('appLanguage').onchange();$('theme').value='light';applyAppearance();")
                                self.require("$('musicSingle').getAttribute('aria-pressed')==='true'&&$('musicQueueWrap').hidden&&!$('musicTrackLabel').hidden&&$('musicSingle').textContent==='Choose a track'&&musicPayload().playlist.length===1"){
                                    self.snapshot("music-single-light-en.png"){
                                        self.js("jobs.export=book.id;renderMusicControls();")
                                        self.require("$('musicCategory').disabled&&$('musicLoop').disabled&&$('musicTrack').disabled"){
                                            self.js("delete jobs.export;$('musicCategory').value='none';$('musicCategory').onchange();")
                                            self.require("musicPayload().playlist.length===0&&$('previewMusic').disabled&&$('musicChoices').hidden"){
                                                guard self.settings.count>=6 else{self.fail("Music choices not persisted through bridge")}
                                                print("PASS: categories, single/shuffle, reshuffle, persisted gain/order, loop, preview payload, export lock, VI/EN dark/light");exit(0)
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
    func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
        guard let value=message.body as? [String:Any],let action=value["action"] as? String else{return}
        if action=="qaError"{fail(value["message"] as? String ?? "JS error")}
        if action=="init"{send(fixture["models"]!);send(fixture["init"]!)}
        if action=="get"{send(fixture["book"]!);if !started{started=true;DispatchQueue.main.asyncAfter(deadline:.now()+0.4){self.run()}}}
        if action=="settings",let music=value["music"] as? [String:Any]{settings.append(music)}
        if action=="musicPreview",value["playing"] as? Bool==true {payload=value}
    }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=MusicUIQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
