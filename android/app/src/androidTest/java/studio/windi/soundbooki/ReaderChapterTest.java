package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.pdmodel.font.PDType1Font;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.atomic.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class ReaderChapterTest {
    Context c;BookStore store;
    @Before public void setup(){c=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(c.getFilesDir(),".qa/reader-chapters");BookStore.fixtureRoot.mkdirs();store=new BookStore(c);c.getSharedPreferences("onboarding",0).edit().putBoolean("done",true).commit();}
    @After public void after()throws Exception {c.startService(new Intent(c,PlaybackService.class).setAction("stop"));Thread.sleep(300);BookStore.fixtureRoot=null;}
    static Object field(Object o,String name)throws Exception {Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    static void invoke(Object o,String name,Class<?> type,Object value)throws Exception {Method m=o.getClass().getDeclaredMethod(name,type);m.setAccessible(true);m.invoke(o,value);}
    void activate(JSONObject book){c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",book.optString("id")).commit();}
    @Test public void cleanupLargeBookOpensAndApplies()throws Exception {
        // Probe the exact old static initializer on Android, which JVM unit tests missed.
        String probe;
        try{java.util.regex.Pattern.compile("x",256);probe="old Unicode flag accepted";}catch(Exception e){probe=e.toString();}
        AudioFiles.atomic(new File(BookStore.fixtureRoot,"old-pattern-probe.txt"),probe.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String text="***\n- 12 -\nMột trang sách giữ nguyên tiếng Việt có dấu.\n".repeat(8000);
        JSONObject book=store.create("QA dọn sách dài",text,null);activate(book);AtomicReference<CleanupDialog> ref=new AtomicReference<>();AtomicReference<String> applied=new AtomicReference<>();
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{CleanupDialog d=new CleanupDialog(a,new UiTheme(a),text,Set.of(),applied::set);ref.set(d);d.show();});
            long end=System.currentTimeMillis()+20000;
            while(System.currentTimeMillis()<end){AtomicBoolean done=new AtomicBoolean();scenario.onActivity(a->{try{done.set(field(ref.get(),"lastResult")!=null);}catch(Exception e){throw new RuntimeException(e);}});if(done.get())break;Thread.sleep(100);}
            screenshot("cleanup-preview");
            scenario.onActivity(a->{try{assertTrue(ref.get().isShowing());assertNotNull(field(ref.get(),"lastResult"));assertTrue(((LinearLayout)field(ref.get(),"changesList")).getChildCount()<=102);((Button)field(ref.get(),"applyBtn")).performClick();}catch(Exception e){throw new RuntimeException(e);}});
            assertNotNull(applied.get());assertFalse(applied.get().contains("***"));assertTrue(applied.get().contains("tiếng Việt có dấu"));assertEquals(text,store.load(book.getString("id")).getString("originalText"));
        }
    }
    @Test public void pdfTypographyWithoutChapterWordAndEpubHeadings()throws Exception {
        com.tom_roush.pdfbox.android.PDFBoxResourceLoader.init(c);File pdf=new File(BookStore.fixtureRoot,"numbered.pdf");
        try(PDDocument doc=new PDDocument()){
            addPage(doc,"1",24,"",12);addPage(doc,"FIRST REAL TITLE",24,"The original body has enough letters for a normal font baseline.",12);
            addPage(doc,"2",24,"SECOND REAL TITLE",24);addPage(doc,"More source text for the second section of this test book.",12,"",12);doc.save(pdf);
        }
        String raw=BookImporter.pdf(pdf);JSONArray markers=PdfChapterSource.markers(pdf);assertEquals(markers.toString(),2,markers.length());
        JSONObject book=store.create("QA nguồn PDF",raw,pdf).put("sourceFormat","pdf");book.put("text",PdfReflow.process(raw).text);BookChapters.set(book,BookChapters.fromSource(book,markers));List<PdfReflow.ChapterItem> chapters=BookChapters.get(book);assertEquals(book.getString("text"),join(chapters));assertTrue(chapters.stream().anyMatch(ch->ch.title.contains("FIRST REAL TITLE")));assertTrue(chapters.stream().anyMatch(ch->ch.title.contains("SECOND REAL TITLE")));
        String epub="LỜI MỞ ĐẦU\nNội dung.\n\nMỘT KHỞI ĐẦU MỚI\nMột đoạn tiếng Việt.";JSONObject e=store.create("QA EPUB heading",epub,null);JSONArray hs=new JSONArray().put(new JSONObject().put("title","LỜI MỞ ĐẦU").put("startOffset",0)).put(new JSONObject().put("title","MỘT KHỞI ĐẦU MỚI").put("startOffset",epub.indexOf("MỘT")));BookChapters.set(e,BookChapters.fromSource(e,hs));assertEquals(2,BookChapters.get(e).size());assertEquals(epub,join(BookChapters.get(e)));
        e.put("text","Đã sửa hoàn toàn. "+epub);assertEquals(1,BookChapters.get(e).size());
    }
    @Test public void selected203PagePdf() throws Exception {
        File source=new File(c.getExternalFilesDir(null),"qa/selected-203-page.pdf");
        org.junit.Assume.assumeTrue("Owner-selected real-book fixture is optional",source.isFile());
        com.tom_roush.pdfbox.android.PDFBoxResourceLoader.init(c);
        StringBuilder text=new StringBuilder();AtomicInteger pages=new AtomicInteger();long start=System.nanoTime();
        JSONArray markers=PdfChapterSource.extract(source,(i,n,t,h)->{if(i>0)text.append("\n\n");text.append(t);pages.incrementAndGet();});
        assertEquals(203,pages.get());assertTrue("Expected verified source chapter sequence: "+markers,markers.length()>=20);
        JSONObject book=store.create("QA sách 203 trang",text.toString(),null).put("sourceFormat","pdf");
        book.put("text",PdfReflow.process(text.toString()).text);BookChapters.set(book,BookChapters.fromSource(book,markers));
        assertEquals(book.optString("text"),join(BookChapters.get(book)));
        assertTrue(BookChapters.get(book).size()>=20);
        AudioFiles.atomic(new File(BookStore.fixtureRoot,"selected-book-result.json"),new JSONObject().put("pages",pages.get()).put("chapters",BookChapters.get(book).size()).put("seconds",(System.nanoTime()-start)/1e9).put("sourceMarkers",markers).toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
    static void addPage(PDDocument d,String a,int sizeA,String b,int sizeB)throws Exception {PDPage page=new PDPage();d.addPage(page);try(PDPageContentStream s=new PDPageContentStream(d,page)){s.beginText();s.setFont(PDType1Font.HELVETICA,sizeA);s.newLineAtOffset(50,700);s.showText(a);s.setFont(PDType1Font.HELVETICA,sizeB);s.newLineAtOffset(0,-60);s.showText(b);s.endText();}}
    static String join(List<PdfReflow.ChapterItem> chapters){StringBuilder b=new StringBuilder();for(PdfReflow.ChapterItem ch:chapters)b.append(ch.text);return b.toString();}
    @Test public void pagedReaderPreservesEveryCharacterAndRestoresAnchor()throws Exception {
        String text="Phần 1: Trang sách\n"+"Người đọc lật từng trang, giữ nguyên tiếng Việt và dấu câu. 👋\n\n".repeat(180)+"Phần 2: Ngày mới\n"+"Chúng ta đọc tiếp câu chuyện. ".repeat(80);
        JSONObject b=store.create("QA trang lật",text,null);activate(b);AtomicReference<ReaderDialog> ref=new AtomicReference<>();
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{ReaderDialog d=new ReaderDialog(a,new UiTheme(a),store,b,i->{});ref.set(d);d.show();});
            waitPages(scenario,ref);
            scenario.onActivity(a->{try{
                List<int[]> pages=(List<int[]>)field(ref.get(),"pages");assertTrue(pages.size()>10);StringBuilder out=new StringBuilder();int prior=0;for(int[] r:pages){assertEquals(prior,r[0]);assertTrue(r[1]>r[0]);out.append(text.substring(r[0],r[1]));prior=r[1];}assertEquals(text,out.toString());
                for(int i=0;i<pages.size();i++)invoke(ref.get(),"turn",int.class,1);
                invoke(ref.get(),"turn",int.class,-4);ref.get().dismiss();
                ReaderDialog again=new ReaderDialog(a,new UiTheme(a),store,b,i->{});ref.set(again);again.show();
            }catch(Exception e){throw new RuntimeException(e);}});
            waitPages(scenario,ref);
            scenario.onActivity(a->{try{assertTrue((int)field(ref.get(),"page")>0);}catch(Exception e){throw new RuntimeException(e);}});
            Thread.sleep(200);
            scenario.onActivity(a->{try{
                TextView body=(TextView)field(ref.get(),"body");android.text.Layout layout=body.getLayout();
                int last=layout.getLineCount()-1;while(last>0 && body.getText().subSequence(layout.getLineStart(last),layout.getLineEnd(last)).toString().trim().isEmpty())last--;
                assertTrue("Visible glyphs clipped: height="+body.getHeight()+" bottom="+layout.getLineBottom(last),layout.getLineBottom(last)<=body.getHeight());
            }catch(Exception e){throw new RuntimeException(e);}});
            screenshot("reader-paged");scenario.onActivity(a->ref.get().dismiss());
        }
    }
    void waitPages(ActivityScenario<MainActivity> scenario,AtomicReference<ReaderDialog> ref)throws Exception {for(int n=0;n<100;n++){AtomicBoolean done=new AtomicBoolean();scenario.onActivity(a->{try{done.set(!((List<?>)field(ref.get(),"pages")).isEmpty());}catch(Exception e){throw new RuntimeException(e);}});if(done.get())return;Thread.sleep(100);}fail("Pagination timed out");}
    // Distinct sentences avoid legitimately filling a short chapter from repeated cache hits
    // before the first MediaPlayer callback on a fast emulator.
    @Test public void realChapterBufferCompletionAndCancellation()throws Exception {
        String text="Phần 1: Chưa chọn\nKhông tạo phần này.\n\nPhần 2: Đang nghe\n"+java.util.stream.IntStream.range(1,19).mapToObj(i->"Trang "+i+" mở ra một thế giới mới để chúng ta lắng nghe và khám phá. ").collect(java.util.stream.Collectors.joining())+"\nPhần 3: Chưa nghe\nGiữ lại phần sau.";
        text += "\nMã lần kiểm tra " + System.nanoTime() + ".";
        JSONObject b=store.create("QA tạo chương",text,null);BookChapters.set(b,PdfReflow.extractChapters(text));store.save(b);BookChapters.Plan plan=new BookChapters.Plan(b);assertEquals(3,plan.chapters.size());assertEquals(text,String.join("",plan.parts));for(int p=plan.starts.get(1);p<plan.ends.get(1);p++)store.audio(plan.parts.get(p),b.optString("voice")).delete();activate(b);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->a.startForegroundService(new Intent(a,PlaybackService.class).setAction("local").putExtra("book",b.optString("id")).putExtra("chapter",1)));
            long deadline=System.currentTimeMillis()+120000;while(System.currentTimeMillis()<deadline&&!PlaybackService.playing)Thread.sleep(30);
            assertTrue(PlaybackService.message,PlaybackService.playing);assertTrue("Must buffer at least 5%",PlaybackService.chapterPercent>=5);assertEquals(plan.starts.get(1).intValue(),PlaybackService.current);assertTrue("Must continue producing after playback begins",PlaybackService.ready<plan.ends.get(1)-plan.starts.get(1));
            scenario.onActivity(a->a.startService(new Intent(a,PlaybackService.class).setAction("pause")));Thread.sleep(200);
            ChapterAudio library=new ChapterAudio(store,b.getString("id"));deadline=System.currentTimeMillis()+120000;while(System.currentTimeMillis()<deadline&&library.list().isEmpty())Thread.sleep(100);
            assertEquals(1,library.list().size());assertEquals(plan.chapters.get(1).title,library.list().get(0).getString("title"));assertTrue(AudioFiles.valid(library.file(library.list().get(0))));
            assertFalse(store.audio(plan.parts.get(0),b.getString("voice")).exists());assertFalse(store.audio(plan.parts.get(plan.starts.get(2)),b.getString("voice")).exists());
            scenario.onActivity(a->a.startService(new Intent(a,PlaybackService.class).setAction("stop")));Thread.sleep(250);assertFalse(PlaybackService.running);assertEquals(1,library.list().size());
            b.put("text","Bản chữ mới đã sửa.");store.save(b);assertEquals("Old take survives edit",1,library.list().size());
            scenario.onActivity(a->{AudioLibraryDialog d=new AudioLibraryDialog(a,new UiTheme(a),store,b);d.show();});Thread.sleep(400);screenshot("chapter-library");
        }
    }
    @Test public void stopDuringBufferKeepsOnlyCompletedParts() throws Exception {
        String text="Mã kiểm tra " + System.nanoTime() + ". " + "Những trang sách đưa ta đến một thế giới rộng lớn hơn. ".repeat(60);
        JSONObject b=store.create("QA hủy trong khi đệm",text,null);BookChapters.Plan plan=new BookChapters.Plan(b);activate(b);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->a.startForegroundService(new Intent(a,PlaybackService.class).setAction("local").putExtra("book",b.optString("id"))));
            long deadline=System.currentTimeMillis()+30000;
            while(System.currentTimeMillis()<deadline&&(!b.optString("id").equals(PlaybackService.bookId)||PlaybackService.ready<1))Thread.sleep(10);
            assertEquals(b.optString("id"),PlaybackService.bookId);assertTrue(PlaybackService.ready>=1);assertTrue(PlaybackService.chapterPercent<5);assertFalse(PlaybackService.playing);
            scenario.onActivity(a->a.startService(new Intent(a,PlaybackService.class).setAction("stop")));Thread.sleep(500);
            assertFalse(PlaybackService.running);assertTrue(AudioFiles.valid(store.audio(plan.parts.get(0),b.optString("voice"))));assertTrue(new ChapterAudio(store,b.getString("id")).list().isEmpty());
        }
    }
    void screenshot(String name)throws Exception {android.graphics.Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File dir=new File(c.getExternalFilesDir(null),"qa");dir.mkdirs();try(OutputStream out=new FileOutputStream(new File(dir,name+".png"))){image.compress(android.graphics.Bitmap.CompressFormat.PNG,100,out);}image.recycle();}
}
