package studio.windi.soundbooki;

import android.content.*;
import android.app.*;
import android.graphics.Bitmap;
import android.view.*;
import android.view.inspector.WindowInspector;
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
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class ProProfileTest {
    Context context;BookStore store;JSONObject book;
    @Before public void setup() throws Exception {
        context=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(context.getFilesDir(),".qa/pro-profile-"+System.nanoTime());BookStore.fixtureRoot.mkdirs();store=new BookStore(context);
        String text="Chương 1\nKhông gửi đoạn đầu.\nChương 2\n"+"Tiếng Việt nguyên vẹn 😄. ".repeat(300)+"\nChương 3\nKhông gửi chương kế tiếp.";
        book=store.create("Hồ sơ QA",text,null);BookChapters.set(book,PdfReflow.extractChapters(text));store.save(book);
        context.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",book.getString("id")).commit();context.getSharedPreferences("settings",0).edit().putString("cloudURL","").putBoolean(WalkthroughDialog.PREF_SEEN,true).commit();
    }
    @After public void done(){BookStore.fixtureRoot=null;}
    @Test public void selectedChapterIsVerbatimBoundedAndWholeBookQuoteIsUnaffected() throws Exception {
        List<PdfReflow.ChapterItem> chapters=BookChapters.get(book);assertEquals(3,chapters.size());
        JSONObject sample=CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],true,1);String text=join(sample);String selected=chapters.get(1).text;
        assertEquals(5000,text.codePointCount(0,text.length()));assertEquals(selected.substring(0,selected.offsetByCodePoints(0,5000)),text);assertFalse(text.contains("Không gửi"));
        JSONObject old=new JSONObject(sample.toString());JSONArray prefix=new JSONArray();int left=4000;JSONArray pieces=old.getJSONArray("segments");for(int i=0;i<pieces.length()&&left>0;i++){JSONObject part=new JSONObject(pieces.getJSONObject(i).toString());String value=part.getString("text");int n=Math.min(left,value.codePointCount(0,value.length()));part.put("text",value.substring(0,value.offsetByCodePoints(0,n)));prefix.put(part);left-=n;}old.put("segments",prefix);
        assertTrue(CloudClient.sameTrialPrefix(old,sample));assertEquals(4000,join(old).codePointCount(0,join(old).length()));old.put("voice",CloudClient.VOICE_IDS[1]);assertFalse(CloudClient.sameTrialPrefix(old,sample));
        assertEquals(chapters.get(0).text,join(CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],true,0)));
        assertEquals(book.getString("text"),join(CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],false,1)));
        try{CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],true,99);fail("Stale chapter accepted");}catch(IOException expected){}
    }
    @Test public void profileAndChapterTrialAreVisibleWithoutSendingText() throws Exception {
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            Thread.sleep(500);scenario.onActivity(a->{a.appProfile();});Thread.sleep(200);screenshot("profile-dark");
            scenario.onActivity(a->{View name=global("Tên hồ sơ");assertNotNull(name);assertTrue(name instanceof EditText);((EditText)name).setText("Bạn đọc QA");View save=globalText("Lưu hồ sơ");assertNotNull(save);save.performClick();assertEquals("Bạn đọc QA",a.getSharedPreferences("profile",0).getString("name",""));globalText("Đóng").performClick();a.appCloudChapter(1);});Thread.sleep(250);
            scenario.onActivity(a->{try{Field f=MainActivity.class.getDeclaredField("cloudPanel");f.setAccessible(true);Object panel=f.get(a);Field chapter=panel.getClass().getDeclaredField("sampleChapter");chapter.setAccessible(true);assertEquals(1,chapter.getInt(panel));Field trial=panel.getClass().getDeclaredField("trial");trial.setAccessible(true);Button button=(Button)trial.get(panel);assertEquals("Tạo thử chương này · Pro",button.getText());assertFalse(button.isEnabled());Field units=panel.getClass().getDeclaredField("sampleUnits");units.setAccessible(true);assertEquals(1,units.getInt(panel));Field choice=panel.getClass().getDeclaredField("trialChoice");choice.setAccessible(true);RadioGroup radios=(RadioGroup)choice.get(panel);radios.check(radios.getChildAt(1).getId());assertEquals(2,units.getInt(panel));assertFalse(button.isEnabled());radios.check(radios.getChildAt(0).getId());assertEquals(1,units.getInt(panel));}catch(Exception e){throw new RuntimeException(e);}});screenshot("pro-chapter");
        }
        assertEquals(0,store.load(book.getString("id")).getJSONArray("cloudOrders").length());
    }
    @Test public void fiveLifetimeQuotaRetainsOldUsage() throws Exception {
        SharedPreferences cache=ProfileDialog.cache(context);cache.edit().clear().commit();assertEquals(5,ProfileDialog.remaining(context));
        for(int used=0;used<=10;used++){cache.edit().putInt("limit",10).putInt("remaining",10-used).commit();assertEquals(Math.max(0,5-used),ProfileDialog.remaining(context));}
        cache.edit().clear().commit();assertEquals(5,CloudClient.TRIAL_LIMIT);
    }
    @Test public void groupedChapterUsesAtMostFourUnitsAndNeverIncludesNextChapter() throws Exception {
        int[][] cases={{1,1},{5000,1},{5001,2},{10000,2},{10001,3},{15000,3},{15001,4},{20000,4},{24000,4}};
        for(int[] item:cases){
            String repeated="a😀".repeat(item[0]);String selected=repeated.substring(0,repeated.offsetByCodePoints(0,item[0]));String text=selected+"Không lấy chương sau.";
            JSONObject current=store.create("Gộp lượt QA",text,null);
            BookChapters.set(current,List.of(new PdfReflow.ChapterItem("one","Chương đã chọn",0,selected.length(),selected),new PdfReflow.ChapterItem("two","Chương sau",selected.length(),text.length(),text.substring(selected.length()))));
            int planned=CloudClient.chapterTrialUnits(current,0);assertEquals(item[1],planned);
            JSONObject sample=CloudClient.snapshot(current,CloudClient.VOICE_IDS[0],true,0,planned);String actual=join(sample);
            assertEquals(Math.min(item[0],20000),actual.codePointCount(0,actual.length()));
            assertEquals(selected.substring(0,selected.offsetByCodePoints(0,Math.min(item[0],20000))),actual);
            assertEquals(item[1],sample.optInt("trialUnits",1));assertEquals(item[1],CloudClient.trialUnits(sample));
            assertEquals(text,current.getString("originalText"));
            if(planned>1)assertFalse(CloudClient.sameTrialPrefix(CloudClient.snapshot(current,CloudClient.VOICE_IDS[0],true,0),sample));
        }
        try{CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],true,1,5);fail("Five units accepted");}catch(IOException expected){}
    }
    static String join(JSONObject snapshot)throws Exception{StringBuilder s=new StringBuilder();JSONArray parts=snapshot.getJSONArray("segments");for(int i=0;i<parts.length();i++)s.append(parts.getJSONObject(i).getString("text"));return s.toString();}
    static View global(String label){for(View root:WindowInspector.getGlobalWindowViews()){View v=description(root,label);if(v!=null)return v;}return null;}
    static View description(View root,String label){if(label.contentEquals(root.getContentDescription()==null?"":root.getContentDescription()))return root;if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){View v=description(((ViewGroup)root).getChildAt(i),label);if(v!=null)return v;}return null;}
    static View globalText(String label){for(View root:WindowInspector.getGlobalWindowViews()){View v=text(root,label);if(v!=null)return v;}return null;}
    static View text(View root,String label){if(root instanceof TextView&&label.contentEquals(((TextView)root).getText()))return root;if(root instanceof ViewGroup)for(int i=0;i<((ViewGroup)root).getChildCount();i++){View v=text(((ViewGroup)root).getChildAt(i),label);if(v!=null)return v;}return null;}
    void screenshot(String name)throws Exception{Bitmap bitmap=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();File folder=new File(context.getExternalFilesDir(null),"qa");folder.mkdirs();try(OutputStream out=new FileOutputStream(new File(folder,name+".png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();}
}
