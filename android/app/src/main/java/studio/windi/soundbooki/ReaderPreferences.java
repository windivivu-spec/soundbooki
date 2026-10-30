package studio.windi.soundbooki;

import android.content.SharedPreferences;
import android.graphics.Color;
import org.json.*;
import java.util.*;

/** Reader-only settings are per book; bookmarks are bound to the exact source edition. */
final class ReaderPreferences {
    static final String[] THEME_IDS={"system","paper","white","sepia","sage","night","oled"};
    static final String[] THEME_LABELS={"Theo máy","Giấy ấm","Trắng","Nâu dịu","Xanh dịu","Ban đêm","Đen"};
    static final String[] MOTION_IDS={"curl","slide","none"};
    static final String[] MOTION_LABELS={"Lật giấy","Trượt nhẹ","Không hiệu ứng"};
    final SharedPreferences prefs;
    final String key,marksKey,legacyMarkKey;
    float fontSize,lineSpacing;
    int margin,brightness;
    boolean serif,keepAwake;
    String background,motion;
    private final ArrayList<Mark> marks=new ArrayList<>();
    ReaderPreferences(SharedPreferences prefs,String bookId,String hash,int textLength){
        this.prefs=prefs;key="book-style-"+bookId;marksKey="marks-"+bookId+"-"+hash;legacyMarkKey="bookmark-offset-"+bookId+"-"+hash;
        JSONObject data;try{data=new JSONObject(prefs.getString(key,"{}"));}catch(Exception ignored){data=new JSONObject();}
        fontSize=clamp((float)data.optDouble("fontSize",prefs.getFloat("fontSize",19)),14,34);
        serif=data.optBoolean("serif",prefs.getBoolean("useSerif",true));lineSpacing=clamp((float)data.optDouble("lineSpacing",1.35),1.15f,1.85f);
        margin=Math.max(16,Math.min(40,data.optInt("margin",24)));brightness=Math.max(-1,Math.min(100,data.optInt("brightness",-1)));keepAwake=data.optBoolean("keepAwake",false);
        background=valid(data.optString("background","system"),THEME_IDS,"system");motion=valid(data.optString("motion","curl"),MOTION_IDS,"curl");
        try{JSONArray array=new JSONArray(prefs.getString(marksKey,"[]"));for(int i=0;i<array.length();i++){JSONObject m=array.optJSONObject(i);if(m==null)continue;int at=m.optInt("offset",-1);if(at>=0&&at<Math.max(1,textLength))marks.add(new Mark(m.optString("id",UUID.randomUUID().toString()),at,m.optString("note",""),m.optLong("created",0)));}}catch(Exception ignored){}
        if(!prefs.contains(marksKey)&&prefs.contains(legacyMarkKey)){int at=prefs.getInt(legacyMarkKey,-1);if(at>=0&&at<Math.max(1,textLength)){marks.add(new Mark(UUID.randomUUID().toString(),at,"",0));saveMarks();}}
        marks.sort(Comparator.comparingInt(m->m.offset));
    }
    private static float clamp(float x,float min,float max){return Float.isFinite(x)?Math.max(min,Math.min(max,x)):min;}
    private static String valid(String value,String[] options,String fallback){return Arrays.asList(options).contains(value)?value:fallback;}
    void save(){try{JSONObject d=new JSONObject().put("fontSize",fontSize).put("serif",serif).put("lineSpacing",lineSpacing).put("margin",margin).put("background",background).put("motion",motion).put("brightness",brightness).put("keepAwake",keepAwake);prefs.edit().putString(key,d.toString()).apply();}catch(JSONException impossible){throw new IllegalStateException(impossible);}}
    List<Mark> bookmarks(){return new ArrayList<>(marks);}
    Mark inRange(int start,int end){int lo=0,hi=marks.size();while(lo<hi){int mid=(lo+hi)>>>1;if(marks.get(mid).offset<start)lo=mid+1;else hi=mid;}return lo<marks.size()&&marks.get(lo).offset<end?marks.get(lo):null;}
    int bookmarkCount(){return marks.size();}
    Mark add(int offset){for(Mark m:marks)if(m.offset==offset)return m;Mark mark=new Mark(UUID.randomUUID().toString(),offset,"",System.currentTimeMillis());marks.add(mark);marks.sort(Comparator.comparingInt(m->m.offset));saveMarks();return mark;}
    void remove(String id){marks.removeIf(m->m.id.equals(id));saveMarks();}
    void rename(String id,String note){for(Mark m:marks)if(m.id.equals(id))m.note=note.codePointCount(0,note.length())>160?note.substring(0,note.offsetByCodePoints(0,160)):note;saveMarks();}
    private void saveMarks(){try{JSONArray array=new JSONArray();for(Mark m:marks)array.put(new JSONObject().put("id",m.id).put("offset",m.offset).put("note",m.note).put("created",m.created));prefs.edit().putString(marksKey,array.toString()).apply();}catch(JSONException impossible){throw new IllegalStateException(impossible);}}
    static final class Mark {final String id;final int offset;final long created;String note;Mark(String id,int offset,String note,long created){this.id=id;this.offset=offset;this.note=note;this.created=created;}}
    static final class Palette {
        final int paper,ink,muted,control,rule,accent;final boolean dark;
        Palette(String paper,String ink,String muted,String control,String rule,String accent,boolean dark){this.paper=Color.parseColor(paper);this.ink=Color.parseColor(ink);this.muted=Color.parseColor(muted);this.control=Color.parseColor(control);this.rule=Color.parseColor(rule);this.accent=Color.parseColor(accent);this.dark=dark;}
    }
    static Palette palette(String id,boolean systemDark){
        if(id.equals("system"))id=systemDark?"night":"paper";
        return switch(id){
            case "white" -> new Palette("#FAFAF7","#242A31","#59616B","#F0F1EE","#CFD3D3","#245EB6",false);
            case "sepia" -> new Palette("#EBDDCA","#382D23","#68523F","#E2D1B9","#C4AE91","#70451F",false);
            case "sage" -> new Palette("#DFE8DE","#263C30","#4B6053","#D2DFD0","#ADBFAD","#225A3A",false);
            case "night" -> new Palette("#1E2733","#E7EBEF","#A8B4BF","#26323F","#455463","#98C1FF",true);
            case "oled" -> new Palette("#000000","#F2F4F7","#A8B4BF","#151C28","#384B67","#98C1FF",true);
            default -> new Palette("#F3EFE5","#2C2A25","#5D5A50","#EAE4D7","#CDC5B5","#77512D",false);
        };
    }
}
