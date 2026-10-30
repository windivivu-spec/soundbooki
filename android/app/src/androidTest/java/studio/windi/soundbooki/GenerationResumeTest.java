package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.graphics.Bitmap;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.lifecycle.Lifecycle;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import java.io.*;
import java.nio.file.Files;
import java.util.*;
import java.util.function.BooleanSupplier;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
@FixMethodOrder(org.junit.runners.MethodSorters.NAME_ASCENDING)
public class GenerationResumeTest {
    Context c;BookStore store;
    @Before public void setup(){c=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(c.getFilesDir(),".qa/generation-resume");BookStore.fixtureRoot.mkdirs();store=new BookStore(c);c.getSharedPreferences("settings",0).edit().putBoolean(WalkthroughDialog.PREF_SEEN,true).putInt("threads",2).commit();}
    @After public void cleanup()throws Exception {c.startService(new Intent(c,PlaybackService.class).setAction("stop"));Thread.sleep(250);BookStore.fixtureRoot=null;}
    static void waitFor(String reason,int seconds,BooleanSupplier test)throws Exception {long until=SystemClock.elapsedRealtime()+seconds*1000L;while(SystemClock.elapsedRealtime()<until){if(test.getAsBoolean())return;Thread.sleep(20);}fail(reason+" · "+PlaybackService.message);}
    JSONObject create(String title,int sentences)throws Exception {
        StringBuilder text=new StringBuilder("Phần 1: Một ngày mới\nMã kiểm tra "+System.nanoTime()+".\n");
        for(int i=0;i<sentences;i++)text.append("Trang sách thứ ").append(i+1).append(" kể về những điều nhỏ bé giúp chúng ta sống bình yên hơn mỗi ngày. ");
        JSONObject b=store.create(title,text.toString(),null);for(String part:new BookChapters.Plan(b).parts)store.audio(part,b.optString("voice")).delete();c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",b.getString("id")).commit();return b;
    }
    @Test public void fivePercentStartsAndProductionContinuesWithScreenOff()throws Exception {
        JSONObject b=create("QA tạo nền năm phần trăm",24);BookChapters.Plan plan=new BookChapters.Plan(b);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{a.appPlay(0,false,true);a.appShell().select(AppShell.LISTENING);});
            waitFor("Playback before completing the chapter",60,()->b.optString("id").equals(PlaybackService.bookId)&&PlaybackService.playing);
            assertTrue("Must meet 5%",PlaybackService.chapterPercent>=5);assertTrue("Must start before old 30%",PlaybackService.chapterPercent<30);assertTrue(PlaybackService.generating);
            Thread.sleep(550);screenshot("generation-loading");int before=PlaybackService.ready;
            scenario.moveToState(Lifecycle.State.CREATED);shell("input keyevent 223");
            try{
                waitFor("Screen must be off",5,()->!((PowerManager)c.getSystemService(Context.POWER_SERVICE)).isInteractive());
                waitFor("Producer must advance while app is backgrounded and screen is off",60,()->PlaybackService.ready>=before+2);
                assertTrue(PlaybackService.running);assertTrue(PlaybackService.ready<plan.parts.size());
                NotificationManager nm=(NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE);assertTrue(nm.getActiveNotifications().length>0);
            }finally{shell("input keyevent 224");shell("wm dismiss-keyguard");scenario.moveToState(Lifecycle.State.RESUMED);}
        }
    }
    @Test public void aPauseAndSaveForProcessRestart()throws Exception {
        JSONObject b=create("QA lưu tiến độ Nano",10);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{a.appPlay(0,false,true);a.appShell().select(AppShell.LISTENING);});
            waitFor("First audio",60,()->b.optString("id").equals(PlaybackService.bookId)&&PlaybackService.playing);
            scenario.onActivity(a->{a.appCommand("pause",null,0);a.appCommand("generation-pause",null,0);});
            waitFor("Finish bounded segment then release producer",60,()->PlaybackService.generationPaused&&!PlaybackService.generating);
            int ready=PlaybackService.ready;Thread.sleep(700);assertEquals("Paused producer must not advance",ready,PlaybackService.ready);assertTrue(PlaybackService.paused);assertFalse(PlaybackService.playing);
            String power=shell("dumpsys power"),activeLocks=power.substring(power.indexOf("Wake Locks:"),power.indexOf("Suspend Blockers:"));
            assertFalse("Paused playback and generation must release CPU",activeLocks.contains("soundbooki:narration"));
            scenario.onActivity(a->a.appCommand("generation-resume",null,0));
            waitFor("Resume the same worker without replaying audio",60,()->PlaybackService.ready>ready);assertTrue(PlaybackService.paused);
            scenario.onActivity(a->a.appCommand("generation-pause",null,0));
            waitFor("Pause again at a completed segment",60,()->PlaybackService.generationPaused&&!PlaybackService.generating);
            JSONObject saved=GenerationProgress.pending(store,b);assertNotNull(saved);assertEquals("paused",saved.getString("state"));assertEquals(0,saved.getInt("chapter"));assertFalse(saved.getBoolean("continuous"));
            BookChapters.Plan plan=new BookChapters.Plan(b);JSONArray cached=new JSONArray();Set<String> seen=new HashSet<>();
            for(String part:plan.parts){File f=store.audio(part,b.optString("voice"));if(AudioFiles.valid(f)&&seen.add(f.getName()))cached.put(new JSONObject().put("path",f.getPath()).put("mtime",f.lastModified()).put("hash",BookStore.hash(Files.readAllBytes(f.toPath()))));}
            assertTrue(cached.length()>0);assertTrue(cached.length()<plan.parts.size());assertTrue(new ChapterAudio(store,b.getString("id")).list().isEmpty());
            AudioFiles.atomic(restartFile(),new JSONObject().put("book",b.getString("id")).put("cached",cached).put("pid",android.os.Process.myPid()).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            Thread.sleep(550);screenshot("generation-paused");
        }
    }
    @Test public void bResumeAfterProcessRestartReusesOnlyValidCompletedAudio()throws Exception {
        Assume.assumeTrue("Run pause fixture first; also run independently after adb force-stop",restartFile().isFile());
        JSONObject fixture=NanoEngine.read(restartFile()),b=store.load(fixture.getString("book"));JSONObject checkpoint=GenerationProgress.pending(store,b);assertNotNull(checkpoint);
        if("true".equals(InstrumentationRegistry.getArguments().getString("requireProcessRestart")))assertNotEquals("Resume must run in a new Android process",fixture.getInt("pid"),android.os.Process.myPid());
        // Also reject an interrupted WAV despite the durable completed counter.
        JSONArray cached=fixture.getJSONArray("cached");File damaged=new File(cached.getJSONObject(0).getString("path"));try(RandomAccessFile f=new RandomAccessFile(damaged,"rw")){f.setLength(45);}assertFalse(AudioFiles.valid(damaged));
        c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",b.getString("id")).commit();
        ChapterAudio library=new ChapterAudio(store,b.getString("id"));
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->a.appShell().select(AppShell.LISTENING));Thread.sleep(650);
            scenario.onActivity(a->{View resume=text(a.getWindow().getDecorView(),"Tiếp tục tạo");assertNotNull("Restored progress has an explicit resume action",resume);resume.performClick();});
            waitFor("Generation resumes without unsolicited playback",15,()->PlaybackService.running&&PlaybackService.generating);assertTrue(PlaybackService.paused);assertFalse(PlaybackService.playing);
            waitFor("Only complete chapter is archived",120,()->!library.list().isEmpty());
            waitFor("Checkpoint completed",10,()->GenerationProgress.pending(store,b)==null);
            assertTrue(AudioFiles.valid(damaged));for(int i=1;i<cached.length();i++){JSONObject prior=cached.getJSONObject(i);File f=new File(prior.getString("path"));assertEquals("Reuse cache without rewriting",prior.getLong("mtime"),f.lastModified());assertEquals(prior.getString("hash"),BookStore.hash(Files.readAllBytes(f.toPath())));}
            assertEquals(1,library.list().size());assertTrue(AudioFiles.valid(library.file(library.list().get(0))));assertEquals(b.getString("originalText"),store.load(b.getString("id")).getString("originalText"));
        }
        restartFile().delete();
    }
    @Test public void checkpointNeverResumesAgainstChangedTextOrVoice()throws Exception {
        JSONObject b=create("QA snapshot tiến độ",2);GenerationProgress p=new GenerationProgress(store,b,0,false,true);p.part(0,5,"Chương đã chọn");p.state("paused");assertNotNull(GenerationProgress.pending(store,b));
        b.put("voice","Một giọng khác");assertNull(GenerationProgress.pending(store,b));b.put("voice","Đức Trí").put("text",b.getString("text")+" Đã sửa.");assertNull(GenerationProgress.pending(store,b));
        b.put("text",b.getString("originalText"));assertNotNull(GenerationProgress.pending(store,b));String source=b.getString("text");int cut=source.indexOf("Trang sách");BookChapters.set(b,List.of(new PdfReflow.ChapterItem("a","Mở đầu",0,cut,source.substring(0,cut)),new PdfReflow.ChapterItem("b","Phần mới",cut,source.length(),source.substring(cut))));assertNull("Changed chapter boundaries need a fresh selection",GenerationProgress.pending(store,b));
    }
    @Test public void resumeContinuousRequestKeepsCurrentChapterAndCanPauseUpcomingWork()throws Exception {
        String text="Phần 1: Trước đó\nChữ ở chương trước vẫn được giữ nguyên.\n\nPhần 2: Tiếp tục tại đây\nChỉ chuẩn bị đoạn đang nghe từ tiến độ đã lưu.\n\nPhần 3: Phía sau\nChương phía sau chưa cần tạo khi đang tạm dừng nghe.";
        JSONObject b=store.create("QA phạm vi nghe liên tục",text,null);BookChapters.set(b,PdfReflow.extractChapters(text));BookChapters.Plan plan=new BookChapters.Plan(b);b.put("positionChar",plan.chapters.get(1).startChar);store.save(b);
        float[] tone=new float[24000];Arrays.fill(tone,.01f);for(int i=plan.starts.get(1);i<plan.ends.get(1);i++)AudioFiles.wav(store.audio(plan.parts.get(i),b.optString("voice")),tone);
        GenerationProgress p=new GenerationProgress(store,b,0,true,true);p.state("paused");JSONObject saved=GenerationProgress.pending(store,b);assertNotNull(saved);
        c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",b.getString("id")).commit();ChapterAudio library=new ChapterAudio(store,b.getString("id"));
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{a.appResumeGeneration(saved);a.appShell().select(AppShell.LISTENING);});
            waitFor("Resume the saved chapter, rather than restarting the original chapter",15,()->!library.list().isEmpty());
            waitFor("Wait for the next chapter without inference",5,()->!PlaybackService.generating);assertEquals(plan.starts.get(1).intValue(),PlaybackService.current);assertTrue(PlaybackService.generationPending);assertTrue(PlaybackService.paused);
            assertFalse(store.audio(plan.parts.get(0),b.optString("voice")).exists());assertFalse(store.audio(plan.parts.get(plan.starts.get(2)),b.optString("voice")).exists());
            scenario.onActivity(a->a.appCommand("generation-pause",null,0));waitFor("Pause future chapter work",5,()->PlaybackService.generationPaused);assertEquals("paused",GenerationProgress.pending(store,b).optString("state"));
            scenario.onActivity(a->a.appCommand("generation-resume",null,0));Thread.sleep(350);assertFalse(PlaybackService.generationPaused);assertFalse("Do not claim inference while waiting for the next chapter",PlaybackService.generating);
        }
    }
    private File restartFile(){return new File(BookStore.fixtureRoot,"restart.json");}
    static View text(View v,String value){if(v instanceof Button&&((Button)v).getText().toString().equals(value)&&v.getVisibility()==View.VISIBLE)return v;if(v instanceof ViewGroup){ViewGroup group=(ViewGroup)v;for(int i=0;i<group.getChildCount();i++){View found=text(group.getChildAt(i),value);if(found!=null)return found;}}return null;}
    static String shell(String command)throws Exception {try(ParcelFileDescriptor fd=InstrumentationRegistry.getInstrumentation().getUiAutomation().executeShellCommand(command);InputStream in=new ParcelFileDescriptor.AutoCloseInputStream(fd)){return new String(in.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);}}
    private void screenshot(String name)throws Exception {Bitmap bitmap=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File dir=new File(c.getExternalFilesDir(null),"qa");dir.mkdirs();try(OutputStream out=new FileOutputStream(new File(dir,name+".png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();}
}
