import AppKit
import WebKit
import AVFoundation
import UniformTypeIdentifiers

final class LicenseFetchDelegate:NSObject,URLSessionTaskDelegate {
    func urlSession(_ session:URLSession,task:URLSessionTask,willPerformHTTPRedirection response:HTTPURLResponse,newRequest request:URLRequest,completionHandler:@escaping(URLRequest?)->Void){completionHandler(nil)}
}

final class WindowDragView: NSView {
    override func mouseDown(with event:NSEvent) { window?.performDrag(with:event) }
}

final class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate, AVAudioPlayerDelegate {
    var window:NSWindow!; var web:ImportWebView!; var worker:Process!; var input:Pipe!; var player:AVAudioPlayer?
    var musicPlayer:MusicPlayback?=MusicPlayback(); var musicVolume:Float=0.12; var previewingMusic=false
    var auxPlayer:AVAudioPlayer?; var auxToken=""
    let welcomeAudio=WelcomePlayback()
    let narrationQueue=NarrationQueue();var playSession=""
    let sourceReader=SourcePageRenderer()
    let ebookTurn=EbookTurnBridge()
    var preparedNarration:AVAudioPlayer?;var preparedPath=""
    var buffer=Data(); var timer:Timer?; var bookId=""; var segment=0; var ticks=0
    let root:URL = Bundle.main.object(forInfoDictionaryKey:"WindiPortable") as? Bool == true ? Bundle.main.resourceURL!.appendingPathComponent("App") : URL(fileURLWithPath:Bundle.main.object(forInfoDictionaryKey:"WindiProjectRoot") as? String ?? FileManager.default.currentDirectoryPath)
    let importPanelPolicy=ImportPanelPolicy()
    var pendingImport: (token:String,urls:[URL])?
    var selectingDocuments=false
    var accessTier=""
    var accessDevice="";var checkingLicense=false
    var licenseTask:URLSessionDataTask?;var licenseCheckID=""
    var library:URL { if let p=ProcessInfo.processInfo.environment["WINDI_SACH_HOME"] {return URL(fileURLWithPath:p)}; return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Windi Sach Noi/library") }
    func applicationDidFinishLaunching(_ n:Notification) {
        NSApp.setActivationPolicy(.regular)
        let menu=NSMenu(); let item=NSMenuItem(); menu.addItem(item); let sub=NSMenu(); sub.addItem(withTitle:"Thoát Windi Sách Nói",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q"); item.submenu=sub; NSApp.mainMenu=menu
        sub.insertItem(withTitle:"Giới thiệu Windi Sách Nói",action:#selector(showAbout),keyEquivalent:"",at:0)
        sub.insertItem(NSMenuItem.separator(),at:1)
        sub.insertItem(withTitle:"Hiển thị và chuyển động…",action:#selector(showAppearance),keyEquivalent:",",at:2)
        sub.insertItem(NSMenuItem.separator(),at:3)
        let fileItem=NSMenuItem();menu.addItem(fileItem);let file=NSMenu(title:"Tệp");fileItem.submenu=file
        file.addItem(withTitle:"Thêm sách…",action:#selector(openDocument),keyEquivalent:"o")
        file.addItem(withTitle:"Về Trang chủ",action:#selector(showHome),keyEquivalent:"1")
        file.addItem(withTitle:"Xuất bản đọc…",action:#selector(exportAudio),keyEquivalent:"e")
        let editItem=NSMenuItem();menu.addItem(editItem);let edit=NSMenu(title:"Chỉnh sửa");editItem.submenu=edit
        edit.addItem(withTitle:"Cắt",action:#selector(NSText.cut(_:)),keyEquivalent:"x")
        edit.addItem(withTitle:"Sao chép",action:#selector(NSText.copy(_:)),keyEquivalent:"c")
        edit.addItem(withTitle:"Dán",action:#selector(NSText.paste(_:)),keyEquivalent:"v")
        edit.addItem(withTitle:"Chọn tất cả",action:#selector(NSText.selectAll(_:)),keyEquivalent:"a")
        edit.addItem(NSMenuItem.separator())
        edit.addItem(withTitle:"Tìm trong thư viện",action:#selector(findInLibrary),keyEquivalent:"f")
        let config=WKWebViewConfiguration(); config.userContentController.add(self,name:"app")
        web=ImportWebView(frame:.zero,configuration:config); web.navigationDelegate=self; web.underPageBackgroundColor = .clear
        web.registerForDraggedTypes([.fileURL])
        web.onFileDrag={[weak self] active in self?.send(["event":"fileDrag","active":active])}
        web.onFiles={[weak self] urls in self?.stageImport(urls)}
        window=NSWindow(contentRect:NSRect(x:0,y:0,width:1180,height:800),styleMask:[.titled,.closable,.miniaturizable,.resizable,.fullSizeContentView],backing:.buffered,defer:false)
        window.title="Windi Sách Nói"; window.minSize=NSSize(width:860,height:660)
        window.titleVisibility = .hidden; window.titlebarAppearsTransparent = true
        let material=NSVisualEffectView(frame:NSRect(x:0,y:0,width:1180,height:800)); material.material = .underWindowBackground; material.blendingMode = .behindWindow; material.state = .active
        web.frame=material.bounds; web.autoresizingMask=[.width,.height];material.addSubview(web)
        let drag=WindowDragView(frame:NSRect(x:250,y:772,width:850,height:28));drag.autoresizingMask=[.width,.minYMargin];material.addSubview(drag)
        window.contentView=material; window.center(); window.makeKeyAndOrderFront(nil)
        NSWorkspace.shared.notificationCenter.addObserver(self,selector:#selector(accessibilityChanged),name:NSWorkspace.accessibilityDisplayOptionsDidChangeNotification,object:nil)
        web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"))
        startWorker(); NSApp.activate(ignoringOtherApps:true)
        timer=Timer.scheduledTimer(withTimeInterval:0.5,repeats:true){[weak self] _ in self?.tick()}
    }
    @objc func showAbout() { send(["event":"showAppInfo"]) }
    @objc func showHome() { send(["event":"showHome"]) }
    @objc func showAppearance() { web.evaluateJavaScript("document.getElementById('appearance').click()",completionHandler:nil) }
    @objc func openDocument() {send(["event":"requestImport"])}
    func stageImport(_ urls:[URL]) {
        do {
            let urls=try DocumentImport.validate(urls),token=UUID().uuidString
            pendingImport=(token,urls);send(["event":"filesSelected","selectionToken":token])
        } catch {send(["event":"pickCancelled"]);send(["event":"error","message":error.localizedDescription])}
    }
    @objc func exportAudio() { web.evaluateJavaScript("document.getElementById('export').click()",completionHandler:nil) }
    @objc func findInLibrary() { web.evaluateJavaScript("document.getElementById('librarySearch').focus();document.getElementById('librarySearch').select()",completionHandler:nil) }
    @objc func accessibilityChanged() {
        send(["event":"accessibility","reduceTransparency":NSWorkspace.shared.accessibilityDisplayShouldReduceTransparency,"increaseContrast":NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast])
    }
    func localizeMenus(_ language:String) {
        let labels=[("Thoát Windi Sách Nói","Quit Windi Sách Nói"),("Giới thiệu Windi Sách Nói","About Windi Sách Nói"),("Hiển thị và chuyển động…","Appearance and motion…"),("Tệp","File"),("Thêm sách…","Add a book…"),("Xuất bản đọc…","Export audio…"),("Chỉnh sửa","Edit"),("Cắt","Cut"),("Sao chép","Copy"),("Dán","Paste"),("Chọn tất cả","Select all"),("Tìm trong thư viện","Search library")]
        func translated(_ text:String)->String {if let pair=labels.first(where:{$0.0==text || $0.1==text}){return language == "en" ? pair.1 : pair.0};return text}
        func visit(_ menu:NSMenu) {menu.title=translated(menu.title);for item in menu.items {item.title=translated(item.title);if let sub=item.submenu {visit(sub)}}}
        if let menu=NSApp.mainMenu {visit(menu)}
    }
    func webView(_ webView:WKWebView,didStartProvisionalNavigation navigation:WKNavigation!){welcomeAudio.stop(immediately:true)}
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!) {
        accessibilityChanged()
        ebookTurn.web=web;ebookTurn.emit={[weak self] value in self?.send(value)}
        send(["event":"pageTurnSupport","supported":true])
        send(["event":"buildInfo","version":Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "local",
              "build":Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "—"])
    }
    func startWorker() {
        worker=Process(); worker.executableURL=root.appendingPathComponent(".runtime/bin/python")
        worker.arguments=["-B",root.appendingPathComponent("backend/worker.py").path]
        var env=ProcessInfo.processInfo.environment;env.removeValue(forKey:"PYTHONHOME");env.removeValue(forKey:"PYTHONPATH");env["PYTHONNOUSERSITE"]="1"; env["WINDI_EXTRACTOR"]=root.appendingPathComponent(".build/windi-extract").path; env["PYTHONUNBUFFERED"]="1";env["WINDI_MEMORY_BYTES"]=String(ProcessInfo.processInfo.physicalMemory);worker.environment=env
        input=Pipe(); let output=Pipe(); worker.standardInput=input; worker.standardOutput=output; worker.standardError=FileHandle.standardError
        output.fileHandleForReading.readabilityHandler={[weak self] h in
            let data=h.availableData
            DispatchQueue.main.async {guard let self=self else{return}; self.buffer.append(data)
                while let range=self.buffer.range(of:Data([10])) {
                    let line=self.buffer.subdata(in:0..<range.lowerBound); self.buffer.removeSubrange(0...range.lowerBound)
                    if let obj=try? JSONSerialization.jsonObject(with:line) as? [String:Any] {
                        if let entitlement=obj["entitlement"] as? [String:Any],let tier=entitlement["tier"] as? String {
                            if self.accessTier == "pro" && tier != "pro" {self.narrationQueue.clear();self.player?.stop();self.auxPlayer?.stop();self.musicPlayer?.stop()}
                            self.accessTier=tier
                            self.accessDevice=entitlement["deviceCode"] as? String ?? ""
                        }
                        if obj["event"] as? String=="readerPage"{self.sourceReader.receive(obj,library:self.library){[weak self] result in self?.send(result)}}else{self.send(obj)}
                    }
                }
            }
        }
        do {try worker.run()} catch {DispatchQueue.main.asyncAfter(deadline:.now()+1){self.send(["event":"error","message":"Ứng dụng chưa mở được bộ đọc. Hãy đóng app, mở lại hoặc cài lại bản mới nhất."])}}
    }
    func command(_ value:[String:Any]) {
        guard worker?.isRunning == true, var d=try? JSONSerialization.data(withJSONObject:value) else{return}
        d.append(10); try? input.fileHandleForWriting.write(contentsOf:d)
    }
    func send(_ value:[String:Any]) {
        guard let d=try? JSONSerialization.data(withJSONObject:value), let s=String(data:d,encoding:.utf8) else{return}
        web.evaluateJavaScript("window.receive(\(s))",completionHandler:nil)
    }
    func persist(_ finished:Bool=false) {
        if !bookId.isEmpty,let activePlayer=player {command(["action":"position","bookId":bookId,"segment":segment,"seconds":activePlayer.currentTime,"finished":finished])}
    }
    func tick() {
        ticks+=1;if ticks%120==0 {command(["action":"license"])}
        if let p=auxPlayer {send(["event":"auxPlayback","token":auxToken,"seconds":p.currentTime,"duration":p.duration,"playing":p.isPlaying]);return}
        guard let p=player else{return}
        send(["event":"playback","seconds":p.currentTime,"duration":p.duration,"playing":p.isPlaying,"segment":segment,"bookId":bookId])
        if ticks%4==0 {persist()}
    }
    func configureMusic(_ value:[String:Any],shouldPlay:Bool,seek:Bool=true) {
        musicVolume=min(0.5,max(0,(value["volume"] as? NSNumber)?.floatValue ?? 0.12))
        let paths=value["playlist"] as? [String] ?? ((value["path"] as? String).map{[$0]} ?? [])
        if paths.isEmpty || paths==[""] {musicPlayer?.stop();player?.volume=1;narrationQueue.setVolume(1);auxPlayer?.volume=1;return}
        let allowed=root.appendingPathComponent("assets/music").resolvingSymlinksInPath().path+"/"
        let urls=paths.map{URL(fileURLWithPath:$0).resolvingSymlinksInPath()}
        guard urls.count<=500,urls.allSatisfy({$0.path.hasPrefix(allowed) && $0.pathExtension=="wav"}) else{musicPlayer?.stop();return}
        musicPlayer?.onEnded = {[weak self] in self?.send(["event":"musicEnded"])}
        do{
            try musicPlayer?.configure(urls:urls,volume:musicVolume,loop:value["loop"] as? Bool ?? true,offset:(value["offset"] as? NSNumber)?.doubleValue ?? 0,seek:seek,shouldPlay:shouldPlay)
            player?.volume=musicVolume>0 ? 0.94 : 1;auxPlayer?.volume=musicVolume>0 ? 0.94 : 1
            narrationQueue.setVolume(musicVolume>0 ? 0.94 : 1)
        }catch{musicPlayer?.stop();send(["event":"error","message":"Chưa mở được nhạc nền. Hãy chọn bài khác và thử lại."])}
    }
    func userContentController(_ c:WKUserContentController,didReceive message:WKScriptMessage) {
        guard message.frameInfo.isMainFrame, let r=message.body as? [String:Any], let action=r["action"] as? String else{return}
        switch action {
        case "bookPaymentQR":
            guard let bank=r["bank"] as? [String:Any], let bin=bank["bin"] as? String,
                  bin.range(of:"^[0-9]{6}$",options:.regularExpression) != nil,
                  let account=bank["account"] as? String, account.range(of:"^[0-9]{6,32}$",options:.regularExpression) != nil,
                  let code=r["code"] as? String, code.range(of:"^SB[A-F0-9]{32}$",options:.regularExpression) != nil,
                  let amount=r["amount"] as? Int, amount>=10000, amount<=1000000 else{return}
            let payload=VietQR.payload(bin:bin,account:account,amount:amount,content:code)
            if let vector=VietQR.vector(payload){send(["event":"bookPaymentQR","code":code,"qrPath":vector.path,"qrSize":vector.size])}
        case "copyBookPayment":
            guard let value=r["value"] as? String, value.range(of:"^(SB[A-F0-9]{32}|[0-9]{6,32})$",options:.regularExpression) != nil else{return}
            NSPasteboard.general.clearContents();NSPasteboard.general.setString(value,forType:.string)
        case "purchase":
            send(["event":"purchaseError","message":"Pro được thanh toán theo từng cuốn. Mở Pro Cloud để xem giá cuốn sách này."])
        case "copyPaymentAccount":
            guard let data=try? Data(contentsOf:root.appendingPathComponent("release.json")),
                  let config=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
                  let checkout=VietQR.checkout(config,device:accessDevice),let account=checkout["account"] as? String else{return}
            NSPasteboard.general.clearContents();NSPasteboard.general.setString(account,forType:.string)
            send(["event":"paymentAccountCopied"])
        case "copyDeviceCode":
            guard accessDevice.range(of:"^SN[A-F0-9]{12}$",options:.regularExpression) != nil else{return}
            NSPasteboard.general.clearContents();NSPasteboard.general.setString(accessDevice,forType:.string)
            send(["event":"deviceCopied"])
        case "checkLicense":
            let requestID=r["requestId"] as? String ?? UUID().uuidString
            guard !checkingLicense else {send(["event":"licenseCheck","requestId":requestID,"state":"error","message":"App đang cập nhật Pro. Vui lòng chờ một chút."]);return}
            guard accessDevice.range(of:"^SN[A-F0-9]{12}$",options:.regularExpression) != nil,
                  let data=try? Data(contentsOf:root.appendingPathComponent("release.json")),let config=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
                  let raw=config["licenseBaseURL"] as? String,let base=URL(string:raw),base.scheme=="https",base.host != nil else {
                send(["event":"licenseCheck","requestId":requestID,"state":"unavailable","message":"Thanh toán tạm thời chưa sẵn sàng. Hãy đóng cửa sổ và thử lại sau."]);return
            }
            checkingLicense=true;licenseCheckID=requestID
            var request=URLRequest(url:base.appendingPathComponent(accessDevice+".windilicense"));request.timeoutInterval=20;request.cachePolicy = .reloadIgnoringLocalCacheData
            let session=URLSession(configuration:.ephemeral,delegate:LicenseFetchDelegate(),delegateQueue:nil)
            licenseTask=session.dataTask(with:request){data,response,error in
                DispatchQueue.main.async {
                    defer{session.finishTasksAndInvalidate()}
                    guard self.licenseCheckID==requestID else{return}
                    self.checkingLicense=false;self.licenseTask=nil;self.licenseCheckID=""
                    guard error==nil,let response=response as? HTTPURLResponse else{self.send(["event":"licenseCheck","requestId":requestID,"state":"error","message":"Chưa kết nối được. App sẽ thử lại khi có mạng."]);return}
                    guard response.statusCode==200 else{
                        let pending=response.statusCode==404 || response.statusCode==410
                        self.send(["event":"licenseCheck","requestId":requestID,"state":pending ? "pending" : "error","message":pending ? "Chưa nhận được Pro cho Mac này. Nếu đã chuyển khoản, hãy chờ giao dịch được xác nhận." : "Chưa cập nhật được Pro. App sẽ thử lại sau."]);return
                    }
                    guard let data=data,data.count<=16384,let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{self.send(["event":"licenseCheck","requestId":requestID,"state":"error","message":"Chưa nhận được thông tin Pro hợp lệ. App sẽ thử lại sau."]);return}
                    var payload:[String:Any]=["action":"installLicense","license":value,"requestId":requestID]
                    if let baseline=r["afterExpiresAt"] as? String {payload["afterExpiresAt"]=baseline}
                    if let bid=r["bookId"]{payload["bookId"]=bid};self.command(payload)
                }
            };licenseTask?.resume()
        case "cancelLicenseCheck":
            if let id=r["requestId"] as? String,id==licenseCheckID {licenseCheckID="";licenseTask?.cancel();licenseTask=nil;checkingLicense=false}
        case "licenseDialog":
            let panel=NSOpenPanel();panel.canChooseFiles=true;panel.canChooseDirectories=false;panel.allowsMultipleSelection=false
            panel.allowedContentTypes=[UTType(filenameExtension:"windilicense") ?? .json,.json]
            panel.message="Chọn tệp kích hoạt Pro đã nhận cho Mac này."
            panel.beginSheetModal(for:window){response in
                if response == .OK,let url=panel.url {var value:[String:Any]=["action":"importLicense","path":url.path];if let bid=r["bookId"] {value["bookId"]=bid};self.command(value)}
            }
        case "locale":localizeMenus(r["language"] as? String ?? "vi")
        case "appearance":
            let theme=r["theme"] as? String ?? "system"
            window.appearance = theme == "dark" ? NSAppearance(named:.darkAqua) : theme == "light" ? NSAppearance(named:.aqua) : nil
        case "pick":
            guard !selectingDocuments,window.attachedSheet == nil else{return}
            selectingDocuments=true
            let panel=NSOpenPanel();panel.canChooseDirectories=true;panel.canChooseFiles=true;panel.treatsFilePackagesAsDirectories=false;panel.allowsMultipleSelection=true
            // EPUB may be reported as ZIP, a package or a dynamic type by Finder.
            // The extension-based delegate keeps those valid files selectable.
            panel.delegate=importPanelPolicy;panel.allowsOtherFileTypes=true;panel.resolvesAliases=true
            panel.message=r["uiLanguage"] as? String == "en" ? "Choose one EPUB, one PDF, or several images." : "Chọn một EPUB (file hoặc thư mục .epub), một PDF hoặc nhiều ảnh."
            panel.beginSheetModal(for:window) { response in
                self.selectingDocuments=false
                if response == .OK {self.stageImport(panel.urls)} else {self.send(["event":"pickCancelled"])}
            }
        case "importSelection":
            guard let token=r["selectionToken"] as? String,let pending=pendingImport,pending.token==token else{return}
            pendingImport=nil
            do {
                let urls=try DocumentImport.validate(pending.urls)
                command(["action":"import","paths":urls.map(\.path),"language":r["language"] as? String ?? "vi","forceOCR":r["forceOCR"] as? Bool ?? false])
            } catch {send(["event":"error","message":error.localizedDescription])}
        case "walkthroughAudio":
            guard let operation=r["operation"] as? String,["start","mute","stop"].contains(operation) else{return}
            let token=r["token"] as? String ?? ""
            do {
                switch operation {
                case "start":
                    try welcomeAudio.start(root:root,muted:r["muted"] as? Bool ?? false)
                case "mute": welcomeAudio.setMuted(r["muted"] as? Bool ?? false)
                default: welcomeAudio.stop()
                }
                send(["event":"walkthroughAudio","token":token,"success":true,"active":welcomeAudio.active,"muted":welcomeAudio.muted])
            } catch {
                welcomeAudio.stop(immediately:true)
                send(["event":"walkthroughAudio","token":token,"success":false,"active":false])
            }
        case "music":
            configureMusic(r,shouldPlay:player?.isPlaying == true || auxPlayer?.isPlaying == true,seek:r["seek"] as? Bool ?? false)
        case "musicPreview":
            welcomeAudio.stop(immediately:true)
            previewingMusic=r["playing"] as? Bool ?? false
            configureMusic(r,shouldPlay:previewingMusic,seek:r["seek"] as? Bool ?? true)
        case "prepareCurrent":
            guard let path=r["path"] as? String else{return}
            let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
            guard url.path.hasPrefix(library.resolvingSymlinksInPath().path+"/"),url.pathExtension=="wav",preparedPath != url.path else{return}
            do{let ready=try AVAudioPlayer(contentsOf:url);ready.enableRate=true;ready.prepareToPlay();preparedNarration=ready;preparedPath=url.path}catch{preparedNarration=nil;preparedPath=""}
        case "play":
            welcomeAudio.stop(immediately:true)
            guard let path=r["path"] as? String else{return}
            let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
            guard url.path.hasPrefix(library.resolvingSymlinksInPath().path+"/"),url.pathExtension=="wav" else{return}
            persist();narrationQueue.clear();playSession=r["sessionId"] as? String ?? ""; player?.stop();auxPlayer?.stop();auxPlayer=nil;auxToken=""
            do {
                player=preparedPath==url.path ? preparedNarration : try AVAudioPlayer(contentsOf:url)
                preparedNarration=nil;preparedPath="";player?.delegate=self; player?.enableRate=true
                player?.rate=(r["speed"] as? NSNumber)?.floatValue ?? 1
                bookId=r["bookId"] as? String ?? ""; segment=r["segment"] as? Int ?? 0
                player?.currentTime=min((r["seconds"] as? NSNumber)?.doubleValue ?? 0,max(0,(player?.duration ?? 0)-0.05))
                player?.prepareToPlay(); player?.play();previewingMusic=false
                configureMusic(r["music"] as? [String:Any] ?? [:],shouldPlay:true);tick()
            } catch {send(["event":"error","message":"Không phát được audio: \(error.localizedDescription)"])}
        case "queueNext":
            guard let current=player,r["bookId"] as? String==bookId,
                  r["fromSegment"] as? Int==segment,r["sessionId"] as? String==playSession else{return}
            let raw=r["segments"] as? [[String:Any]] ?? []
            guard raw.count<=12 else{return}
            var entries:[(URL,Int)]=[];var previous=segment
            for item in raw {
                guard let path=item["path"] as? String,let index=item["segment"] as? Int,index>previous else{return}
                let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
                guard url.path.hasPrefix(library.resolvingSymlinksInPath().path+"/"),url.pathExtension=="wav" else{return}
                entries.append((url,index));previous=index
            }
            do{try narrationQueue.prepare(after:current,entries:entries,delegate:self)}
            catch{narrationQueue.clear()}
        case "auxQueue":
            guard let current=auxPlayer,let token=r["token"] as? String,token==auxToken,let path=r["path"] as? String,let segment=r["segment"] as? Int,segment>=0 else{return}
            let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
            guard url.pathExtension=="wav",url.path.hasPrefix(library.resolvingSymlinksInPath().path+"/") else{return}
            do{try narrationQueue.prepare(after:current,entries:[(url,segment)],delegate:self)}catch{narrationQueue.clear()}
        case "auxPlay":
            welcomeAudio.stop(immediately:true)
            guard let path=r["path"] as? String,let token=r["token"] as? String,token.range(of:"^[a-f0-9]{32}$",options:.regularExpression) != nil else{return}
            let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
            let previewRoot=root.appendingPathComponent("assets/voice-previews").resolvingSymlinksInPath().path+"/"
            let localPreview=library.deletingLastPathComponent().appendingPathComponent("voice-previews").resolvingSymlinksInPath().path+"/"
            guard url.pathExtension=="wav",url.path.hasPrefix(library.resolvingSymlinksInPath().path+"/") || url.path.hasPrefix(previewRoot) || url.path.hasPrefix(localPreview) else{return}
            persist();narrationQueue.clear();playSession="";player?.stop();player=nil;bookId="";auxPlayer?.stop();musicPlayer?.stop()
            do {
                auxPlayer=try AVAudioPlayer(contentsOf:url);auxPlayer?.delegate=self;auxPlayer?.enableRate=true
                auxPlayer?.rate=(r["speed"] as? NSNumber)?.floatValue ?? 1;auxToken=token
                auxPlayer?.prepareToPlay();auxPlayer?.play()
                configureMusic(r["music"] as? [String:Any] ?? [:],shouldPlay:true);tick()
            } catch {send(["event":"error","message":"Không phát được audio: \(error.localizedDescription)"])}
        case "pause": syncNarrationSegment();narrationQueue.pause();player?.pause();auxPlayer?.pause();musicPlayer?.pause();previewingMusic=false;persist();tick()
        case "continue": player?.play();if let p=player ?? auxPlayer{narrationQueue.reschedule(after:p)};auxPlayer?.play();musicPlayer?.play();previewingMusic=false;tick()
        case "stop": persist();narrationQueue.clear();playSession="";preparedNarration=nil;preparedPath="";player?.stop();player=nil;auxPlayer?.stop();auxPlayer=nil;auxToken="";musicPlayer?.stop();previewingMusic=false;bookId=""
        case "seek":
            syncNarrationSegment()
            if let seconds=r["seconds"] as? Double {if let p=auxPlayer ?? player {p.currentTime=max(0,min(seconds,p.duration))};if let p=player ?? auxPlayer{narrationQueue.reschedule(after:p)};musicPlayer?.seek(to:(r["musicOffset"] as? NSNumber)?.doubleValue ?? seconds);persist();tick()}
        case "rate": syncNarrationSegment();player?.rate=(r["speed"] as? NSNumber)?.floatValue ?? 1;auxPlayer?.rate=(r["speed"] as? NSNumber)?.floatValue ?? 1;if let p=player ?? auxPlayer{narrationQueue.reschedule(after:p)}
        case "original":
            if let bid=r["bookId"] as? String, bid.range(of:"^[a-f0-9]{32}$",options:.regularExpression) != nil,
               let file=r["file"] as? String, file.range(of:"^source-[0-9]+\\.(epub|pdf|png|jpg|jpeg|heic|tiff|tif|webp)$",options:.regularExpression) != nil {
                NSWorkspace.shared.open(library.appendingPathComponent(bid).appendingPathComponent(file))
            }
        case "beginPageTurn","stagePageTurn","releasePageTurn","endPageTurn","cancelPageTurn": ebookTurn.handle(r)
        case "readerFullscreen": window.toggleFullScreen(nil)
        case "exportEbookDialog":
            let panel=NSSavePanel();panel.allowedContentTypes=[UTType(filenameExtension:"epub") ?? .data];panel.nameFieldStringValue="\(r["title"] as? String ?? "Sach").epub"
            panel.beginSheetModal(for:window){response in
                if response == .OK,let url=panel.url{var payload:[String:Any]=["action":"exportEbook","bookId":r["bookId"] ?? "","path":url.path];if let take=r["takeId"] as? String{payload["takeId"]=take};self.command(payload)}
            }
        case "exportDialog":
            let format=r["format"] as? String ?? "mp3"
            guard ["mp3","wav","m4a","m4b","zip"].contains(format) else{return}
            let panel=NSSavePanel(); panel.allowedContentTypes=[UTType(filenameExtension:format) ?? .data]; panel.nameFieldStringValue="\(r["title"] as? String ?? "Sach noi").\(format)"
            panel.beginSheetModal(for:window) { response in
                if response == .OK,let url=panel.url {var payload:[String:Any]=["action":"export","bookId":r["bookId"] ?? "","path":url.path,"scope":r["scope"] ?? ["type":"all"]];if let take=r["takeId"] as? String {payload["takeId"]=take};self.command(payload)}
            }
        case "revealExport":
            if let path=r["path"] as? String {let url=URL(fileURLWithPath:path);if ["mp3","wav","m4a","m4b","zip"].contains(url.pathExtension.lowercased()),FileManager.default.fileExists(atPath:url.path) {NSWorkspace.shared.activateFileViewerSelecting([url])}}
        case "reveal": NSWorkspace.shared.open(library)
        default:
            let allowed=["readingSearch","readingNotes","readingAnnotation","init","get","bookCover","resume","processPDF","readerBook","readerImage","readerListen","readerPage","readerSettings","deleteBook","restoreBook","generate","prepareListening","cancelListening","cancel","edit","settings","position","chapter","models","downloadModel","cleanChapter","editChapter","voicePreview","license","profileInfo","profileSave","bookCloudInfo","bookCloudAvailability","bookCloudQuote","bookCloudTrial","bookCloudCheck","bookCloudCombo","launchInfo","launchQuote","launchCheck"]
            if allowed.contains(action) {command(r)}
        }
    }
    func advanceNarration(_ next:AVAudioPlayer,_ nextSegment:Int){
        persist();let previous=segment;self.player=next;segment=nextSegment
        send(["event":"advanced","bookId":bookId,"fromSegment":previous,"segment":segment,"sessionId":playSession,"playing":next.isPlaying]);persist()
    }
    func syncNarrationSegment(){
        while let current=player,current.currentTime>=current.duration-0.005,
              let upcoming=narrationQueue.player,upcoming.currentTime>0,
              let (next,index)=narrationQueue.take(){advanceNarration(next,index)}
    }
    func audioPlayerDidFinishPlaying(_ player:AVAudioPlayer,successfully flag:Bool) {
        if player === auxPlayer {
            if flag,let (next,at)=narrationQueue.take(){auxPlayer=next;if !next.isPlaying{next.play()};send(["event":"auxAdvanced","token":auxToken,"segment":at]);tick();return}
            musicPlayer?.pause();auxPlayer=nil;send(["event":"auxEnded","token":auxToken,"success":flag]);return
        }
        guard player === self.player else{return}
        if flag,let (next,nextSegment)=narrationQueue.take(){
            advanceNarration(next,nextSegment);tick();return
        }
        narrationQueue.clear()
        persist();musicPlayer?.pause();send(["event":"ended","bookId":bookId,"segment":segment,"success":flag]); self.player=nil
    }
    func webView(_ webView:WKWebView,decidePolicyFor navigationAction:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {
        let url=navigationAction.request.url
        decisionHandler(url?.isFileURL == true && url!.path.hasPrefix(root.appendingPathComponent("ui").path+"/") ? .allow : .cancel)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool {true}
    func applicationWillTerminate(_ notification:Notification) {welcomeAudio.stop(immediately:true);persist();command(["action":"shutdown"]);input?.fileHandleForWriting.closeFile()}
}
@main
struct WindiSachNoi {
    static func main() {
        let app=NSApplication.shared
        let delegate=AppDelegate();app.delegate=delegate
        withExtendedLifetime(delegate){app.run()}
    }
}
