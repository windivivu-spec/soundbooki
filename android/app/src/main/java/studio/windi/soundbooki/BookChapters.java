package studio.windi.soundbooki;

import org.json.*;
import java.util.*;

/** One chapter model shared by reader, producer and export. Offsets are UTF-16. */
public final class BookChapters {
    public static final int START_BUFFER_CHARS = 500;
    public static final String REVISION = "source-chapters-v2";
    public static List<PdfReflow.ChapterItem> get(JSONObject book) {
        String text=book.optString("text");
        JSONArray saved=book.optJSONArray("chapters");
        List<PdfReflow.ChapterItem> result=new ArrayList<>();
        if(BookStore.hash(text).equals(book.optString("chaptersTextHash")) && saved!=null) {
            int end=0;
            for(int i=0;i<saved.length();i++) {
                JSONObject c=saved.optJSONObject(i);if(c==null){result.clear();break;}
                int a=c.optInt("startChar",-1),b=c.optInt("endChar",-1);
                if(a!=end||b<=a||b>text.length()){result.clear();break;}
                result.add(new PdfReflow.ChapterItem(c.optString("id"),c.optString("title"),a,b,text.substring(a,b)));end=b;
            }
            if(end!=text.length())result.clear();
        }
        return result.isEmpty()?PdfReflow.extractChapters(text):result;
    }
    public static void set(JSONObject book,List<PdfReflow.ChapterItem> chapters) throws JSONException {
        JSONArray a=new JSONArray();
        for(PdfReflow.ChapterItem c:chapters)a.put(new JSONObject().put("id",c.id).put("title",c.title).put("startChar",c.startChar).put("endChar",c.endChar));
        book.put("chapters",a).put("chaptersTextHash",BookStore.hash(book.optString("text"))).put("chapterRevision",REVISION);
    }
    /** Map source anchors only when differences are whitespace / old PDF wrap hyphens. */
    public static List<PdfReflow.ChapterItem> fromSource(JSONObject book,JSONArray markers) {
        String raw=book.optString("originalText"),text=book.optString("text");
        int[] map=new int[raw.length()+1];int at=0;
        for(int i=0;i<raw.length();i++) {
            map[i]=at;char ch=raw.charAt(i);
            if(ignored(ch))continue;
            while(at<text.length()&&ignored(text.charAt(at)))at++;
            map[i]=at;
            if(at>=text.length()||text.charAt(at)!=ch)return PdfReflow.extractChapters(text);
            at++;
        }
        map[raw.length()]=text.length();
        while(at<text.length()&&ignored(text.charAt(at)))at++;
        if(at!=text.length())return PdfReflow.extractChapters(text);
        TreeMap<Integer,String> cuts=new TreeMap<>();
        if(markers!=null)for(int i=0;i<markers.length();i++) {
            JSONObject m=markers.optJSONObject(i);if(m==null)continue;
            int off=m.optInt("startOffset",-1);String title=m.optString("title").trim();
            if(off>=0&&off<raw.length()&&!title.isEmpty())cuts.put(map[off],title);
        }
        if(cuts.isEmpty())return PdfReflow.extractChapters(text);
        if(cuts.firstKey()>0)cuts.put(0,"Phần mở đầu");
        ArrayList<Integer> offsets=new ArrayList<>(cuts.keySet());List<PdfReflow.ChapterItem> result=new ArrayList<>();
        for(int i=0;i<offsets.size();i++){int a=offsets.get(i),b=i+1<offsets.size()?offsets.get(i+1):text.length();if(b>a)result.add(new PdfReflow.ChapterItem("source-"+a,cuts.get(a),a,b,text.substring(a,b)));}
        return result;
    }
    private static boolean ignored(char c){return Character.isWhitespace(c)||c=='-'||c=='–'||c=='—';}
    public static final class Plan {
        public final List<PdfReflow.ChapterItem> chapters;
        public final List<String> parts=new ArrayList<>();
        public final List<Integer> starts=new ArrayList<>(),ends=new ArrayList<>(),offsets=new ArrayList<>();
        public Plan(JSONObject book){chapters=get(book);for(PdfReflow.ChapterItem c:chapters){starts.add(parts.size());int offset=c.startChar;for(String part:split(book,c.text)){offsets.add(offset);parts.add(part);offset+=part.length();}ends.add(parts.size());}}
        private static List<String> split(JSONObject book,String text){if(!book.optBoolean("bilingual"))return BookStore.spokenParts(text);List<String> result=new ArrayList<>();for(String sentence:Bilingual.parts(text))result.addAll(BookStore.spokenParts(sentence));return result;}
        public int chapterAt(int part){for(int c=0;c<ends.size();c++)if(part<ends.get(c))return c;return Math.max(0,chapters.size()-1);}
        public int partAtOffset(int offset){int at=0;for(int i=0;i<parts.size();i++){at+=parts.get(i).length();if(offset<at)return i;}return Math.max(0,parts.size()-1);}
        public int bufferEnd(int from,int end){int count=0;for(int i=from;i<end;i++){count+=parts.get(i).length();if(count>=START_BUFFER_CHARS)return i+1;}return end;}
    }
}
