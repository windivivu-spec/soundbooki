package studio.windi.soundbooki;
import java.nio.charset.StandardCharsets;
public final class Phonemizer implements AutoCloseable {
    static { System.loadLibrary("soundbooki_g2p"); }
    private long handle;
    public Phonemizer(String path) { handle=open(path.getBytes(StandardCharsets.UTF_8)); }
    public synchronized String phones(String text) {
        if(handle==0) throw new IllegalStateException("Bộ phát âm đã đóng.");
        return new String(convert(handle,text.getBytes(StandardCharsets.UTF_8)),StandardCharsets.UTF_8);
    }
    @Override public synchronized void close() { if(handle!=0) release(handle); handle=0; }
    private static native long open(byte[] path);
    private static native byte[] convert(long handle,byte[] text);
    private static native void release(long handle);
}
