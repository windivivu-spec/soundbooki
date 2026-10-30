package studio.windi.soundbooki;

import android.content.Context;
import android.graphics.*;
import android.media.*;
import java.io.*;
import java.nio.*;
import java.util.*;
import java.util.function.*;
import org.json.JSONObject;

/** Streams cached PCM through the platform AAC encoder; no model or network calls. */
final class M4bExport {
    static File create(Context context,BookStore store,JSONObject book,List<File> files,List<Mp4BookMetadata.Chapter> chapters,BooleanSupplier cancelled,IntConsumer progress)throws Exception{
        File output=File.createTempFile("soundbooki-", ".m4b",context.getCacheDir());MediaCodec codec=null;MediaMuxer muxer=null;boolean started=false,success=false;
        try{
            long total=0;int rate=0;for(File f:files){long[] info=AudioFiles.inspect(f);if(rate!=0&&rate!=info[2])throw new IOException("Tần số audio không khớp.");rate=(int)info[2];total+=info[1];}if(total==0)throw new IOException("Chưa có audio hoàn tất.");
            ExportMusic music=new ExportMusic(context,book.optString("bgmTrack","none"),(float)book.optDouble("bgmVolume",.18),cancelled);
            MediaFormat format=MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC,rate,1);format.setInteger(MediaFormat.KEY_AAC_PROFILE,MediaCodecInfo.CodecProfileLevel.AACObjectLC);format.setInteger(MediaFormat.KEY_BIT_RATE,64000);format.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE,16384);
            codec=MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC);codec.configure(format,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE);codec.start();muxer=new MediaMuxer(output.getPath(),MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();int track=-1,index=0;long consumed=0,remaining=0;RandomAccessFile input=null;boolean inputDone=false,outputDone=false;
            try{
                while(!outputDone){if(cancelled.getAsBoolean()||Thread.currentThread().isInterrupted())throw new InterruptedIOException("Đã hủy xuất M4B.");
                    if(!inputDone){int slot=codec.dequeueInputBuffer(10000);if(slot>=0){ByteBuffer buffer=codec.getInputBuffer(slot);buffer.clear();int n=0;
                        while(buffer.remaining()>=2){if(input==null){if(index>=files.size())break;long[] wav=AudioFiles.inspect(files.get(index));input=new RandomAccessFile(files.get(index++),"r");input.seek(wav[0]);remaining=wav[1];}int count=(int)Math.min(Math.min(remaining,buffer.remaining()),16384);count-=count%2;byte[] pcm=new byte[count];input.readFully(pcm);music.mix(pcm,rate);buffer.put(pcm);n+=count;remaining-=count;if(remaining==0){input.close();input=null;}if(n>0)break;}
                        long pts=consumed/2*1_000_000/rate;consumed+=n;inputDone=n==0&&index>=files.size();codec.queueInputBuffer(slot,0,n,pts,inputDone?MediaCodec.BUFFER_FLAG_END_OF_STREAM:0);progress.accept((int)(consumed*100/total));
                    }}
                    int slot=codec.dequeueOutputBuffer(info,10000);if(slot==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED){if(started)throw new IOException("AAC format thay đổi.");track=muxer.addTrack(codec.getOutputFormat());muxer.start();started=true;}else if(slot>=0){ByteBuffer encoded=codec.getOutputBuffer(slot);if((info.flags&MediaCodec.BUFFER_FLAG_CODEC_CONFIG)!=0)info.size=0;if(info.size>0){if(!started)throw new IOException("AAC muxer chưa sẵn sàng.");encoded.position(info.offset);encoded.limit(info.offset+info.size);muxer.writeSampleData(track,encoded,info);}outputDone=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;codec.releaseOutputBuffer(slot,false);}
                }
            }finally{if(input!=null)input.close();}
            muxer.stop();started=false;muxer.release();muxer=null;codec.stop();codec.release();codec=null;
            Bitmap cover=BookArtwork.cover(store,book);if(cover==null){cover=Bitmap.createBitmap(600,800,Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(cover);canvas.drawColor(0xffdfe8f1);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);p.setColor(0xff20334b);p.setTextSize(32);int y=110;StringBuilder row=new StringBuilder();for(String word:book.optString("title").split("\\s+")){if(p.measureText(row+" "+word)>510){canvas.drawText(row.toString(),45,y,p);y+=45;row.setLength(0);}row.append(word).append(' ');if(y>650)break;}canvas.drawText(row.toString(),45,y,p);p.setTextSize(24);canvas.drawText("SOUNDBOOKI",45,740,p);}
            ByteArrayOutputStream art=new ByteArrayOutputStream();cover.compress(Bitmap.CompressFormat.JPEG,88,art);Mp4BookMetadata.apply(output,book.optString("title"),book.optString("author"),art.toByteArray(),chapters);if(cancelled.getAsBoolean())throw new InterruptedIOException("Đã hủy xuất M4B.");success=true;return output;
        }finally{if(codec!=null){try{codec.stop();}catch(Exception ignored){}codec.release();}if(muxer!=null){try{if(started)muxer.stop();}catch(Exception ignored){}muxer.release();}if(!success)output.delete();}
    }
}
