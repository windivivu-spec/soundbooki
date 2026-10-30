import Foundation
import AVFoundation

// One persisted playlist timeline shared with the WAV/M4A/web export mixer.
final class MusicPlayback:NSObject,AVAudioPlayerDelegate {
    var onEnded:(()->Void)?
    private(set) var player:AVAudioPlayer?
    private(set) var urls:[URL]=[]
    private(set) var durations:[Double]=[]
    private(set) var index=0
    private var loops=true
    private var exhausted=false
    private var gain:Float=0.12

    static func position(seconds:Double,durations:[Double],loop:Bool)->(Int,Double)? {
        let total=durations.reduce(0,+)
        guard seconds.isFinite,total>0,durations.allSatisfy({$0>0 && $0.isFinite}) else{return nil}
        var offset=max(0,seconds)
        if !loop && offset>=total{return nil}
        if loop {offset=offset.truncatingRemainder(dividingBy:total)}
        for (i,duration) in durations.enumerated(){if offset<duration{return (i,offset)};offset-=duration}
        return nil
    }
    func configure(urls:[URL],volume:Float,loop:Bool,offset:Double,seek:Bool,shouldPlay:Bool)throws {
        let changed=self.urls != urls
        gain=volume;loops=loop
        if changed {
            stop();self.urls=[];durations=[]
            // Validate the entire queue before starting any music.
            let lengths=try urls.map{url->Double in let p=try AVAudioPlayer(contentsOf:url);return p.duration}
            self.urls=urls;durations=lengths
        }
        if changed || seek {try setPosition(offset)}
        player?.volume=gain
        if shouldPlay {play()}else{pause()}
    }
    private func setPosition(_ offset:Double)throws {
        guard let (target,seconds)=Self.position(seconds:offset,durations:durations,loop:loops) else{player?.stop();exhausted=true;return}
        exhausted=false
        if index != target || player == nil {
            player?.stop();player=try AVAudioPlayer(contentsOf:urls[target]);index=target
            player?.delegate=self;player?.numberOfLoops=0;player?.volume=gain;player?.prepareToPlay()
        }
        player?.currentTime=seconds
    }
    func seek(to seconds:Double){let active=player?.isPlaying==true;do{try setPosition(seconds);if active{play()}}catch{stop()}}
    func play(){if !exhausted{player?.play()}}
    func pause(){player?.pause()}
    func stop(){player?.stop();player=nil;index=0;exhausted=false}
    func audioPlayerDidFinishPlaying(_ finished:AVAudioPlayer,successfully flag:Bool){
        guard finished === player else{return}
        guard flag,!urls.isEmpty,index+1<urls.count || loops else{exhausted=true;onEnded?();return}
        let target=(index+1)%urls.count
        do{
            player=try AVAudioPlayer(contentsOf:urls[target]);index=target;player?.delegate=self
            player?.numberOfLoops=0;player?.volume=gain;player?.prepareToPlay();player?.play()
        }catch{exhausted=true;onEnded?()}
    }
}
