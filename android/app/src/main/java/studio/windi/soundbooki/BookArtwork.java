package studio.windi.soundbooki;

import android.content.Context;
import android.graphics.*;
import android.graphics.pdf.PdfRenderer;
import android.os.*;
import android.util.LruCache;
import android.view.View;
import org.json.*;
import org.jsoup.Jsoup;
import org.jsoup.nodes.*;
import org.jsoup.parser.Parser;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.*;

/** Covers come from the imported file. Text-only books use a typographic jacket. */
final class BookArtwork extends View {
    private static final ExecutorService worker=Executors.newSingleThreadExecutor();
    private static final LruCache<String,Bitmap> cache=new LruCache<>(12);
    private final UiTheme theme;private final BookStore store;private JSONObject book;private Bitmap bitmap;private String key="";private int revision=0;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
    BookArtwork(Context c,UiTheme t,BookStore s,JSONObject b){super(c);theme=t;store=s;setBook(b);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
    void setBook(JSONObject value){book=value;bitmap=null;int token=++revision;key=store.root().getAbsolutePath()+"/"+value.optString("id");Bitmap old=cache.get(key);if(old!=null){bitmap=old;invalidate();return;}invalidate();String pathKey=key;JSONObject source=value;
        worker.submit(()->{Bitmap result=null;try{result=cover(store,source);}catch(Exception ignored){}if(result!=null){cache.put(pathKey,result);Bitmap done=result;post(()->{if(token==revision){bitmap=done;invalidate();}});}});
    }
    static Bitmap cover(BookStore store,JSONObject b)throws Exception {
        File dir=new File(store.root(),b.getString("id"));File cached=new File(dir,"cover-v1.jpg");if(cached.isFile())return BitmapFactory.decodeFile(cached.getPath());
        File source=store.sourceFile(b.getString("id"));if(!source.isFile())return null;Bitmap result=null;
        if("pdf".equals(b.optString("sourceFormat"))){try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(source,ParcelFileDescriptor.MODE_READ_ONLY);PdfRenderer renderer=new PdfRenderer(fd);PdfRenderer.Page page=renderer.openPage(0)){int width=360,height=Math.max(1,Math.min(640,width*page.getHeight()/page.getWidth()));result=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);result.eraseColor(Color.WHITE);page.render(result,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);}}
        else if("epub".equals(b.optString("sourceFormat"))){try(ZipFile zip=new ZipFile(source)){
            Document container=Jsoup.parse(BookImporter.entry(zip,"META-INF/container.xml"),"",Parser.xmlParser());Element root=container.selectFirst("rootfile");if(root==null)return null;String opf=root.attr("full-path"),base=opf.contains("/")?opf.substring(0,opf.lastIndexOf('/')+1):"";
            Document meta=Jsoup.parse(BookImporter.entry(zip,opf),"",Parser.xmlParser());Element cover=meta.selectFirst("meta[name=cover]");String id=cover==null?"":cover.attr("content"),href="";
            for(Element item:meta.select("manifest > item"))if(item.attr("properties").contains("cover-image")||(!id.isEmpty()&&id.equals(item.attr("id")))){href=item.attr("href");break;}
            if(!href.isEmpty()){String path=java.net.URI.create(base+href).normalize().getPath();ZipEntry entry=zip.getEntry(path);if(entry!=null&&entry.getSize()<=5_000_000){try(InputStream in=zip.getInputStream(entry)){byte[] data=in.readNBytes(5_000_001);if(data.length<=5_000_000){BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(data,0,data.length,bounds);BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=Math.max(1,Math.max(bounds.outWidth,bounds.outHeight)/640);result=BitmapFactory.decodeByteArray(data,0,data.length,options);}}}}
        }}
        if(result!=null){ByteArrayOutputStream bytes=new ByteArrayOutputStream();result.compress(Bitmap.CompressFormat.JPEG,88,bytes);AudioFiles.atomic(cached,bytes.toByteArray());}return result;
    }
    @Override protected void onDraw(Canvas canvas){super.onDraw(canvas);float w=getWidth(),h=getHeight(),r=theme.dp(12);Path clip=new Path();clip.addRoundRect(new RectF(0,0,w,h),r,r,Path.Direction.CW);canvas.save();canvas.clipPath(clip);
        if(bitmap!=null){float scale=Math.max(w/bitmap.getWidth(),h/bitmap.getHeight());float bw=bitmap.getWidth()*scale,bh=bitmap.getHeight()*scale;canvas.drawBitmap(bitmap,null,new RectF((w-bw)/2,(h-bh)/2,(w+bw)/2,(h+bh)/2),paint);}
        else {int[] colors=theme.dark?new int[]{0xff344d70,0xff4b5054,0xff4c4668,0xff3b5a58}:new int[]{0xffd8e5f3,0xffe9dfce,0xffe1dcee,0xffd3e6df};int color=colors[Math.floorMod(book.optString("title").hashCode(),colors.length)];paint.setColor(color);canvas.drawRect(0,0,w,h,paint);paint.setColor(theme.dark?0xffdbe8fc:0xff2c4662);paint.setAlpha(24);canvas.drawCircle(w*.96f,h*.86f,w*.8f,paint);paint.setAlpha(255);paint.setStrokeWidth(theme.dp(1));canvas.drawLine(w*.14f,h*.16f,w*.4f,h*.16f,paint);
            paint.setTypeface(theme.serif);paint.setTextSize(Math.max(theme.dp(6),w*.13f));paint.setColor(theme.dark?0xfff0f4fb:0xff243f59);String[] words=book.optString("title","Sách của tôi").replace('-', ' ').split("\\s+");String line="";float y=h*.3f;int count=0;
            for(String word:words){String next=line.isEmpty()?word:line+" "+word;if(paint.measureText(next)>w*.74f&&!line.isEmpty()){canvas.drawText(line,w*.13f,y,paint);y+=paint.getTextSize()*1.3f;line=word;if(++count>=4)break;}else line=next;}if(count<4)canvas.drawText(line,w*.13f,y,paint);
            paint.setTypeface(theme.bold);paint.setTextSize(w*.065f);paint.setAlpha(170);canvas.drawText("SOUNDBOOKI",w*.13f,h*.88f,paint);paint.setAlpha(255);
        }
        paint.setColor(theme.dark?0x30ffffff:0x18ffffff);canvas.drawRect(0,0,theme.dp(5),h,paint);paint.setColor(theme.edge);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(theme.dp(1));canvas.drawRoundRect(new RectF(.5f,.5f,w-.5f,h-.5f),r,r,paint);paint.setStyle(Paint.Style.FILL);canvas.restore();
    }
}
