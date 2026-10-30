package studio.windi.soundbooki;
import android.content.*;
import android.provider.Settings;
import android.security.keystore.*;
import android.util.Base64;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import java.security.*;
import java.nio.charset.StandardCharsets;

/** Per-device code and a separate random bearer, encrypted by Android Keystore. */
final class CloudIdentity {
    static final String ALIAS="soundbooki.book-device.v1";
    static synchronized String credential(Context c,String base) throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(!store.containsAlias(ALIAS)){
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());generator.generateKey();
        }
        SecretKey key=(SecretKey)store.getKey(ALIAS,null);SharedPreferences prefs=c.getSharedPreferences("cloud-secrets",Context.MODE_PRIVATE);String name=BookStore.hash(base),saved=prefs.getString(name,null);Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        if(saved!=null){String[] pair=saved.split(":");cipher.init(Cipher.DECRYPT_MODE,key,new GCMParameterSpec(128,Base64.decode(pair[0],Base64.NO_WRAP)));return new String(cipher.doFinal(Base64.decode(pair[1],Base64.NO_WRAP)),StandardCharsets.UTF_8);}
        byte[] random=new byte[32];new SecureRandom().nextBytes(random);String token="wsn_book_"+BookStore.hex(random);cipher.init(Cipher.ENCRYPT_MODE,key);
        String encrypted=Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)+":"+Base64.encodeToString(cipher.doFinal(token.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP);
        if(!prefs.edit().putString(name,encrypted).commit())throw new java.io.IOException("Chưa lưu được khóa thiết bị.");return token;
    }
    static String code(Context c){String android=Settings.Secure.getString(c.getContentResolver(),Settings.Secure.ANDROID_ID);if(android==null)throw new IllegalStateException("Chưa nhận được mã thiết bị.");return "SN"+BookStore.hash(c.getPackageName()+":"+android).substring(0,12).toUpperCase(java.util.Locale.ROOT);}
}
