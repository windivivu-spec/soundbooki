package studio.windi.soundbooki;

import android.text.*;
import java.util.*;

/** Bounded worker-only layout. Ranges partition the unchanged UTF-16 source. */
final class ReaderPaginator {
    private static final int WINDOW_CHARS=6000;
    static List<int[]> paginate(String text,List<PdfReflow.ChapterItem> chapters,TextPaint paint,int width,int height,int lineExtra){
        return paginate(text,chapters,paint,width,height,lineExtra,1.35f);
    }
    static List<int[]> paginate(String text,List<PdfReflow.ChapterItem> chapters,TextPaint paint,int width,int height,int lineExtra,float spacing){
        List<int[]> pages=new ArrayList<>();
        for(PdfReflow.ChapterItem chapter:chapters){
            int at=chapter.startChar,window=WINDOW_CHARS;
            while(at<chapter.endChar){
                if(Thread.currentThread().isInterrupted())return null;
                int limit=at+Math.min(window,chapter.endChar-at);
                if(limit<chapter.endChar&&Character.isLowSurrogate(text.charAt(limit)))limit--;
                String chunk=text.substring(at,limit);
                StaticLayout layout=measure(chunk,paint,width,lineExtra,spacing);
                int line=0,consumed=at;
                while(line<layout.getLineCount()){
                    if(Thread.currentThread().isInterrupted())return null;
                    int first=line,top=layout.getLineTop(first);
                    while(line<layout.getLineCount()&&layout.getLineBottom(line)-top<=height)line++;
                    if(line==first)line++; // Still make progress if the viewport cannot fit one glyph line.
                    // Remeasure the final partial page with the next window, so a
                    // window boundary cannot truncate a word or waste a whole page.
                    if(line==layout.getLineCount()&&limit<chapter.endChar)break;
                    int end=at+layout.getLineEnd(line-1);
                    if(end>consumed){
                        // A paragraph rebased onto a page can wrap differently from
                        // the same lines inside a larger block (e.g. unspaced words).
                        // Verify each candidate once; retain block measurement for
                        // all remaining pages unless a boundary actually changes.
                        boolean rebased=false;
                        while(true){
                            if(Thread.currentThread().isInterrupted())return null;
                            String candidate=text.substring(consumed,end);
                            StaticLayout pageLayout=measure(candidate,paint,width,lineExtra,spacing);
                            int last=pageLayout.getLineCount()-1;
                            while(last>0&&blank(candidate,pageLayout.getLineStart(last),pageLayout.getLineEnd(last)))last--;
                            if(pageLayout.getLineBottom(last)<=height)break;
                            int fit=0;
                            while(fit<=last&&pageLayout.getLineBottom(fit)<=height)fit++;
                            int smaller=consumed+pageLayout.getLineEnd(Math.max(0,fit-1));
                            if(smaller>=end)break; // One line may exceed an unusually short viewport.
                            end=smaller;rebased=true;
                        }
                        pages.add(new int[]{consumed,end});consumed=end;
                        if(rebased)break;
                    }
                }
                if(consumed==at){
                    if(limit==chapter.endChar)break;
                    window=Math.min(chapter.endChar-at,window*2);
                }else{at=consumed;window=WINDOW_CHARS;}
            }
        }
        return pages;
    }
    private static StaticLayout measure(String text,TextPaint paint,int width,int extra,float spacing){
        return StaticLayout.Builder.obtain(text,0,text.length(),paint,width)
            .setIncludePad(false).setUseLineSpacingFromFallbacks(true).setLineSpacing(extra,spacing)
            .setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE).setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE).build();
    }
    private static boolean blank(String text,int start,int end){for(int i=start;i<end;i++)if(!Character.isWhitespace(text.charAt(i)))return false;return true;}

}
