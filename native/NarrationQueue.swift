import Foundation
import AVFoundation

// Decode and schedule contiguous WAVs on one device clock before delegates fire.
final class NarrationQueue {
    private struct Item {let player:AVAudioPlayer;let segment:Int;let url:URL;var time:TimeInterval}
    private var items:[Item]=[]
    private var paused=false
    var player:AVAudioPlayer? {items.first?.player}
    var segment:Int {items.first?.segment ?? 0}
    var scheduledTime:TimeInterval {items.first?.time ?? 0}

    func prepare(after current:AVAudioPlayer,url:URL,segment:Int,delegate:AVAudioPlayerDelegate?) throws {
        clear();try prepare(after:current,entries:[(url,segment)],delegate:delegate)
    }
    func prepare(after current:AVAudioPlayer,entries:[(URL,Int)],delegate:AVAudioPlayerDelegate?) throws {
        let prefix=zip(items,entries).allSatisfy{$0.url==$1.0 && $0.segment==$1.1}
        if !prefix || entries.count<items.count{let held=paused;clear();paused=held}
        let active=current.isPlaying || (!paused && (!items.isEmpty || current.currentTime>=current.duration-0.005))
        if current.isPlaying{paused=false}
        for (url,index) in entries.dropFirst(items.count) {
            let next=try AVAudioPlayer(contentsOf:url)
            next.enableRate=true;next.rate=current.rate;next.volume=current.volume;next.delegate=delegate;next.prepareToPlay()
            let time:TimeInterval
            if let previous=items.last{time=previous.time+previous.player.duration/Double(max(0.5,current.rate))}
            else{time=current.deviceCurrentTime+max(0,current.duration-current.currentTime)/Double(max(0.5,current.rate))}
            items.append(Item(player:next,segment:index,url:url,time:time))
            if active{next.play(atTime:time)}
        }
    }
    func reschedule(after current:AVAudioPlayer){
        paused = !current.isPlaying
        var time=current.deviceCurrentTime+max(0,current.duration-current.currentTime)/Double(max(0.5,current.rate))
        for i in items.indices {
            let next=items[i].player;next.stop();next.currentTime=0;next.rate=current.rate;next.volume=current.volume;next.prepareToPlay();items[i].time=time
            if current.isPlaying{next.play(atTime:time)}
            time+=next.duration/Double(max(0.5,current.rate))
        }
    }
    func setVolume(_ volume:Float){for item in items{item.player.volume=volume}}
    func pause(){paused=true;for item in items{item.player.stop();item.player.currentTime=0}}
    func take()->(AVAudioPlayer,Int)?{
        guard !items.isEmpty else{return nil}
        let next=items.removeFirst()
        return (next.player,next.segment)
    }
    func clear(){for item in items{item.player.stop()};items=[];paused=false}
}
