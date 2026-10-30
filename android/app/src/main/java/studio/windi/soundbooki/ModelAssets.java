package studio.windi.soundbooki;
import android.content.Context;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.function.Consumer;

public final class ModelAssets {
    public static File prepare(Context c,Consumer<String> status) throws Exception {
        File directory=new File(c.getFilesDir(),"nano");directory.mkdirs();JSONObject manifest;
        try(InputStream in=c.getAssets().open("nano/manifest.json")){manifest=new JSONObject(new String(in.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8));}
        JSONArray list=manifest.getJSONArray("files");
        for(int i=0;i<list.length();i++){
            JSONObject entry=list.getJSONObject(i);File target=new File(directory,entry.getString("file"));
            File stamp=new File(directory,entry.getString("file")+".sha256");
            if(target.isFile()&&target.length()==entry.getLong("size")&&stamp.isFile()&&new String(Files.readAllBytes(stamp.toPath()),java.nio.charset.StandardCharsets.UTF_8).equals(entry.getString("sha256")))continue;
            status.accept("Chuẩn bị giọng lần đầu · "+(i+1)+" / "+list.length());File partial=new File(target.getPath()+".partial");MessageDigest digest=MessageDigest.getInstance("SHA-256");
            try(InputStream in=c.getAssets().open("nano/"+entry.getString("file"));FileOutputStream out=new FileOutputStream(partial)){
                byte[] buffer=new byte[262144];int n;while((n=in.read(buffer))!=-1){out.write(buffer,0,n);digest.update(buffer,0,n);}out.getFD().sync();
            }catch(FileNotFoundException notFound){
                // Model file temporarily excluded for fast UI testing
                partial.delete();
                continue;
            }
            if(partial.length()!=entry.getLong("size")||!BookStore.hex(digest.digest()).equals(entry.getString("sha256"))){partial.delete();throw new IOException("Model chưa sao chép đủ; mở lại app để tiếp tục.");}
            Files.move(partial.toPath(),target.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
            AudioFiles.atomic(stamp,entry.getString("sha256").getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
        return directory;
    }
}
