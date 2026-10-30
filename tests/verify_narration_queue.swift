import Foundation
import AVFoundation

final class QueueQA:NSObject,AVAudioPlayerDelegate {
 let queue=NarrationQueue();var current:AVAudioPlayer!;var urls:[URL]=[];var index=0;var advances=0;var latencies:[Double]=[];var finished=false;var scheduledStarts:[Double]=[]
 func audioPlayerDidFinishPlaying(_ p:AVAudioPlayer,successfully flag:Bool){
  guard p===current else{return};precondition(flag)
  let scheduled=queue.scheduledTime
  if let (next,i)=queue.take(){
   scheduledStarts.append(scheduled)
   current=next;index=i;advances+=1
   // Scheduled next audio should already be near its intended start at callback.
   latencies.append(next.currentTime)

  }else{finished=true}
 }
 func run()throws{
  let dir=URL(fileURLWithPath:FileManager.default.currentDirectoryPath).appendingPathComponent(".qa/narration-native");try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
  for i in 0..<5{
   let u=dir.appendingPathComponent("\(i).wav"),f=AVAudioFormat(commonFormat:.pcmFormatInt16,sampleRate:24000,channels:1,interleaved:true)!
   let file=try AVAudioFile(forWriting:u,settings:f.settings,commonFormat:.pcmFormatInt16,interleaved:true)
   let b=AVAudioPCMBuffer(pcmFormat:f,frameCapacity:16800)!;b.frameLength=16800;memset(b.int16ChannelData![0],0,33600);try file.write(from:b);urls.append(u)
  }
  current=try AVAudioPlayer(contentsOf:urls[0]);current.enableRate=true;current.rate=1;current.volume=0;current.delegate=self;current.prepareToPlay();current.play()
  try queue.prepare(after:current,entries:Array(urls.enumerated().dropFirst()).map{($0.element,$0.offset)},delegate:self)
  RunLoop.current.run(until:Date().addingTimeInterval(0.15))
  queue.pause();current.pause();let before=advances
  RunLoop.current.run(until:Date().addingTimeInterval(0.85));precondition(advances==before && queue.player!.currentTime==0)
  current.rate=2;current.currentTime=0.3;current.play();queue.reschedule(after:current)
  RunLoop.current.run(until:Date().addingTimeInterval(2.5))
  precondition(finished && advances==4)
  let intervals=zip(scheduledStarts.dropFirst(),scheduledStarts).map{$0-$1}
  precondition(intervals.allSatisfy{abs($0-0.35)<0.001},"Scheduled audio boundaries are not contiguous: \(intervals)")
  let report:[String:Any]=["passed":true,"fixtureOnly":true,"advances":advances,"pauseHeldQueue":true,"seekAndRateRescheduled":true,"nextTimeAtCallback":latencies,"scheduledStartIntervals":intervals]
  let data=try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]);try data.write(to:dir.appendingPathComponent("report.json"));print(String(data:data,encoding:.utf8)!)
 }
}
@main struct Main {static func main()throws{try QueueQA().run()}}
