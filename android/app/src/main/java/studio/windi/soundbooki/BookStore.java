package studio.windi.soundbooki;
import android.content.Context;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;

public final class BookStore {
    public static final Object LOCK=new Object();
    private final File root;
    static volatile File fixtureRoot;
    public BookStore(Context c){root=fixtureRoot==null?new File(c.getFilesDir(),"library"):new File(fixtureRoot,"library");root.mkdirs();}
    public File root(){return root;}
    public File sourceFile(String id){return new File(folder(id),"source");}
    public File generationFile(String id){return new File(folder(id),"generation.json");}
    public static String hash(String s){return hash(s.getBytes(StandardCharsets.UTF_8));}
    public static String hash(byte[] data){try{return hex(MessageDigest.getInstance("SHA-256").digest(data));}catch(Exception e){throw new IllegalStateException(e);}}
    static String hex(byte[] data){StringBuilder s=new StringBuilder();for(byte b:data)s.append(String.format(Locale.ROOT,"%02x",b&255));return s.toString();}
    public static String id(){return UUID.randomUUID().toString().replace("-","");}
    private File folder(String id){if(!id.matches("[a-f0-9]{32}"))throw new IllegalArgumentException("Sách không hợp lệ.");return new File(root,id);}
    public JSONObject load(String id) throws Exception{synchronized(LOCK){return NanoEngine.read(new File(folder(id),"book.json"));}}
    public void save(JSONObject book) throws Exception {synchronized(LOCK){AudioFiles.atomic(new File(folder(book.getString("id")),"book.json"),book.toString().getBytes(StandardCharsets.UTF_8));}}
    public synchronized JSONObject create(String title,String text,File original) throws Exception {
        JSONObject b=new JSONObject().put("id",id()).put("title",title).put("status","ready").put("originalText",text).put("text",text).put("voice","Đức Trí").put("position",0).put("positionMs",0).put("cloudOrders",new JSONArray()).put("createdAt",System.currentTimeMillis()).put("lastOpened",System.currentTimeMillis());
        File dir=folder(b.getString("id"));dir.mkdirs();if(original!=null)Files.copy(original.toPath(),new File(dir,"source").toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        save(b);return b;
    }
    public synchronized List<JSONObject> books(){ArrayList<JSONObject> list=new ArrayList<>();File[] dirs=root.listFiles();if(dirs!=null)for(File d:dirs)if(d.isDirectory())try{list.add(load(d.getName()));}catch(Exception ignored){}list.sort((a,b)->a.optString("title").compareToIgnoreCase(b.optString("title")));return list;}
    public static String contentSignature(JSONObject b){return hash(b.optString("text")+"\u0000"+b.optString("voice")+"\u0000"+NanoEngine.REVISION+(b.optBoolean("bilingual")?Bilingual.REVISION+b.optString("englishVoice")+b.optString("englishRevision"):""));}
    public File audio(String text,String voice){return new File(root.getParentFile(),"audio/"+hash(NanoEngine.REVISION+"\u0000"+voice+"\u0000"+text)+".wav");}
    public File audio(String text,JSONObject book){if(!book.optBoolean("bilingual"))return audio(text,book.optString("voice"));return new File(root.getParentFile(),"audio/"+hash(NanoEngine.REVISION+"\0"+Bilingual.REVISION+"\0"+book.optString("voice")+"\0"+book.optString("englishVoice")+"\0"+book.optString("englishRevision")+"\0"+text)+".wav");}
    public File cloudAudio(String order,String segment){if(!order.matches("[a-f0-9-]{36}")||!segment.matches("[a-f0-9]{32}"))throw new IllegalArgumentException("Audio cloud không hợp lệ.");return new File(root.getParentFile(),"cloud/"+order+"/"+segment+".wav");}
    public void position(String id,String signature,int index,int millis) throws Exception {synchronized(LOCK){JSONObject b=load(id);if(!contentSignature(b).equals(signature))return;b.put("position",index).put("positionMs",millis);save(b);}}
    public void position(String id,String signature,int index,int millis,int offset) throws Exception {synchronized(LOCK){JSONObject b=load(id);if(!contentSignature(b).equals(signature))return;b.put("position",index).put("positionMs",millis).put("positionChar",offset);save(b);}}
    public static List<String> spokenParts(String text){return TextChunks.split(text);}
    public List<File> readyFiles(JSONObject b) throws Exception {
        ArrayList<File> files=new ArrayList<>();for(String s:new BookChapters.Plan(b).parts){File f=audio(s,b);if(!AudioFiles.valid(f))throw new IOException("Hãy nghe hoặc tạo xong toàn bộ sách trước khi xuất WAV.");files.add(f);}return files;
    }
}
