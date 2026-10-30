package studio.windi.soundbooki;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.media.*;
import android.os.Handler;
import android.os.Looper;

/**
 * Separate local players for walkthrough discovery:
 * - Welcome greeting (assets/welcome/welcome.wav) plays once at 80% gain.
 * - Piano podcast Bài 01 (assets/welcome/piano_podcast_1.mp3) loops at 40% gain with 1.8s fade-in.
 * - Gentle acoustic harmonic chimes play on page transitions and CTA actions when unmuted.
 * Never alters book narration or cache state.
 */
public final class WelcomeAudioPlayer {
    public static final float VOICE_GAIN = 0.8f;
    public static final float MUSIC_GAIN = 0.4f;
    private static final String VOICE_ASSET = "welcome/welcome.wav";
    private static final String MUSIC_ASSET = "welcome/piano_podcast_1.mp3";

    private final Handler handler = new Handler(Looper.getMainLooper());
    private MediaPlayer voice;
    private MediaPlayer music;
    private boolean active = false;
    private boolean muted = false;
    private long sessionToken = 0;

    public boolean isActive() {
        return active;
    }

    public boolean isMuted() {
        return muted;
    }

    public boolean isVoiceReady() {
        return voice != null;
    }

    public boolean isMusicReady() {
        return music != null;
    }

    public void start(Context context, boolean initialMuted) throws Exception {
        if (active && voice != null && music != null) {
            setMuted(initialMuted);
            return; // Paging never restarts the greeting.
        }
        stop(true);
        sessionToken++;
        long token = sessionToken;
        muted = initialMuted;

        MediaPlayer nextVoice = new MediaPlayer();
        MediaPlayer nextMusic = new MediaPlayer();
        try {
            AudioAttributes attrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build();
            nextVoice.setAudioAttributes(attrs);
            nextMusic.setAudioAttributes(attrs);

            try (AssetFileDescriptor vfd = context.getAssets().openFd(VOICE_ASSET)) {
                nextVoice.setDataSource(vfd.getFileDescriptor(), vfd.getStartOffset(), vfd.getLength());
            }
            try (AssetFileDescriptor mfd = context.getAssets().openFd(MUSIC_ASSET)) {
                nextMusic.setDataSource(mfd.getFileDescriptor(), mfd.getStartOffset(), mfd.getLength());
            }
            nextVoice.setLooping(false);
            nextMusic.setLooping(true);
            nextVoice.prepare();
            nextMusic.prepare();

            float vGain = muted ? 0f : VOICE_GAIN;
            nextVoice.setVolume(vGain, vGain);
            nextMusic.setVolume(0f, 0f);

            voice = nextVoice;
            music = nextMusic;
            active = true;

            nextMusic.start();
            if (!muted) {
                fadeMusicTo(token, 0f, MUSIC_GAIN, 1800);
                // Delay voice start by 0.8s so background music fades in first, and first words of greeting are clear
                handler.postDelayed(() -> {
                    if (active && token == sessionToken && !muted && voice != null) {
                        setPlayerVol(voice, VOICE_GAIN);
                        try {
                            voice.start();
                        } catch (Exception ignored) {}
                    }
                }, 800L);
            }
        } catch (Exception e) {
            safeRelease(nextVoice);
            safeRelease(nextMusic);
            voice = null;
            music = null;
            active = false;
            throw e;
        }
    }

    public void setMuted(boolean value) {
        this.muted = value;
        long token = ++sessionToken;
        handler.removeCallbacksAndMessages(null);
        if (!active) return;
        float targetVoice = value ? 0f : VOICE_GAIN;
        float targetMusic = value ? 0f : MUSIC_GAIN;
        int dur = value ? 150 : 550;
        fadeBoth(token, value ? VOICE_GAIN : 0f, targetVoice, value ? MUSIC_GAIN : 0f, targetMusic, dur);
        if (!value && voice != null) {
            try {
                if (!voice.isPlaying()) {
                    setPlayerVol(voice, VOICE_GAIN);
                    voice.start();
                }
            } catch (Exception ignored) {}
        }
    }

    public void stop(boolean immediately) {
        active = false;
        long token = ++sessionToken;
        handler.removeCallbacksAndMessages(null);
        if (immediately || (voice == null && music == null)) {
            clear();
            return;
        }
        final MediaPlayer v = voice, m = music;
        final float startV = muted ? 0f : VOICE_GAIN;
        final float startM = muted ? 0f : MUSIC_GAIN;
        final int steps = 8;
        for (int i = 1; i <= steps; i++) {
            final int step = i;
            handler.postDelayed(() -> {
                if (token != sessionToken) return;
                float ratio = 1f - (step / (float) steps);
                setPlayerVol(v, startV * ratio);
                setPlayerVol(m, startM * ratio);
                if (step == steps) clear();
            }, i * 65L);
        }
    }

    /** Plays a soft, warm harmonic acoustic chime on page step or completion when unmuted. */
    public void playEffect(String kind) {
        if (muted) return;
        new Thread(() -> {
            AudioTrack track = null;
            try {
                int sr = 24000;
                double durationSec = "complete".equals(kind) ? 0.34 : 0.14;
                int samples = (int) (sr * durationSec);
                short[] pcm = new short[samples];
                double f1 = "complete".equals(kind) ? 587.33 : ("back".equals(kind) ? 440.0 : 523.25);
                double f2 = "complete".equals(kind) ? 880.0 : ("back".equals(kind) ? 659.25 : 783.99);
                for (int i = 0; i < samples; i++) {
                    double t = i / (double) sr;
                    double env = Math.sin(Math.PI * Math.pow(i / (double) samples, 0.65));
                    double wave = 0.65 * Math.sin(2.0 * Math.PI * f1 * t)
                                + 0.35 * Math.sin(2.0 * Math.PI * f2 * t);
                    double val = wave * env * 0.16;
                    pcm[i] = (short) Math.max(-32767, Math.min(32767, Math.round(val * 32767.0)));
                }
                track = new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build())
                    .setAudioFormat(new AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(sr)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build())
                    .setBufferSizeInBytes(pcm.length * 2)
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .build();
                track.write(pcm, 0, pcm.length);
                track.play();
                Thread.sleep((long) (durationSec * 1000) + 60);
            } catch (Throwable ignored) {
            } finally {
                if (track != null) {
                    try { track.release(); } catch (Exception ignored) {}
                }
            }
        }, "soundbooki-sfx").start();
    }

    private void fadeMusicTo(long token, float from, float to, int durationMs) {
        int steps = 12;
        long stepMs = Math.max(16, durationMs / steps);
        for (int i = 1; i <= steps; i++) {
            final int s = i;
            handler.postDelayed(() -> {
                if (!active || token != sessionToken || muted) return;
                float vol = from + (to - from) * (s / (float) steps);
                setPlayerVol(music, vol);
            }, i * stepMs);
        }
    }

    private void fadeBoth(long token, float vFrom, float vTo, float mFrom, float mTo, int durationMs) {
        int steps = 8;
        long stepMs = Math.max(16, durationMs / steps);
        for (int i = 1; i <= steps; i++) {
            final int s = i;
            handler.postDelayed(() -> {
                if (!active || token != sessionToken) return;
                float ratio = s / (float) steps;
                setPlayerVol(voice, vFrom + (vTo - vFrom) * ratio);
                setPlayerVol(music, mFrom + (mTo - mFrom) * ratio);
            }, i * stepMs);
        }
    }

    private static void setPlayerVol(MediaPlayer mp, float v) {
        if (mp == null) return;
        try {
            float c = Math.max(0f, Math.min(1f, v));
            mp.setVolume(c, c);
        } catch (Exception ignored) {}
    }

    private void clear() {
        safeRelease(voice);
        safeRelease(music);
        voice = null;
        music = null;
    }

    private static void safeRelease(MediaPlayer mp) {
        if (mp == null) return;
        try { mp.stop(); } catch (Exception ignored) {}
        try { mp.release(); } catch (Exception ignored) {}
    }
}
