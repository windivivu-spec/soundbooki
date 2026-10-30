package studio.windi.soundbooki;
import android.content.Context;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

public final class CloudClient {
    public static final int TRIAL_LIMIT=5,TRIAL_CHARACTERS=5000,TRIAL_MAX_UNITS=4;
    public static final String REVISION="pro-cloud-heygen-v1";
    public static final String[] VOICE_IDS={"3414fd7fdaa64e619fb8b021534ce368","3ab886ca76924521bbed407e45762540","eff592346cac4febbba5d5fef4621ff0","b241299543834cd8994186e600280e25","60dce6af562449f294ceeddb4130a9ee","6a92e2ed9d3843f2b059ef8e6809366c","5ee4ba10bd0446ba85421ab177462aba"};
    public static final String[] VOICES={"Đình Mạnh · Nam (Podcast)","Đình Gia · Nam","Minh Bùi · Nam","Minh Tài · Nam","Kim Thoa · Nữ","Ngân Quỳnh · Nữ","Thanh Thảo · Nữ"};
    private final Context context;public final String base;
    public CloudClient(Context c,String url) throws Exception {context=c.getApplicationContext();base=validateBase(url);}
    public static String validateBase(String value) throws Exception {
        URI u=new URI(value.trim());if(!"https".equals(u.getScheme())||u.getHost()==null||u.getUserInfo()!=null||u.getRawQuery()!=null||u.getFragment()!=null)throw new IOException("Nhập URL HTTPS của dịch vụ sách.");return value.trim().replaceAll("/+$","");
    }
    public static JSONObject snapshot(JSONObject book,String voice,boolean sample) throws Exception {
        if(!Arrays.asList(VOICE_IDS).contains(voice))throw new IOException("Chọn lại giọng Cloud.");
        return snapshot(book,voice,sample,-1);
    }
    public static JSONObject snapshot(JSONObject book,String voice,boolean sample,int chapter) throws Exception {
        return snapshot(book,voice,sample,chapter,1);
    }
    public static int chapterTrialUnits(JSONObject book,int chapter) throws Exception {
        if(chapter<0)return 1;
        List<PdfReflow.ChapterItem> chapters=BookChapters.get(book);
        if(chapter>=chapters.size())throw new IOException("Chương đã thay đổi. Hãy chọn lại.");
        String text=chapters.get(chapter).text;
        return Math.max(1,Math.min(TRIAL_MAX_UNITS,(text.codePointCount(0,text.length())+TRIAL_CHARACTERS-1)/TRIAL_CHARACTERS));
    }
    public static int trialUnits(JSONObject snapshot) throws Exception {
        int count=0;JSONArray parts=snapshot.getJSONArray("segments");
        for(int i=0;i<parts.length();i++){String text=parts.getJSONObject(i).getString("text");count+=text.codePointCount(0,text.length());}
        return Math.max(1,(count+TRIAL_CHARACTERS-1)/TRIAL_CHARACTERS);
    }
    public static JSONObject snapshot(JSONObject book,String voice,boolean sample,int chapter,int units) throws Exception {
        if(!Arrays.asList(VOICE_IDS).contains(voice))throw new IOException("Chọn lại giọng Cloud.");
        if(sample&&(units<1||units>TRIAL_MAX_UNITS||(units>1&&chapter<0)))throw new IOException("Chọn chương và dùng tối đa 4 lượt Pro mỗi lần.");
        String allText=book.getString("text");int opening=0,openingPage=0,end=allText.length();
        if(allText.equals(book.optString("originalText"))&&book.optJSONArray("sourceHeadings")!=null){
            JSONArray headings=book.getJSONArray("sourceHeadings");JSONObject chosen=headings.length()>0?headings.getJSONObject(0):null;
            for(int i=0;i<headings.length();i++){JSONObject h=headings.getJSONObject(i);if(h.optString("title").trim().matches("(?iu)^(?:chương|chapter|hồi)\\s+(?:0*1|i|một|one)(?:\\b|\\s|[:.\\-]).*")){chosen=h;break;}}
            if(chosen!=null){opening=Math.max(0,Math.min(allText.length(),chosen.getInt("startOffset")));openingPage=chosen.optInt("page");}
        }
        if(sample&&chapter>=0){List<PdfReflow.ChapterItem> chapters=BookChapters.get(book);if(chapter>=chapters.size())throw new IOException("Chương đã thay đổi. Hãy chọn lại.");PdfReflow.ChapterItem selected=chapters.get(chapter);opening=selected.startChar;end=selected.endChar;}
        JSONArray parts=new JSONArray();List<String> source=BookStore.spokenParts(sample?allText.substring(opening,end):allText);int remaining=sample?TRIAL_CHARACTERS*units:2_000_000,index=0,offset=sample?opening:0;
        for(String original:source){if(remaining<=0)break;int n=Math.min(remaining,original.codePointCount(0,original.length()));String text=original.substring(0,original.offsetByCodePoints(0,n));
            int page=0;JSONArray pages=allText.equals(book.optString("originalText"))?book.optJSONArray("pages"):null;if(pages!=null)for(int p=0;p<pages.length();p++){if(pages.getJSONObject(p).getInt("startOffset")<=offset)page=p;else break;}
            parts.put(new JSONObject().put("id",BookStore.hash(book.getString("id")+":"+offset+":"+text).substring(0,32)).put("page",page).put("index",index++).put("text",text));remaining-=n;offset+=original.length();
        }
        if(parts.length()==0)throw new IOException("Sách chưa có chữ để tạo.");
        if(sample)openingPage=parts.getJSONObject(0).getInt("page");
        JSONObject result=new JSONObject().put("title",book.getString("title")).put("language","vi").put("voice",voice).put("revision",REVISION).put("audioRevision",REVISION+"-audio-v1").put("openingPage",openingPage).put("segments",parts);
        if(sample&&trialUnits(result)>1)result.put("trialUnits",trialUnits(result));
        return result;
    }
    public static boolean sameTrialPrefix(JSONObject old,JSONObject next) throws Exception {
        int units=old.optInt("trialUnits",1);if(units!=next.optInt("trialUnits",1))return false;
        for(String key:new String[]{"title","language","voice","revision","audioRevision","openingPage"})if(!Objects.equals(old.opt(key),next.opt(key)))return false;
        JSONArray a=old.getJSONArray("segments"),b=next.getJSONArray("segments");if(a.length()==0||a.length()>b.length()||(units>1&&a.length()!=b.length()))return false;
        for(int i=0;i<a.length();i++){JSONObject x=a.getJSONObject(i),y=b.getJSONObject(i);for(String key:new String[]{"id","index","page"})if(!Objects.equals(x.opt(key),y.opt(key)))return false;
            if(i==a.length()-1&&units==1?!y.getString("text").startsWith(x.getString("text")):!y.getString("text").equals(x.getString("text")))return false;
        }return true;
    }
    public JSONObject post(String action,JSONObject payload) throws Exception {
        if(!Set.of("trial","trial-group","quote","status","profile").contains(action))throw new IOException("Thao tác Cloud không hợp lệ.");
        payload.put("deviceCode",CloudIdentity.code(context));byte[] body=payload.toString().getBytes(StandardCharsets.UTF_8);if(body.length>12_000_000)throw new IOException("Nội dung quá lớn.");
        HttpURLConnection connection=(HttpURLConnection)new URL(base+"/"+action).openConnection();connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(15000);connection.setReadTimeout(35000);connection.setRequestMethod("POST");connection.setDoOutput(true);connection.setFixedLengthStreamingMode(body.length);connection.setRequestProperty("Content-Type","application/json");connection.setRequestProperty("Authorization","Bearer "+CloudIdentity.credential(context,base));
        try {
            try(OutputStream out=connection.getOutputStream()){out.write(body);}
            int status=connection.getResponseCode();InputStream response=status>=200&&status<300?connection.getInputStream():connection.getErrorStream();
            if(response==null)throw new IOException("Dịch vụ chưa phản hồi ("+status+").");JSONObject result;
            try(InputStream in=response){byte[] raw=in.readNBytes(12_000_001);if(raw.length>12_000_000)throw new IOException("Phản hồi quá lớn.");result=new JSONObject(new String(raw,StandardCharsets.UTF_8));}
            if(status<200||status>=300)throw new IOException(result.optString("error","Cloud chưa sẵn sàng ("+status+")."));return result;
        } finally {connection.disconnect();}
    }
    public static void validateOrder(JSONObject order) throws Exception {
        if(!order.getString("id").matches("[a-f0-9-]{36}")||!Set.of("awaiting_payment","queued","processing","ready","failed","expired").contains(order.getString("state")))throw new IOException("Đơn Cloud không hợp lệ.");
        if("book".equals(order.optString("kind"))&&order.getLong("amountVND")<=0)throw new IOException("Thiếu báo giá từ máy chủ.");
    }
    public JSONArray receive(BookStore store,JSONObject entry,JSONObject response,java.util.function.BooleanSupplier allowed) throws Exception {
        JSONObject order=response.getJSONObject("order");validateOrder(order);String id=entry.getJSONObject("order").getString("id");if(!id.equals(order.getString("id")))throw new IOException("Cloud trả về sai đơn.");
        JSONArray audio=response.optJSONArray("audio"),segments=entry.getJSONObject("snapshot").getJSONArray("segments");JSONArray received=new JSONArray();if(audio==null)return received;
        if(!Set.of("queued","processing","ready").contains(order.getString("state"))&&audio.length()>0)throw new IOException("Đơn chưa được phép nhận audio.");
        for(int i=0;i<audio.length();i++){
            if(!allowed.getAsBoolean())throw new InterruptedException();JSONObject item=audio.getJSONObject(i);String sid=item.getString("id"),expected=item.getString("sha256");boolean found=false;for(int j=0;j<segments.length();j++)if(sid.equals(segments.getJSONObject(j).getString("id")))found=true;
            if(!found||!expected.matches("[a-f0-9]{64}"))throw new IOException("Audio không thuộc bản chữ đã mua.");
            URI url=URI.create(item.getString("url")),gateway=URI.create(base);
            if(!"https".equals(url.getScheme())||url.getUserInfo()!=null||!Objects.equals(url.getHost(),gateway.getHost())||url.getPort()!=gateway.getPort()||!url.getPath().startsWith("/storage/v1/object/sign/wsn-book-audio/"+id+"/"))throw new IOException("Địa chỉ nhận audio không hợp lệ.");
            File file=store.cloudAudio(id,sid);if(AudioFiles.valid(file)&&BookStore.hash(Files.readAllBytes(file.toPath())).equals(expected)){received.put(sid);continue;}
            file.getParentFile().mkdirs();File partial=new File(file.getPath()+".partial");HttpURLConnection c=(HttpURLConnection)url.toURL().openConnection();c.setInstanceFollowRedirects(false);c.setConnectTimeout(15000);c.setReadTimeout(60000);
            try {
                if(c.getResponseCode()!=200)throw new IOException("Chưa tải được audio; mở lại đơn để tiếp tục.");long total=0;MessageDigest digest=MessageDigest.getInstance("SHA-256");
                try(InputStream in=c.getInputStream();FileOutputStream out=new FileOutputStream(partial)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1){total+=n;if(total>52_428_800)throw new IOException("Đoạn audio quá lớn.");digest.update(b,0,n);out.write(b,0,n);}out.getFD().sync();}
                if(!BookStore.hex(digest.digest()).equals(expected)||!AudioFiles.valid(partial))throw new IOException("Audio tải chưa đủ; các đoạn hoàn tất vẫn được giữ.");
                Files.move(partial.toPath(),file.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);received.put(sid);
            } finally {c.disconnect();}
        }
        return received;
    }
}
