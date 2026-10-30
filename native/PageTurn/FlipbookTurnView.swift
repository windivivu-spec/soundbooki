// Adapted from rayhankhilji/flipbook, PageTurnNSView.swift.
// Upstream 94c8724245e768e9f597c3b1859a300ef061797e (MIT, Rayhan Khilji 2026).
// See licenses/Flipbook-MIT.txt. Adaptation: WKWebView ebook snapshots instead of
// PDF ReadingSession; no upstream persistence, providers, AI or network code.
import AppKit
import QuartzCore

final class FlipbookTurnView:NSView {
    let leftPage=CALayer(),rightPage=CALayer(),flipContainer=CATransformLayer()
    let front=CALayer(),back=CALayer(),frontShade=CAGradientLayer(),backShade=CAGradientLayer()
    let castShadow=CAGradientLayer(),spine=CAGradientLayer()
    private(set) var progress:CGFloat=0
    private(set) var forward=true
    private var single=false
    private var old:CGImage?
    private var next:CGImage?
    private var generation=0
    var completion:((Bool)->Void)?
    override var isFlipped:Bool{true}
    override func hitTest(_ point:NSPoint)->NSView?{nil}
    override init(frame:NSRect){
        super.init(frame:frame);wantsLayer=true;layerContentsRedrawPolicy = .onSetNeedsDisplay;layer?.masksToBounds=true
        var perspective=CATransform3DIdentity;perspective.m34 = -1/1600.0;layer?.sublayerTransform=perspective
        for face in [leftPage,rightPage,front,back]{face.contentsGravity = .resize;face.minificationFilter = .trilinear;face.isDoubleSided=false}
        for shade in [frontShade,backShade,castShadow,spine]{shade.startPoint=CGPoint(x:0,y:0.5);shade.endPoint=CGPoint(x:1,y:0.5)}
        spine.colors=[CGColor(gray:0,alpha:0),CGColor(gray:0,alpha:0.14),CGColor(gray:0,alpha:0)]
        front.addSublayer(frontShade);back.addSublayer(backShade);back.transform=CATransform3DMakeRotation(.pi,0,1,0)
        flipContainer.addSublayer(front);flipContainer.addSublayer(back)
        for child in [leftPage,rightPage,castShadow,spine,flipContainer]{layer?.addSublayer(child)}
        flipContainer.isHidden=true;castShadow.opacity=0
    }
    required init?(coder:NSCoder){nil}
    func begin(image:CGImage,forward:Bool,single:Bool,paper:CGColor,dark:Bool){
        generation+=1;self.old=image;self.next=nil;self.forward=forward;self.single=single;progress=0
        layer?.backgroundColor=paper
        for face in [leftPage,rightPage,front,back]{face.backgroundColor=paper;face.contentsScale=window?.backingScaleFactor ?? 2}
        let alpha:CGFloat=dark ? 0.42:0.34
        castShadow.colors=[CGColor(gray:0,alpha:alpha),CGColor(gray:0,alpha:alpha*0.45),CGColor(gray:0,alpha:0)]
        for shade in [frontShade,backShade]{shade.colors=[CGColor(gray:0,alpha:alpha*0.8),CGColor(gray:0,alpha:0.02)]}
        CATransaction.begin();CATransaction.setDisableActions(true)
        leftPage.frame=CGRect(x:0,y:0,width:bounds.width/2,height:bounds.height);rightPage.frame=CGRect(x:bounds.width/2,y:0,width:bounds.width/2,height:bounds.height)
        leftPage.contents=half(image,left:true);rightPage.contents=half(image,left:false)
        spine.frame=CGRect(x:bounds.midX-12,y:0,width:24,height:bounds.height);spine.isHidden=single
        flipContainer.isHidden=true;CATransaction.commit()
    }
    private func half(_ image:CGImage,left:Bool)->CGImage?{
        let split=image.width/2
        return image.cropping(to:CGRect(x:left ? 0:split,y:0,width:left ? split:image.width-split,height:image.height))
    }
    func stage(image:CGImage){
        next=image;guard let old=old else{return}
        CATransaction.begin();CATransaction.setDisableActions(true)
        let width=single ? bounds.width:bounds.width/2
        let anchor:CGFloat=forward ? 0:1
        flipContainer.bounds=CGRect(x:0,y:0,width:width,height:bounds.height)
        flipContainer.anchorPoint=CGPoint(x:anchor,y:0.5)
        flipContainer.position=CGPoint(x:single ? 0:bounds.midX,y:bounds.midY)
        let face=CGRect(x:0,y:0,width:width,height:bounds.height)
        front.frame=face;back.frame=face;frontShade.frame=face;backShade.frame=face
        front.contents=single ? old:half(old,left:!forward)
        back.contents=single ? image:half(image,left:forward)
        if forward{rightPage.contents=half(image,left:false)}else{leftPage.contents=half(image,left:true)}
        castShadow.frame=forward ? rightPage.frame:leftPage.frame
        castShadow.startPoint=CGPoint(x:forward ? 0:1,y:0.5);castShadow.endPoint=CGPoint(x:forward ? 1:0,y:0.5)
        frontShade.startPoint=castShadow.startPoint;frontShade.endPoint=castShadow.endPoint
        backShade.startPoint=castShadow.endPoint;backShade.endPoint=castShadow.startPoint
        flipContainer.isHidden=false;CATransaction.commit();apply(progress:progress)
    }
    // Upstream's two-sided rotation and progress-driven self/cast shading.
    func apply(progress:CGFloat){
        self.progress=min(max(progress,0),1);let p=self.progress,lift=sin(p * .pi)
        CATransaction.begin();CATransaction.setDisableActions(true)
        flipContainer.transform=CATransform3DMakeRotation((forward ? -1:1) * .pi * p,0,1,0)
        frontShade.opacity=Float(min(p*2,1)*lift);backShade.opacity=Float(min((1-p)*2,1)*lift)
        castShadow.opacity=Float(lift*0.9);spine.opacity=Float(0.9+0.7*lift)
        CATransaction.commit()
    }
    func settle(commit:Bool,velocity:CGFloat){
        generation+=1;let stamp=generation
        guard !single else{completion?(commit);return}
        let target:CGFloat=commit ? 1:0,remaining=abs(target-progress)
        if remaining<0.002{completion?(commit);return}
        let spring=CASpringAnimation(keyPath:"transform")
        spring.fromValue=flipContainer.presentation()?.transform ?? flipContainer.transform
        let finalTransform=CATransform3DMakeRotation((forward ? -1:1) * .pi * target,0,1,0)
        spring.toValue=finalTransform
        spring.damping=32;spring.stiffness=260;spring.mass=1
        spring.initialVelocity=min(max(commit ? velocity:-velocity,0)/max(remaining,0.01),12)
        spring.duration=min(spring.settlingDuration,0.8)
        CATransaction.begin();CATransaction.setDisableActions(true)
        flipContainer.transform=finalTransform
        flipContainer.add(spring,forKey:"settle")
        // The transform uses the original spring constants. Keyframes retain the
        // upstream lift/shading curve throughout a button-initiated full turn.
        for (shade,kind) in [(frontShade,0),(backShade,1),(castShadow,2)] {
            let animation=CAKeyframeAnimation(keyPath:"opacity");animation.duration=spring.duration
            animation.values=(0...24).map{step->Float in let p=progress+(target-progress)*CGFloat(step)/24,lift=sin(p * .pi);return Float(kind==2 ? lift*0.9:min(kind==0 ? p*2:(1-p)*2,1)*lift)}
            animation.keyTimes=(0...24).map{NSNumber(value:Double($0)/24)};shade.opacity=0;shade.add(animation,forKey:"depth")
        }
        CATransaction.commit()
        DispatchQueue.main.asyncAfter(deadline:.now()+spring.duration){[weak self] in guard let self=self,self.generation==stamp else{return};self.apply(progress:target);self.completion?(commit)}
    }
    func cancel(){generation+=1;layer?.sublayers?.forEach{$0.removeAllAnimations()};completion=nil;removeFromSuperview()}
}
