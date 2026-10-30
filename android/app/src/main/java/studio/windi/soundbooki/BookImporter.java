package studio.windi.soundbooki;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import com.tom_roush.pdfbox.pdmodel.PDDocument;
import com.tom_roush.pdfbox.text.PDFTextStripper;
import org.jsoup.Jsoup;
import org.jsoup.nodes.*;
import org.jsoup.parser.Parser;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.charset.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public final class BookImporter {
    interface PageSink {void page(int index,int total,String text,List<String> headings) throws Exception;}
    public static JSONObject importFile(Context c,Uri uri,BookStore store) throws Exception {
        String name="Sách mới";
        try(Cursor q=c.getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){if(q!=null&&q.moveToFirst())name=q.getString(0);}
        String lower=name.toLowerCase(Locale.ROOT),mime=c.getContentResolver().getType(uri),format=lower.endsWith(".epub")||"application/epub+zip".equals(mime)?"epub":lower.endsWith(".pdf")||"application/pdf".equals(mime)?"pdf":lower.endsWith(".txt")||lower.endsWith(".md")||"text/plain".equals(mime)?"txt":"";
        if(format.isEmpty())throw new IOException("Chọn EPUB, PDF có chữ hoặc TXT UTF-8.");
        File source=File.createTempFile("import-",".source",c.getCacheDir());
        try {
            try(InputStream in=c.getContentResolver().openInputStream(uri);FileOutputStream out=new FileOutputStream(source)){
                if(in==null)throw new IOException("Chưa mở được tài liệu.");byte[] b=new byte[65536];long size=0;int n;
                while((n=in.read(b))!=-1){size+=n;if(size>80_000_000)throw new IOException("Bản thử nhận tài liệu tối đa 80 MB.");out.write(b,0,n);}out.getFD().sync();
            }
            JSONObject book=store.create(name.replaceFirst("(?i)\\.(epub|pdf|txt|md)$",""),"",source);
            book.put("sourceFormat",format).put("sourceName",name).put("status","importing").put("importedPages",0).put("pages",new JSONArray()).put("sourceHeadings",new JSONArray());store.save(book);
            return resume(book,store);
        } finally {source.delete();}
    }
    public static JSONObject resume(JSONObject book,BookStore store) throws Exception {
        final String id=book.getString("id");File source=store.sourceFile(id);int completed=book.optInt("importedPages");StringBuilder text=new StringBuilder(book.getString("originalText"));
        PageSink sink=(page,total,body,headings)->{
            if(Thread.currentThread().isInterrupted())throw new InterruptedException("Đã giữ lại các trang đã nhập.");
            if(page<completed)return;
            if(page>0)text.append("\n\n");int start=text.length();text.append(body);
            if(text.codePointCount(0,text.length())>2_000_000)throw new IOException("Bản thử nhận tối đa 2 triệu ký tự mỗi sách.");
            synchronized(BookStore.LOCK){JSONObject current=store.load(id);JSONArray pages=current.optJSONArray("pages");if(pages==null)pages=new JSONArray();pages.put(new JSONObject().put("index",page).put("startOffset",start).put("endOffset",text.length()));
                JSONArray hs=current.optJSONArray("sourceHeadings");if(hs==null)hs=new JSONArray();int after=0;for(String heading:headings){int at=body.indexOf(heading,after);if(at>=0){hs.put(new JSONObject().put("title",heading).put("startOffset",start+at).put("page",page));after=at+heading.length();}}
                current.put("originalText",text.toString()).put("text",text.toString()).put("pages",pages).put("sourceHeadings",hs).put("importedPages",page+1).put("totalPages",total).put("status","importing");store.save(current);
            }
        };
        try {
            String format=book.getString("sourceFormat");JSONArray pdfMarkers=null;if(format.equals("pdf"))pdfMarkers=PdfChapterSource.extract(source,sink);else if(format.equals("epub"))epubPages(source,sink);else sink.page(0,1,decode(Files.readAllBytes(source.toPath())),List.of());
            if(text.toString().trim().isEmpty())throw new IOException("Chưa tìm thấy chữ. Bản thử này nhận PDF có lớp chữ; PDF scan cần OCR.");
            synchronized(BookStore.LOCK){
                JSONObject ready=store.load(id);
                ready.put("status","ready");
                ready.remove("importError");
                String fullText = ready.optString("text", text.toString());
                if ("pdf".equals(format)) {
                    ready.put("text", PdfReflow.process(fullText).text);
                    ready.put("sourceHeadings", pdfMarkers);
                }
                BookChapters.set(ready, BookChapters.fromSource(ready, ready.optJSONArray("sourceHeadings")));
                store.save(ready);
                return ready;
            }
        }catch(Exception error){synchronized(BookStore.LOCK){JSONObject partial=store.load(id);partial.put("status","interrupted").put("importError",error.getMessage());store.save(partial);}throw error;}
    }
    static JSONObject refreshChapters(BookStore store,String id) throws Exception {
        JSONObject before=store.load(id);String hash=BookStore.hash(before.optString("text"));
        JSONArray markers=before.optJSONArray("sourceHeadings");
        if("pdf".equals(before.optString("sourceFormat")))markers=PdfChapterSource.markers(store.sourceFile(id));
        synchronized(BookStore.LOCK){JSONObject latest=store.load(id);if(!hash.equals(BookStore.hash(latest.optString("text"))) || (BookChapters.REVISION.equals(latest.optString("chapterRevision")) && !BookChapters.REVISION.equals(before.optString("chapterRevision"))))return latest;
            latest.put("sourceHeadings",markers==null?new JSONArray():markers);
            BookChapters.set(latest,BookChapters.fromSource(latest,markers));store.save(latest);return latest;}
    }
    static String decode(byte[] bytes) throws CharacterCodingException {
        Charset charset=StandardCharsets.UTF_8;int skip=0;
        if(bytes.length>=2&&bytes[0]==(byte)0xff&&bytes[1]==(byte)0xfe){charset=StandardCharsets.UTF_16LE;skip=2;}
        else if(bytes.length>=2&&bytes[0]==(byte)0xfe&&bytes[1]==(byte)0xff){charset=StandardCharsets.UTF_16BE;skip=2;}
        else if(bytes.length>=3&&bytes[0]==(byte)0xef&&bytes[1]==(byte)0xbb&&bytes[2]==(byte)0xbf)skip=3;
        return charset.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes,skip,bytes.length-skip)).toString();
    }
    static void pdfPages(File file,PageSink sink) throws Exception { PdfChapterSource.extract(file,sink); }
    static String pdf(File file) throws Exception {StringBuilder out=new StringBuilder();pdfPages(file,(i,n,t,h)->{if(i>0)out.append("\n\n");out.append(t);});return out.toString();}
    static String entry(ZipFile zip,String name) throws IOException {
        if(name.startsWith("/")||name.contains("..")||name.contains("\\"))throw new IOException("Đường EPUB không hợp lệ.");
        ZipEntry e=zip.getEntry(name);if(e==null||e.getSize()>8_000_000)throw new IOException("Thiếu hoặc quá lớn: "+name);
        try(InputStream in=zip.getInputStream(e)){byte[] b=in.readNBytes(8_000_001);if(b.length>8_000_000)throw new IOException("Mục EPUB quá lớn.");return new String(b,StandardCharsets.UTF_8);}
    }
    static void epubPages(File file,PageSink sink) throws Exception {
        try(ZipFile zip=new ZipFile(file)){
            if(zip.getEntry("META-INF/encryption.xml")!=null)throw new IOException("Bản thử chưa hỗ trợ EPUB có mã hóa/DRM.");
            Document container=Jsoup.parse(entry(zip,"META-INF/container.xml"),"",Parser.xmlParser());
            Element root=container.selectFirst("rootfile");if(root==null)throw new IOException("EPUB thiếu mục lục gốc.");String opfPath=root.attr("full-path");
            Document opf=Jsoup.parse(entry(zip,opfPath),"",Parser.xmlParser());String base=opfPath.contains("/")?opfPath.substring(0,opfPath.lastIndexOf('/')+1):"";
            HashMap<String,String> manifest=new HashMap<>();for(Element item:opf.select("manifest > item"))manifest.put(item.attr("id"),item.attr("href"));
            List<Element> spine=new ArrayList<>();for(Element item:opf.select("spine > itemref"))if(!"no".equals(item.attr("linear")))spine.add(item);
            for(int i=0;i<spine.size();i++) {
                String href=manifest.get(spine.get(i).attr("idref"));if(href==null)throw new IOException("EPUB thiếu nội dung spine.");href=href.split("#",2)[0];String path=java.net.URI.create(base+href).normalize().getPath();
                Document html=Jsoup.parse(entry(zip,path));html.select("script,style").remove();List<String> headings=new ArrayList<>();for(Element h:html.select("h1,h2"))headings.add(h.wholeText());for(Element block:html.select("p,h1,h2,h3,h4,li,blockquote,br"))block.after(new TextNode("\n"));sink.page(i,spine.size(),html.body().wholeText(),headings);
            }
        }
    }
    static String epub(File file) throws Exception {StringBuilder out=new StringBuilder();epubPages(file,(i,n,t,h)->{if(i>0)out.append("\n\n");out.append(t);});return out.toString();}
}
