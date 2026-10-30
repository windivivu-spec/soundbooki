package studio.windi.soundbooki;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Durable request/checkpoint; WAV validation, never this counter, decides what can be reused. */
final class GenerationProgress {
    private final File file;
    private final JSONObject data;
    GenerationProgress(BookStore store,JSONObject book,int chapter,boolean continuous,boolean playbackPaused) throws Exception {
        file=store.generationFile(book.getString("id"));
        data=new JSONObject().put("signature",BookStore.contentSignature(book)).put("engine",NanoEngine.REVISION).put("chaptersHash",chaptersHash(book))
            .put("chapter",chapter).put("continuous",continuous).put("playbackPaused",playbackPaused)
            .put("state","running").put("completedParts",0).put("chapterPercent",0);
        write();
    }
    static JSONObject pending(BookStore store,JSONObject book){
        try{
            JSONObject saved;
            synchronized(BookStore.LOCK){saved=NanoEngine.read(store.generationFile(book.getString("id")));}
            if(!BookStore.contentSignature(book).equals(saved.optString("signature"))||!NanoEngine.REVISION.equals(saved.optString("engine"))||!chaptersHash(book).equals(saved.optString("chaptersHash"))||"complete".equals(saved.optString("state")))return null;
            int chapter=saved.optInt("chapter",-2);
            return chapter>=-1&&chapter<BookChapters.get(book).size()?saved:null;
        }catch(Exception ignored){return null;}
    }
    private static String chaptersHash(JSONObject book){StringBuilder ranges=new StringBuilder();for(PdfReflow.ChapterItem c:BookChapters.get(book))ranges.append(c.startChar).append(':').append(c.endChar).append(';');return BookStore.hash(ranges.toString());}
    synchronized void part(int index,int percent,String title) throws Exception {part(index,percent,title,true);}
    synchronized void part(int index,int percent,String title,boolean flush) throws Exception {
        data.put("completedParts",data.optInt("completedParts")+1).put("lastCompletedPart",index)
            .put("chapterPercent",percent).put("chapterTitle",title);if(flush)write();
    }
    synchronized void state(String state) throws Exception {data.put("state",state);write();}
    private void write() throws Exception {
        data.put("updatedAt",System.currentTimeMillis());
        synchronized(BookStore.LOCK){AudioFiles.atomic(file,data.toString().getBytes(StandardCharsets.UTF_8));}
    }
}
