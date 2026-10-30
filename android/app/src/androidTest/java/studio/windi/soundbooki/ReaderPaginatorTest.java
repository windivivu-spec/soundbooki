package studio.windi.soundbooki;

import android.content.Context;
import android.text.*;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import java.util.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class ReaderPaginatorTest {
    @Test public void windowsAndChaptersPartitionUnicodeAndFitBothFonts(){
        Context c=InstrumentationRegistry.getInstrumentation().getTargetContext();UiTheme theme=new UiTheme(c);
        String prefix="a".repeat(5999)+"🙂\n\n",body="Tiếng Việt có dấu: Ă, số 3.14, tên riêng. 👩🏽‍💻𠮷\n\n".repeat(220);
        String text=prefix+body+"CHƯƠNG HAI\n"+body;
        int split=prefix.length()+body.length();
        List<PdfReflow.ChapterItem> chapters=Arrays.asList(new PdfReflow.ChapterItem("one","Một",0,split),new PdfReflow.ChapterItem("two","Hai",split,text.length()));
        for(boolean serif:new boolean[]{false,true})for(int sp:new int[]{19,30}){
            TextPaint paint=new TextPaint(android.graphics.Paint.ANTI_ALIAS_FLAG);paint.setTextSize(sp*c.getResources().getDisplayMetrics().scaledDensity);paint.setTypeface(serif?theme.serif:theme.regular);
            int width=theme.dp(280),height=theme.dp(350),extra=theme.dp(2);
            List<int[]> pages=ReaderPaginator.paginate(text,chapters,paint,width,height,extra);assertNotNull(pages);int prior=0;boolean chapterStart=false;
            for(int[] p:pages){
                assertEquals(prior,p[0]);assertTrue(p[1]>p[0]);assertFalse(Character.isLowSurrogate(text.charAt(p[0])));if(p[0]==split)chapterStart=true;
                assertFalse(p[0]<split&&p[1]>split);
                String page=text.substring(p[0],p[1]);StaticLayout l=StaticLayout.Builder.obtain(page,0,page.length(),paint,width).setIncludePad(false).setUseLineSpacingFromFallbacks(true).setLineSpacing(extra,1.35f).setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE).setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE).build();
                int last=l.getLineCount()-1;while(last>0&&page.substring(l.getLineStart(last),l.getLineEnd(last)).trim().isEmpty())last--;
                assertTrue("Glyphs clipped at "+p[0]+": "+l.getLineBottom(last)+">"+height,l.getLineBottom(last)<=height);prior=p[1];
            }
            assertTrue(chapterStart);assertEquals(text.length(),prior);
        }
    }
    @Test public void interruptedLayoutDoesNotPublishPartialPages(){
        TextPaint paint=new TextPaint();paint.setTextSize(30);String text="Đọc tiếp. ".repeat(1000);
        Thread.currentThread().interrupt();
        try{assertNull(ReaderPaginator.paginate(text,List.of(new PdfReflow.ChapterItem("one","Một",0,text.length())),paint,300,500,2));}finally{Thread.interrupted();}
    }
}
