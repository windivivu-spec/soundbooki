package studio.windi.soundbooki;
import java.io.*;
public final class HostSmoke {
 public static void main(String[] args) throws Exception {
  File dir=new File(args[0]);long start=System.nanoTime();
  try(NanoEngine engine=new NanoEngine(dir,2)) {
   float[] audio=engine.synthesize("Mỗi trang sách mở ra một thế giới mới. Hôm nay, tôi muốn lắng nghe và học thêm một điều thú vị.","Đức Trí",()->false);
   AudioFiles.wav(new File(args[1]),audio);
   System.out.printf(java.util.Locale.ROOT,"REAL NANO: load %.3fs; total %.3fs; audio %.3fs; samples %d%n",engine.loadSeconds,(System.nanoTime()-start)/1e9,audio.length/24000.0,audio.length);
  }
 }
}
