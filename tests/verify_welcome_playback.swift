import Foundation
import AVFoundation

@main struct WelcomeQA {
    static func require(_ ok:Bool,_ reason:String){if !ok{fputs("FAIL: "+reason+"\n",stderr);exit(1)}}
    static func wait(_ seconds:Double){RunLoop.current.run(until:Date().addingTimeInterval(seconds))}
    static func main()throws {
        let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath),p=WelcomePlayback()
        try p.start(root:root,muted:true);wait(0.3)
        require(p.voice?.isPlaying==true && p.music?.isPlaying==true,"Both real local files must play")
        require(abs((p.voice?.duration ?? 0)-18.08)<0.01,"Provided welcome file preserved")
        require(p.voice?.volume==0 && p.music?.volume==0,"Muted startup")
        let voice=p.voice,music=p.music,at=p.voice!.currentTime
        try p.start(root:root,muted:true);wait(0.2)
        require(p.voice===voice && p.music===music && p.voice!.currentTime>at,"Repeated start must not restart or overlap")
        p.setMuted(false);wait(1)
        require(abs(p.voice!.volume-0.8)<0.001 && abs(p.music!.volume-0.4)<0.001,"80 percent voice and 40 percent music")
        require(p.voice!.numberOfLoops==0 && p.music!.numberOfLoops == -1,"Greeting once, music loops")
        let beforeMute=p.voice!.currentTime
        p.setMuted(true);wait(0.3)
        require(p.voice!.volume==0 && p.music!.volume==0 && p.voice!.currentTime>beforeMute,"Mute preserves the shared timeline")
        p.stop();require(!p.active,"Close ends active session")
        try p.start(root:root,muted:true);let reopened=p.voice;wait(0.9)
        require(p.active && p.voice===reopened && p.voice?.isPlaying==true,"Old fade must not stop a reopened greeting")
        p.stop();wait(0.85)
        require(p.voice==nil && p.music==nil && !p.active,"Fade releases both players")
        do{try p.start(root:root.appendingPathComponent(".qa/missing-welcome-assets"),muted:false);require(false,"Missing assets must fail")}catch{}
        require(!p.active && p.voice==nil && p.music==nil,"Missing files leave no partial playback")
        print("PASS: real 18.08s welcome + Piano podcast Bài 01, voice 80% / music 40%, mute, single greeting, looping music, idempotent start, close fade, rapid reopen, missing-assets cleanup")
    }
}
