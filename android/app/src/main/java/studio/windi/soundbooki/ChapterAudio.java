package studio.windi.soundbooki;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.function.BooleanSupplier;

/** Immutable completed chapter takes. Tiny manifests are the library index. */
final class ChapterAudio {
    private final File dir;
    ChapterAudio(BookStore store,String bookId){if(!bookId.matches("[a-f0-9]{32}"))throw new IllegalArgumentException();dir=new File(store.root().getParentFile(),"chapter-audio/"+bookId);dir.mkdirs();}
    JSONObject complete(JSONObject book,PdfReflow.ChapterItem chapter,List<File> parts,BooleanSupplier cancelled) throws Exception {
        String key=BookStore.hash(BookStore.contentSignature(book)+"\0"+book.optString("voice")+"\0"+chapter.startChar+":"+chapter.endChar+":"+chapter.title+"\0"+chapter.text);
        File wav=new File(dir,key+".wav"),partial=new File(dir,key+".wav.partial");
        if(!AudioFiles.valid(wav)){
            try(FileOutputStream out=new FileOutputStream(partial)){
                AudioFiles.export(parts,new FilterOutputStream(out){@Override public void write(byte[] b,int off,int len)throws IOException{if(cancelled.getAsBoolean())throw new InterruptedIOException();out.write(b,off,len);}});out.getFD().sync();
            }
            if(cancelled.getAsBoolean())throw new InterruptedException();
            if(!AudioFiles.valid(partial))throw new IOException("Chương chưa có đủ âm thanh.");
            Files.move(partial.toPath(),wav.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        }
        if(cancelled.getAsBoolean())throw new InterruptedException();
        long[] info=AudioFiles.inspect(wav);
        JSONObject take=new JSONObject().put("id",key).put("title",chapter.title).put("bookTitle",book.optString("title"))
            .put("voice",book.optString("voice")).put("bilingual",book.optBoolean("bilingual")).put("contentSignature",BookStore.contentSignature(book)).put("revision",NanoEngine.REVISION).put("textHash",BookStore.hash(chapter.text))
            .put("startChar",chapter.startChar).put("endChar",chapter.endChar).put("bytes",wav.length()).put("seconds",info[1]/(info[2]*2.0)).put("completedAt",System.currentTimeMillis());
        AudioFiles.atomic(new File(dir,key+".json"),take.toString().getBytes(StandardCharsets.UTF_8));return take;
    }
    List<JSONObject> list(){List<JSONObject> result=new ArrayList<>();File[] files=dir.listFiles((d,n)->n.endsWith(".json"));if(files!=null)for(File f:files)try{JSONObject m=NanoEngine.read(f);File audio=file(m);if(audio.isFile()&&audio.length()==m.getLong("bytes"))result.add(m);}catch(Exception ignored){}result.sort((a,b)->{int order=Integer.compare(a.optInt("startChar"),b.optInt("startChar"));return order!=0?order:Long.compare(b.optLong("completedAt"),a.optLong("completedAt"));});return result;}
    File file(JSONObject take){String id=take.optString("id");if(!id.matches("[a-f0-9]{64}"))throw new IllegalArgumentException();return new File(dir,id+".wav");}
}
