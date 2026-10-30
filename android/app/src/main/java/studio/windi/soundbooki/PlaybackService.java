package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.media.*;
import android.media.session.*;
import android.os.*;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** One foreground player and one bounded producer. Completed WAVs survive stop. */
public final class PlaybackService extends Service {
    public static volatile String bookId="",message="Sẵn sàng để nghe",metrics="";
    public static volatile boolean running=false,paused=false,playing=false,generating=false,generationPaused=false,generationPending=false;
    public static volatile int current=0,total=0,ready=0,chapterPercent=0;
    public static volatile String chapterTitle="",playbackText="",activeVoice="";
    public static volatile int chapterPositionMs=0,chapterDurationMs=0;
    public static volatile boolean chapterDurationComplete=false,sourceTextMatches=true;
    public static volatile int currentCharOffset=0;
    public static volatile long sleepUntilElapsed=0;
    private final Map<File,Integer> durationCache=new HashMap<>();
    private List<String> cloudTexts=List.of();
    private long lastPersistElapsed=0;
    private BookChapters.Plan plan;
    private int bufferedChapter=-1,bufferFrom=0,playEnd=0;
    private boolean libraryPlayback=false;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private Future<?> job;private volatile long epoch=0;
    private final Object generationGate=new Object();
    private volatile GenerationProgress progress;
    private int foregroundTypes=-1;private boolean foregroundAttached=false;
    private String lastNotification="";
    private NanoEngine engine;private int engineThreads=0;
    private EnglishSpeech englishSpeech;
    private MediaPlayer player, bgmPlayer;private MediaSession media;private AudioManager audioManager;private AudioFocusRequest focus;
    private PowerManager.WakeLock wake;private BookStore store;
    private ArrayList<File> queue=new ArrayList<>();private String signature="",activeId="",title="",orderId="",currentBgmTrack="none";
    private int index=0,resumeMs=0;private boolean producerDone=false,cloud=false;private long requested=0;private boolean firstPlayed=false;
    private float speed=1f,bgmVolume=0.18f;
    @Override public void onCreate(){
        super.onCreate();store=new BookStore(this);audioManager=(AudioManager)getSystemService(AUDIO_SERVICE);
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);nm.createNotificationChannel(new NotificationChannel("listening","Nghe sách",NotificationManager.IMPORTANCE_LOW));
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"soundbooki:narration");wake.setReferenceCounted(false);
        focus=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN).setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()).setOnAudioFocusChangeListener(change->{if(change==AudioManager.AUDIOFOCUS_LOSS||change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT||change==AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK)pause();}).build();
        media=new MediaSession(this,"Soundbooki");media.setCallback(new MediaSession.Callback(){@Override public void onPlay(){resume();}@Override public void onPause(){pause();}@Override public void onStop(){stopPlayback();}@Override public void onSkipToNext(){next();}});media.setActive(true);
        handler.post(tick);
    }
    @Override public IBinder onBind(Intent i){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null)return START_NOT_STICKY;String action=intent.getAction();
        if("stop".equals(action)){stopPlayback();return START_NOT_STICKY;}
        if("generation-pause".equals(action)){changeGeneration(true);return START_NOT_STICKY;}
        if("generation-resume".equals(action)){changeGeneration(false);return START_NOT_STICKY;}
        if("pause".equals(action)){if(paused)resume();else pause();return START_NOT_STICKY;}
        if("next".equals(action)){next();return START_NOT_STICKY;}
        if("seek".equals(action)){seekChapter(intent.getIntExtra("chapterMillis",0));return START_NOT_STICKY;}
        if("relative".equals(action)){publishPosition();seekChapter(chapterPositionMs+intent.getIntExtra("deltaMs",0));return START_NOT_STICKY;}
        if("sleep".equals(action)){int minutes=intent.getIntExtra("minutes",0);sleepUntilElapsed=minutes>0?SystemClock.elapsedRealtime()+Math.min(120,minutes)*60_000L:0;return START_NOT_STICKY;}
        if("music".equals(action)){syncBgm(playing&&!paused);return START_NOT_STICKY;}
        if("speed".equals(action)){speed=Math.max(.7f,Math.min(2f,intent.getFloatExtra("speed",1f)));if(player!=null)try{player.setPlaybackParams(player.getPlaybackParams().setSpeed(speed));if(paused)player.pause();}catch(Exception ignored){}return START_NOT_STICKY;}
        stopWork();epoch++;long token=epoch;
        activeId=intent.getStringExtra("book");bookId=activeId;plan=null;bufferedChapter=-1;chapterPercent=0;chapterTitle="";playbackText="";activeVoice="";chapterPositionMs=chapterDurationMs=0;chapterDurationComplete=false;durationCache.clear();queue=new ArrayList<>();cloudTexts=List.of();sourceTextMatches=true;currentCharOffset=0;libraryPlayback="take".equals(action);cloud="cloud".equals(action);orderId=intent.getStringExtra("order");
        speed=getSharedPreferences("settings",MODE_PRIVATE).getFloat("speed",1f);paused=intent.getBooleanExtra("pausePlayback",false);playing=false;running=true;producerDone=false;firstPlayed=false;requested=System.nanoTime();metrics="";ready=0;total=0;message="Đang chuẩn bị giọng đọc…";
        generating=!cloud&&!libraryPlayback;generationPending=generating;
        foregroundAttached=true;updateForeground();keepAwake();
        job=worker.submit(()->{
            try{
                if(englishSpeech!=null){englishSpeech.close();englishSpeech=null;}
                JSONObject book=store.load(activeId);String localId=book.getString("id"),sig=BookStore.contentSignature(book);String localTitle=book.getString("title");
                activeVoice=book.optString("voice");
                if(cloud){prepareCloud(book,token,localTitle);return;}
                if(libraryPlayback){
                    ChapterAudio library=new ChapterAudio(store,localId);JSONObject take=null;
                    for(JSONObject t:library.list())if(t.optString("id").equals(intent.getStringExtra("take")))take=t;
                    if(take==null)throw new IOException("Chưa có bản chương hoàn tất.");
                    File file=library.file(take);if(!AudioFiles.valid(file))throw new IOException("Audio chương chưa hoàn tất.");
                    String label=take.optString("title");activeVoice=take.optString("voice");
                    int a=take.optInt("startChar",-1),b=take.optInt("endChar",-1);String currentText=book.optString("text");
                    if(a>=0&&b>a&&b<=currentText.length()&&BookStore.hash(currentText.substring(a,b)).equals(take.optString("textHash"))){playbackText=currentText.substring(a,b);currentCharOffset=a;}
                    else {playbackText="Bản chương đã lưu · "+activeVoice;sourceTextMatches=false;}
                    handler.post(()->{if(token!=epoch)return;queue=new ArrayList<>(List.of(file));title=localTitle;chapterTitle=label;signature="";total=ready=1;index=current=0;resumeMs=0;producerDone=true;chapterPercent=100;tryPlay();});return;
                }
                BookChapters.Plan localPlan=new BookChapters.Plan(book);List<String> parts=localPlan.parts;
                if(parts.isEmpty())throw new IOException("Thêm nội dung trước khi nghe.");
                int selected=intent.getIntExtra("chapter",-1);
                boolean selectedOnly=selected>=0&&selected<localPlan.chapters.size();
                int position=Math.min(Math.max(0,book.optInt("position")),parts.size()-1);
                if(book.has("positionChar")) position=localPlan.partAtOffset(book.optInt("positionChar"));
                else { List<String> oldParts=BookStore.spokenParts(book.optString("text"));int charAt=0;for(int p=0;p<Math.min(book.optInt("position"),oldParts.size());p++)charAt+=oldParts.get(p).length();position=localPlan.partAtOffset(charAt); }
                int from=intent.getBooleanExtra("beginning",false)?0:position;
                boolean resumeGeneration=intent.getBooleanExtra("resumeGeneration",false);
                if(selectedOnly && (intent.getBooleanExtra("beginning",false)||(!resumeGeneration&&localPlan.chapterAt(position)!=selected)||position<localPlan.starts.get(selected)))from=localPlan.starts.get(selected);
                int end=selectedOnly&&!intent.getBooleanExtra("continuous",false)?localPlan.ends.get(selected):parts.size();
                if(from>=end)from=selectedOnly?localPlan.starts.get(selected):0;
                int seek=from==position&&!intent.getBooleanExtra("beginning",false)?book.optInt("positionMs"):0;
                int first=from,finish=end;
                if(token!=epoch)return;
                GenerationProgress checkpoint=new GenerationProgress(store,book,selectedOnly?selected:-1,intent.getBooleanExtra("continuous",false),paused);
                progress=checkpoint;
                if(token!=epoch)return;
                if(generationPaused)checkpoint.state("pausing");
                handler.post(()->{if(token!=epoch)return;plan=localPlan;signature=sig;title=localTitle;total=finish;playEnd=finish;index=first;current=index;bufferFrom=first;resumeMs=seek;queue=new ArrayList<>(Collections.nCopies(finish,null));});
                int threads=getSharedPreferences("settings",MODE_PRIVATE).getInt("threads",2);
                for(int c=localPlan.chapterAt(first);c<localPlan.chapters.size()&&localPlan.starts.get(c)<finish;c++) {
                    while(c>localPlan.chapterAt(current)&&token==epoch){if((paused||generationPaused)&&engine!=null){engine.close();engine=null;engineThreads=0;}Thread.sleep(150);}
                    if(token!=epoch||Thread.currentThread().isInterrupted())return;
                    handler.post(()->{if(token!=epoch)return;generating=true;keepAwake();notifyPlayer();});
                    int start=localPlan.starts.get(c),endPart=localPlan.ends.get(c);List<File> chapterFiles=new ArrayList<>();
                    // Prepare the audible suffix first on resume; fill an uncached prefix before archiving.
                    List<Integer> sequence=new ArrayList<>();int audible=Math.max(start,first);
                    for(int i=audible;i<endPart;i++)sequence.add(i);for(int i=start;i<audible;i++)sequence.add(i);
                    int chapterChars=localPlan.chapters.get(c).text.length(),doneChars=0;
                    for(int i:sequence){
                        awaitGeneration(token,checkpoint);
                        if(token!=epoch||Thread.currentThread().isInterrupted())return;
                        if(!BookStore.contentSignature(store.load(localId)).equals(sig))throw new IOException("Nội dung hoặc giọng đã đổi. Bấm Nghe để đọc bản mới.");
                        String part=parts.get(i),voice=book.getString("voice");File file=store.audio(part,book);long started=System.nanoTime();
                        boolean cached=AudioFiles.valid(file);
                        if(!cached && part.trim().isEmpty()) { AudioFiles.wav(file,new float[2400]); cached=true; }
                        final boolean wasCached=cached;
                        if(!wasCached){
                            if(engine==null||engineThreads!=threads){if(engine!=null)engine.close();File models=ModelAssets.prepare(this,t->update(token,t));engine=new NanoEngine(models,threads);engineThreads=threads;}
                            update(token,"Đang tạo · "+localPlan.chapters.get(c).title);
                            float[] audio;
                            if(book.optBoolean("bilingual")&&Bilingual.english(part)){
                                if(englishSpeech==null){englishSpeech=new EnglishSpeech(this);englishSpeech.select(book.optString("englishVoice"));if(!englishSpeech.revision().equals(book.optString("englishRevision")))throw new IOException("Giọng Anh hệ thống đã cập nhật. Bật lại Việt–Anh để dùng bản mới.");}
                                audio=englishSpeech.synthesize(part,file,()->token!=epoch);
                            }else audio=engine.synthesize(part,voice,()->token!=epoch);if(token!=epoch)return;AudioFiles.wav(file,audio);
                        }
                        doneChars+=part.length();
                        checkpoint.part(i,chapterChars==0?100:doneChars*100/chapterChars,localPlan.chapters.get(c).title,!wasCached);
                        double elapsed=(System.nanoTime()-started)/1e9;int item=i;
                        handler.post(()->{if(token!=epoch)return;queue.set(item,file);ready++;if(!firstPlayed)metrics=wasCached?"Audio từ cache trên máy":String.format(Locale.ROOT,"Tạo đoạn %.2f giây · %d luồng CPU",elapsed,threads);tryPlay();});
                    }
                    if(token!=epoch)return;
                    if(!BookStore.contentSignature(store.load(localId)).equals(sig))throw new IOException("Nội dung hoặc giọng đã đổi. Bấm Nghe để đọc bản mới.");
                    for(int i=start;i<endPart;i++)chapterFiles.add(store.audio(parts.get(i),book));
                    new ChapterAudio(store,localId).complete(book,localPlan.chapters.get(c),chapterFiles,()->token!=epoch);
                    handler.post(()->{if(token!=epoch)return;generating=false;if(paused)releaseCpu();notifyPlayer();});
                }
                if(token!=epoch)return;checkpoint.state("complete");
                if(engine!=null){engine.close();engine=null;engineThreads=0;}
                handler.post(()->{if(token!=epoch)return;generationPending=false;generationPaused=false;producerDone=true;tryPlay();notifyPlayer();});
            }catch(InterruptedException ignored){Thread.currentThread().interrupt();}
            catch(Throwable error){handler.post(()->{if(token==epoch){message=friendly(error);generationPending=false;generating=false;generationPaused=false;running=false;playing=false;paused=false;releasePlayer();stopBgm();releaseWake();notifyPlayer();}});}
        });return START_NOT_STICKY;
    }
    private void awaitGeneration(long token,GenerationProgress checkpoint) throws Exception {
        boolean parked=false;
        synchronized(generationGate){
            if(generationPaused&&token==epoch){
                parked=true;
                // Finish one bounded segment before pausing, then release ONNX sessions and CPU.
                if(engine!=null){engine.close();engine=null;engineThreads=0;}
                checkpoint.state("paused");
                handler.post(()->{if(token!=epoch)return;generating=false;if(!playing)releaseCpu();notifyPlayer();});
                while(generationPaused&&token==epoch)generationGate.wait();
            }
        }
        if(token!=epoch||Thread.currentThread().isInterrupted())throw new InterruptedException();
        if(parked)handler.post(()->{if(token!=epoch)return;generating=true;keepAwake();notifyPlayer();});
    }
    private void changeGeneration(boolean pause){
        if(!running||!generationPending)return;
        try{if(progress!=null)progress.state(pause?(generating?"pausing":"paused"):"running");}
        catch(Exception error){message="Chưa lưu được tiến độ. "+friendly(error);notifyPlayer();return;}
        synchronized(generationGate){generationPaused=pause;generationGate.notifyAll();}
        if(!pause)keepAwake();
        notifyPlayer();
    }
    public static String generationStatus(){
        if(generationPaused)return generating?"Đang hoàn tất đoạn hiện tại rồi tạm dừng tạo…":"Đã tạm dừng tạo · "+chapterPercent+"% chương";
        return chapterPercent>=100?"Đang lưu chương sách nói…":"Đang tạo sách nói của bạn… "+chapterPercent+"% chương";
    }
    private void prepareCloud(JSONObject book,long token,String localTitle) throws Exception {
        JSONObject entry=null;JSONArray history=book.getJSONArray("cloudOrders");for(int i=0;i<history.length();i++){JSONObject item=history.getJSONObject(i);if(orderId.equals(item.optJSONObject("order")==null?"":item.getJSONObject("order").optString("id")))entry=item;}
        if(entry==null)throw new IOException("Không có đơn này trong sách.");JSONObject order=entry.getJSONObject("order");
        if(!Set.of("queued","processing","ready").contains(order.getString("state")))throw new IOException("Đơn chưa có audio được xác nhận.");
        ArrayList<File> files=new ArrayList<>();JSONArray parts=entry.getJSONObject("snapshot").getJSONArray("segments");
        ArrayList<String> texts=new ArrayList<>();for(int i=0;i<parts.length();i++)texts.add(parts.getJSONObject(i).optString("text"));
        String selectedVoice=entry.getJSONObject("snapshot").optString("voice");int voiceIndex=Arrays.asList(CloudClient.VOICE_IDS).indexOf(selectedVoice);activeVoice=voiceIndex<0?"Pro":CloudClient.VOICES[voiceIndex];
        cloudTexts=texts;sourceTextMatches=book.optString("text").equals(String.join("",texts));
        for(int i=0;i<parts.length();i++){File f=store.cloudAudio(orderId,parts.getJSONObject(i).getString("id"));if(!AudioFiles.valid(f))throw new IOException("Chọn Nhận audio để tải đủ các đoạn trước khi nghe.");files.add(f);}
        handler.post(()->{if(token!=epoch)return;queue=files;title=localTitle+" · Pro Cloud";signature="";total=files.size();ready=total;index=0;current=0;resumeMs=0;producerDone=true;tryPlay();});
    }
    private void update(long token,String text){handler.post(()->{if(token!=epoch)return;if(!playing&&!paused)message=text;notifyPlayer();});}
    private void tryPlay(){
        if(!running)return;
        if(plan!=null&&index<playEnd){int c=plan.chapterAt(index),all=0,done=0;chapterTitle=plan.chapters.get(c).title;for(int i=plan.starts.get(c);i<plan.ends.get(c);i++){int n=plan.parts.get(i).length();all+=n;if(queue.get(i)!=null)done+=n;}chapterPercent=all==0?100:done*100/all;}
        if(paused||player!=null){notifyPlayer();return;}
        if(index>=queue.size()){if(producerDone){message="Đã nghe hết · Audio được lưu trên máy";running=false;playing=false;stopBgm();if(!cloud&&!libraryPlayback)try{savePosition(0,0);}catch(Exception ignored){}releaseWake();stopForeground(STOP_FOREGROUND_DETACH);notifyPlayer();}return;}
        if(plan!=null && index<playEnd){
            int c=plan.chapterAt(index),start=plan.starts.get(c),end=plan.ends.get(c);
            chapterTitle=plan.chapters.get(c).title;
            int available=0,chars=0;for(int i=start;i<end;i++){int n=plan.parts.get(i).length();chars+=n;if(queue.get(i)!=null)available+=n;}
            chapterPercent=chars==0?100:available*100/chars;
            if(bufferedChapter!=c){
                if(bufferFrom<start||bufferFrom>=end)bufferFrom=index;
                int threshold=plan.bufferEnd(bufferFrom,end);
                if(queue.get(threshold-1)==null){message=generationStatus();notifyPlayer();return;}
                bufferedChapter=c;
            }
        }
        File file=queue.get(index);if(file==null){message="Đang chuẩn bị âm thanh tiếp theo…";notifyPlayer();return;}
        try{
            if(!cloud&&!libraryPlayback&&!BookStore.contentSignature(store.load(activeId)).equals(signature))throw new IOException("Nội dung đã đổi. Hãy mở lại bản mới.");
            if(audioManager.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED){paused=true;message="Âm thanh đang được ứng dụng khác sử dụng.";return;}
            MediaPlayer p=new MediaPlayer();player=p;p.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build());p.setWakeMode(this,PowerManager.PARTIAL_WAKE_LOCK);p.setDataSource(file.getAbsolutePath());
            p.setOnPreparedListener(value->{if(value!=player)return;if(resumeMs>0){value.seekTo(resumeMs);resumeMs=0;}if(paused){message="Đã tạm dừng";notifyPlayer();return;}value.setPlaybackParams(new PlaybackParams().setSpeed(speed));value.start();playing=true;current=index;publishPosition();syncBgm(true);message="Đang nghe · "+chapterTitle;if(!firstPlayed){firstPlayed=true;metrics=String.format(Locale.ROOT,"Âm thanh đầu: %.2f giây · %s",(System.nanoTime()-requested)/1e9,metrics);}notifyPlayer();});
            p.setOnSeekCompleteListener(value->{if(value==player){publishPosition();persist();}});
            p.setOnCompletionListener(value->{if(value!=player)return;releasePlayer();index++;current=index;if(!cloud&&!libraryPlayback)try{savePosition(index,0);}catch(Exception ignored){}tryPlay();});
            p.setOnErrorListener((value,what,extra)->{if(value==player){message="Chưa phát được audio. Bấm Nghe để thử lại.";stopWork();notifyPlayer();}return true;});
            p.prepareAsync();
        }catch(Exception e){message=friendly(e);running=false;releasePlayer();releaseWake();notifyPlayer();}
    }
    private void pause(){if(!running)return;paused=true;playing=false;if(player!=null)try{player.pause();}catch(Exception ignored){}persist();syncBgm(false);audioManager.abandonAudioFocusRequest(focus);if(!generating)releaseCpu();message="Đã tạm dừng";notifyPlayer();}
    private void resume(){if(!running)return;paused=false;keepAwake();if(player!=null){if(audioManager.requestAudioFocus(focus)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED)return;try{player.start();playing=true;syncBgm(true);message="Đang nghe · "+chapterTitle;}catch(Exception ignored){releasePlayer();tryPlay();}}else tryPlay();notifyPlayer();}
    private void next(){if(!running)return;releasePlayer();index=plan==null?index+1:Math.min(playEnd,plan.ends.get(plan.chapterAt(index)));current=index;bufferedChapter=-1;bufferFrom=index;resumeMs=0;tryPlay();}
    private void persist(){if(!cloud&&!libraryPlayback&&running&&player!=null)try{savePosition(index,player.getCurrentPosition());}catch(Exception ignored){}}
    private void savePosition(int part,int millis) throws Exception {
        int offset=plan==null?0:part<plan.offsets.size()?plan.offsets.get(part):plan.chapters.get(plan.chapters.size()-1).endChar;
        store.position(activeId,signature,part,millis,offset);
    }
    private void releasePlayer(){if(player!=null){try{player.release();}catch(Exception ignored){}player=null;}playing=false;}
    // Renew only while doing user-requested work. Pausing audio still finishes the current chapter.
    private void keepAwake(){if(wake!=null&&!wake.isHeld())wake.acquire(10*60*1000L);}
    private void releaseCpu(){if(wake!=null&&wake.isHeld())wake.release();}
    private void releaseWake(){releaseCpu();audioManager.abandonAudioFocusRequest(focus);}
    private void stopWork(){persist();epoch++;if(job!=null)job.cancel(true);if(progress!=null&&generationPending)try{progress.state("paused");}catch(Exception ignored){}progress=null;synchronized(generationGate){generationPaused=false;generationGate.notifyAll();}generationPending=false;generating=false;releasePlayer();stopBgm();releaseWake();running=false;paused=false;producerDone=false;}
    private void stopPlayback(){stopWork();sleepUntilElapsed=0;message="Đã dừng · Các đoạn hoàn tất được giữ lại";notifyPlayer();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    private void syncBgm(boolean play){
        SharedPreferences sp=getSharedPreferences("settings",MODE_PRIVATE);String track=sp.getString("bgmTrack","none");float vol=sp.getFloat("bgmVolume",0.18f);
        try{JSONObject saved=store.load(bookId);track=saved.optString("bgmTrack",track);vol=(float)saved.optDouble("bgmVolume",vol);}catch(Exception ignored){}
        if("none".equals(track)||vol<=0.001f){stopBgm();return;}
        if(bgmPlayer==null||!track.equals(currentBgmTrack)){
            stopBgm();
            try{
                String file="piano".equals(track)?"music/piano_podcast_1.mp3":"rain".equals(track)?"music/rain.mp3":"late_night".equals(track)?"music/late_night.mp3":null;
                if(file==null)return;
                android.content.res.AssetFileDescriptor afd=getAssets().openFd(file);MediaPlayer m=new MediaPlayer();m.setDataSource(afd.getFileDescriptor(),afd.getStartOffset(),afd.getLength());afd.close();
                m.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build());
                m.setLooping(true);m.setVolume(vol,vol);m.prepare();bgmPlayer=m;currentBgmTrack=track;bgmVolume=vol;
            }catch(Exception ignored){stopBgm();return;}
        }
        if(bgmPlayer!=null){bgmPlayer.setVolume(vol,vol);if(play&&!bgmPlayer.isPlaying()){try{bgmPlayer.start();}catch(Exception ignored){}}else if(!play&&bgmPlayer.isPlaying()){try{bgmPlayer.pause();}catch(Exception ignored){}}}
    }
    private void stopBgm(){if(bgmPlayer!=null){try{bgmPlayer.stop();}catch(Exception ignored){}try{bgmPlayer.release();}catch(Exception ignored){}bgmPlayer=null;}currentBgmTrack="none";}
    private int duration(File file){if(file==null)return 0;Integer known=durationCache.get(file);if(known!=null)return known;try{long[] info=AudioFiles.inspect(file);int ms=(int)Math.min(Integer.MAX_VALUE,info[1]*1000/(info[2]*2));durationCache.put(file,ms);return ms;}catch(Exception e){return 0;}}
    private int chapterStart(){return plan==null?index:plan.starts.get(plan.chapterAt(index));}
    private int chapterEnd(){return plan==null?Math.min(queue.size(),index+1):Math.min(playEnd,plan.ends.get(plan.chapterAt(index)));}
    private void publishPosition(){
        if(index>=queue.size())return;
        int start=chapterStart(),end=chapterEnd(),available=0,elapsed=0;boolean complete=true;
        for(int i=start;i<end;i++){int ms=duration(queue.get(i));if(ms<=0)complete=false;available+=ms;if(i<index)elapsed+=ms;}
        if(player!=null)try{elapsed+=player.getCurrentPosition();}catch(Exception ignored){elapsed+=resumeMs;}
        else elapsed+=resumeMs;
        chapterPositionMs=elapsed;chapterDurationMs=available;chapterDurationComplete=complete;
        if(plan!=null&&index<plan.parts.size()){playbackText=plan.parts.get(index);currentCharOffset=plan.offsets.get(index);}
        else if(cloud&&index<cloudTexts.size())playbackText=cloudTexts.get(index);
    }
    private void seekChapter(int millis){
        if(!running||index>=queue.size())return;int start=chapterStart(),end=chapterEnd(),remaining=Math.max(0,millis),target=start,seek=0;
        for(int i=start;i<end;i++){int ms=duration(queue.get(i));if(ms<=0)break;target=i;seek=Math.min(remaining,Math.max(0,ms-1));if(remaining<ms)break;remaining-=ms;}
        if(queue.get(target)==null)return;
        if(target==index&&player!=null){try{player.seekTo(seek);publishPosition();persist();return;}catch(Exception ignored){}}
        releasePlayer();index=target;current=target;resumeMs=seek;if(!cloud&&!libraryPlayback)try{savePosition(index,seek);}catch(Exception ignored){}tryPlay();publishPosition();
    }
    private final Runnable tick=new Runnable(){public void run(){
        if(running){if(generating||playing)keepAwake();else if(player==null||paused)releaseCpu();publishPosition();long now=SystemClock.elapsedRealtime();if(playing&&now-lastPersistElapsed>=2000){persist();lastPersistElapsed=now;}
            if(sleepUntilElapsed>0&&now>=sleepUntilElapsed){sleepUntilElapsed=0;pause();message="Đã tạm dừng theo hẹn giờ ngủ";notifyPlayer();}}
        handler.postDelayed(this,500);
    }};
    private PendingIntent command(String action){return PendingIntent.getService(this,action.hashCode(),new Intent(this,PlaybackService.class).setAction(action),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);}
    private Notification notification(){
        Notification.Builder n=new Notification.Builder(this,"listening").setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle(title.isEmpty()?"Soundbooki":title).setContentText(generating||generationPaused?generationStatus():message)
            .setOngoing(running&&(!paused||generating)).setOnlyAlertOnce(true)
            .setContentIntent(PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE))
            .addAction(new Notification.Action.Builder(android.R.drawable.ic_media_pause,paused?"Nghe tiếp":"Dừng nghe",command("pause")).build());
        if(generationPending)n.addAction(new Notification.Action.Builder(android.R.drawable.ic_media_pause,generationPaused?"Tạo tiếp":"Dừng tạo",command(generationPaused?"generation-resume":"generation-pause")).build());
        else n.addAction(new Notification.Action.Builder(android.R.drawable.ic_media_next,"Chương sau",command("next")).build());
        return n.addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,"Dừng",command("stop")).build())
            .setStyle(new Notification.MediaStyle().setMediaSession(media.getSessionToken()).setShowActionsInCompactView(0,1)).build();
    }
    private void notifyPlayer(){
        String state=title+"|"+message+"|"+running+"|"+playing+"|"+paused+"|"+generating+"|"+generationPaused+"|"+generationPending+"|"+chapterPercent;
        if(state.equals(lastNotification))return;lastNotification=state;
        media.setPlaybackState(new PlaybackState.Builder().setActions(PlaybackState.ACTION_PLAY|PlaybackState.ACTION_PAUSE|PlaybackState.ACTION_STOP|PlaybackState.ACTION_SKIP_TO_NEXT).setState(playing?PlaybackState.STATE_PLAYING:paused?PlaybackState.STATE_PAUSED:running?PlaybackState.STATE_BUFFERING:PlaybackState.STATE_STOPPED,0,speed).build());
        media.setMetadata(new MediaMetadata.Builder().putString(MediaMetadata.METADATA_KEY_TITLE,title).putString(MediaMetadata.METADATA_KEY_ARTIST,"Soundbooki").build());
        if(running&&foregroundAttached)updateForeground();
        else if(!running&&foregroundAttached){stopForeground(STOP_FOREGROUND_DETACH);foregroundAttached=false;foregroundTypes=-1;}
        ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(21,notification());
    }
    private void updateForeground(){
        int types=ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK;
        if(generating)types|=Build.VERSION.SDK_INT>=35?ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROCESSING:ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC;
        if(types!=foregroundTypes){startForeground(21,notification(),types);foregroundTypes=types;}
    }
    @Override public void onTimeout(int startId,int type){stopPlayback();message="Android đã tạm dừng xử lý nền. Tiến độ đã lưu; mở app để tiếp tục tạo.";notifyPlayer();}
    static String friendly(Throwable e){if(e instanceof OutOfMemoryError)return "Máy đang thiếu RAM. Đóng bớt ứng dụng rồi thử lại với 2 luồng CPU.";String m=e.getMessage();return m==null?"Chưa hoàn tất. Các đoạn đã tạo vẫn được giữ; hãy thử lại.":m;}
    @Override public void onDestroy(){stopWork();handler.removeCallbacksAndMessages(null);media.release();worker.submit(()->{if(engine!=null)engine.close();});worker.shutdown();if(englishSpeech!=null){englishSpeech.close();englishSpeech=null;}super.onDestroy();}
}
