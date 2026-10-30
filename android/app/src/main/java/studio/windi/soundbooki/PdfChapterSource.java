package studio.windi.soundbooki;

import com.tom_roush.pdfbox.pdmodel.*;
import com.tom_roush.pdfbox.text.*;
import com.tom_roush.pdfbox.pdmodel.interactive.documentnavigation.outline.*;
import com.tom_roush.pdfbox.pdmodel.interactive.documentnavigation.destination.*;
import com.tom_roush.pdfbox.pdmodel.interactive.action.PDActionGoTo;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;

/** Large number/title pairs must form a verified sequence in source typography. */
final class PdfChapterSource {
    static final class Row {
        final String text;final float size,y;final int page,offset;
        Row(String t,float s,int p,int o,float y){text=t;size=s;page=p;offset=o;this.y=y;}
    }
    static final class Extractor extends PDFTextStripper {
        final List<Row> rows=new ArrayList<>();int page=0,base=0;StringWriter writer;
        Extractor() throws IOException {setSortByPosition(true);}
        @Override protected void writeString(String text,List<TextPosition> positions) throws IOException {
            int at=writer.getBuffer().length();float size=0,y=0;
            for(TextPosition p:positions){size=Math.max(size,p.getFontSizeInPt());y=p.getYDirAdj();}
            rows.add(new Row(text.trim(),size,page,base+at,y));
            super.writeString(text,positions);
        }
    }
    static JSONArray markers(File file) throws Exception {return extract(file,(i,n,t,h)->{});}
    static JSONArray extract(File file,BookImporter.PageSink sink) throws Exception {
        List<Integer> pageOffsets=new ArrayList<>();int offset=0;
        try(PDDocument doc=PDDocument.load(file)) {
            if(doc.isEncrypted()&&!doc.getCurrentAccessPermission().canExtractContent())throw new IOException("PDF không cho phép trích chữ.");
            Extractor x=new Extractor();
            for(int p=0;p<doc.getNumberOfPages();p++) {
                if(Thread.currentThread().isInterrupted())throw new InterruptedException();
                if(p>0)offset+=2;pageOffsets.add(offset);
                x.page=p;x.base=offset;x.writer=new StringWriter();x.setStartPage(p+1);x.setEndPage(p+1);x.writeText(doc,x.writer);
                String body=x.writer.toString();offset+=body.length();sink.page(p,doc.getNumberOfPages(),body,List.of());
            }
            JSONArray outline=new JSONArray();PDDocumentOutline root=doc.getDocumentCatalog().getDocumentOutline();
            if(root!=null)readOutline(root,doc,pageOffsets,x.rows,outline);
            return outline.length()>1?outline:numbered(x.rows);
        }
    }
    private static void readOutline(PDOutlineNode node,PDDocument doc,List<Integer> offsets,List<Row> rows,JSONArray out) throws Exception {
        for(PDOutlineItem item:node.children()) {
            PDPage page=item.findDestinationPage(doc);int p=page==null?-1:doc.getPages().indexOf(page);String title=item.getTitle();
            if(p>=0&&title!=null&&!title.trim().isEmpty()){
                int off=offsets.get(p);
                boolean matched=false;
                for(Row r:rows)if(r.page==p&&r.text.equalsIgnoreCase(title.trim())){off=r.offset;matched=true;break;}
                if(!matched){
                    PDDestination dest=item.getDestination();
                    if(dest==null&&item.getAction() instanceof PDActionGoTo)dest=((PDActionGoTo)item.getAction()).getDestination();
                    if(dest instanceof PDNamedDestination)dest=doc.getDocumentCatalog().findNamedDestinationPage((PDNamedDestination)dest);
                    int top=dest instanceof PDPageXYZDestination?((PDPageXYZDestination)dest).getTop():dest instanceof PDPageFitWidthDestination?((PDPageFitWidthDestination)dest).getTop():-1;
                    if(top>=0){float y=page.getCropBox().getUpperRightY()-top;for(Row r:rows)if(r.page==p&&r.y>=y-8){off=r.offset;break;}}
                }
                out.put(new JSONObject().put("title",title).put("startOffset",off));
            }
            readOutline(item,doc,offsets,rows,out);
        }
    }
    static JSONArray numbered(List<Row> rows) throws JSONException {
        ArrayList<Float> fonts=new ArrayList<>();for(Row r:rows)if(r.text.length()>40&&r.size>0)fonts.add(r.size);
        if(fonts.isEmpty())return new JSONArray();Collections.sort(fonts);float threshold=Math.max(18,fonts.get(fonts.size()/2)*1.35f);
        Pattern number=Pattern.compile("(?i)^(?:(?:chương|chapter)\\s+)?(\\d{1,3})[.:]?(?:\\s+(.+))?$");
        List<Row> candidates=new ArrayList<>();List<Integer> nums=new ArrayList<>();List<String> titles=new ArrayList<>();
        List<Row> large=new ArrayList<>();for(Row r:rows)if(r.size>=threshold)large.add(r);
        for(int i=0;i<large.size();i++){
            Row r=large.get(i);Matcher m=number.matcher(r.text);if(!m.matches())continue;
            StringBuilder title=new StringBuilder(m.group(2)==null?"":m.group(2));
            for(int j=i+1;j<Math.min(large.size(),i+5);j++){
                Row next=large.get(j);if(next.page>r.page+1||next.size<threshold||number.matcher(next.text).matches())break;
                int letters=0,upper=0;for(char c:next.text.toCharArray())if(Character.isLetter(c)){letters++;if(Character.isUpperCase(c))upper++;}
                if(letters==0||upper<letters*.75)break;
                if(title.length()>0)title.append(' ');title.append(next.text);
            }
            if(title.length()>0){candidates.add(r);nums.add(Integer.parseInt(m.group(1)));titles.add(title.toString());}
        }
        List<Integer> best=new ArrayList<>();
        for(int i=0;i<nums.size();i++)if(nums.get(i)==1){List<Integer> run=new ArrayList<>();run.add(i);int n=1;for(int j=i+1;j<nums.size();j++)if(nums.get(j)==n+1){run.add(j);n++;}if(run.size()>best.size())best=run;}
        JSONArray result=new JSONArray();Set<Integer> pages=new HashSet<>();for(int i:best)pages.add(candidates.get(i).page);
        if(best.size()<2||pages.size()<2)return result;
        for(int i:best)result.put(new JSONObject().put("title",nums.get(i)+" · "+titles.get(i)).put("startOffset",candidates.get(i).offset));
        return result;
    }
}
