import Foundation
import AVFoundation

@main struct MusicPlaybackQA {
    static func main()throws {
        let base=URL(fileURLWithPath:FileManager.default.currentDirectoryPath).appendingPathComponent(".qa/music-native")
        try FileManager.default.createDirectory(at:base,withIntermediateDirectories:true)
        var urls:[URL]=[]
        for i in 0..<2 {
            let url=base.appendingPathComponent("\(i).wav")
            let format=AVAudioFormat(commonFormat:.pcmFormatInt16,sampleRate:24000,channels:1,interleaved:true)!
            let file=try AVAudioFile(forWriting:url,settings:format.settings,commonFormat:.pcmFormatInt16,interleaved:true)
            let buffer=AVAudioPCMBuffer(pcmFormat:format,frameCapacity:4800)!;buffer.frameLength=4800
            memset(buffer.int16ChannelData![0],0,9600);try file.write(from:buffer);urls.append(url)
        }
        precondition(MusicPlayback.position(seconds:2.5,durations:[2,1],loop:true)!.0==1)
        precondition(abs(MusicPlayback.position(seconds:3.25,durations:[2,1],loop:true)!.1-0.25)<0.001)
        precondition(MusicPlayback.position(seconds:3,durations:[2,1],loop:false)==nil)
        let player=MusicPlayback();var ended=false;player.onEnded={ended=true}
        try player.configure(urls:urls,volume:0,loop:false,offset:0,seek:true,shouldPlay:true)
        RunLoop.current.run(until:Date().addingTimeInterval(1.0))
        guard ended,player.index==1 else{fatalError("Native queue did not advance/finish")}
        try player.configure(urls:urls,volume:0,loop:true,offset:0.3,seek:true,shouldPlay:false)
        precondition(player.index==1);precondition(abs(player.player!.currentTime-0.1)<0.02)
        player.seek(to:0.45);precondition(player.index==0);precondition(abs(player.player!.currentTime-0.05)<0.02)
        player.stop()
        print("PASS: native playlist transition, no-loop finish, offset seek and repeat timeline")
    }
}
