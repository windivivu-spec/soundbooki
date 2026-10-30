package studio.windi.soundbooki;

import android.content.Context;
import android.speech.tts.*;
import android.os.Bundle;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.BooleanSupplier;

/** Only an installed, explicitly offline English voice. No download/network fallback. */
final class EnglishSpeech implements AutoCloseable {
    private final TextToSpeech tts;private final Context context;
    EnglishSpeech(Context context)throws Exception{this.context=context;CountDownLatch ready=new CountDownLatch(1);int[] result={TextToSpeech.ERROR};tts=new TextToSpeech(context,s->{result[0]=s;ready.countDown();});if(!ready.await(20,TimeUnit.SECONDS)||result[0]!=TextToSpeech.SUCCESS){tts.shutdown();throw new IOException("Chưa mở được giọng Anh offline của hệ thống.");}}
    String select(String name)throws Exception{Set<Voice> available=tts.getVoices();if(available==null)throw new IOException("Cài giọng Anh offline trong Cài đặt văn bản thành giọng nói của Android trước.");List<Voice> voices=new ArrayList<>();for(Voice v:available)if(!v.isNetworkConnectionRequired()&&v.getLocale().getLanguage().equals("en")&&(v.getFeatures()==null||!v.getFeatures().contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)))voices.add(v);voices.sort(Comparator.comparing(Voice::getName));Voice chosen=voices.stream().filter(v->v.getName().equals(name)).findFirst().orElse(name.isEmpty()&&!voices.isEmpty()?voices.get(0):null);if(chosen==null||tts.setVoice(chosen)!=TextToSpeech.SUCCESS)throw new IOException("Máy chưa có giọng Anh offline đã chọn. Cài giọng trong cài đặt hệ thống rồi bật lại Việt–Anh.");return chosen.getName();}
    String revision()throws Exception{return tts.getDefaultEngine()+":"+context.getPackageManager().getPackageInfo(tts.getDefaultEngine(),0).getLongVersionCode();}
    float[] synthesize(String text,File destination,BooleanSupplier cancelled)throws Exception{
        CountDownLatch ready=new CountDownLatch(1);int[] state={-1};String token=UUID.randomUUID().toString();
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener(){public void onStart(String id){}public void onDone(String id){if(token.equals(id)){state[0]=0;ready.countDown();}}public void onError(String id){if(token.equals(id)){state[0]=1;ready.countDown();}}});
        File temp=new File(destination.getPath()+".english.partial.wav");Bundle options=new Bundle();options.putString(TextToSpeech.Engine.KEY_FEATURE_EMBEDDED_SYNTHESIS,"true");
        try{if(tts.synthesizeToFile(text,options,temp,token)!=TextToSpeech.SUCCESS)throw new IOException("Chưa tạo được giọng Anh offline.");long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(90);while(!ready.await(100,TimeUnit.MILLISECONDS)){if(cancelled.getAsBoolean())throw new InterruptedException();if(System.nanoTime()>deadline)throw new IOException("Giọng Anh offline chưa phản hồi.");}if(cancelled.getAsBoolean())throw new InterruptedException();if(state[0]!=0)throw new IOException("Giọng Anh offline chưa tạo xong đoạn này.");
            long[] info=AudioFiles.inspect(temp);if(info[1]>16_000_000)throw new IOException("Đoạn tiếng Anh quá dài.");byte[] bytes=new byte[(int)info[1]];try(RandomAccessFile in=new RandomAccessFile(temp,"r")){in.seek(info[0]);in.readFully(bytes);}int size=(int)Math.round(bytes.length/2.0*24000/info[2]);float[] out=new float[size];for(int i=0;i<size;i++){double at=i*info[2]/24000.0;int a=Math.min(bytes.length/2-1,(int)at),b=Math.min(bytes.length/2-1,a+1);float x=(short)((bytes[a*2]&255)|(bytes[a*2+1]<<8))/32768f,y=(short)((bytes[b*2]&255)|(bytes[b*2+1]<<8))/32768f;out[i]=x+(y-x)*(float)(at-a);}return out;
        }finally{tts.stop();temp.delete();}
    }
    public void close(){tts.stop();tts.shutdown();}
}
