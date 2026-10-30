package studio.windi.soundbooki;
import android.content.*;
import android.graphics.Bitmap;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class AndroidSmokeTest {
 @Before public void isolateLibrary(){BookStore.fixtureRoot=new File(context().getFilesDir(),".qa/smoke");BookStore.fixtureRoot.mkdirs();}
 @After public void releaseLibrary() throws Exception {context().startService(new Intent(context(),PlaybackService.class).setAction("stop"));Thread.sleep(300);BookStore.fixtureRoot=null;}
 private Context context(){return InstrumentationRegistry.getInstrumentation().getTargetContext();}
 private File qa(){File q=new File(context().getFilesDir(),".qa");q.mkdirs();return q;}
 @Test public void sourcePartitionAndCache() throws Exception {
  String source="  Tiếng Việt: số 12,5 và người đọc.\n\n"+"Một câu giữ nguyên dấu. ".repeat(40)+" 👋 phần cuối  ";
  assertEquals(source,String.join("",TextChunks.split(source)));
  for(String part:TextChunks.split(source))assertTrue(part.codePointCount(0,part.length())<=120);
  BookStore s=new BookStore(context());File a=s.audio("Điều tôi muốn nghe","Đức Trí"),b=s.audio("Điều tôi muốn nghe","Mỹ Duyên");assertNotEquals(a,b);assertNotEquals(a,s.audio("Chữ đã sửa","Đức Trí"));
  JSONObject book=s.create("QA riêng","Một đoạn nguyên bản.",null);String original=book.getString("originalText"),sig=BookStore.contentSignature(book);book.put("text","Đã sửa.");s.save(book);s.position(book.getString("id"),sig,9,999);assertEquals(0,s.load(book.getString("id")).getInt("position"));assertEquals(original,s.load(book.getString("id")).getString("originalText"));
  float[] tone=new float[2400];for(int i=0;i<tone.length;i++)tone[i]=(float)(.15*Math.sin(i*.1));File f=new File(qa(),"atomic.wav");AudioFiles.wav(f,tone);assertTrue(AudioFiles.valid(f));byte[] good=Files.readAllBytes(f.toPath());File partial=new File(qa(),"broken.partial");AudioFiles.atomic(partial,Arrays.copyOf(good,good.length-10));assertFalse(AudioFiles.valid(partial));
  ByteArrayOutputStream export=new ByteArrayOutputStream();AudioFiles.export(List.of(f,f),export);File twice=new File(qa(),"twice.wav");AudioFiles.atomic(twice,export.toByteArray());assertEquals(9600,AudioFiles.inspect(twice)[1]);
 }
 @Test public void realEpubAndPdfExtraction() throws Exception {
  File epub=new File(qa(),"book.epub");try(ZipOutputStream z=new ZipOutputStream(new FileOutputStream(epub))){
   put(z,"META-INF/container.xml","<container><rootfiles><rootfile full-path='OEBPS/content.opf'/></rootfiles></container>");
   put(z,"OEBPS/content.opf","<package><manifest><item id='two' href='two.xhtml'/><item id='one' href='one.xhtml'/></manifest><spine><itemref idref='one'/><itemref idref='two'/></spine></package>");
   put(z,"OEBPS/one.xhtml","<html><body><h1>Chương Một</h1><p>Đây là tiếng Việt có dấu.</p></body></html>");put(z,"OEBPS/two.xhtml","<html><body><h1>Chương Hai</h1><p>Nội dung tiếp theo.</p></body></html>");
  }
  String t=BookImporter.epub(epub);assertTrue(t.indexOf("Chương Một")<t.indexOf("Chương Hai"));assertTrue(t.contains("tiếng Việt có dấu"));
  com.tom_roush.pdfbox.android.PDFBoxResourceLoader.init(context());File pdf=new File(qa(),"book.pdf");
  try(com.tom_roush.pdfbox.pdmodel.PDDocument d=new com.tom_roush.pdfbox.pdmodel.PDDocument()){
   com.tom_roush.pdfbox.pdmodel.PDPage page=new com.tom_roush.pdfbox.pdmodel.PDPage();d.addPage(page);
   try(com.tom_roush.pdfbox.pdmodel.PDPageContentStream stream=new com.tom_roush.pdfbox.pdmodel.PDPageContentStream(d,page)){stream.beginText();stream.setFont(com.tom_roush.pdfbox.pdmodel.font.PDType1Font.HELVETICA,12);stream.newLineAtOffset(50,700);stream.showText("Soundbooki PDF local test.");stream.endText();}d.save(pdf);
  }
  assertTrue(BookImporter.pdf(pdf).contains("Soundbooki PDF local test."));
 }
 @Test public void importResumeKeepsCompletedPages() throws Exception {
  BookStore s=new BookStore(context());File epub=new File(qa(),"resume.epub");
  try(ZipOutputStream z=new ZipOutputStream(new FileOutputStream(epub))){
   put(z,"META-INF/container.xml","<container><rootfiles><rootfile full-path='book.opf'/></rootfiles></container>");
   put(z,"book.opf","<package><manifest><item id='a' href='a.xhtml'/><item id='b' href='b.xhtml'/></manifest><spine><itemref idref='a'/><itemref idref='b'/></spine></package>");
   put(z,"a.xhtml","<html><body><h1>Chương Một</h1><p>Trang đã hoàn tất.</p></body></html>");
   put(z,"b.xhtml","<html><body><h1>Chương Hai</h1><p>Trang tiếp theo.</p></body></html>");
  }
  String full=BookImporter.epub(epub);String[] firstPage={""};BookImporter.epubPages(epub,(i,n,t,h)->{if(i==0)firstPage[0]=t;});String first=firstPage[0];
  JSONObject b=s.create("QA resume",first,epub).put("sourceFormat","epub").put("status","interrupted").put("importedPages",1).put("pages",new JSONArray().put(new JSONObject().put("index",0).put("startOffset",0).put("endOffset",first.length()))).put("sourceHeadings",new JSONArray());s.save(b);
  JSONObject result=BookImporter.resume(b,s);assertEquals("ready",result.getString("status"));assertEquals(2,result.getInt("importedPages"));assertEquals(full,result.getString("text"));assertEquals(full,result.getString("originalText"));assertEquals(2,result.getJSONArray("pages").length());
 }
 static void put(ZipOutputStream z,String path,String value) throws Exception {z.putNextEntry(new ZipEntry(path));z.write(value.getBytes(StandardCharsets.UTF_8));z.closeEntry();}
 @Test public void realNanoNativeAndCancellation() throws Exception {
  Context c=context();long start=System.nanoTime();File models=ModelAssets.prepare(c,s->{});
  try(NanoEngine engine=new NanoEngine(models,2)){
   float[] samples=engine.synthesize("Mỗi trang sách mở ra một thế giới mới. Hãy lắng nghe và khám phá.","Đức Trí",()->false);assertTrue(samples.length>24000);File output=new File(qa(),"android-real-nano.wav");AudioFiles.wav(output,samples);assertTrue(AudioFiles.valid(output));
   AtomicInteger checks=new AtomicInteger();try{engine.synthesize("Đoạn này sẽ được hủy giữa quá trình tạo giọng.","Đức Trí",()->checks.incrementAndGet()>3);fail("Cancellation ignored");}catch(InterruptedException expected){}
   JSONObject metrics=new JSONObject().put("model","VieNeu v3 Nano").put("abi",Build.SUPPORTED_ABIS[0]).put("sdk",Build.VERSION.SDK_INT).put("device",Build.MODEL).put("loadSeconds",engine.loadSeconds).put("totalSeconds",(System.nanoTime()-start)/1e9).put("audioSeconds",samples.length/24000.0).put("threads",2).put("steps",16);
   AudioFiles.atomic(new File(qa(),"nano-results.json"),metrics.toString(2).getBytes(StandardCharsets.UTF_8));
  }
 }
 @Test public void cloudSnapshotIdentityAndQuoteQR() throws Exception {
  JSONObject book=new JSONObject().put("id",BookStore.id()).put("title","Sách thử").put("text","Tiếng Việt nguyên văn. ".repeat(250));
  JSONObject trial=CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],true),full=CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],false);
  int count=0;JSONArray parts=trial.getJSONArray("segments");for(int i=0;i<parts.length();i++){JSONObject p=parts.getJSONObject(i);String s=p.getString("text");count+=s.codePointCount(0,s.length());assertTrue(p.getString("id").matches("[a-f0-9]{32}"));}
  assertEquals(4000,count);assertTrue(full.getJSONArray("segments").length()>parts.length());assertEquals("pro-cloud-heygen-v1",trial.getString("revision"));
  String credential=CloudIdentity.credential(context(),"https://example.invalid/books");assertTrue(credential.matches("wsn_book_[a-f0-9]{64}"));assertEquals(credential,CloudIdentity.credential(context(),"https://example.invalid/books"));assertNotEquals(credential,CloudIdentity.credential(context(),"https://other.invalid/books"));assertTrue(CloudIdentity.code(context()).matches("SN[A-F0-9]{12}"));
  try{CloudClient.validateBase("http://example.invalid");fail("HTTP accepted");}catch(IOException expected){}
  JSONObject bank=new JSONObject().put("bin","970423").put("account","1234567890");JSONObject order=new JSONObject().put("paymentCode","SB"+"A".repeat(32)).put("amountVND",25000);
  String payload=PaymentQR.payload(bank,order);assertTrue(payload.contains("540525000"));assertTrue(payload.contains("SB"+"A".repeat(32)));assertEquals(660,PaymentQR.image(bank,order).getWidth());
  try{PaymentQR.payload(bank,order.put("paymentCode","SN000000000000"));fail("Device code accepted as payment");}catch(IOException expected){}
 }
 @Test public void nativePlayerAndScreens() throws Exception {
  Context c=context();BookStore store=new BookStore(c);JSONObject book=store.create("Góc nghe thử Android","Trong một thế giới bận rộn, mỗi trang sách mở ra những điều mới mẻ để chúng ta lắng nghe và suy ngẫm.\n\nĐây là đoạn tiếp theo của cuốn sách trên điện thoại, được tạo trong khi phần đầu đang phát.",null);
  c.getSharedPreferences(MainActivity.class.getName(),Context.MODE_PRIVATE).edit().putString("book",book.getString("id")).commit();
  try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
   Thread.sleep(1200);screenshot("home");
   scenario.onActivity(a->{
    WalkthroughDialog wt=a.openWalkthrough();
    assertNotNull(wt);
    assertTrue(wt.isShowing());
    assertEquals(0,wt.getPageIndex());
    assertTrue("Welcome audio should be active",wt.getAudioPlayer().isActive());
    assertTrue("Welcome voice player should be prepared",wt.getAudioPlayer().isVoiceReady());
    assertTrue("Welcome background music should be prepared",wt.getAudioPlayer().isMusicReady());
   });
   Thread.sleep(600);screenshot("walkthrough-1");
   scenario.onActivity(a->{
    WalkthroughDialog wt=a.getWalkthroughDialog();
    wt.setPage(1);assertEquals(1,wt.getPageIndex());
    wt.setPage(2);assertEquals(2,wt.getPageIndex());
    wt.setPage(3);assertEquals(3,wt.getPageIndex());
    wt.setPage(4);assertEquals(4,wt.getPageIndex());
    wt.toggleMute();assertTrue(wt.getAudioPlayer().isMuted());
    wt.toggleMute();assertFalse(wt.getAudioPlayer().isMuted());
   });
   Thread.sleep(600);screenshot("walkthrough-5");
   scenario.onActivity(a->{
    WalkthroughDialog wt=a.getWalkthroughDialog();
    wt.dismiss();
   });
   Thread.sleep(300);
   scenario.onActivity(a->{assertFalse("Welcome audio must stop after dismiss",a.getWalkthroughDialog().getAudioPlayer().isActive());});
   scenario.onActivity(a->a.appShell().select(AppShell.CREATE));
   scenario.onActivity(a->{ArrayList<View> editors=new ArrayList<>();a.getWindow().getDecorView().findViewsWithText(editors,"Nội dung sách, có thể chỉnh sửa",View.FIND_VIEWS_WITH_CONTENT_DESCRIPTION);assertFalse(editors.isEmpty());assertEquals(book.optString("text"),((EditText)editors.get(0)).getText().toString());Button b=find(a.getWindow().getDecorView(),"Nghe chương đã chọn");assertNotNull(b);b.performClick();});
   long deadline=System.currentTimeMillis()+120000;while(System.currentTimeMillis()<deadline&&!PlaybackService.playing)Thread.sleep(300);
   assertTrue("Player did not start: "+PlaybackService.message,PlaybackService.playing);assertTrue(PlaybackService.current<PlaybackService.total);Thread.sleep(650);screenshot("playing");long bgAt=android.os.SystemClock.elapsedRealtime();scenario.moveToState(androidx.lifecycle.Lifecycle.State.CREATED);Thread.sleep(1400);assertTrue("Background state after "+(android.os.SystemClock.elapsedRealtime()-bgAt)+"ms: "+PlaybackService.message+" running="+PlaybackService.running+" paused="+PlaybackService.paused+" index="+PlaybackService.current+"/"+PlaybackService.total,PlaybackService.playing);scenario.moveToState(androidx.lifecycle.Lifecycle.State.RESUMED);
   scenario.onActivity(a->a.startService(new Intent(a,PlaybackService.class).setAction("pause")));Thread.sleep(400);assertTrue("Pause state: "+PlaybackService.message,PlaybackService.paused);Thread.sleep(1000);JSONObject saved=store.load(book.getString("id"));assertTrue("Persisted position: "+saved.getInt("positionMs")+"ms for "+saved.getString("id")+" active="+PlaybackService.bookId,saved.getInt("positionMs")>0);
   scenario.onActivity(MainActivity::appCloud);Thread.sleep(500);screenshot("cloud-unconfigured");
   scenario.onActivity(a->a.startService(new Intent(a,PlaybackService.class).setAction("stop")));Thread.sleep(500);assertFalse(PlaybackService.running);
   assertTrue(store.audio(BookStore.spokenParts(book.getString("text")).get(0),"Đức Trí").isFile());
  }
 }
 static Button find(View view,String label){if(view instanceof Button&&((Button)view).getText().toString().equals(label))return (Button)view;if(view instanceof ViewGroup){ViewGroup g=(ViewGroup)view;for(int i=0;i<g.getChildCount();i++){Button b=find(g.getChildAt(i),label);if(b!=null)return b;}}return null;}
 void screenshot(String name) throws Exception {Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File dir=new File(context().getExternalFilesDir(null),"qa");dir.mkdirs();try(OutputStream out=new FileOutputStream(new File(dir,name+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();}
}
