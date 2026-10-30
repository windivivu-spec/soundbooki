package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.graphics.Bitmap;
import android.os.*;
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
import java.util.*;
import java.util.concurrent.atomic.*;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class ShelfLayoutTest {
    Context c;BookStore store;JSONObject current;
    @Before public void setup() throws Exception {
        c=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(c.getFilesDir(),".qa/shelf-"+System.nanoTime());BookStore.fixtureRoot.mkdirs();store=new BookStore(c);
        String[] names={"Những trang bình yên","Đi chậm lại","Một khu vườn nhỏ","Ngày mới bắt đầu"};
        for(int i=0;i<names.length;i++){
            String text="Phần 1: Một khoảng riêng\n"+"Mỗi trang sách mở ra một thế giới mới để chúng ta lắng nghe và khám phá. ".repeat(4)+"\nPhần 2: Điều nhỏ bé\n"+"Chúng ta có thể bắt đầu ngày mới bằng một điều nhỏ bé và bình yên. ".repeat(5)+"\nPhần 3: Đi tiếp\nCâu chuyện vẫn tiếp tục với những trang sách mới.";
            JSONObject b=store.create(names[i],text,null).put("author","Tủ sách thử nghiệm").put("lastOpened",System.currentTimeMillis()-i*1000);BookChapters.set(b,PdfReflow.extractChapters(text));store.save(b);if(i==0)current=b;
        }
        c.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",current.getString("id")).commit();c.getSharedPreferences("settings",0).edit().putBoolean(WalkthroughDialog.PREF_SEEN,true).putString("cloudURL","").commit();
    }
    @After public void cleanup() throws Exception {c.startService(new Intent(c,PlaybackService.class).setAction("stop"));Thread.sleep(300);BookStore.fixtureRoot=null;}
    static View description(View root,String label){if(android.text.TextUtils.equals(label,root.getContentDescription()))return root;if(root instanceof ViewGroup){ViewGroup group=(ViewGroup)root;for(int i=0;i<group.getChildCount();i++){View result=description(group.getChildAt(i),label);if(result!=null)return result;}}return null;}
    static Object field(Object value,String name)throws Exception {Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}
    @Test public void homeLibraryDetailAndCreateNavigation() throws Exception {
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            Thread.sleep(1200);scenario.onActivity(a->{assertEquals(AppShell.HOME,a.appShell().selectedPage());for(String label:new String[]{"Trang chủ","Thư viện","Tạo sách","Đang nghe","Cài đặt"})assertNotNull(label,description(a.getWindow().getDecorView(),label));assertNull(description(a.getWindow().getDecorView(),"Nội dung sách, có thể chỉnh sửa"));});screenshot("shelf-home");
            scenario.onActivity(a->description(a.getWindow().getDecorView(),"Thư viện").performClick());Thread.sleep(500);screenshot("shelf-library");
            scenario.onActivity(a->{View tile=description(a.getWindow().getDecorView(),"Mở sách Những trang bình yên");assertNotNull(tile);tile.performClick();});Thread.sleep(500);scenario.onActivity(a->assertEquals(AppShell.DETAIL,a.appShell().selectedPage()));screenshot("shelf-detail");
            scenario.onActivity(a->description(a.getWindow().getDecorView(),"Về tủ sách").performClick());Thread.sleep(200);
            scenario.onActivity(a->description(a.getWindow().getDecorView(),"Tạo sách").performClick());Thread.sleep(300);scenario.onActivity(a->assertNotNull(description(a.getWindow().getDecorView(),"Nội dung sách, có thể chỉnh sửa")));screenshot("shelf-create");
            scenario.onActivity(a->description(a.getWindow().getDecorView(),"Cài đặt").performClick());Thread.sleep(150);screenshot("shelf-settings");scenario.onActivity(a->assertTrue(a.appShell().back()));scenario.onActivity(a->assertEquals(AppShell.HOME,a.appShell().selectedPage()));
        }
        assertEquals(current.optString("originalText"),store.load(current.getString("id")).getString("originalText"));
    }
    @Test public void proSamplesPlayOfflineAndStopOnBackground() throws Exception {
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(MainActivity::appProVoices);Thread.sleep(250);AtomicReference<VoicePreview.Card> card=new AtomicReference<>();
            scenario.onActivity(a->{try{Dialog dialog=(Dialog)field(a,"voiceDialog");assertTrue(dialog.isShowing());card.set((VoicePreview.Card)dialog.getWindow().getDecorView().findViewWithTag("pro-sample"));assertNotNull(card.get());}catch(Exception e){throw new RuntimeException(e);}});
            for(int i=0;i<7;i++){final int voice=i;scenario.onActivity(a->{try{Dialog dialog=(Dialog)field(a,"voiceDialog");ListView list=dialog.getWindow().getDecorView().findViewWithTag("pro-voice-list");list.performItemClick(null,voice+list.getHeaderViewsCount(),voice);card.get().play.performClick();}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(220);scenario.onActivity(a->assertTrue("Voice "+voice,card.get().isPlaying()));}
            screenshot("shelf-pro-voices");scenario.moveToState(androidx.lifecycle.Lifecycle.State.CREATED);Thread.sleep(200);scenario.onActivity(a->assertFalse(card.get().isPlaying()));scenario.moveToState(androidx.lifecycle.Lifecycle.State.RESUMED);
            assertEquals("No quote/trial created for local samples",0,store.load(current.getString("id")).getJSONArray("cloudOrders").length());
        }
    }
    @Test public void chapterTimelineSeekAndSleepTimer() throws Exception {
        BookChapters.Plan plan=new BookChapters.Plan(current);float[] tone=new float[96_000];for(int i=0;i<tone.length;i++)tone[i]=(float)(.02*Math.sin(i*.1));for(String part:plan.parts)AudioFiles.wav(store.audio(part,current.optString("voice")),tone);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{a.appPlay(1,true,true);a.appShell().select(AppShell.LISTENING);});
            long deadline=System.currentTimeMillis()+15000;while(System.currentTimeMillis()<deadline&&!PlaybackService.playing)Thread.sleep(20);assertTrue(PlaybackService.message,PlaybackService.playing);Thread.sleep(650);assertTrue(PlaybackService.chapterDurationComplete);assertEquals(plan.parts.size(),PlaybackService.total);assertEquals(plan.starts.get(1).intValue(),PlaybackService.current);assertTrue(PlaybackService.chapterDurationMs>=12000);screenshot("shelf-listening");
            scenario.onActivity(a->a.appCommand("pause",null,0));Thread.sleep(100);scenario.onActivity(a->a.appCommand("seek","chapterMillis",9500));Thread.sleep(350);assertTrue(PlaybackService.paused);assertTrue("Seek: "+PlaybackService.chapterPositionMs,Math.abs(PlaybackService.chapterPositionMs-9500)<800);assertTrue(PlaybackService.current>plan.starts.get(1));
            scenario.onActivity(a->a.appCommand("relative","deltaMs",-15000));Thread.sleep(250);assertEquals(plan.starts.get(1).intValue(),PlaybackService.current);assertTrue(PlaybackService.chapterPositionMs<500);
            scenario.onActivity(a->a.appCommand("relative","deltaMs",15000));Thread.sleep(350);assertTrue(PlaybackService.paused);assertTrue("Forward 15 seconds crosses cached segments",Math.abs(PlaybackService.chapterPositionMs-Math.min(15000,PlaybackService.chapterDurationMs-1))<800);
            scenario.onActivity(a->a.appCommand("relative","deltaMs",-15000));Thread.sleep(250);assertTrue(PlaybackService.chapterPositionMs<800);
            scenario.onActivity(a->a.appCommand("sleep","minutes",5));Thread.sleep(100);assertTrue(PlaybackService.sleepUntilElapsed>SystemClock.elapsedRealtime());scenario.onActivity(a->a.appCommand("pause",null,0));Thread.sleep(150);assertFalse(PlaybackService.paused);PlaybackService.sleepUntilElapsed=SystemClock.elapsedRealtime()-1;Thread.sleep(700);assertTrue(PlaybackService.paused);assertEquals(0,PlaybackService.sleepUntilElapsed);assertTrue(PlaybackService.message.contains("hẹn giờ"));
        }
    }
    private void screenshot(String name)throws Exception {Bitmap bitmap=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File dir=new File(c.getExternalFilesDir(null),"qa");dir.mkdirs();try(OutputStream out=new FileOutputStream(new File(dir,name+".png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();}
}
