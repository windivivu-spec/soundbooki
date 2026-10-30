import AppKit
import WebKit

// Controlled UI fixture: no bank requests, no license writes, no user library.
final class PaymentUIQA:NSObject,NSApplicationDelegate,WKScriptMessageHandler,WKNavigationDelegate {
    var window:NSWindow!;var web:WKWebView!;var stage="purchase";var checks=0;var renewalChecks=0
    let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
    let expiry="2027-10-20T00:00:00Z"
    func applicationDidFinishLaunching(_ notification:Notification){
        NSApp.setActivationPolicy(.regular)
        let config=WKWebViewConfiguration();config.userContentController.add(self,name:"app")
        // The desktop test runner can occlude this window. Visibility lifecycle
        // is tested separately; keep this fixture visible for deterministic timers.
        config.userContentController.addUserScript(WKUserScript(source:"Object.defineProperty(document,'hidden',{get:()=>false});window.addEventListener('error',e=>window.webkit.messageHandlers.app.postMessage({action:'qaError',message:e.message}));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
        web=WKWebView(frame:NSRect(x:0,y:0,width:1180,height:800),configuration:config);web.navigationDelegate=self
        window=NSWindow(contentRect:web.bounds,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.contentView=web;window.makeKeyAndOrderFront(nil)
        web.loadFileURL(root.appendingPathComponent("ui/index.html"),allowingReadAccessTo:root.appendingPathComponent("ui"));NSApp.activate(ignoringOtherApps:true)
        DispatchQueue.main.asyncAfter(deadline:.now()+30){self.js("JSON.stringify({ready:document.readyState,receive:typeof window.receive,watcher:typeof PaymentWatcher,disabled:document.getElementById('buyPro')?.disabled})"){value in self.fail("UI test timed out: \(value ?? "no DOM")")}}
    }
    func fail(_ message:String){fputs(message+"\n",stderr);exit(1)}
    func js(_ script:String,_ done:((Any?)->Void)?=nil){web.evaluateJavaScript(script){result,error in if let error=error{self.fail(error.localizedDescription)};done?(result)}}
    func send(_ value:[String:Any]){let data=try! JSONSerialization.data(withJSONObject:value);js("window.receive(\(String(data:data,encoding:.utf8)!))")}
    func models(_ pro:Bool){send(["event":"models","models":[],"hardware":["architecture":"arm64","memoryGB":16],"freeBytes":10000000000,"entitlement":["tier":pro ? "pro":"free","allowedModels":pro ? ["nano","kitten","f5-private"]:["nano","kitten"],"deviceCode":"SN000000000000","checkoutURL":"https://img.vietqr.io/image/TPB-55111685555-qr_only.png?amount=189000&accountName=BUI%20QUOC%20HUNG","licenseBaseURL":"https://example.invalid/licenses/","expiresAt":pro ? expiry:"","privateVoiceIncluded":true]])}
    func snapshot(_ name:String,_ done:@escaping()->Void){
        DispatchQueue.main.asyncAfter(deadline:.now()+0.4){
            self.web.takeSnapshot(with:nil){image,error in
                guard let image=image,let data=image.tiffRepresentation,let rep=NSBitmapImageRep(data:data),let png=rep.representation(using:.png,properties:[:]) else{self.fail("snapshot failed");return}
                let folder=self.root.appendingPathComponent(".qa/payment-copy");try! FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true);try! png.write(to:folder.appendingPathComponent(name));done()
            }
        }
    }
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){
        fputs("loaded UI\n",stderr)
        DispatchQueue.main.asyncAfter(deadline:.now()+0.3){self.js("$('theme').value='dark';applyAppearance();paymentWatcher.interval=60;$('manageLicense').click();$('buyPro').click();")}
    }
    func userContentController(_ controller:WKUserContentController,didReceive message:WKScriptMessage){
        guard let r=message.body as? [String:Any],let action=r["action"] as? String else{return}
        fputs("bridge: \(action)\n",stderr)
        if action=="qaError"{fail(r["message"] as? String ?? "JavaScript error")}
        if action=="init"{send(["event":"init","books":[],"voices":[],"ready":false,"music":[]]);models(false)}
        if action=="purchase"{
            let config:[String:Any]=["checkoutURL":"https://img.vietqr.io/image/TPB-55111685555-qr_only.png?amount=189000&accountName=BUI%20QUOC%20HUNG"]
            guard let qr=VietQR.checkout(config,device:"SN000000000000") else{fail("QR fixture failed");return};send(qr)
        }
        if action != "checkLicense"{return}
        guard let id=r["requestId"] as? String else{fail("missing requestId");return}
        checks+=1
        if stage=="purchase"&&checks==1 {
            snapshot("qr-dark-vi.png") {self.send(["event":"licenseCheck","requestId":id,"state":"pending"])}
        } else if stage=="purchase" {
            models(true);send(["event":"licenseImported","requestId":id])
            DispatchQueue.main.asyncAfter(deadline:.now()+0.2){self.js("$('paymentPanel').dataset.state==='success'&&!$('paymentSuccess').hidden&&$('paymentContent').hidden") {ok in
                guard ok as? Bool==true else{self.fail("automatic success not shown");return}
                self.stage="renewal";self.js("closePayment();openLicense();paymentWatcher.interval=1000;$('buyPro').click();")
            }}
        } else if stage=="renewal" {
            renewalChecks+=1;guard r["afterExpiresAt"] as? String==expiry else{fail("renewal missing old expiry");return}
            send(["event":"licenseCheck","requestId":id,"state":"pending"])
            js("$('paymentSuccess').hidden&&$('paymentPanel').dataset.state==='pending'") {ok in
                guard ok as? Bool==true else{self.fail("old license became purchase success");return}
                self.stage="closed";self.js("closePayment();")
                DispatchQueue.main.asyncAfter(deadline:.now()+1.2){
                    guard self.renewalChecks==1 else{self.fail("polling continued after closing");return}
                    self.stage="english";self.js("$('appLanguage').value='en';$('appLanguage').onchange();$('theme').value='light';applyAppearance();$('buyPro').click();")
                }
            }
        } else if stage=="english" {
            send(["event":"licenseCheck","requestId":id,"state":"pending"])
            js("({ok:$('paymentStatus').textContent.includes('automatically')&&$('checkPayment').textContent==='Check now',qrHidden:$('paymentQR').hasAttribute('hidden'),qrDisplay:getComputedStyle($('paymentQR')).display,qrFill:getComputedStyle($('paymentQR').querySelector('path')).fill})") {value in
                guard let value=value as? [String:Any],value["ok"] as? Bool==true else{self.fail("English payment copy missing");return}
                guard value["qrHidden"] as? Bool==false,value["qrDisplay"] as? String != "none",value["qrFill"] as? String=="rgb(0, 0, 0)" else{self.fail("QR hidden on reopen: \(value)");return}
                self.js("(()=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),a=[];let n;while(n=w.nextNode()){if(n.parentElement.closest('script,style,.user-text'))continue;const s=n.nodeValue.trim();if(/[À-ỹĐđ]/.test(s)&&!s.includes('Windi Sách Nói'))a.push(s)}return JSON.stringify([...new Set(a)])})()") {report in
                    let folder=self.root.appendingPathComponent(".qa/payment-copy");try! (report as? String ?? "[]").write(to:folder.appendingPathComponent("untranslated.json"),atomically:true,encoding:.utf8)
                    self.snapshot("qr-light-en.png") {self.js("closePayment();"){_ in print("UI PASS: auto pending→success, renewal baseline, close cancellation, VI/EN, dark/light; fixtures only");exit(0)}}
                }
            }
        } else {fail("unexpected check after close")}
    }
}
@main struct Main{static func main(){let app=NSApplication.shared;let delegate=PaymentUIQA();app.delegate=delegate;withExtendedLifetime(delegate){app.run()}}}
