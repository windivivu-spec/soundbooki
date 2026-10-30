package studio.windi.soundbooki;
import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.media.*;
import java.io.*;
import java.nio.*;
import java.util.function.BooleanSupplier;

/** Bounded decode of bundled music, independent of narration cache. */
final class ExportMusic {
    final float[] samples;final float gain;long at=0;
    ExportMusic(Context context,String track,float gain,BooleanSupplier cancel)throws Exception{
        this.gain=Math.max(0,Math.min(.5f,gain));String name=switch(track){case "piano"->"music/piano_podcast_1.mp3";case "rain"->"music/rain.mp3";case "late_night"->"music/late_night.mp3";default->null;};if(name==null||gain<=0){samples=new float[0];return;}
        MediaExtractor extractor=new MediaExtractor();MediaCodec codec=null;ByteArrayOutputStream pcm=new ByteArrayOutputStream();int channels=1,rate=24000;
        try(AssetFileDescriptor fd=context.getAssets().openFd(name)){extractor.setDataSource(fd.getFileDescriptor(),fd.getStartOffset(),fd.getLength());MediaFormat format=null;for(int i=0;i<extractor.getTrackCount();i++)if(extractor.getTrackFormat(i).getString(MediaFormat.KEY_MIME).startsWith("audio/")){extractor.selectTrack(i);format=extractor.getTrackFormat(i);break;}if(format==null)throw new IOException("Nhạc nền không có audio.");channels=format.getInteger(MediaFormat.KEY_CHANNEL_COUNT);rate=format.getInteger(MediaFormat.KEY_SAMPLE_RATE);codec=MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME));codec.configure(format,null,null,0);codec.start();boolean inputDone=false,done=false;MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();
            while(!done){if(cancel.getAsBoolean())throw new InterruptedIOException("Đã hủy xuất.");if(!inputDone){int slot=codec.dequeueInputBuffer(10000);if(slot>=0){ByteBuffer buffer=codec.getInputBuffer(slot);int n=extractor.readSampleData(buffer,0);inputDone=n<0;codec.queueInputBuffer(slot,0,Math.max(0,n),inputDone?0:extractor.getSampleTime(),inputDone?MediaCodec.BUFFER_FLAG_END_OF_STREAM:0);if(!inputDone)extractor.advance();}}
                int slot=codec.dequeueOutputBuffer(info,10000);if(slot==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED){MediaFormat decoded=codec.getOutputFormat();channels=decoded.getInteger(MediaFormat.KEY_CHANNEL_COUNT);rate=decoded.getInteger(MediaFormat.KEY_SAMPLE_RATE);if(decoded.containsKey(MediaFormat.KEY_PCM_ENCODING)&&decoded.getInteger(MediaFormat.KEY_PCM_ENCODING)!=2)throw new IOException("Định dạng nhạc PCM chưa hỗ trợ.");}else if(slot>=0){ByteBuffer buffer=codec.getOutputBuffer(slot);byte[] bytes=new byte[info.size];buffer.position(info.offset);buffer.get(bytes);pcm.write(bytes);if(pcm.size()>32_000_000)throw new IOException("Nhạc nền quá dài để trộn. Chọn bản ngắn hơn.");done=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;codec.releaseOutputBuffer(slot,false);}}
        }finally{extractor.release();if(codec!=null){try{codec.stop();}catch(Exception ignored){}codec.release();}}
        byte[] bytes=pcm.toByteArray();int frames=bytes.length/(2*channels);samples=new float[(int)((long)frames*24000/rate)];for(int i=0;i<samples.length;i++){double pos=(double)i*rate/24000.0;int a=Math.min(frames-1,(int)pos),b=Math.min(frames-1,a+1);float x=0,y=0;for(int c=0;c<channels;c++){int ia=(a*channels+c)*2,ib=(b*channels+c)*2;x+=(short)((bytes[ia]&255)|(bytes[ia+1]<<8))/32768f;y+=(short)((bytes[ib]&255)|(bytes[ib+1]<<8))/32768f;}samples[i]=(x+(y-x)*(float)(pos-a))/channels;}
    }
    void mix(byte[] pcm,int rate){if(samples.length==0)return;for(int i=0;i<pcm.length;i+=2){long frame=at++;double pos=frame*24000.0/rate;int a=(int)((long)pos%samples.length),b=(a+1)%samples.length;float bed=samples[a]+(samples[b]-samples[a])*(float)(pos-Math.floor(pos));float voice=(short)((pcm[i]&255)|(pcm[i+1]<<8))/32768f;int value=Math.round(Math.max(-1,Math.min(.999969f,voice*.94f+bed*gain))*32768);pcm[i]=(byte)value;pcm[i+1]=(byte)(value>>8);}}
}
