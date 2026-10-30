package studio.windi.soundbooki;
import android.graphics.Bitmap;
import com.google.zxing.*;
import com.google.zxing.qrcode.QRCodeWriter;
import com.google.zxing.common.BitMatrix;
import org.json.JSONObject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.*;

final class PaymentQR {
    static String field(String tag,String value){return tag+String.format(Locale.ROOT,"%02d",value.getBytes(StandardCharsets.UTF_8).length)+value;}
    static String payload(JSONObject bank,JSONObject order) throws Exception {
        String bin=bank.getString("bin"),account=bank.getString("account"),code=order.getString("paymentCode");long amount=order.getLong("amountVND");
        if(!bin.matches("[0-9]{6}")||!account.matches("[0-9]{6,32}")||!code.matches("SB[A-F0-9]{32}")||amount<10000||amount>1000000)throw new IOException("Đơn thiếu thông tin QR hợp lệ.");
        String beneficiary=field("00",bin)+field("01",account),merchant=field("00","A000000727")+field("01",beneficiary)+field("02","QRIBFTTA");
        String raw=field("00","01")+field("01","12")+field("38",merchant)+field("53","704")+field("54",String.valueOf(amount))+field("58","VN")+field("62",field("08",code))+"6304";
        int crc=0xffff;for(byte b:raw.getBytes(StandardCharsets.UTF_8)){crc^=(b&255)<<8;for(int i=0;i<8;i++)crc=((crc&0x8000)!=0?(crc<<1)^0x1021:crc<<1)&0xffff;}return raw+String.format(Locale.ROOT,"%04X",crc);
    }
    static Bitmap image(JSONObject bank,JSONObject order) throws Exception {
        BitMatrix m=new QRCodeWriter().encode(payload(bank,order),BarcodeFormat.QR_CODE,660,660,Map.of(EncodeHintType.MARGIN,4,EncodeHintType.ERROR_CORRECTION,com.google.zxing.qrcode.decoder.ErrorCorrectionLevel.M));
        int[] colors=new int[m.getWidth()*m.getHeight()];for(int y=0;y<m.getHeight();y++)for(int x=0;x<m.getWidth();x++)colors[y*m.getWidth()+x]=m.get(x,y)?0xff000000:0xffffffff;
        return Bitmap.createBitmap(colors,m.getWidth(),m.getHeight(),Bitmap.Config.ARGB_8888);
    }
}
