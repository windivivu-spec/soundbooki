package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import androidx.core.graphics.ColorUtils;
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

/** Isolated reader state and native gestures. No network, audio generation or customer library. */
@RunWith(AndroidJUnit4.class)
public class ReaderFeaturesTest {
    Context context;BookStore store;final AtomicReference<ReaderDialog> dialog=new AtomicReference<>();
    static Object get(Object object,String name)throws Exception{Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}
    static Object call(Object object,String name,Class<?>[] types,Object... args)throws Exception{Method method=object.getClass().getDeclaredMethod(name,types);method.setAccessible(true);return method.invoke(object,args);}
    static void call(Object object,String name)throws Exception{call(object,name,new Class<?>[]{});}
    @Before public void setup(){context=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new File(context.getFilesDir(),".qa/reader-features");BookStore.fixtureRoot.mkdirs();store=new BookStore(context);context.getSharedPreferences("onboarding",0).edit().putBoolean("done",true).commit();}
    @After public void cleanup(){BookStore.fixtureRoot=null;}
    JSONObject fixture()throws Exception{JSONObject b=store.create("Những ngày đọc chậm",("Mỗi trang sách mở ra một khoảng trời. Giữ nguyên tiếng Việt, tên riêng và dấu câu. 🙂\n\n").repeat(900),null);context.getSharedPreferences(MainActivity.class.getName(),0).edit().putString("book",b.getString("id")).commit();return b;}
    void awaitPages(ActivityScenario<MainActivity> activity)throws Exception{for(int n=0;n<1200;n++){AtomicBoolean ready=new AtomicBoolean();activity.onActivity(a->{try{ready.set(dialog.get()!=null&&!((List<?>)get(dialog.get(),"pages")).isEmpty()&&!(boolean)get(dialog.get(),"paginationRunning"));}catch(Exception e){throw new RuntimeException(e);}});if(ready.get())return;Thread.sleep(25);}fail("Reader layout timeout");}
    void open(ActivityScenario<MainActivity> activity,JSONObject book){activity.onActivity(a->{ReaderDialog d=new ReaderDialog(a,new UiTheme(a),store,book,i->{});dialog.set(d);d.show();});}
    void screenshot(String name)throws Exception{InstrumentationRegistry.getInstrumentation().waitForIdleSync();Thread.sleep(260);File dir=new File(context.getExternalFilesDir(null),"qa");dir.mkdirs();String tag=InstrumentationRegistry.getArguments().getString("readerTag","default");Bitmap image=InstrumentationRegistry.getInstrumentation().getUiAutomation().takeScreenshot();try(OutputStream out=new FileOutputStream(new File(dir,"ebook-"+name+"-"+tag+".png"))){image.compress(Bitmap.CompressFormat.PNG,100,out);}image.recycle();}
    static View find(View view,String description){if(description.contentEquals(view.getContentDescription()==null?"":view.getContentDescription()))return view;if(view instanceof ViewGroup){ViewGroup g=(ViewGroup)view;for(int i=0;i<g.getChildCount();i++){View result=find(g.getChildAt(i),description);if(result!=null)return result;}}return null;}
    static void gesture(ReaderDialog d,int action,float fraction,long start,long time)throws Exception{TextView body=(TextView)get(d,"body");MotionEvent event=MotionEvent.obtain(start,time,action,body.getWidth()*fraction,body.getHeight()*.45f,0);body.dispatchTouchEvent(event);event.recycle();}

    @Test public void bookmarksMigratePersistAndStayBoundToTheSourceEdition()throws Exception{
        SharedPreferences prefs=context.getSharedPreferences(".qa-reader-model-"+System.nanoTime(),0);String id="qa-book",hash="source-one";
        prefs.edit().putInt("bookmark-offset-"+id+"-"+hash,45).commit();ReaderPreferences state=new ReaderPreferences(prefs,id,hash,30000);assertEquals(45,state.bookmarks().get(0).offset);
        ReaderPreferences.Mark a=state.add(1234),b=state.add(18000);state.add(1234);state.rename(a.id,"Chỗ cần đọc lại — tiếng Việt 🙂");state.background="sepia";state.fontSize=30;state.margin=28;state.motion="slide";state.lineSpacing=1.55f;state.brightness=45;state.save();
        ReaderPreferences reopened=new ReaderPreferences(prefs,id,hash,30000);assertEquals(3,reopened.bookmarks().size());assertEquals("Chỗ cần đọc lại — tiếng Việt 🙂",reopened.bookmarks().get(1).note);assertEquals("sepia",reopened.background);assertEquals(30,reopened.fontSize,.01);assertEquals(28,reopened.margin);assertEquals(45,reopened.brightness);
        ReaderPreferences edited=new ReaderPreferences(prefs,id,"source-two",30000);assertTrue(edited.bookmarks().isEmpty());assertEquals("sepia",edited.background);assertEquals(3,new ReaderPreferences(prefs,id,hash,30000).bookmarks().size());
        for(ReaderPreferences.Mark m:reopened.bookmarks())reopened.remove(m.id);assertTrue(new ReaderPreferences(prefs,id,hash,30000).bookmarks().isEmpty());assertEquals("system",new ReaderPreferences(prefs,"another",hash,30000).background);
        prefs.edit().clear().commit();
    }
    @Test public void palettesHaveReadableTextInEveryBackground(){for(String id:ReaderPreferences.THEME_IDS)for(boolean dark:new boolean[]{false,true}){ReaderPreferences.Palette p=ReaderPreferences.palette(id,dark);assertTrue(id+" primary",ColorUtils.calculateContrast(p.ink,p.paper)>=4.5);assertTrue(id+" secondary",ColorUtils.calculateContrast(p.muted,p.paper)>=4.5);assertTrue(id+" controls",ColorUtils.calculateContrast(p.ink,p.control)>=4.5);}}
    @Test public void canceledSwipeKeepsPositionCommittedSwipeSurvivesReflow()throws Exception{
        JSONObject b=fixture();try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            open(activity,b);awaitPages(activity);AtomicInteger startAnchor=new AtomicInteger();long start=SystemClock.uptimeMillis();
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();startAnchor.set((int)get(d,"anchor"));gesture(d,MotionEvent.ACTION_DOWN,.88f,start,start);gesture(d,MotionEvent.ACTION_MOVE,.38f,start,start+200);assertEquals(1,(int)get(d,"page"));assertTrue((boolean)get(d,"dragTurning"));assertEquals("System animation preference",!UiTheme.reducedMotion(),((ReaderPageTurnView)get(d,"turnLayer")).hasSnapshots());assertEquals(startAnchor.get(),context.getSharedPreferences("reader",0).getInt("offset-"+b.optString("id")+"-"+BookStore.hash(b.optString("text")),-1));}catch(Exception e){throw new RuntimeException(e);}});
            screenshot("fold");activity.onActivity(a->{try{gesture(dialog.get(),MotionEvent.ACTION_CANCEL,.38f,start,start+300);}catch(Exception e){throw new RuntimeException(e);}});Thread.sleep(400);
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();assertEquals(0,(int)get(d,"page"));assertEquals(startAnchor.get(),(int)get(d,"anchor"));assertFalse(((ReaderPageTurnView)get(d,"turnLayer")).hasSnapshots());long now=SystemClock.uptimeMillis();gesture(d,MotionEvent.ACTION_DOWN,.88f,now,now);gesture(d,MotionEvent.ACTION_MOVE,.30f,now,now+200);gesture(d,MotionEvent.ACTION_UP,.30f,now,now+300);assertEquals(1,(int)get(d,"page"));assertFalse((boolean)get(d,"dragTurning"));startAnchor.set((int)get(d,"anchor"));Field font=ReaderDialog.class.getDeclaredField("fontSize");font.setAccessible(true);font.setFloat(d,30);((TextView)get(d,"body")).setTextSize(30);call(d,"paginate");}catch(Exception e){throw new RuntimeException(e);}});awaitPages(activity);
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();assertEquals(startAnchor.get(),(int)get(d,"anchor"));call(d,"toggleBookmark");assertEquals(startAnchor.get(),((ReaderPreferences)get(d,"settings")).bookmarks().get(0).offset);d.dismiss();}catch(Exception e){throw new RuntimeException(e);}});
            open(activity,b);awaitPages(activity);activity.onActivity(a->{try{assertEquals(startAnchor.get(),(int)get(dialog.get(),"anchor"));assertTrue(((ImageButton)get(dialog.get(),"bookmarkButton")).isSelected());dialog.get().dismiss();}catch(Exception e){throw new RuntimeException(e);}});
        }
    }
    @Test public void appearanceControlsPersistWithoutTouchingSourceOrAudio()throws Exception{
        JSONObject b=fixture();String source=b.getString("text");AtomicInteger saved=new AtomicInteger();try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            open(activity,b);awaitPages(activity);
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();call(d,"showPage",new Class<?>[]{int.class,boolean.class},6,false);saved.set((int)get(d,"anchor"));call(d,"typography");List<Dialog> panels=(List<Dialog>)get(d,"panels");AlertDialog panel=(AlertDialog)panels.get(panels.size()-1);View root=panel.getWindow().getDecorView();assertNotNull(find(root,"Nền đọc Nâu dịu"));find(root,"Nền đọc Nâu dịu").performClick();((SeekBar)find(root,"Cỡ chữ")).setProgress(16);((SeekBar)find(root,"Lề trang")).setProgress(3);((SeekBar)find(root,"Giãn dòng")).setProgress(4);panel.getButton(AlertDialog.BUTTON_POSITIVE).performClick();}catch(Exception e){throw new RuntimeException(e);}});awaitPages(activity);screenshot("sepia");
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();ReaderPreferences state=(ReaderPreferences)get(d,"settings");assertEquals("sepia",state.background);assertEquals(30,state.fontSize,.01);assertEquals(28,state.margin);assertEquals(1.55f,state.lineSpacing,.01);assertEquals(saved.get(),(int)get(d,"anchor"));assertEquals(source,b.optString("text"));TextView body=(TextView)get(d,"body");body.measure(View.MeasureSpec.makeMeasureSpec(body.getWidth(),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(body.getHeight(),View.MeasureSpec.EXACTLY));body.layout(body.getLeft(),body.getTop(),body.getRight(),body.getBottom());android.text.Layout layout=body.getLayout();int last=layout.getLineCount()-1;while(last>0&&body.getText().subSequence(layout.getLineStart(last),layout.getLineEnd(last)).toString().trim().isEmpty())last--;assertTrue("Margin/spacing clipped text",layout.getLineBottom(last)<=body.getHeight());int before=(int)get(d,"layoutRevision");state.background="night";state.brightness=35;state.keepAwake=true;state.save();call(d,"applyAppearance");assertEquals(before,(int)get(d,"layoutRevision"));assertEquals(ReaderPreferences.palette("night",false).ink,((TextView)get(d,"body")).getCurrentTextColor());assertEquals(.35f,d.getWindow().getAttributes().screenBrightness,.001);assertTrue((d.getWindow().getAttributes().flags&WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)!=0);}catch(Exception e){throw new RuntimeException(e);}});screenshot("night");
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();call(d,"typography");}catch(Exception e){throw new RuntimeException(e);}});screenshot("settings");activity.onActivity(a->dialog.get().dismiss());open(activity,b);awaitPages(activity);
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();assertEquals("night",((ReaderPreferences)get(d,"settings")).background);assertEquals(saved.get(),(int)get(d,"anchor"));d.dismiss();}catch(Exception e){throw new RuntimeException(e);}});
        }
    }
    @Test public void activityRecreationRestoresReaderWithoutLeakingTheOldWindow()throws Exception{
        JSONObject b=fixture();AtomicInteger offset=new AtomicInteger();try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            open(activity,b);awaitPages(activity);activity.onActivity(a->{try{ReaderDialog d=dialog.get();call(d,"showPage",new Class<?>[]{int.class,boolean.class},8,false);offset.set((int)get(d,"anchor"));ReaderPreferences state=(ReaderPreferences)get(d,"settings");state.background="sage";state.save();call(d,"applyAppearance");}catch(Exception e){throw new RuntimeException(e);}});
            ReaderDialog old=dialog.get();activity.recreate();
            for(int i=0;i<100;i++){AtomicBoolean found=new AtomicBoolean();activity.onActivity(a->{try{ReaderDialog restored=(ReaderDialog)get(a,"readerDialog");if(restored!=null){dialog.set(restored);found.set(true);}}catch(Exception e){throw new RuntimeException(e);}});if(found.get())break;Thread.sleep(30);}
            awaitPages(activity);activity.onActivity(a->{try{ReaderDialog restored=dialog.get();assertNotSame(old,restored);assertFalse(old.isShowing());assertTrue(restored.isShowing());assertEquals(offset.get(),(int)get(restored,"anchor"));assertEquals("sage",((ReaderPreferences)get(restored,"settings")).background);restored.dismiss();}catch(Exception e){throw new RuntimeException(e);}});
        }
    }
    @Test public void disabledMotionAndRepeatedBookmarkPanelsReleaseSnapshotsAndViews()throws Exception{
        JSONObject b=fixture();try(ActivityScenario<MainActivity> activity=ActivityScenario.launch(MainActivity.class)){
            open(activity,b);awaitPages(activity);
            activity.onActivity(a->{try{ReaderDialog d=dialog.get();ReaderPreferences state=(ReaderPreferences)get(d,"settings");state.motion="none";int labelCount=((List<?>)get(d,"labels")).size();call(d,"turn",new Class<?>[]{int.class},1);assertFalse(((ReaderPageTurnView)get(d,"turnLayer")).hasSnapshots());call(d,"toggleBookmark");for(int i=0;i<10;i++){call(d,"bookmarks");List<Dialog> panels=(List<Dialog>)get(d,"panels");panels.get(panels.size()-1).dismiss();}assertEquals(labelCount,((List<?>)get(d,"labels")).size());assertEquals(1,state.bookmarks().size());call(d,"bookmarks");}catch(Exception e){throw new RuntimeException(e);}});screenshot("bookmarks");activity.onActivity(a->{try{ReaderDialog d=dialog.get();List<Dialog> panels=(List<Dialog>)get(d,"panels");View hint=find(panels.get(panels.size()-1).getWindow().getDecorView(),"Thao tác dấu trang");Rect visible=new Rect();assertTrue(hint.getGlobalVisibleRect(visible));assertEquals("Bookmark hint clipped",hint.getHeight(),visible.height());d.dismiss();}catch(Exception e){throw new RuntimeException(e);}});
        }
    }
}
