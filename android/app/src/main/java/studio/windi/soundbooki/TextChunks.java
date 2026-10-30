package studio.windi.soundbooki;
import java.util.*;
/** Every boundary partitions the source verbatim, including whitespace. */
public final class TextChunks {
    public static List<String> split(String source) {
        ArrayList<String> parts=new ArrayList<>();int begin=0;
        while(begin<source.length()) {
            int limit=begin;for(int count=0;count<120&&limit<source.length();count++)limit+=Character.charCount(source.codePointAt(limit));
            int end=limit;
            if(limit<source.length()) {
                for(int p=begin;p<limit;p++)if(".!?\n;".indexOf(source.charAt(p))>=0&&p-begin>=35){end=p+1;break;}
                if(end==limit) {int space=source.lastIndexOf(' ',limit-1);if(space>begin+20)end=space+1;}
            }
            parts.add(source.substring(begin,end));begin=end;
        }
        return parts;
    }
}
