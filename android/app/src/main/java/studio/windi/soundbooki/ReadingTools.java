package studio.windi.soundbooki;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.*;

/** Edition-bound ranges use original UTF-16 offsets, never displayed page numbers. */
final class ReadingTools {
    static String fold(String text){return Normalizer.normalize(text.toLowerCase(Locale.ROOT).replace('đ','d'),Normalizer.Form.NFD).replaceAll("\\p{M}+","");}
    static List<int[]> search(String text,String query){
        List<int[]> out=new ArrayList<>();String needle=fold(query.trim());if(needle.isEmpty()||needle.length()>200)return out;
        StringBuilder normalized=new StringBuilder();ArrayList<Integer> map=new ArrayList<>();
        for(int i=0;i<text.length();){int cp=text.codePointAt(i),end=i+Character.charCount(cp);String part=fold(new String(Character.toChars(cp)));for(int j=0;j<part.length();j++){normalized.append(part.charAt(j));map.add(i);}i=end;}
        String value=normalized.toString();for(int at=0;out.size()<200&&(at=value.indexOf(needle,at))>=0;at+=Math.max(1,needle.length())){int a=map.get(at),b=map.get(at+needle.length()-1);b+=Character.charCount(text.codePointAt(b));while(b<text.length()&&Character.getType(text.codePointAt(b))==Character.NON_SPACING_MARK)b+=Character.charCount(text.codePointAt(b));out.add(new int[]{a,b});}return out;
    }
    static File file(BookStore store,String id){if(!id.matches("[a-f0-9]{32}"))throw new IllegalArgumentException();return new File(store.root(),id+"/annotations.json");}
    static JSONArray notes(BookStore store,String id)throws Exception{File f=file(store,id);return f.isFile()?new JSONArray(new String(java.nio.file.Files.readAllBytes(f.toPath()),StandardCharsets.UTF_8)):new JSONArray();}
    static JSONObject save(BookStore store,JSONObject book,int start,int end,String note,String color,String id)throws Exception{
        synchronized(BookStore.LOCK){String text=book.optString("text");if(!BookStore.hash(store.load(book.getString("id")).optString("text")).equals(BookStore.hash(text)))throw new IOException("Nội dung đã đổi. Mở lại sách trước khi ghi chú.");
            if(start<0||start>=end||end>text.length()||end-start>10000||note.length()>10000)throw new IOException("Đoạn chữ hoặc ghi chú quá dài.");
            if(!List.of("yellow","green","blue","pink").contains(color))throw new IOException("Màu không hợp lệ.");
            JSONObject entry=new JSONObject().put("id",id==null?BookStore.id():id).put("edition",BookStore.hash(text)).put("start",start).put("end",end).put("quote",text.substring(start,end)).put("note",note).put("color",color).put("updatedAt",System.currentTimeMillis());
            JSONArray entries=notes(store,book.getString("id")),result=new JSONArray();for(int i=0;i<entries.length();i++)if(!entry.getString("id").equals(entries.getJSONObject(i).optString("id")))result.put(entries.get(i));result.put(entry);AudioFiles.atomic(file(store,book.getString("id")),result.toString().getBytes(StandardCharsets.UTF_8));return entry;}
    }
    static void remove(BookStore store,String bid,String id)throws Exception{synchronized(BookStore.LOCK){JSONArray old=notes(store,bid),result=new JSONArray();for(int i=0;i<old.length();i++)if(!id.equals(old.getJSONObject(i).optString("id")))result.put(old.get(i));AudioFiles.atomic(file(store,bid),result.toString().getBytes(StandardCharsets.UTF_8));}}
    static int color(String value){return switch(value){case "green"->0xffa8dab4;case "blue"->0xffacd4ef;case "pink"->0xfff2bed6;default->0xfff4d96e;};}
}
