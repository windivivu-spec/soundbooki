package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.content.res.AssetFileDescriptor;
import android.graphics.*;
import android.media.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.function.IntConsumer;

/** Explicit, offline playback of the owner's seven local Pro voice demos. */
final class VoicePreview {
    static final class Card extends LinearLayout {
        final Activity host; final UiTheme theme; final MobileUi ui; final Handler handler=new Handler(Looper.getMainLooper());
        final TextView label,time,note; final ImageButton play; final Waveform waveform;
        private JSONArray catalog; private int selected=0; private MediaPlayer player; private boolean prepared=false;
        private AudioFocusRequest focus; private AudioManager manager; private long startedAt;
        private static final long PREVIEW_LIMIT_MS=60_000;
        Card(Activity host,UiTheme theme){super(host);this.host=host;this.theme=theme;ui=new MobileUi(host,theme);setOrientation(VERTICAL);setPadding(ui.dp(14),ui.dp(12),ui.dp(14),ui.dp(12));setBackground(theme.card(theme.blueWash,theme.edge,18));
            try(InputStream in=host.getAssets().open("voice-previews/pro.json")){catalog=new JSONArray(new String(in.readAllBytes(),StandardCharsets.UTF_8));}catch(Exception e){catalog=new JSONArray();}
            LinearLayout heading=ui.row();label=ui.text("Nghe thử giọng Pro",14,true);heading.addView(label,new LayoutParams(0,-2,1));time=ui.text("0:00 / 1:00",12,false);heading.addView(time);addView(heading);
            note=ui.text("Đoạn cắt từ audio gốc · tối đa 1 phút",11,false);LayoutParams noteLp=new LayoutParams(-1,-2);noteLp.topMargin=ui.dp(4);addView(note,noteLp);
            LinearLayout controls=ui.row();play=ui.icon("play","Phát mẫu giọng Pro",v->toggle());play.setBackground(theme.buttonBackground(true,24));play.setImageDrawable(theme.icon("play",Color.WHITE,22));controls.addView(play,new LayoutParams(ui.dp(48),ui.dp(48)));
            waveform=new Waveform(host,theme);LayoutParams waveLp=new LayoutParams(0,ui.dp(44),1);waveLp.leftMargin=ui.dp(14);controls.addView(waveform,waveLp);LayoutParams controlsLp=new LayoutParams(-1,-2);controlsLp.topMargin=ui.dp(10);addView(controls,controlsLp);select(0);
        }
        void select(int index){select(index,false);}
        void select(int index,boolean playNow){stop();selected=Math.max(0,Math.min(6,index));JSONObject sample=catalog.optJSONObject(selected);label.setText("Nghe thử · "+CloudClient.VOICES[selected].split(" · ")[0]);long duration=Math.min(PREVIEW_LIMIT_MS,sample==null?0:sample.optLong("durationMs",0));time.setText("0:00 / "+MobileUi.time(duration));note.setText("Đoạn cắt từ audio gốc · "+MobileUi.time(duration));waveform.values=sample==null?new JSONArray():sample.optJSONArray("waveform");waveform.progress=0;waveform.invalidate();play.setEnabled(sample!=null&&duration>0);if(playNow&&sample!=null&&duration>0)toggle();}
        private void toggle(){if(player!=null){stop();return;}JSONObject sample=catalog.optJSONObject(selected);if(sample==null)return;
            try{manager=(AudioManager)host.getSystemService(Context.AUDIO_SERVICE);focus=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT).setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()).setOnAudioFocusChangeListener(change->{if(change<0)stop();}).build();if(manager.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED)return;
                MediaPlayer p=new MediaPlayer();player=p;prepared=false;p.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build());try(AssetFileDescriptor fd=host.getAssets().openFd("voice-previews/"+sample.getString("file"))){p.setDataSource(fd.getFileDescriptor(),fd.getStartOffset(),fd.getLength());}
                p.setOnPreparedListener(m->{if(player!=m)return;prepared=true;startedAt=SystemClock.elapsedRealtime();m.setLooping(false);m.start();play.setImageDrawable(theme.icon("pause",Color.WHITE,22));play.setContentDescription("Dừng mẫu giọng Pro");handler.post(tick);});p.setOnCompletionListener(m->{if(player==m)stop();});p.setOnErrorListener((m,w,e)->{stop();Toast.makeText(host,"Chưa phát được mẫu giọng này.",Toast.LENGTH_SHORT).show();return true;});p.prepareAsync();
            }catch(Exception e){stop();Toast.makeText(host,"Chưa mở được mẫu giọng.",Toast.LENGTH_SHORT).show();}
        }
        boolean isPlaying(){return player!=null&&prepared;}
        private final Runnable tick=new Runnable(){public void run(){if(player==null||!prepared)return;try{long elapsed=SystemClock.elapsedRealtime()-startedAt;if(elapsed>=PREVIEW_LIMIT_MS){stop();return;}long at=Math.min(PREVIEW_LIMIT_MS,player.getCurrentPosition()),duration=Math.min(PREVIEW_LIMIT_MS,player.getDuration());time.setText(MobileUi.time(at)+" / "+MobileUi.time(duration));waveform.progress=duration>0?at/(float)duration:0;waveform.invalidate();handler.postDelayed(this,150);}catch(Exception ignored){stop();}}};
        void stop(){handler.removeCallbacksAndMessages(null);if(player!=null){try{player.release();}catch(Exception ignored){}player=null;}prepared=false;startedAt=0;if(manager!=null&&focus!=null)manager.abandonAudioFocusRequest(focus);focus=null;if(play!=null){play.setImageDrawable(theme.icon("play",Color.WHITE,22));play.setContentDescription("Phát mẫu giọng Pro");}waveform.progress=0;waveform.invalidate();JSONObject sample=catalog==null?null:catalog.optJSONObject(selected);long duration=Math.min(PREVIEW_LIMIT_MS,sample==null?0:sample.optLong("durationMs",0));time.setText("0:00 / "+MobileUi.time(duration));}
    }
    static final class Waveform extends View {
        JSONArray values=new JSONArray();float progress=0;final UiTheme theme;final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        Waveform(Context c,UiTheme t){super(c);theme=t;setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
        @Override protected void onDraw(Canvas c){int n=values==null?0:values.length();if(n==0)return;float gap=getWidth()/(float)n,w=Math.max(1,gap*.52f),middle=getHeight()/2f;for(int i=0;i<n;i++){float height=Math.max(theme.dp(2),(float)Math.sqrt(values.optDouble(i))*getHeight()*.85f);p.setColor(i/(float)n<progress?theme.accent:theme.dark?0xff637a9b:0xffa6bcd9);c.drawRoundRect(i*gap,middle-height/2,i*gap+w,middle+height/2,w/2,w/2,p);}}
    }
    static void stopDialog(Dialog dialog){if(dialog!=null&&dialog.getWindow()!=null){Object view=dialog.getWindow().getDecorView().getTag();if(view instanceof Card)((Card)view).stop();}}
    static Dialog show(Activity host,UiTheme theme,IntConsumer onChoose){
        MobileUi ui=new MobileUi(host,theme);Dialog dialog=new Dialog(host,android.R.style.Theme_DeviceDefault_NoActionBar);LinearLayout root=ui.column();root.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),ui.dp(16));root.setBackgroundColor(theme.canvas);root.setOnApplyWindowInsetsListener((v,insets)->{Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(safe.left+ui.dp(20),safe.top+ui.dp(12),safe.right+ui.dp(20),safe.bottom+ui.dp(16));return insets;});
        LinearLayout bar=ui.row();bar.addView(ui.heading("Giọng Pro",24),new LinearLayout.LayoutParams(0,-2,1));bar.addView(ui.icon("close","Đóng giọng Pro",v->dialog.dismiss()),new LinearLayout.LayoutParams(ui.dp(48),ui.dp(48)));root.addView(bar);
        LinearLayout intro=ui.column();ui.gap(intro,8);intro.addView(ui.text("Chọn một chất giọng, nghe mẫu rồi thử với cuốn sách của bạn.",14,false));ui.gap(intro,16);
        Card preview=new Card(host,theme);preview.setTag("pro-sample");intro.addView(preview);ui.gap(intro,16);
        ListView voices=new ListView(host);voices.setTag("pro-voice-list");voices.setDivider(null);if(host.getResources().getConfiguration().screenHeightDp<480)voices.addHeaderView(intro,null,false);else root.addView(intro);String[] labels=CloudClient.VOICES;final int[] chosen={0};ArrayAdapter<String> adapter=new ArrayAdapter<String>(host,0,labels){@Override public View getView(int position,View view,ViewGroup parent){LinearLayout row=new LinearLayout(host);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(ui.dp(14),ui.dp(8),ui.dp(12),ui.dp(8));row.setMinimumHeight(ui.dp(56));row.setBackground(theme.chipBackground(chosen[0]==position?theme.blueWash:theme.canvas,0,12));TextView name=ui.text(getItem(position),15,true);name.setTypeface(theme.bold);row.addView(name,new LinearLayout.LayoutParams(0,-2,1));ImageView marker=new ImageView(host);marker.setImageDrawable(theme.icon(chosen[0]==position?"check":"wave",chosen[0]==position?theme.accent:theme.quiet,20));row.addView(marker,new LinearLayout.LayoutParams(ui.dp(28),ui.dp(28)));return row;}};
        voices.setAdapter(adapter);voices.setChoiceMode(ListView.CHOICE_MODE_SINGLE);voices.setItemChecked(voices.getHeaderViewsCount(),true);voices.setOnItemClickListener((p,v,position,id)->{int index=position-voices.getHeaderViewsCount();if(index<0)return;chosen[0]=index;preview.select(index,true);adapter.notifyDataSetChanged();});root.addView(voices,new LinearLayout.LayoutParams(-1,0,1));
        Button use=ui.button("Thử với sách này",true,"book");use.setOnClickListener(v->{preview.stop();dialog.dismiss();onChoose.accept(chosen[0]);});root.addView(use,new LinearLayout.LayoutParams(-1,ui.dp(52)));dialog.setContentView(root);dialog.setOnDismissListener(d->{preview.stop();if(dialog.getWindow()!=null)dialog.getWindow().getDecorView().setTag(null);});dialog.show();dialog.getWindow().getDecorView().setTag(preview);dialog.getWindow().getDecorView().getWindowInsetsController().setSystemBarsAppearance(theme.dark?0:WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);dialog.getWindow().setLayout(-1,-1);dialog.getWindow().setStatusBarColor(theme.canvas);dialog.getWindow().setNavigationBarColor(theme.canvas);return dialog;
    }
}
