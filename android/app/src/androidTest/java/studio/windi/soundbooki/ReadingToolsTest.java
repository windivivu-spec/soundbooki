package studio.windi.soundbooki;

import android.app.*;import android.content.*;import android.graphics.*;import android.media.*;import android.os.*;import android.text.*;import android.view.*;import android.widget.*;
import androidx.test.core.app.ActivityScenario;import androidx.test.ext.junit.runners.AndroidJUnit4;import androidx.test.platform.app.InstrumentationRegistry;
import org.json.*;import org.junit.*;import org.junit.runner.RunWith;import java.io.*;import java.lang.reflect.*;import java.nio.file.*;import java.util.*;import java.util.concurrent.atomic.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class ReadingToolsTest {
 Context context;BookStore store;
 @Before public void setup(){context=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(context.getFilesDir(),".qa/reading-tools");BookStore.fixtureRoot.mkdirs();store=new BookStore(context);context.getSharedPreferences("settings",0).edit().putBoolean(WalkthroughDialog.PREF_SEEN,true).commit();}
 @After public void cleanup(){BookStore.fixtureRoot=null;}
 static Object field(Object obj,String name)throws Exception{Field f=obj.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(obj);}
 static Object call(Object obj,String name,Class<?>[] types,Object... args)throws Exception{Method m=obj.getClass().getDeclaredMethod(name,types);m.setAccessible(true);return m.invoke(obj,args);}
 void snap(String name)throws Exception{InstrumentationRegistry.getInstrumentation().waitForIdleSync();Thread.sleep(250);Bitmap bitmap=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File dir=new File(context.getExternalFilesDir(null),"qa/reading-tools");dir.mkdirs();try(OutputStream out=new FileOutputStream(new File(dir,name+".png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();}
 JSONObject fixture()throws Exception{JSONObject b=store.create("Sách QA Việt–Anh","Đọc tiếng Việt thật dễ. It is a truth universally acknowledged. 🌍\n\n"+"Một trang sách mở ra một khoảng trời. ".repeat(60),null);context.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",b.getString("id")).commit();return b;}
 @Test public void accentsRangesEditionsAndRouting()throws Exception{
  JSONObject b=fixture();String text=b.getString("text");List<int[]> found=ReadingTools.search(text,"doc tieng viet");assertEquals(1,found.size());assertEquals("Đọc tiếng Việt",text.substring(found.get(0)[0],found.get(0)[1]));assertEquals(1,ReadingTools.search(text,"🌍").size());assertEquals(1,ReadingTools.search("Điện", "dien").size());
  JSONObject note=ReadingTools.save(store,b,0,22,"Ghi chú 🌍","pink",null);assertEquals(1,ReadingTools.notes(store,b.getString("id")).length());ReadingTools.save(store,b,0,22,"Sửa ghi chú","blue",note.getString("id"));assertEquals(1,ReadingTools.notes(store,b.getString("id")).length());
  String old=BookStore.contentSignature(b);b.put("bilingual",true).put("englishVoice","offline").put("englishRevision","1");assertNotEquals(old,BookStore.contentSignature(b));String sig=BookStore.contentSignature(b);b.put("speed",2);assertEquals(sig,BookStore.contentSignature(b));assertNotEquals(store.audio(text,"Đức Trí"),store.audio(text,b));assertEquals(text,String.join("",new BookChapters.Plan(b).parts));
  assertFalse(Bilingual.english("Sherlock Holmes"));assertFalse(Bilingual.english("Đây là tiếng Việt."));assertTrue(Bilingual.english("It is a truth universally acknowledged."));
  b.put("text","Nội dung mới.");store.save(b);assertEquals(1,ReadingTools.notes(store,b.getString("id")).length());assertNotEquals(BookStore.hash(b.getString("text")),note.getString("edition"));ReadingTools.remove(store,b.getString("id"),note.getString("id"));assertEquals(0,ReadingTools.notes(store,b.getString("id")).length());
 }
 @Test public void realAacM4bWithCoverChaptersMusicAndCancellation()throws Exception{
  JSONObject b=fixture();b.put("bgmTrack","rain").put("bgmVolume",.12);List<File> files=new ArrayList<>();for(int i=0;i<2;i++){File f=store.audio("fixture-"+i,b);float[] audio=new float[24000*(i+1)];for(int n=0;n<audio.length;n++)audio[n]=(float)(Math.sin(n*2*Math.PI*440/24000)*.1);AudioFiles.wav(f,audio);files.add(f);}
  List<Mp4BookMetadata.Chapter> chapters=List.of(new Mp4BookMetadata.Chapter("Chương Một",0,1000),new Mp4BookMetadata.Chapter("Chương Hai 🌍",1000,3000));File result=M4bExport.create(context,store,b,files,chapters,()->false,p->{});assertTrue(result.length()>1000);MediaExtractor extractor=new MediaExtractor();try{extractor.setDataSource(result.getPath());boolean aac=false;for(int i=0;i<extractor.getTrackCount();i++)if("audio/mp4a-latm".equals(extractor.getTrackFormat(i).getString(MediaFormat.KEY_MIME)))aac=true;assertTrue(aac);}finally{extractor.release();}
  File dir=new File(context.getExternalFilesDir(null),"qa/reading-tools");dir.mkdirs();Files.copy(result.toPath(),new File(dir,"android-native.m4b").toPath(),StandardCopyOption.REPLACE_EXISTING);result.delete();
  try{M4bExport.create(context,store,b,files,chapters,()->true,p->{});fail("Expected cancellation");}catch(InterruptedIOException expected){}
 }
 @Test public void nativeReaderSearchHighlightsNotebookAndPaste()throws Exception{
  JSONObject b=fixture();ReadingTools.save(store,b,0,22,"Ghi chú tiếng Việt 🌍","yellow",null);AtomicReference<ReaderDialog> reader=new AtomicReference<>();
  try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
   activity.onActivity(a->{ReaderDialog d=new ReaderDialog(a,new UiTheme(a),store,b,c->{});reader.set(d);d.show();});
   for(int i=0;i<120;i++){AtomicBoolean ready=new AtomicBoolean();activity.onActivity(a->{try{ready.set(!((List<?>)field(reader.get(),"pages")).isEmpty()&&!(boolean)field(reader.get(),"paginationRunning"));}catch(Exception e){throw new RuntimeException(e);}});if(ready.get())break;Thread.sleep(50);}
   activity.onActivity(a->{try{TextView body=(TextView)field(reader.get(),"body");assertTrue(body.getText() instanceof Spanned);assertEquals(1,((Spanned)body.getText()).getSpans(0,body.length(),android.text.style.BackgroundColorSpan.class).length);call(reader.get(),"notebook",new Class<?>[]{});}catch(Exception e){throw new RuntimeException(e);}});snap("notebook-light");
   activity.onActivity(a->{try{for(Dialog p:new ArrayList<>((List<Dialog>)field(reader.get(),"panels")))p.dismiss();call(reader.get(),"searchContent",new Class<?>[]{});List<Dialog> panels=(List<Dialog>)field(reader.get(),"panels");View view=panels.get(panels.size()-1).getWindow().getDecorView();EditText query=(EditText)ReaderFeaturesTest.find(view,"Tìm trong nội dung sách");query.setText("doc tieng viet");}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(600);snap("search-light");
   activity.onActivity(a->{try{for(Dialog p:new ArrayList<>((List<Dialog>)field(reader.get(),"panels")))p.dismiss();ReaderPreferences prefs=(ReaderPreferences)field(reader.get(),"settings");prefs.background="night";prefs.save();call(reader.get(),"applyAppearance",new Class<?>[]{});call(reader.get(),"notebook",new Class<?>[]{});}catch(Exception e){throw new RuntimeException(e);}});snap("notebook-dark");
   activity.onActivity(a->{reader.get().dismiss();a.appPasteText();});snap("paste-dialog");
  }
 }
 @Test public void actualBilingualServiceProducesBothLanguages()throws Exception{
  JSONObject b=store.create("Việt–Anh inference QA","Xin chào bạn. It is a truth universally acknowledged. Chúc bạn vui vẻ.",null);
  try(EnglishSpeech speech=new EnglishSpeech(context)){b.put("bilingual",true).put("englishVoice",speech.select("")).put("englishRevision",speech.revision());}store.save(b);
  context.startForegroundService(new Intent(context,PlaybackService.class).setAction("local").putExtra("book",b.getString("id")).putExtra("pausePlayback",true));
  try{BookChapters.Plan plan=new BookChapters.Plan(b);long until=SystemClock.elapsedRealtime()+180000;boolean complete=false;while(SystemClock.elapsedRealtime()<until){complete=true;for(String part:plan.parts)if(!AudioFiles.valid(store.audio(part,b)))complete=false;if(complete)break;Thread.sleep(250);}assertTrue("Bilingual generation: "+PlaybackService.message,complete);assertEquals(b.getString("text"),store.load(b.getString("id")).getString("originalText"));assertTrue(plan.parts.stream().anyMatch(Bilingual::english));}finally{context.startService(new Intent(context,PlaybackService.class).setAction("stop"));Thread.sleep(500);}
 }
 @Test public void englishOfflineAvailabilityNeverFallsBackToNetwork()throws Exception{
  File dir=new File(context.getExternalFilesDir(null),"qa/reading-tools");dir.mkdirs();JSONObject report=new JSONObject();try(EnglishSpeech speech=new EnglishSpeech(context)){String name=speech.select("");report.put("voice",name).put("revision",speech.revision());File file=new File(dir,"english.wav");float[] audio=speech.synthesize("It is a truth universally acknowledged.",file,()->false);assertTrue(audio.length>1000);AudioFiles.wav(file,audio);report.put("inference","PASS");}catch(IOException missing){report.put("inference","UNAVAILABLE").put("reason",missing.getMessage());assertTrue(missing.getMessage().contains("offline"));}AudioFiles.atomic(new File(dir,"english-report.json"),report.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
 }
}
