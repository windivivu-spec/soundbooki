package studio.windi.soundbooki;

import android.content.*;
import android.graphics.Bitmap;
import android.os.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.atomic.*;
import static org.junit.Assert.*;

/** Native layout, exact source partition and real TextView clipping checks. No inference/network. */
@RunWith(AndroidJUnit4.class)
public class ReaderPerformanceTest {
    Context c;BookStore store;final AtomicReference<ReaderDialog> dialog=new AtomicReference<>();
    static Field field(String name)throws Exception{Field f=ReaderDialog.class.getDeclaredField(name);f.setAccessible(true);return f;}
    static Object get(ReaderDialog d,String name)throws Exception{return field(name).get(d);}
    static void invoke(ReaderDialog d,String name)throws Exception{Method m=ReaderDialog.class.getDeclaredMethod(name);m.setAccessible(true);m.invoke(d);}
    @Before public void setup(){c=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(c.getFilesDir(),".qa/reader-performance");BookStore.fixtureRoot.mkdirs();store=new BookStore(c);c.getSharedPreferences("onboarding",0).edit().putBoolean("done",true).commit();}
    @After public void cleanup(){BookStore.fixtureRoot=null;}
    void awaitPages(ActivityScenario<MainActivity> activity)throws Exception{
        for(int n=0;n<1200;n++){AtomicBoolean ready=new AtomicBoolean();activity.onActivity(a->{try{ready.set(((TextView)get(dialog.get(),"pageLabel")).getText().toString().startsWith("Trang "));}catch(Exception e){throw new RuntimeException(e);}});if(ready.get())return;Thread.sleep(25);}fail("Pagination timeout");
    }
    @Test public void rapidTypographyAndChromeChangesKeepExactSourceAnchor()throws Exception{
        String text="Đọc tiếp từ đúng vị trí. 🙂\n\n".repeat(2400);int offset=text.indexOf("Đọc tiếp",18000);
        JSONObject book=store.create("QA đổi bố cục",text,null);c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",book.getString("id")).commit();
        c.getSharedPreferences("reader",0).edit().putFloat("fontSize",19).putBoolean("useSerif",true).commit();
        try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            activity.onActivity(a->{ReaderDialog d=new ReaderDialog(a,new UiTheme(a),store,book,i->{}).startAt(offset);dialog.set(d);d.show();});awaitPages(activity);
            activity.onActivity(a->{try{
                ReaderDialog d=dialog.get();assertEquals(offset,(int)get(d,"anchor"));
                for(int size:new int[]{30,16,28,19,30}){field("fontSize").setFloat(d,size);((TextView)get(d,"body")).setTextSize(size);invoke(d,"paginate");}
            }catch(Exception e){throw new RuntimeException(e);}});awaitPages(activity);
            activity.onActivity(a->{try{assertEquals(offset,(int)get(dialog.get(),"anchor"));invoke(dialog.get(),"toggleChrome");}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(100);awaitPages(activity);
            activity.onActivity(a->{try{assertEquals(offset,(int)get(dialog.get(),"anchor"));invoke(dialog.get(),"toggleChrome");}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(100);awaitPages(activity);
            File dir=new File(c.getExternalFilesDir(null),"qa");dir.mkdirs();String tag=InstrumentationRegistry.getArguments().getString("readerTag","after");Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();try(OutputStream out=new FileOutputStream(new File(dir,"reader-large-"+tag+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();
            activity.onActivity(a->{try{
                ReaderDialog d=dialog.get();assertEquals(offset,(int)get(d,"anchor"));assertTrue(((Map<?,?>)get(d,"layoutCache")).size()<=4);d.dismiss();
                ReaderDialog again=new ReaderDialog(a,new UiTheme(a),store,book,i->{});dialog.set(again);again.show();
            }catch(Exception e){throw new RuntimeException(e);}});awaitPages(activity);
            activity.onActivity(a->{try{assertEquals(offset,(int)get(dialog.get(),"anchor"));dialog.get().dismiss();ReaderDialog cancelled=new ReaderDialog(a,new UiTheme(a),store,book,i->{}).startAt(offset+100);cancelled.show();cancelled.dismiss();}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(100);
        }
    }
    @Test public void selectedBookLargeTypeAndRepeatedLayout()throws Exception{
        File source=new File(c.getExternalFilesDir(null),"qa/selected-reader-text.txt");
        String text=source.isFile()?new String(Files.readAllBytes(source.toPath()),StandardCharsets.UTF_8):("Chương 1\n\n"+"Giữ nguyên tiếng Việt. 🙂 👩🏽‍💻 Một trang sách dài với số 123 và tên riêng.\n\n".repeat(3500));
        JSONObject book=store.create("QA hiệu năng đọc",text,null);
        c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",book.getString("id")).commit();
        c.getSharedPreferences("reader",0).edit().putFloat("fontSize",19).putBoolean("useSerif",true).commit();
        JSONObject report=new JSONObject().put("characters",text.length()).put("selectedBook",source.isFile());
        try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            long start=SystemClock.elapsedRealtime();
            activity.onActivity(a->{ReaderDialog d=new ReaderDialog(a,new UiTheme(a),store,book,i->{});dialog.set(d);d.show();});awaitPages(activity);
            report.put("openMs",SystemClock.elapsedRealtime()-start);
            AtomicInteger restored=new AtomicInteger();
            activity.onActivity(a->{try{
                ReaderDialog d=dialog.get();List<int[]> pages=(List<int[]>)get(d,"pages");report.put("pages19",pages.size());
                Method show=ReaderDialog.class.getDeclaredMethod("showPage",int.class,boolean.class);show.setAccessible(true);show.invoke(d,pages.size()*3/4,false);restored.set((int)get(d,"anchor"));
                field("fontSize").setFloat(d,30);((TextView)get(d,"body")).setTextSize(30);invoke(d,"paginate");
            }catch(Exception e){throw new RuntimeException(e);}});
            start=SystemClock.elapsedRealtime();awaitPages(activity);report.put("resize30Ms",SystemClock.elapsedRealtime()-start);
            activity.onActivity(a->{try{
                ReaderDialog d=dialog.get();List<int[]> pages=(List<int[]>)get(d,"pages");TextView body=(TextView)get(d,"body");
                report.put("pages30",pages.size()).put("widthPx",body.getWidth()).put("heightPx",body.getHeight());
                int prior=0;StringBuilder out=new StringBuilder();
                for(int[] p:pages){assertEquals(prior,p[0]);assertTrue(p[1]>p[0]);assertFalse(p[0]>0&&Character.isLowSurrogate(text.charAt(p[0])));out.append(text,p[0],p[1]);prior=p[1];}
                assertEquals(text,out.toString());int current=(int)get(d,"page");assertTrue(pages.get(current)[0]<=restored.get());assertTrue(pages.get(current)[1]>restored.get());
                Method show=ReaderDialog.class.getDeclaredMethod("showPage",int.class,boolean.class);show.setAccessible(true);
                // Measure exactly what TextView renders, including fallback glyphs and trailing newlines.
                for(int i=0;i<pages.size();i++){
                    show.invoke(d,i,false);body.measure(View.MeasureSpec.makeMeasureSpec(body.getWidth(),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(body.getHeight(),View.MeasureSpec.EXACTLY));body.layout(body.getLeft(),body.getTop(),body.getRight(),body.getBottom());
                    Layout l=body.getLayout();int last=l.getLineCount()-1;while(last>0&&body.getText().subSequence(l.getLineStart(last),l.getLineEnd(last)).toString().trim().isEmpty())last--;
                    assertTrue("Clipped page "+i+": "+l.getLineBottom(last)+">"+body.getHeight()+" offset="+pages.get(i)[0],l.getLineBottom(last)<=body.getHeight());
                    for(int line=0;line<=last;line++){
                        int begin=l.getLineStart(line),end=l.getLineEnd(line);while(end>begin&&Character.isWhitespace(body.getText().charAt(end-1)))end--;
                        float right=end==begin?0:Math.max(l.getPrimaryHorizontal(begin),l.getPrimaryHorizontal(end));
                        assertTrue("Text outside horizontal bounds: "+right+">"+body.getWidth()+" page="+i+" line="+line+" text="+body.getText().subSequence(begin,end),right<=body.getWidth()+1);
                    }
                }
                show.invoke(d,current,false);
            }catch(Exception e){throw new RuntimeException(e);}});
            // Returning to an already seen font/viewport should restore the source anchor.
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();field("fontSize").setFloat(d,19);((TextView)get(d,"body")).setTextSize(19);invoke(d,"paginate");}catch(Exception e){throw new RuntimeException(e);}});
            start=SystemClock.elapsedRealtime();awaitPages(activity);report.put("return19Ms",SystemClock.elapsedRealtime()-start);
            File dir=new File(c.getExternalFilesDir(null),"qa");dir.mkdirs();String tag=InstrumentationRegistry.getArguments().getString("readerTag","after");
            Files.write(new File(dir,"reader-"+tag+".json").toPath(),report.toString(2).getBytes(StandardCharsets.UTF_8));
            Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();try(OutputStream out=new FileOutputStream(new File(dir,"reader-"+tag+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();
            activity.onActivity(a->dialog.get().dismiss());
        }
    }
}
