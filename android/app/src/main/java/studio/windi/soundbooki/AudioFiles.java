package studio.windi.soundbooki;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;

public final class AudioFiles {
    public static void atomic(File file,byte[] data) throws IOException {
        File parent=file.getParentFile();if(parent!=null&&!parent.exists()&&!parent.mkdirs())throw new IOException("Chưa tạo được thư mục lưu.");
        File part=new File(file.getPath()+".partial");
        try(FileOutputStream out=new FileOutputStream(part)){out.write(data);out.getFD().sync();}
        Files.move(part.toPath(),file.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
    }
    public static void wav(File file,float[] samples) throws IOException {
        ByteBuffer b=ByteBuffer.allocate(44+samples.length*2).order(ByteOrder.LITTLE_ENDIAN);
        header(b,samples.length*2,NanoEngine.SAMPLE_RATE);
        for(float value:samples){if(!Float.isFinite(value))throw new IOException("Audio không hợp lệ.");b.putShort((short)Math.round(Math.max(-1,Math.min(1,value))*32767));}
        atomic(file,b.array());if(!valid(file))throw new IOException("Audio chưa hoàn tất.");
    }
    static void header(ByteBuffer b,int bytes,int sampleRate){
        b.put(new byte[]{'R','I','F','F'}).putInt(bytes+36).put(new byte[]{'W','A','V','E','f','m','t',' '}).putInt(16).putShort((short)1).putShort((short)1).putInt(sampleRate).putInt(sampleRate*2).putShort((short)2).putShort((short)16).put(new byte[]{'d','a','t','a'}).putInt(bytes);
    }
    public static boolean valid(File f){try{inspect(f);return true;}catch(Exception e){return false;}}
    /** PCM mono 16-bit RIFF only. Chunk offsets are parsed; cloud WAVs may have metadata. */
    public static long[] inspect(File f) throws IOException {
        try(RandomAccessFile in=new RandomAccessFile(f,"r")) {
            if(f.length()<46||in.readInt()!=0x52494646)throw new IOException("WAV thiếu dữ liệu.");
            long declared=Integer.toUnsignedLong(Integer.reverseBytes(in.readInt()))+8;
            if(declared!=f.length()||in.readInt()!=0x57415645)throw new IOException("WAV chưa tải đủ.");
            int rate=0;long at=0,length=0;boolean pcm=false;
            while(in.getFilePointer()+8<=in.length()) {
                int id=in.readInt();long size=Integer.toUnsignedLong(Integer.reverseBytes(in.readInt()));long pos=in.getFilePointer();
                if(size>in.length()-pos)throw new IOException("WAV thiếu chunk.");
                if(id==0x666d7420&&size>=16) {
                    int type=Short.toUnsignedInt(Short.reverseBytes(in.readShort())),channels=Short.toUnsignedInt(Short.reverseBytes(in.readShort()));
                    rate=Integer.reverseBytes(in.readInt());in.skipBytes(6);int bits=Short.toUnsignedInt(Short.reverseBytes(in.readShort()));pcm=type==1&&channels==1&&bits==16;
                }else if(id==0x64617461){at=pos;length=size;}
                in.seek(pos+size+(size%2));
            }
            if(!pcm||rate<8000||rate>96000||length<2||length%2!=0)throw new IOException("Chỉ nhận WAV PCM mono 16 bit.");
            return new long[]{at,length,rate};
        }
    }
    public static void export(List<File> files,OutputStream out) throws IOException {
        if(files.isEmpty())throw new IOException("Chưa có audio để xuất.");long bytes=0;int rate=0;
        for(File f:files){long[] info=inspect(f);if(rate!=0&&rate!=info[2])throw new IOException("Các đoạn có sample rate khác nhau.");rate=(int)info[2];bytes+=info[1];}
        if(bytes>Integer.MAX_VALUE-44)throw new IOException("Bản đọc quá dài để xuất WAV một file.");
        ByteBuffer header=ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN);header(header,(int)bytes,rate);out.write(header.array());byte[] buffer=new byte[65536];
        for(File f:files){long[] info=inspect(f);try(RandomAccessFile in=new RandomAccessFile(f,"r")){in.seek(info[0]);long remain=info[1];while(remain>0){int n=in.read(buffer,0,(int)Math.min(buffer.length,remain));if(n<0)throw new EOFException();out.write(buffer,0,n);remain-=n;}}}
    }
}
