package studio.windi.soundbooki;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Adds a QuickTime chapter text track and iTunes cover/title metadata without moving audio offsets. */
final class Mp4BookMetadata {
    static final class Chapter {final String title;final long startMs,endMs;Chapter(String title,long a,long b){this.title=title;startMs=a;endMs=b;}}
    static byte[] bytes(String s){return s.getBytes(StandardCharsets.UTF_8);}
    static byte[] join(byte[]... chunks)throws IOException{ByteArrayOutputStream out=new ByteArrayOutputStream();for(byte[] b:chunks)out.write(b);return out.toByteArray();}
    static byte[] ints(int... values)throws IOException{ByteArrayOutputStream b=new ByteArrayOutputStream();DataOutputStream out=new DataOutputStream(b);for(int n:values)out.writeInt(n);return b.toByteArray();}
    static byte[] longs(long... values)throws IOException{ByteArrayOutputStream b=new ByteArrayOutputStream();DataOutputStream out=new DataOutputStream(b);for(long n:values)out.writeLong(n);return b.toByteArray();}
    static byte[] box(String type,byte[]... content)throws IOException{byte[] data=join(content);return join(ints(data.length+8),type.getBytes(StandardCharsets.ISO_8859_1),data);}
    static long u32(byte[] b,int i){return Integer.toUnsignedLong(java.nio.ByteBuffer.wrap(b,i,4).getInt());}
    static String type(byte[] b,int at){return new String(b,at+4,4,StandardCharsets.ISO_8859_1);}
    static List<byte[]> children(byte[] b,int from)throws IOException{List<byte[]> out=new ArrayList<>();for(int at=from;at<b.length;){long len=u32(b,at);if(len<8||len>b.length-at)throw new IOException("MP4 metadata không hợp lệ.");out.add(Arrays.copyOfRange(b,at,at+(int)len));at+=(int)len;}return out;}
    static byte[] item(String type,String value)throws IOException{return box(type,box("data",ints(1,0),bytes(value)));}
    static final int[] MATRIX={0x10000,0,0,0,0x10000,0,0,0,0x40000000};
    static byte[] track(int id,long duration,int movieScale,List<Chapter> chapters,long offset,int[] sizes)throws IOException{
        // version 1 headers retain durations above 32-bit limits.
        byte[] tkhd=box("tkhd",ints(0x01000002),longs(0,0),ints(id,0),longs(duration*movieScale/1000),longs(0),ints(0,0),ints(MATRIX),ints(0,0));
        byte[] mdhd=box("mdhd",ints(0x01000000),longs(0,0),ints(1000),longs(duration),ints(0x55c40000));
        byte[] hdlr=box("hdlr",ints(0,0),bytes("text"),ints(0,0,0),bytes("Chapters\0"));
        ByteArrayOutputStream desc=new ByteArrayOutputStream();DataOutputStream entry=new DataOutputStream(desc);entry.write(new byte[6]);entry.writeShort(1);entry.writeInt(0);entry.writeInt(1);entry.write(new byte[6]);entry.write(new byte[8]);entry.write(new byte[8]);entry.writeShort(1);entry.writeShort(0);entry.writeByte(0);entry.writeByte(12);entry.write(new byte[6]);
        byte[] stsd=box("stsd",ints(0,1),box("text",desc.toByteArray()));
        ByteArrayOutputStream times=new ByteArrayOutputStream();DataOutputStream dt=new DataOutputStream(times);dt.writeInt(0);dt.writeInt(chapters.size());for(Chapter c:chapters){dt.writeInt(1);dt.writeInt((int)Math.max(1,c.endMs-c.startMs));}
        byte[] stbl=box("stbl",stsd,box("stts",times.toByteArray()),box("stsc",ints(0,1,1,chapters.size(),1)),box("stsz",ints(0,0,sizes.length),ints(sizes)),box("co64",ints(0,1),longs(offset)));
        byte[] gmhd=box("gmhd",box("gmin",ints(0,0x40000000,0,0)),box("text",ints(MATRIX)));
        byte[] dinf=box("dinf",box("dref",ints(0,1),box("url ",ints(1))));
        return box("trak",tkhd,box("mdia",mdhd,hdlr,box("minf",gmhd,dinf,stbl)));
    }
    static void apply(File file,String title,String author,byte[] cover,List<Chapter> chapters)throws IOException{
        if(chapters.isEmpty())throw new IOException("Chưa có chương để xuất.");
        try(RandomAccessFile io=new RandomAccessFile(file,"rw")){
            long oldAt=-1;byte[] old=null;
            for(long at=0;at+8<=io.length();){io.seek(at);long size=Integer.toUnsignedLong(io.readInt());byte[] type=new byte[4];io.readFully(type);int header=8;if(size==1){size=io.readLong();header=16;}if(size<header||size>io.length()-at)throw new IOException("MP4 chưa hoàn tất.");if(new String(type,StandardCharsets.ISO_8859_1).equals("moov")){if(size>32_000_000||header!=8)throw new IOException("MP4 metadata quá lớn.");oldAt=at;old=new byte[(int)size];io.seek(at);io.readFully(old);break;}at+=size;}
            if(old==null)throw new IOException("Không có MP4 movie metadata.");
            List<byte[]> atoms=children(old,8);int maxId=0,scale=1000;
            for(byte[] atom:atoms){if(type(atom,0).equals("mvhd"))scale=(int)u32(atom,atom[8]==1?28:20);if(type(atom,0).equals("trak"))for(byte[] child:children(atom,8))if(type(child,0).equals("tkhd"))maxId=Math.max(maxId,(int)u32(child,child[8]==1?28:20));}
            int chapterId=maxId+1;ByteArrayOutputStream samples=new ByteArrayOutputStream();DataOutputStream data=new DataOutputStream(samples);int[] sizes=new int[chapters.size()];for(int i=0;i<chapters.size();i++){byte[] name=bytes(chapters.get(i).title);if(name.length>65535)throw new IOException("Tên chương quá dài.");data.writeShort(name.length);data.write(name);sizes[i]=name.length+2;}
            long sampleOffset=io.length()+8;byte[] mdat=box("mdat",samples.toByteArray());
            ByteArrayOutputStream movie=new ByteArrayOutputStream();for(byte[] atom:atoms){String kind=type(atom,0);if(kind.equals("udta"))continue;if(kind.equals("mvhd")){java.nio.ByteBuffer.wrap(atom).putInt(atom.length-4,chapterId+1);}if(kind.equals("trak")){boolean audio=false;for(byte[] child:children(atom,8))if(type(child,0).equals("mdia"))for(byte[] field:children(child,8))if(type(field,0).equals("hdlr")&&new String(field,16,4,StandardCharsets.ISO_8859_1).equals("soun"))audio=true;if(audio)atom=box("trak",Arrays.copyOfRange(atom,8,atom.length),box("tref",box("chap",ints(chapterId))));}movie.write(atom);}
            long duration=chapters.get(chapters.size()-1).endMs;movie.write(track(chapterId,duration,scale,chapters,sampleOffset,sizes));
            byte[] art=cover==null?new byte[0]:box("covr",box("data",ints(13,0),cover));
            byte[] ilst=box("ilst",item("©nam",title),item("©ART",author),item("©alb",title),item("©gen","Audiobook"),box("stik",box("data",ints(21,0),new byte[]{2})),art);
            byte[] meta=box("meta",ints(0),box("hdlr",ints(0,0),bytes("mdir"),bytes("appl"),ints(0,0),new byte[]{0}),ilst);
            ByteArrayOutputStream nero=new ByteArrayOutputStream();DataOutputStream ch=new DataOutputStream(nero);ch.writeInt(0x01000000);ch.writeInt(0);ch.writeByte(Math.min(255,chapters.size()));for(Chapter c:chapters.subList(0,Math.min(255,chapters.size()))){ch.writeLong(c.startMs*10000);byte[] name=bytes(c.title);int n=Math.min(255,name.length);while(n>0&&n<name.length&&(name[n]&0xc0)==0x80)n--;ch.writeByte(n);ch.write(name,0,n);}
            movie.write(box("udta",meta,box("chpl",nero.toByteArray())));byte[] moov=box("moov",movie.toByteArray());
            io.seek(io.length());io.write(mdat);io.write(moov);io.getFD().sync();io.seek(oldAt+4);io.write(bytes("free"));io.getFD().sync();
        }
    }
}
