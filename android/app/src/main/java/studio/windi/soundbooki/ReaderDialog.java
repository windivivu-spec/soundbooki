package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.content.res.ColorStateList;
import android.view.accessibility.AccessibilityManager;
import android.graphics.*;
import android.graphics.drawable.ColorDrawable;
import android.os.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.IntConsumer;

/** Screen-sized pages; only the current page is attached to the view tree. */
public final class ReaderDialog extends Dialog {
    private final Activity host;
    private final UiTheme theme;
    private final BookStore store;
    private final JSONObject book;
    private final IntConsumer onListen;
    private final String text;
    private final String textHash;
    private List<PdfReflow.ChapterItem> chapters=Collections.emptyList();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private LinearLayout root,top,bottom;
    private ReaderPreferences settings;
    private ReaderPreferences.Palette palette;
    private ReaderPageTurnView turnLayer;
    private ImageButton bookmarkButton;
    private Button bookmarkListButton;
    private final ArrayList<TextView> labels=new ArrayList<>(),buttons=new ArrayList<>();
    private final HashMap<ImageButton,String> icons=new HashMap<>();
    private final ArrayList<Dialog> panels=new ArrayList<>();
    private float downX,downY;
    private int dragDirection=0,dragStartPage,dragStartAnchor;
    private float dragProgress;
    private boolean dragTurning=false,moved=false,buildingChrome=true;
    private VelocityTracker velocity;
    private long lastTurnAnimation=0;
    private TextView body,chapterLabel,pageLabel,playerStatus;
    private FrameLayout paper;
    private Button previous,next,play;
    private SeekBar seek;
    private List<int[]> pages=new ArrayList<>();
    private final LinkedHashMap<String,List<int[]>> layoutCache=new LinkedHashMap<>(4,.75f,true);
    private int page=0,anchor=0,layoutRevision=0,lastWidth=0,lastHeight=0,initialOffset=-1;
    private int savedOffset=-1;
    private float fontSize=19;
    private boolean serif=true,chrome=true,closed=false,changingSeek=false,paginationRunning=false;
    private Future<?> pagination;
    private Runnable pendingLayout;

    public ReaderDialog(Activity host,UiTheme theme,BookStore store,JSONObject book,IntConsumer onListen){
        super(host,android.R.style.Theme_DeviceDefault_NoActionBar);this.host=host;this.theme=theme;this.store=store;this.book=book;this.onListen=onListen;
        text=book.optString("text");textHash=BookStore.hash(text);
    }
    Bundle readerSnapshot(){finishTurn();Bundle state=new Bundle();state.putString("book",book.optString("id"));state.putString("hash",textHash);state.putInt("offset",anchor);state.putBoolean("chrome",chrome);return state;}
    void restoreChrome(boolean visible){if(chrome!=visible)toggleChrome();}
    ReaderDialog startAt(int offset){initialOffset=Math.max(0,Math.min(text.length(),offset));return this;}
    @Override protected void onCreate(Bundle state){
        super.onCreate(state);if(host instanceof MainActivity)((MainActivity)host).readerOpened(this);requestWindowFeature(Window.FEATURE_NO_TITLE);
        prefs=host.getSharedPreferences("reader",Context.MODE_PRIVATE);settings=new ReaderPreferences(prefs,book.optString("id"),textHash,text.length());fontSize=settings.fontSize;serif=settings.serif;palette=ReaderPreferences.palette(settings.background,theme.dark);
        anchor=Math.max(0,Math.min(text.length(),initialOffset>=0?initialOffset:prefs.getInt(positionKey(),0)));
        root=new LinearLayout(host);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(theme.surface);
        root.setOnApplyWindowInsetsListener((v,insets)->{Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(safe.left,safe.top,safe.right,safe.bottom);return insets;});
        top=new LinearLayout(host);top.setOrientation(LinearLayout.VERTICAL);top.setPadding(theme.dp(12),theme.dp(4),theme.dp(12),theme.dp(8));top.setBackgroundColor(theme.glass);
        LinearLayout toolbar=row();
        toolbar.addView(icon("back","Đóng trang đọc",v->dismiss()),new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        TextView title=label(book.optString("title"),16,true);title.setMaxLines(host.getResources().getConfiguration().screenHeightDp<480||host.getResources().getConfiguration().fontScale>1.4f?1:2);title.setContentDescription(book.optString("title"));title.setEllipsize(TextUtils.TruncateAt.END);title.setPadding(theme.dp(8),0,theme.dp(8),0);toolbar.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        toolbar.addView(icon("book","Mục lục",v->contents()),new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        Button aa=button("Aa",false);aa.setContentDescription("Giao diện đọc: nền, chữ, lật trang và độ sáng");aa.setOnClickListener(v->typography());toolbar.addView(aa,new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        bookmarkButton=icon("bookmark","Đánh dấu trang này",v->toggleBookmark());bookmarkButton.setOnLongClickListener(v->{bookmarks();return true;});toolbar.addView(bookmarkButton,new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        toolbar.addView(icon("search","Tìm nội dung và sổ tay",v->readingMenu()),new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        top.addView(toolbar);chapterLabel=label("Đang chia trang…",12,false);chapterLabel.setPadding(theme.dp(12),theme.dp(4),theme.dp(12),0);chapterLabel.setMaxLines(1);chapterLabel.setEllipsize(TextUtils.TruncateAt.END);top.addView(chapterLabel);root.addView(top);
        paper=new FrameLayout(host);paper.setPadding(theme.dp(settings.margin),theme.dp(16),theme.dp(settings.margin),theme.dp(12));
        body=new TextView(host);body.setTextColor(theme.ink);body.setPadding(0,0,0,0);body.setGravity(Gravity.TOP|Gravity.START);body.setHorizontallyScrolling(false);body.setIncludeFontPadding(false);body.setFallbackLineSpacing(true);body.setTextSize(fontSize);body.setTypeface(serif?theme.serif:theme.regular);body.setLineSpacing(theme.dp(2),settings.lineSpacing);body.setBreakStrategy(Layout.BREAK_STRATEGY_SIMPLE);body.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE);body.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        body.setText("Đang chia trang theo màn hình…");paper.addView(body,new FrameLayout.LayoutParams(-1,-1));FrameLayout viewport=new FrameLayout(host);viewport.addView(paper,new FrameLayout.LayoutParams(-1,-1));turnLayer=new ReaderPageTurnView(host);viewport.addView(turnLayer,new FrameLayout.LayoutParams(-1,-1));root.addView(viewport,new LinearLayout.LayoutParams(-1,0,1));
        loadAnnotations();
        body.setCustomSelectionActionModeCallback(new ActionMode.Callback(){public boolean onCreateActionMode(ActionMode m,Menu menu){menu.add(0,9001,0,"Tô / Ghi chú");return true;}public boolean onPrepareActionMode(ActionMode m,Menu menu){return false;}public boolean onActionItemClicked(ActionMode m,MenuItem item){if(item.getItemId()==9001){selectionNote();m.finish();return true;}return false;}public void onDestroyActionMode(ActionMode m){}});
        body.setOnTouchListener((v,e)->touchPage(e));
        body.setOnClickListener(v->toggleChrome());
        body.setAccessibilityDelegate(new View.AccessibilityDelegate(){
            @Override public void onInitializeAccessibilityNodeInfo(View v,android.view.accessibility.AccessibilityNodeInfo info){super.onInitializeAccessibilityNodeInfo(v,info);info.addAction(android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_FORWARD);info.addAction(android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction.ACTION_SCROLL_BACKWARD);}
            @Override public boolean performAccessibilityAction(View v,int action,Bundle args){if(action==android.view.accessibility.AccessibilityNodeInfo.ACTION_SCROLL_FORWARD){turn(1);return true;}if(action==android.view.accessibility.AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD){turn(-1);return true;}return super.performAccessibilityAction(v,action,args);}
        });
        bottom=new LinearLayout(host);bottom.setOrientation(LinearLayout.VERTICAL);bottom.setPadding(theme.dp(16),theme.dp(8),theme.dp(16),theme.dp(8));bottom.setBackground(theme.card(theme.glass,theme.edge,20));
        LinearLayout navigation=row();previous=button("‹",false);previous.setContentDescription("Trang trước");previous.setOnClickListener(v->turn(-1));navigation.addView(previous,new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));
        pageLabel=label("Đang chia trang",12,true);pageLabel.setGravity(Gravity.CENTER);pageLabel.setContentDescription("Vị trí đọc");pageLabel.setOnClickListener(v->jump());pageLabel.setMinHeight(theme.dp(48));pageLabel.setMaxLines(2);pageLabel.setEllipsize(TextUtils.TruncateAt.END);navigation.addView(pageLabel,new LinearLayout.LayoutParams(0,-2,1));next=button("›",false);next.setContentDescription("Trang sau");next.setOnClickListener(v->turn(1));navigation.addView(next,new LinearLayout.LayoutParams(theme.dp(48),theme.dp(48)));bookmarkListButton=button("Dấu trang",false);bookmarkListButton.setContentDescription("Danh sách dấu trang");bookmarkListButton.setOnClickListener(v->bookmarks());LinearLayout.LayoutParams markLp=new LinearLayout.LayoutParams(-2,theme.dp(48));markLp.leftMargin=theme.dp(8);navigation.addView(bookmarkListButton,markLp);bottom.addView(navigation);
        seek=new SeekBar(host);seek.setContentDescription("Chuyển trang đọc");seek.setMinimumHeight(theme.dp(48));seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){changingSeek=true;}public void onStopTrackingTouch(SeekBar s){changingSeek=false;showPage(s.getProgress(),true);}public void onProgressChanged(SeekBar s,int p,boolean user){if(user)pageLabel.setText("Trang "+(p+1)+" / "+pages.size());}});bottom.addView(seek,new LinearLayout.LayoutParams(-1,theme.dp(40)));
        LinearLayout player=row();playerStatus=label("Sẵn sàng nghe chương",12,false);playerStatus.setMaxLines(2);player.addView(playerStatus,new LinearLayout.LayoutParams(0,-2,1));
        play=button("Nghe chương",true);play.setOnClickListener(v->{if(ownPlayback())host.startService(new Intent(host,PlaybackService.class).setAction("pause"));else onListen.accept(chapterAt(currentOffset()));});LinearLayout.LayoutParams playLp=new LinearLayout.LayoutParams(-2,theme.dp(48));playLp.leftMargin=theme.dp(8);player.addView(play,playLp);bottom.addView(player);root.addView(bottom);
        if(host.getResources().getConfiguration().screenHeightDp < 480){
            chapterLabel.setVisibility(View.GONE);seek.setVisibility(View.GONE);
        }
        setContentView(root);buildingChrome=false;applyAppearance();
        paper.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob)->updateMargins());
        body.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob)->{int width=body.getWidth(),height=body.getHeight();if(width>0&&height>0&&(width!=lastWidth||height!=lastHeight)){lastWidth=width;lastHeight=height;paginate();}});
        setOnDismissListener(d->{finishTurn();closed=true;remember();if(host instanceof MainActivity)((MainActivity)host).readerClosed(this);for(Dialog panel:new ArrayList<>(panels))panel.dismiss();panels.clear();layoutRevision++;if(pagination!=null)pagination.cancel(true);worker.shutdownNow();ui.removeCallbacksAndMessages(null);});ui.post(sync);
    }
    @Override public void show(){super.show();Window w=getWindow();if(w!=null){w.setLayout(-1,-1);applyAppearance();}}
    private LinearLayout row(){LinearLayout r=new LinearLayout(host);r.setGravity(Gravity.CENTER_VERTICAL);return r;}
    private TextView label(String value,float size,boolean bold){TextView t=new TextView(host);t.setText(value);t.setTextSize(size);t.setTextColor(bold?palette.ink:palette.muted);t.setTypeface(bold?theme.bold:theme.regular);t.setTag(bold);if(buildingChrome)labels.add(t);return t;}
    private Button button(String value,boolean primary){Button b=new Button(host);b.setText(value);b.setAllCaps(false);b.setTextSize(13);b.setTypeface(theme.bold);b.setTag(primary);b.setMinWidth(0);b.setPadding(theme.dp(8),0,theme.dp(8),0);b.setMinimumHeight(theme.dp(48));if(buildingChrome)buttons.add(b);styleButton(b,primary);return b;}
    private void styleButton(TextView b,boolean primary){b.setTextColor(primary?palette.paper:palette.accent);b.setBackground(theme.chipBackground(primary?palette.ink:palette.control,primary?0:palette.rule,12));}
    private ImageButton icon(String kind,String description,View.OnClickListener action){ImageButton b=new ImageButton(host);b.setImageDrawable(theme.icon(kind,palette.accent,22));b.setContentDescription(description);b.setBackground(theme.chipBackground(palette.control,0,12));b.setOnClickListener(action);icons.put(b,kind);return b;}
    private void updateMargins(){int side=Math.max(theme.dp(settings.margin),Math.max(0,(paper.getWidth()-theme.dp(720))/2));if(paper.getPaddingLeft()!=side)paper.setPadding(side,theme.dp(16),side,theme.dp(12));}
    private void applyAppearance(){
        if(settings==null||root==null)return;finishTurn();palette=ReaderPreferences.palette(settings.background,theme.dark);
        root.setBackgroundColor(palette.paper);paper.setBackgroundColor(palette.paper);body.setTextColor(palette.ink);top.setBackgroundColor(palette.control);bottom.setBackground(theme.card(palette.control,palette.rule,20));
        for(TextView t:labels)t.setTextColor(Boolean.TRUE.equals(t.getTag())?palette.ink:palette.muted);
        for(TextView b:buttons)styleButton(b,Boolean.TRUE.equals(b.getTag()));
        for(Map.Entry<ImageButton,String> item:icons.entrySet()){item.getKey().setImageDrawable(theme.icon(item.getValue(),palette.accent,22));item.getKey().setBackground(theme.chipBackground(palette.control,0,12));}
        seek.setProgressTintList(ColorStateList.valueOf(palette.accent));seek.setThumbTintList(ColorStateList.valueOf(palette.accent));
        Window w=getWindow();if(w!=null){w.setBackgroundDrawable(new ColorDrawable(palette.paper));w.setStatusBarColor(palette.control);w.setNavigationBarColor(palette.control);WindowInsetsController controller=w.getDecorView().getWindowInsetsController();if(controller!=null)controller.setSystemBarsAppearance(palette.dark?0:WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);WindowManager.LayoutParams a=w.getAttributes();a.screenBrightness=settings.brightness<0?WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE:Math.max(.05f,settings.brightness/100f);w.setAttributes(a);if(settings.keepAwake)w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);else w.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);}
        updateBookmark();
    }
    private boolean motionEnabled(){AccessibilityManager a=(AccessibilityManager)host.getSystemService(Context.ACCESSIBILITY_SERVICE);return !settings.motion.equals("none")&&!UiTheme.reducedMotion()&&(a==null||!a.isTouchExplorationEnabled());}
    private void finishTurn(){
        if(turnLayer!=null)turnLayer.clear();
        if(dragTurning){dragTurning=false;dragDirection=0;if(!pages.isEmpty()&&!paginationRunning)showPage(dragStartPage,false,dragStartAnchor);}
    }
    private boolean touchPage(MotionEvent e){
        switch(e.getActionMasked()){
            case MotionEvent.ACTION_DOWN -> {finishTurn();downX=e.getX();downY=e.getY();moved=false;dragDirection=0;if(velocity!=null)velocity.recycle();velocity=VelocityTracker.obtain();velocity.addMovement(e);return true;}
            case MotionEvent.ACTION_MOVE -> {
                if(velocity!=null)velocity.addMovement(e);float dx=e.getX()-downX,dy=e.getY()-downY;int slop=ViewConfiguration.get(host).getScaledTouchSlop();
                if(Math.abs(dx)>slop||Math.abs(dy)>slop)moved=true;
                if(!dragTurning&&Math.abs(dx)>slop&&Math.abs(dx)>Math.abs(dy)*1.25f&&!pages.isEmpty()&&!paginationRunning){
                    int direction=dx<0?1:-1,target=page+direction;
                    if(target>=0&&target<pages.size()){dragStartPage=page;dragStartAnchor=anchor;dragTurning=true;dragDirection=direction;Bitmap old=motionEnabled()?ReaderPageTurnView.snapshot(paper,palette.paper):null;showPage(target,false);if(old!=null)turnLayer.prepare(old,ReaderPageTurnView.snapshot(paper,palette.paper),direction,palette.paper,settings.motion);}
                }
                if(dragTurning){dragProgress=Math.max(0,Math.min(1,-dragDirection*dx/Math.max(1,body.getWidth())));turnLayer.progress(dragProgress);}
                return true;
            }
            case MotionEvent.ACTION_UP,MotionEvent.ACTION_CANCEL -> {
                float vx=0;if(velocity!=null){velocity.addMovement(e);velocity.computeCurrentVelocity(1000);vx=velocity.getXVelocity();velocity.recycle();velocity=null;}
                boolean cancel=e.getActionMasked()==MotionEvent.ACTION_CANCEL;
                if(dragTurning){boolean complete=!cancel&&(dragProgress>.24f||(-dragDirection*vx>600&&dragProgress>.04f));if(complete){dragTurning=false;dragDirection=0;remember();}Runnable end=()->{if(closed)return;if(!complete){dragTurning=false;dragDirection=0;showPage(dragStartPage,false,dragStartAnchor);}};if(motionEnabled()&&turnLayer.hasSnapshots())turnLayer.settle(complete,end);else{turnLayer.clear();end.run();}}
                else if(!cancel&&Math.abs(e.getX()-downX)>theme.dp(48)&&Math.abs(e.getX()-downX)>Math.abs(e.getY()-downY)){turn(e.getX()<downX?1:-1);}
                else if(!cancel&&!moved){if(e.getX()<body.getWidth()*.22f)turn(-1);else if(e.getX()>body.getWidth()*.78f)turn(1);else body.performClick();}
                return true;
            }
        }
        return true;
    }
    private void paginate(){
        if(closed||lastWidth<=0||lastHeight<=0)return;finishTurn();int revision=++layoutRevision,width=lastWidth,height=lastHeight,restore=currentOffset();TextPaint paint=new TextPaint(body.getPaint());
        anchor=restore;paginationRunning=true;
        if(pagination!=null)pagination.cancel(true);if(pendingLayout!=null)ui.removeCallbacks(pendingLayout);
        pageLabel.setText("Đang chia trang…");previous.setEnabled(false);next.setEnabled(false);seek.setEnabled(false);
        String key=width+":"+height+":"+Float.floatToIntBits(paint.getTextSize())+":"+serif+":"+Float.floatToIntBits(settings.lineSpacing);
        List<int[]> cached=layoutCache.get(key);
        if(cached!=null){completeLayout(cached,restore);return;}
        // Font changes and inset/size callbacks can arrive in the same frame.
        // Only submit the latest dimensions, with no stale page navigation.
        pendingLayout=()->{if(closed||revision!=layoutRevision)return;pagination=worker.submit(()->{
            List<PdfReflow.ChapterItem> sourceChapters=chapters.isEmpty()?BookChapters.get(book):chapters;
            List<int[]> result=ReaderPaginator.paginate(text,sourceChapters,paint,width,height,theme.dp(2),settings.lineSpacing);
            if(result==null||Thread.currentThread().isInterrupted())return;
            ui.post(()->{if(closed||revision!=layoutRevision)return;chapters=sourceChapters;layoutCache.put(key,result);while(layoutCache.size()>4)layoutCache.remove(layoutCache.keySet().iterator().next());completeLayout(result,restore);});
        });};
        ui.postDelayed(pendingLayout,40);
    }
    private void completeLayout(List<int[]> result,int restore){paginationRunning=false;pages=result;seek.setMax(Math.max(0,pages.size()-1));seek.setEnabled(!pages.isEmpty());showPage(pageFor(restore),false,restore);}
    private int pageFor(int offset){int lo=0,hi=pages.size();while(lo<hi){int mid=(lo+hi)>>>1;if(offset<pages.get(mid)[1])hi=mid;else lo=mid+1;}return Math.min(lo,Math.max(0,pages.size()-1));}
    private int chapterAt(int offset){int lo=0,hi=chapters.size();while(lo<hi){int mid=(lo+hi)>>>1;if(offset<chapters.get(mid).endChar)hi=mid;else lo=mid+1;}return Math.min(lo,Math.max(0,chapters.size()-1));}
    private int currentOffset(){return anchor;}
    private void showPage(int index,boolean animate){
        showPage(index,animate,-1);
    }
    private void showPage(int index,boolean animate,int restore){
        if(pages.isEmpty()||paginationRunning)return;boolean motion=animate&&motionEnabled()&&SystemClock.uptimeMillis()-lastTurnAnimation>=100;Bitmap old=motion?ReaderPageTurnView.snapshot(paper,palette.paper):null;if(old!=null)lastTurnAnimation=SystemClock.uptimeMillis();if(animate)finishTurn();int prior=page;page=Math.max(0,Math.min(pages.size()-1,index));int[] range=pages.get(page);anchor=restore>=0?Math.min(text.length(),restore):range[0];String visible=text.substring(range[0],range[1]);if(!TextUtils.equals(body.getText(),visible))body.setText(visible);paintAnnotations();
        chapterLabel.setText(chapters.get(chapterAt(anchor)).title);pageLabel.setText("Trang "+(page+1)+" / "+pages.size()+" · "+((page+1)*100/pages.size())+"%");if(!changingSeek)seek.setProgress(page);previous.setEnabled(page>0);next.setEnabled(page+1<pages.size());if(!dragTurning)remember();updateBookmark();
        if(old!=null){if(prior!=page&&turnLayer.prepare(old,ReaderPageTurnView.snapshot(paper,palette.paper),page>prior?1:-1,palette.paper,settings.motion))turnLayer.settle(true,()->{});else if(!old.isRecycled())old.recycle();}
    }
    private void turn(int delta){finishTurn();int target=Math.max(0,Math.min(pages.size()-1,page+delta));if(target!=page)showPage(target,true);}
    private String positionKey(){return "offset-"+book.optString("id")+"-"+textHash;}
    private String bookmarkKey(){return "bookmark-"+positionKey();}
    private void remember(){int offset=currentOffset();if(prefs!=null&&offset!=savedOffset){savedOffset=offset;prefs.edit().putInt(positionKey(),offset).apply();}}
    private void toggleChrome(){finishTurn();chrome=!chrome;anchor=currentOffset();top.setVisibility(chrome?View.VISIBLE:View.GONE);bottom.setVisibility(chrome?View.VISIBLE:View.GONE);}
    private void updateBookmark(){
        if(bookmarkButton==null||settings==null)return;ReaderPreferences.Mark mark=pages.isEmpty()?null:settings.inRange(pages.get(page)[0],pages.get(page)[1]);boolean saved=mark!=null;
        bookmarkButton.setImageDrawable(theme.icon(saved?"bookmark-filled":"bookmark",palette.accent,22));bookmarkButton.setSelected(saved);bookmarkButton.setStateDescription(saved?"Trang đã có dấu":"Trang chưa đánh dấu");bookmarkButton.setContentDescription(saved?"Bỏ dấu trang này. Nhấn giữ để xem danh sách":"Đánh dấu trang này. Nhấn giữ để xem danh sách");
        if(bookmarkListButton!=null)bookmarkListButton.setText("Dấu trang"+(settings.bookmarkCount()==0?"":" · "+settings.bookmarkCount()));
    }
    private void toggleBookmark(){if(paginationRunning||pages.isEmpty())return;finishTurn();ReaderPreferences.Mark mark=settings.inRange(pages.get(page)[0],pages.get(page)[1]);if(mark==null){settings.add(currentOffset());Toast.makeText(host,"Đã thêm dấu trang",Toast.LENGTH_SHORT).show();}else{settings.remove(mark.id);Toast.makeText(host,"Đã bỏ dấu trang",Toast.LENGTH_SHORT).show();}updateBookmark();}
    private AlertDialog readerAlert(AlertDialog.Builder builder){AlertDialog d=MobileUi.showAlert(host,theme,builder);panels.add(d);d.setOnDismissListener(dialog->panels.remove(d));d.getWindow().setBackgroundDrawable(theme.card(palette.control,palette.rule,22));colorPanel(d.getWindow().getDecorView());return d;}
    private void colorPanel(View view){if(view instanceof TextView){TextView t=(TextView)view;t.setTextColor(view instanceof Button?palette.accent:palette.ink);if(view instanceof EditText){t.setHintTextColor(palette.muted);t.setBackground(theme.card(palette.paper,palette.rule,12));}}if(view instanceof SeekBar){((SeekBar)view).setProgressTintList(ColorStateList.valueOf(palette.accent));((SeekBar)view).setThumbTintList(ColorStateList.valueOf(palette.accent));}if(view instanceof CompoundButton){((CompoundButton)view).setButtonTintList(ColorStateList.valueOf(palette.accent));}if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++)colorPanel(group.getChildAt(i));}}
    private void contents(){
        if(paginationRunning||chapters.isEmpty())return;finishTurn();String[] titles=new String[chapters.size()];for(int i=0;i<titles.length;i++)titles[i]=chapters.get(i).title;
        readerAlert(new AlertDialog.Builder(host).setTitle("Mục lục").setSingleChoiceItems(titles,chapterAt(anchor),(d,i)->{showPage(pageFor(chapters.get(i).startChar),false,chapters.get(i).startChar);d.dismiss();}).setNeutralButton("Dấu trang · "+settings.bookmarkCount(),(d,i)->bookmarks()).setNegativeButton("Đóng",null));
    }
    private String excerpt(int offset){int end=Math.min(text.length(),offset+110);if(end<text.length()&&Character.isLowSurrogate(text.charAt(end)))end--;return text.substring(offset,end).replaceAll("\\s+"," ").trim();}
    private void bookmarks(){
        if(paginationRunning||pages.isEmpty())return;finishTurn();List<ReaderPreferences.Mark> marks=settings.bookmarks();
        LinearLayout content=new LinearLayout(host){@Override protected void onMeasure(int w,int h){if(marks.isEmpty()){super.onMeasure(w,h);return;}int max=Math.min(theme.dp(Math.min(440,marks.size()*100+72)),host.getResources().getDisplayMetrics().heightPixels/2);int available=View.MeasureSpec.getMode(h)==View.MeasureSpec.UNSPECIFIED?max:Math.min(max,View.MeasureSpec.getSize(h));super.onMeasure(w,View.MeasureSpec.makeMeasureSpec(available,View.MeasureSpec.EXACTLY));}};content.setOrientation(LinearLayout.VERTICAL);content.setPadding(theme.dp(16),theme.dp(6),theme.dp(16),0);
        if(marks.isEmpty()){TextView empty=label("Chưa có dấu trang. Chạm biểu tượng đánh dấu để giữ lại đoạn muốn đọc tiếp.",15,false);empty.setPadding(theme.dp(8),theme.dp(16),theme.dp(8),theme.dp(20));content.addView(empty);}
        ListView list=new ListView(host);list.setDivider(new ColorDrawable(palette.rule));list.setDividerHeight(theme.dp(1));
        list.setAdapter(new BaseAdapter(){public int getCount(){return marks.size();}public Object getItem(int i){return marks.get(i);}public long getItemId(int i){return i;}public View getView(int i,View old,ViewGroup parent){ReaderPreferences.Mark mark=marks.get(i);LinearLayout row=new LinearLayout(host);row.setOrientation(LinearLayout.VERTICAL);row.setPadding(theme.dp(8),theme.dp(12),theme.dp(8),theme.dp(12));row.setMinimumHeight(theme.dp(72));TextView title=label((mark.note.isEmpty()?chapters.get(chapterAt(mark.offset)).title:mark.note),15,true);title.setMaxLines(2);title.setEllipsize(TextUtils.TruncateAt.END);row.addView(title);TextView preview=label("Trang "+(pageFor(mark.offset)+1)+" · "+excerpt(mark.offset),13,false);preview.setMaxLines(2);preview.setEllipsize(TextUtils.TruncateAt.END);row.addView(preview);return row;}});
        if(!marks.isEmpty())content.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        TextView hint=label("Chạm để đọc · Giữ để sửa ghi chú hoặc xóa",12,false);hint.setContentDescription("Thao tác dấu trang");hint.setPadding(theme.dp(8),theme.dp(8),theme.dp(8),theme.dp(12));if(!marks.isEmpty())content.addView(hint);
        AlertDialog dialog=readerAlert(new AlertDialog.Builder(host).setTitle("Dấu trang · "+marks.size()).setView(content).setPositiveButton("Đánh dấu trang này",(d,i)->{if(settings.inRange(pages.get(page)[0],pages.get(page)[1])==null)settings.add(anchor);updateBookmark();}).setNegativeButton("Đóng",null));
        list.setOnItemClickListener((p,v,i,id)->{ReaderPreferences.Mark mark=marks.get(i);dialog.dismiss();showPage(pageFor(mark.offset),false,mark.offset);});
        list.setOnItemLongClickListener((p,v,i,id)->{ReaderPreferences.Mark mark=marks.get(i);dialog.dismiss();EditText note=new EditText(host);note.setText(mark.note);note.setHint("Ghi chú ngắn cho dấu trang");note.setMaxLines(3);note.setFilters(new InputFilter[]{new InputFilter.LengthFilter(160)});note.setPadding(theme.dp(16),theme.dp(12),theme.dp(16),theme.dp(12));readerAlert(new AlertDialog.Builder(host).setTitle("Dấu trang · "+(pageFor(mark.offset)+1)).setView(note).setPositiveButton("Lưu ghi chú",(d,n)->{settings.rename(mark.id,note.getText().toString().trim());updateBookmark();bookmarks();}).setNeutralButton("Xóa dấu",(d,n)->{settings.remove(mark.id);updateBookmark();bookmarks();}).setNegativeButton("Đóng",null));return true;});
    }
    private void jump(){if(pages.isEmpty()||paginationRunning)return;finishTurn();EditText number=new EditText(host);number.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);number.setHint("1 – "+pages.size());readerAlert(new AlertDialog.Builder(host).setTitle("Đến trang đọc").setView(number).setPositiveButton("Mở",(d,i)->{try{showPage(Integer.parseInt(number.getText().toString())-1,false);}catch(NumberFormatException ignored){}}).setNegativeButton("Đóng",null));}
    private SeekBar settingSlider(LinearLayout column,String title,int max,int progress,java.util.function.IntFunction<String> describe){TextView label=label(title+" · "+describe.apply(progress),14,true);column.addView(label);SeekBar slider=new SeekBar(host);slider.setMax(max);slider.setProgress(progress);slider.setContentDescription(title);column.addView(slider,new LinearLayout.LayoutParams(-1,theme.dp(48)));slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}public void onProgressChanged(SeekBar s,int p,boolean user){label.setText(title+" · "+describe.apply(p));}});return slider;}
    private void typography(){
        finishTurn();LinearLayout options=new LinearLayout(host);options.setOrientation(LinearLayout.VERTICAL);options.setPadding(theme.dp(20),theme.dp(8),theme.dp(20),theme.dp(12));
        options.addView(label("Nền trang đọc",15,true));String[] selectedBackground={settings.background};ArrayList<Button> swatches=new ArrayList<>();
        for(int start=0;start<ReaderPreferences.THEME_IDS.length;start+=3){LinearLayout row=row();for(int i=start;i<Math.min(start+3,ReaderPreferences.THEME_IDS.length);i++){final String id=ReaderPreferences.THEME_IDS[i];ReaderPreferences.Palette colors=ReaderPreferences.palette(id,theme.dark);Button choice=new Button(host);choice.setText((id.equals(selectedBackground[0])?"✓ ":"")+ReaderPreferences.THEME_LABELS[i]);choice.setAllCaps(false);choice.setTextSize(12);choice.setTextColor(colors.ink);choice.setMinWidth(0);choice.setMinHeight(theme.dp(52));choice.setMaxLines(2);choice.setPadding(theme.dp(3),0,theme.dp(3),0);choice.setContentDescription("Nền đọc "+ReaderPreferences.THEME_LABELS[i]);choice.setTag(id);choice.setSelected(id.equals(selectedBackground[0]));choice.setBackground(theme.card(colors.paper,choice.isSelected()?palette.accent:colors.rule,12));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);lp.setMargins(theme.dp(3),theme.dp(4),theme.dp(3),theme.dp(4));row.addView(choice,lp);swatches.add(choice);choice.setOnClickListener(v->{selectedBackground[0]=id;for(Button b:swatches){ReaderPreferences.Palette c=ReaderPreferences.palette((String)b.getTag(),theme.dark);b.setSelected(b.getTag().equals(id));b.setText((b.isSelected()?"✓ ":"")+ReaderPreferences.THEME_LABELS[Arrays.asList(ReaderPreferences.THEME_IDS).indexOf(b.getTag().toString())]);b.setStateDescription(b.isSelected()?"Đã chọn":"Chưa chọn");b.setBackground(theme.card(c.paper,b.isSelected()?palette.accent:c.rule,12));} });}options.addView(row);}
        SeekBar size=settingSlider(options,"Cỡ chữ",20,(int)fontSize-14,p->Integer.toString(p+14));
        Switch face=new Switch(host);face.setText("Phông sách có chân");face.setChecked(serif);face.setMinHeight(theme.dp(48));options.addView(face);
        SeekBar spacing=settingSlider(options,"Giãn dòng",7,Math.round((settings.lineSpacing-1.15f)*10),p->String.format(java.util.Locale.forLanguageTag("vi"),"%.2f",1.15f+p*.1f));
        SeekBar margin=settingSlider(options,"Lề trang",6,(settings.margin-16)/4,p->(16+p*4)+" dp");
        options.addView(label("Chuyển trang",15,true));RadioGroup animation=new RadioGroup(host);for(int i=0;i<ReaderPreferences.MOTION_IDS.length;i++){RadioButton radio=new RadioButton(host);radio.setText(ReaderPreferences.MOTION_LABELS[i]);radio.setId(View.generateViewId());radio.setTag(ReaderPreferences.MOTION_IDS[i]);radio.setMinHeight(theme.dp(48));animation.addView(radio);if(settings.motion.equals(radio.getTag()))radio.setChecked(true);}options.addView(animation);
        Switch automatic=new Switch(host);automatic.setText("Độ sáng theo hệ thống");automatic.setChecked(settings.brightness<0);automatic.setMinHeight(theme.dp(48));options.addView(automatic);
        SeekBar brightness=settingSlider(options,"Độ sáng màn đọc",95,Math.max(0,(settings.brightness<0?60:settings.brightness)-5),p->(p+5)+"%");brightness.setEnabled(!automatic.isChecked());automatic.setOnCheckedChangeListener((b,checked)->brightness.setEnabled(!checked));
        Switch awake=new Switch(host);awake.setText("Giữ màn hình sáng khi đọc");awake.setChecked(settings.keepAwake);awake.setMinHeight(theme.dp(48));options.addView(awake);
        TextView tip=label("Lưu riêng cho sách này. Máy bật giảm chuyển động sẽ tự tắt hiệu ứng lật.",12,false);tip.setPadding(0,theme.dp(12),0,0);options.addView(tip);
        ScrollView scroll=new ScrollView(host){@Override protected void onMeasure(int w,int h){int max=Math.min(theme.dp(530),(int)(host.getResources().getDisplayMetrics().heightPixels*.65f));int available=View.MeasureSpec.getMode(h)==View.MeasureSpec.UNSPECIFIED?max:Math.min(max,View.MeasureSpec.getSize(h));super.onMeasure(w,View.MeasureSpec.makeMeasureSpec(available,View.MeasureSpec.AT_MOST));}};scroll.setFillViewport(false);scroll.addView(options);
        AlertDialog dialog=readerAlert(new AlertDialog.Builder(host).setTitle("Giao diện đọc").setView(scroll).setPositiveButton("Áp dụng",(d,i)->{
            anchor=currentOffset();boolean reflow=fontSize!=size.getProgress()+14||serif!=face.isChecked()||Math.abs(settings.lineSpacing-(1.15f+spacing.getProgress()*.1f))>.001||settings.margin!=16+margin.getProgress()*4;
            fontSize=size.getProgress()+14;serif=face.isChecked();settings.fontSize=fontSize;settings.serif=serif;settings.lineSpacing=1.15f+spacing.getProgress()*.1f;settings.margin=16+margin.getProgress()*4;settings.background=selectedBackground[0];View checked=animation.findViewById(animation.getCheckedRadioButtonId());settings.motion=checked==null?"curl":checked.getTag().toString();settings.brightness=automatic.isChecked()?-1:brightness.getProgress()+5;settings.keepAwake=awake.isChecked();settings.save();
            body.setTextSize(fontSize);body.setTypeface(serif?theme.serif:theme.regular);body.setLineSpacing(theme.dp(2),settings.lineSpacing);updateMargins();applyAppearance();if(reflow)paginate();
        }).setNegativeButton("Đóng",null));
        // Keep swatch foregrounds tied to their own paper, independent of dialog theme.
        for(Button b:swatches)b.setTextColor(ReaderPreferences.palette((String)b.getTag(),theme.dark).ink);
    }
    private boolean selecting=false;
    private JSONArray annotations=new JSONArray();
    private void readingMenu(){MobileUi.options(host,theme,"Đọc và ghi nhớ",new String[]{"Tìm trong nội dung","Sổ tay của cuốn sách",selecting?"Kết thúc chọn chữ":"Chọn chữ để tô / ghi chú"},i->{if(i==0)searchContent();else if(i==1)notebook();else{selecting=!selecting;finishTurn();body.setTextIsSelectable(selecting);body.setOnTouchListener(selecting?null:(v,e)->touchPage(e));body.setOnClickListener(selecting?null:v->toggleChrome());if(selecting)Toast.makeText(host,"Nhấn giữ đoạn chữ, chọn Tô / Ghi chú. Dùng nút mũi tên để chuyển trang.",Toast.LENGTH_LONG).show();}});}
    private void loadAnnotations(){try{annotations=ReadingTools.notes(store,book.optString("id"));}catch(Exception e){annotations=new JSONArray();}}
    private void paintAnnotations(){if(pages.isEmpty()||paginationRunning)return;int[] pageRange=pages.get(page);SpannableString marked=new SpannableString(text.substring(pageRange[0],pageRange[1]));for(int i=0;i<annotations.length();i++){JSONObject n=annotations.optJSONObject(i);if(n==null||!textHash.equals(n.optString("edition")))continue;int a=Math.max(pageRange[0],n.optInt("start")),b=Math.min(pageRange[1],n.optInt("end"));if(a<b){marked.setSpan(new android.text.style.BackgroundColorSpan(ReadingTools.color(n.optString("color"))),a-pageRange[0],b-pageRange[0],Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);marked.setSpan(new android.text.style.ForegroundColorSpan(0xff20252d),a-pageRange[0],b-pageRange[0],Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);}}body.setText(marked,TextView.BufferType.SPANNABLE);}
    private void selectionNote(){if(pages.isEmpty())return;int a=Math.min(body.getSelectionStart(),body.getSelectionEnd()),b=Math.max(body.getSelectionStart(),body.getSelectionEnd());if(a<0||a==b){Toast.makeText(host,"Chọn chữ trước khi thêm ghi chú.",Toast.LENGTH_SHORT).show();return;}int base=pages.get(page)[0];editAnnotation(null,base+a,base+b);}
    private void editAnnotation(JSONObject entry,int a,int b){
        if(entry!=null&&!textHash.equals(entry.optString("edition"))){Toast.makeText(host,"Ghi chú thuộc bản chữ trước. Bản đã lưu vẫn được giữ.",Toast.LENGTH_LONG).show();return;}
        LinearLayout content=new LinearLayout(host);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(theme.dp(16),theme.dp(8),theme.dp(16),theme.dp(8));TextView quote=label(text.substring(a,b),14,false);quote.setMaxLines(4);content.addView(quote);EditText input=new EditText(host);input.setHint("Ghi chú của bạn");input.setContentDescription("Ghi chú của bạn");input.setText(entry==null?"":entry.optString("note"));input.setMinLines(2);input.setMaxLines(6);input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(10000)});content.addView(input);Spinner color=new Spinner(host);String[] ids={"yellow","green","blue","pink"};color.setAdapter(new ArrayAdapter<String>(host,android.R.layout.simple_spinner_dropdown_item,new String[]{"Vàng","Xanh lá","Xanh dương","Hồng"}));color.setContentDescription("Màu tô đoạn");color.setSelection(entry==null?0:Math.max(0,Arrays.asList(ids).indexOf(entry.optString("color"))));content.addView(color);
        AlertDialog.Builder builder=new AlertDialog.Builder(host).setTitle("Tô đoạn và ghi chú").setView(content).setPositiveButton("Lưu",(d,i)->{try{ReadingTools.save(store,book,a,b,input.getText().toString(),ids[color.getSelectedItemPosition()],entry==null?null:entry.optString("id"));loadAnnotations();paintAnnotations();}catch(Exception e){Toast.makeText(host,e.getMessage(),Toast.LENGTH_LONG).show();}}).setNegativeButton("Đóng",null);
        if(entry!=null)builder.setNeutralButton("Xóa",(d,i)->{try{ReadingTools.remove(store,book.optString("id"),entry.optString("id"));loadAnnotations();paintAnnotations();}catch(Exception e){Toast.makeText(host,e.getMessage(),Toast.LENGTH_LONG).show();}});readerAlert(builder);
    }
    private void notebook(){loadAnnotations();String[] rows=new String[annotations.length()];for(int i=0;i<rows.length;i++){JSONObject n=annotations.optJSONObject(i);rows[i]=(textHash.equals(n.optString("edition"))?"":"[Bản chữ trước] ")+n.optString("quote")+"\n"+n.optString("note");}if(rows.length==0){readerAlert(new AlertDialog.Builder(host).setTitle("Sổ tay").setMessage("Chưa có ghi chú. Mở Chọn chữ, nhấn giữ đoạn rồi chọn Tô / Ghi chú.").setPositiveButton("Đóng",null));return;}readerAlert(new AlertDialog.Builder(host).setTitle("Sổ tay · "+rows.length).setItems(rows,(d,i)->{JSONObject n=annotations.optJSONObject(i);if(textHash.equals(n.optString("edition")))showPage(pageFor(n.optInt("start")),false,n.optInt("start"));editAnnotation(n,n.optInt("start"),n.optInt("end"));}).setNegativeButton("Đóng",null));}
    private void searchContent(){
        LinearLayout content=new LinearLayout(host);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(theme.dp(16),0,theme.dp(16),0);EditText query=new EditText(host);query.setSingleLine();query.setHint("Tìm có dấu hoặc không dấu");query.setContentDescription("Tìm trong nội dung sách");content.addView(query);ListView list=new ListView(host);content.addView(list,new LinearLayout.LayoutParams(-1,theme.dp(260)));TextView state=label("Nhập chữ để tìm trong sách",13,false);content.addView(state);ArrayList<int[]> hits=new ArrayList<>();ArrayList<String> rows=new ArrayList<>();ArrayAdapter<String> adapter=new ArrayAdapter<>(host,android.R.layout.simple_list_item_1,rows);list.setAdapter(adapter);final int[] revision={0};
        AlertDialog panel=readerAlert(new AlertDialog.Builder(host).setTitle("Tìm nội dung").setView(content).setNegativeButton("Đóng",null));list.setOnItemClickListener((p,v,i,id)->{int at=hits.get(i)[0];panel.dismiss();showPage(pageFor(at),false,at);});query.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int c,int after){}public void afterTextChanged(Editable e){}public void onTextChanged(CharSequence s,int a,int before,int count){int token=++revision[0];String needle=s.toString();ui.postDelayed(()->{if(token!=revision[0]||closed)return;worker.submit(()->{List<int[]> found=ReadingTools.search(text,needle);ArrayList<String> preview=new ArrayList<>();for(int[] hit:found){int lo=Math.max(0,hit[0]-35),hi=Math.min(text.length(),hit[1]+90);if(lo>0&&Character.isLowSurrogate(text.charAt(lo)))lo--;if(hi<text.length()&&Character.isLowSurrogate(text.charAt(hi)))hi++;preview.add(text.substring(lo,hi).replaceAll("\\s+"," "));}ui.post(()->{if(token!=revision[0]||closed)return;hits.clear();hits.addAll(found);rows.clear();rows.addAll(preview);adapter.notifyDataSetChanged();state.setText(found.size()+" kết quả"+(found.size()==200?" đầu tiên":""));});});},220);}});query.requestFocus();
    }

    private boolean ownPlayback(){return PlaybackService.running&&book.optString("id").equals(PlaybackService.bookId);}
    private final Runnable sync=new Runnable(){public void run(){if(closed)return;boolean active=ownPlayback();String action=active?(PlaybackService.paused?"Nghe tiếp":"Tạm dừng"):"Nghe chương",status=active?PlaybackService.message:"Sẵn sàng nghe chương";if(!TextUtils.equals(play.getText(),action))play.setText(action);if(!TextUtils.equals(playerStatus.getText(),status))playerStatus.setText(status);ui.postDelayed(this,500);}};
    @Override public boolean onKeyDown(int code,KeyEvent e){if(code==KeyEvent.KEYCODE_DPAD_RIGHT||code==KeyEvent.KEYCODE_PAGE_DOWN){turn(1);return true;}if(code==KeyEvent.KEYCODE_DPAD_LEFT||code==KeyEvent.KEYCODE_PAGE_UP){turn(-1);return true;}return super.onKeyDown(code,e);}
}
