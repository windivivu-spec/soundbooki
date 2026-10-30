import Foundation
import AVFoundation

// Separate local players: welcome audio never changes a book's narration or music settings.
final class WelcomePlayback {
    static let voiceGain:Float=0.8
    static let musicGain:Float=0.4
    static let musicFile="assets/music/prepared/music-96aee74561b611f1.wav" // Piano podcast / 1.mp3
    private(set) var voice:AVAudioPlayer?
    private(set) var music:AVAudioPlayer?
    private(set) var active=false
    private(set) var muted=false
    private var stopTimer:Timer?

    func start(root:URL,muted:Bool)throws {
        if active {setMuted(muted);return} // A page change cannot restart the greeting.
        stop(immediately:true)
        let nextVoice=try AVAudioPlayer(contentsOf:root.appendingPathComponent("assets/welcome/welcome.wav"))
        let nextMusic=try AVAudioPlayer(contentsOf:root.appendingPathComponent(Self.musicFile))
        guard nextVoice.duration>0,nextMusic.duration>0 else{throw CocoaError(.fileReadCorruptFile)}
        voice=nextVoice;music=nextMusic;self.muted=muted;active=true
        nextVoice.numberOfLoops=0;nextMusic.numberOfLoops = -1
        nextVoice.volume=muted ? 0:Self.voiceGain;nextMusic.volume=0
        nextVoice.prepareToPlay();nextMusic.prepareToPlay()
        // Each player's device clock starts together; only the music eases in.
        guard nextVoice.play(atTime:nextVoice.deviceCurrentTime+0.1),nextMusic.play(atTime:nextMusic.deviceCurrentTime+0.1) else{
            stop(immediately:true);throw CocoaError(.fileReadUnknown)
        }
        nextMusic.setVolume(muted ? 0:Self.musicGain,fadeDuration:1.8)
    }
    func setMuted(_ value:Bool){
        muted=value
        voice?.setVolume(value ? 0:Self.voiceGain,fadeDuration:value ? 0.15:0.5)
        music?.setVolume(value ? 0:Self.musicGain,fadeDuration:value ? 0.15:0.8)
    }
    func stop(immediately:Bool=false){
        stopTimer?.invalidate();stopTimer=nil;active=false
        if immediately {clear();return}
        voice?.setVolume(0,fadeDuration:0.35);music?.setVolume(0,fadeDuration:0.7)
        stopTimer=Timer.scheduledTimer(withTimeInterval:0.72,repeats:false){[weak self] _ in self?.clear()}
    }
    private func clear(){stopTimer?.invalidate();stopTimer=nil;voice?.stop();music?.stop();voice=nil;music=nil}
    deinit{stopTimer?.invalidate();voice?.stop();music?.stop()}
}
