import AppKit
import WebKit

// Local snapshots only. GulLabs' HTML engine handles the curl in WebKit.
// This non-interactive cover hides the two-frame DOM change while capturing
// the destination; no native flat rotation or audio work happens here.
private final class EbookCaptureCover:NSImageView {
    override func hitTest(_ point:NSPoint)->NSView?{nil}
}
final class EbookTurnBridge {
    weak var web:WKWebView?
    var emit:(([String:Any])->Void)?
    private(set) var overlay:NSImageView?
    private(set) var token=""
    private var rect=CGRect.zero
    private var staged=false
    private let encoder=DispatchQueue(label:"studio.windi.page-turn-encoding",qos:.userInitiated)
    func handle(_ value:[String:Any]){
        switch value["action"] as? String {
        case "beginPageTurn":begin(value)
        case "stagePageTurn":stage(value)
        case "releasePageTurn":if matches(value){overlay?.removeFromSuperview();overlay=nil}
        case "endPageTurn":if matches(value){cancel()}
        case "cancelPageTurn":cancel()
        default:break
        }
    }
    private func bounded(_ value:Any?,_ lo:CGFloat,_ hi:CGFloat)->CGFloat{let v=(value as? NSNumber)?.doubleValue ?? 0;return v.isFinite ? min(hi,max(lo,CGFloat(v))):lo}
    private func matches(_ value:[String:Any])->Bool{value["token"] as? String==token && !token.isEmpty}
    func cancel(){overlay?.removeFromSuperview();overlay=nil;token="";staged=false}
    private func begin(_ value:[String:Any]){
        cancel();guard let web=web,let host=web.superview,let id=value["token"] as? String,id.range(of:"^[a-f0-9]{32}$",options:.regularExpression) != nil else{return}
        token=id
        let x=bounded(value["x"],0,web.bounds.width),y=bounded(value["y"],0,web.bounds.height)
        rect=CGRect(x:x,y:y,width:bounded(value["width"],0,web.bounds.width-x),height:bounded(value["height"],0,web.bounds.height-y))
        guard rect.width>=100,rect.height>=80,!NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else{fallback(id);return}
        snapshot{[weak self,weak web,weak host] image,png in
            guard let self=self,self.token==id,let web=web,let host=host else{return}
            guard let image=image,let png=png else{self.fallback(id);return}
            let view=EbookCaptureCover(frame:web.convert(self.rect,to:host));view.image=image;view.imageScaling = .scaleAxesIndependently;view.wantsLayer=true
            view.layer?.backgroundColor=CGColor(red:self.bounded(value["red"],0,1),green:self.bounded(value["green"],0,1),blue:self.bounded(value["blue"],0,1),alpha:1)
            view.setAccessibilityElement(false);host.addSubview(view,positioned:.above,relativeTo:web);self.overlay=view
            self.emit?(["event":"pageTurnCaptured","token":id,"image":png])
        }
        DispatchQueue.main.asyncAfter(deadline:.now()+2){[weak self] in guard let self=self,self.token==id,!self.staged else{return};self.fallback(id)}
    }
    private func fallback(_ id:String){emit?(["event":"pageTurnFallback","token":id]);cancel()}
    private func snapshot(_ done:@escaping(NSImage?,String?)->Void){
        guard let web=web else{done(nil,nil);return};let config=WKSnapshotConfiguration();config.rect=rect;config.afterScreenUpdates=true
        // Bound transient animation faces in pixels, independent of Retina/window size.
        let scale=web.window?.backingScaleFactor ?? 2
        config.snapshotWidth=NSNumber(value:Double(min(rect.width,1400/max(1,scale))))
        let id=token
        web.takeSnapshot(with:config){[weak self] image,_ in
            guard let self=self,self.token==id,let image=image,let cg=image.cgImage(forProposedRect:nil,context:nil,hints:nil) else{done(nil,nil);return}
            self.encoder.async{
                let png=NSBitmapImageRep(cgImage:cg).representation(using:.png,properties:[:])
                let encoded=png.map{"data:image/png;base64,"+$0.base64EncodedString()}
                DispatchQueue.main.async{guard self.token==id else{return};done(image,encoded)}
            }
        }
    }

    private func stage(_ value:[String:Any]){
        guard matches(value),!staged else{return};let id=token
        snapshot{[weak self] image,png in
            guard let self=self,self.token==id else{return}
            guard image != nil,let png=png,self.overlay != nil else{self.fallback(id);return}
            self.staged=true
            DispatchQueue.main.asyncAfter(deadline:.now()+30){[weak self] in guard let self=self,self.token==id else{return};self.fallback(id)}
            self.emit?(["event":"pageTurnStaged","token":id,"image":png])
        }
    }
}
