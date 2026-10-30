import AppKit
import WebKit

// Native WKWebView fixture. No user library, wallet secret, payment or paid API.
final class CreditUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,WKNavigationDelegate {
    var window:NSWindow!;var web:WKWebView!;var generations=0;var walletChecks=0;var paid=false;var offer=false
    let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
    var book:[String:Any]!
    let voice="094e72c3-97d3-439a-9e64-39ac3d3fa897"
    let orderID="12345678123442348234123456789012"
    func fail(_ message:String){fputs(message+"\n",stderr);exit(1)}
    func js(_ source:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(source){value,error in if let error=error{self.fail(error.localizedDescription)};done?(value)}}
    func send(_ value:[String:Any]){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))")}
    func after(_ seconds:Double,_ action:@escaping()->Void){DispatchQueue.main.asyncAfter(deadline:.now()+seconds,execute:action)}
    func check(_ script:String,_ message:String,_ done:@escaping()->Void){js(script){value in guard value as? Bool==true else{self.fail(message+": \(value ?? "nil")");return};done()}}
    func order()->[String:Any]{["id":orderID,"packId":"fixture-only","credits":1000,"amountVND":1,"content":"SC0123456789ABCDEF","bank":["name":"QA ONLY","bin":"970423","account":"0000000000","holder":"NO REAL PAYMENT"],"status":paid ? "paid":"pending"]}
    func wallet()->[String:Any]{["walletId":"fixture-only","balance":paid ? 1000:0,"packs":offer ? [["id":"fixture-only","credits":1000,"amountVND":1]]:[],"orders":offer ? [order()]:[],"salesReady":offer,"charactersPerCredit":1]}
    func models(){send(["event":"models","models":[["id":"nano","label":"VieNeu Nano","ready":true,"supported":true,"entitled":true,"bytes":282000000,"sampleRate":24000,"recommendedRAM":8,"languages":["vi"],"description":"Tạo sách nói trên Mac.","hardwareNote":"Phù hợp với máy này","voices":[["id":"Minh Quân","label":"Minh Quân","default":true]]],["id":"clone-pro","label":"Pro Max · Clone Pro 2.1","cloud":true,"ready":true,"supported":true,"entitled":true,"canDownload":false,"sampleRate":48000,"languages":["vi","en"],"bytes":0,"recommendedRAM":8,"hardwareNote":"Cần mạng khi tạo · Nghe audio đã tải không cần mạng","description":"Credit riêng trong app.","voices":[["id":voice,"label":"Minh Dự","default":true]]]],"hardware":["architecture":"arm64","memoryGB":16],"freeBytes":10000000000,"entitlement":["tier":"free","allowedModels":["nano","kitten","clone-pro"]],"credits":wallet()])}
    func snapshot(_ name:String,_ done:@escaping()->Void){after(0.2){self.web.takeSnapshot(with:nil){image,error in
        guard let image=image,let data=image.tiffRepresentation,let bitmap=NSBitmapImageRep(data:data),let png=bitmap.representation(using:.png,properties:[:]) else{self.fail("snapshot failed");return}
        try! png.write(to:self.root.appendingPathComponent(".qa/credit-ui/"+name));done()
    }}}
    func applicationDidFinishLaunching(_ notification:Notification){
        book=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(".qa/credit-ui/book.json"))) as? [String:Any]
        book["model"]="nano";book["voice"]="Minh Quân";book["sampleRate"]=24000;book["title"]="Sách kiểm thử · Local"
        NSApp.setActivationPolicy(.regular)
        let config=WKWebViewConfiguration();config.userContentController.add(self,name:"app")
        config.userContentController.addUserScript(WKUserScript(source:"window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));Object.defineProperty(document,'hidden',{get:()=>false});const qaTimeout=window.setTimeout;window.setTimeout=(f,t,...a)=>qaTimeout(f,t===10000?50:t,...a);",injectionTime:.atDocumentStart,forMainFrameOnly:true))
        web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:config);web.navigationDelegate=self
        window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
        web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
        after(25){self.fail("Credit UI timed out")}
    }
    func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
        guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
        switch action {
        case "qaError":fail(r["message"] as? String ?? "JS error")
        case "init":send(["event":"init","books":[["id":book["id"]!,"title":book["title"]!,"status":"ready","position":["segment":0,"seconds":0],"finished":false,"segments":3,"pages":3]],"voices":[],"ready":false,"music":[]]);models()
        case "get":send(["event":"book","book":book!])
        case "creditWallet":walletChecks+=1;send(["event":"cloudConnection","running":false,"success":true,"wallet":wallet(),"message":"Đã cập nhật ví credit."])
        case "creditPurchase":
            guard offer, r["packId"] as? String=="fixture-only",r["key"] as? String != nil else{fail("bad purchase action");return}
            send(["event":"cloudConnection","running":false,"success":true,"order":order()])
        case "creditQR":
            let payload=VietQR.payload(bin:"970423",account:"0000000000",amount:1,content:"SC0123456789ABCDEF")
            guard let qr=VietQR.vector(payload) else{fail("QR failed");return};send(["event":"creditQR","orderId":orderID,"qrPath":qr.path,"qrSize":qr.size])
        case "generate":
            generations+=1
            guard let consent=r["cloudConsent"] as? [String:Any],let segments=consent["segments"] as? [[String:Any]],segments.count==2,consent["voice"] as? String==voice,
                  !(segments.contains{($0["text"] as? String ?? "").contains("Phần mở đầu")}) else{fail("wrong consent range");return}
        default:break
        }
    }
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){after(0.3){
        self.js("$('theme').value='light';$('motion').value='off';applyAppearance();openCloud();refreshCredits();$('manageLicense').click();")
        self.after(0.2){self.check("!$('manageCloud')&&!$('cloudPanel').open&&!$('licensePanel').textContent.includes('Pro Max')&&!modelCatalog.some(m=>m.id==='clone-pro')&&!document.querySelector('#modelChoice option[value=\"clone-pro\"]')","Pro Max must remain hidden"){
            self.snapshot("paused-local-plans.png"){
                self.js("$('closeLicense').click();$('theme').value='dark';applyAppearance();openModels();")
                self.after(0.2){self.check("!document.querySelector('#modelList [data-model=\"clone-pro\"]')&&!!document.querySelector('#modelList [data-model=\"nano\"]')","local models must remain available"){
                    guard self.walletChecks==0,self.generations==0 else{self.fail("paused feature sent credit requests");return}
                    self.snapshot("paused-local-models.png"){print("UI PASS: Pro Max hidden from sidebar, plans and models; cloud entry points send no requests; local Free/Pro controls preserved. Fixtures only.");exit(0)}
                }}
            }
        }}
    }}
    func verifyWallet(){
        check("$('cloudPanel').open&&$('buyCredits').disabled&&$('creditBalance').textContent==='0'&&!document.querySelector('#cloudPanel input')&&$('creditPricingHint').textContent.includes('Chưa mở bán')","wallet must be separate and not for sale"){
            self.snapshot("wallet-no-prices-light.png"){
                self.offer=true;self.send(["event":"cloudConnection","running":false,"wallet":self.wallet()]);self.after(0.1){self.js("$('buyCredits').click();");self.after(0.3){self.verifyQR()}}
            }
        }
    }
    func verifyQR(){
        check("!$('creditOrder').hidden&&!!document.querySelector('#creditQR svg')&&$('creditBalance').textContent==='0'&&getComputedStyle(document.querySelector('#creditQR path')).stroke==='none'&&getComputedStyle(document.querySelector('#creditQR path')).fill==='rgb(0, 0, 0)'","QR must not add credit and must keep sharp black modules"){
            self.snapshot("credit-qr-fixture.png"){self.verifyPollClose()}
        }
    }
    func verifyPollClose(){
            self.js("$('closeCloud').click();");let checks=self.walletChecks
            self.after(0.3){guard self.walletChecks==checks else{self.fail("wallet polled after close");return}
                self.paid=true;self.send(["event":"cloudConnection","running":false,"wallet":self.wallet()])
                self.js("startPlay();");self.after(0.1){guard self.generations==0 else{self.fail("Play spent credit");return}
                    self.js("closeProduction();selectChapter('chapter');generateChapter(activeSection());$('theme').value='dark';applyAppearance();")
                    self.after(0.2){self.verifyConfirmation()}
                }
            }
    }
    func verifyConfirmation(){
        check("$('cloudConfirm').open&&$('cloudConfirmDetail').textContent.includes('2–3')&&$('cloudCreditEstimate').textContent.includes('credit app')","confirmation must show selected pages"){
            self.snapshot("confirm-dark.png"){
                self.js("$('cancelCloudConfirm').click();")
                self.after(0.1){guard self.generations==0 else{self.fail("Cancel spent credit");return}
                    self.js("generateChapter(activeSection());$('confirmCloudGenerate').click();")
                    self.after(0.15){guard self.generations==1 else{self.fail("Confirm did not generate exactly once");return}
                        self.js("$('appLanguage').value='en';$('appLanguage').onchange();$('theme').value='light';applyAppearance();$('manageCloud').click();")
                        self.after(0.2){self.check("$('cloudDescription').textContent.includes('No Clone Pro web account')&&$('creditBalance').textContent==='1.000'","English wallet copy missing"){
                            self.snapshot("wallet-en-light.png"){self.js("$('closeCloud').click();"){_ in print("UI PASS: separate wallet, prices disabled, QR does not fund, close stops polls, Play/Cancel do not spend, scoped confirmation, VI/EN and light/dark. Fixtures only.");exit(0)}}
                        }}
                    }
                }
            }
        }
    }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=CreditUIQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
