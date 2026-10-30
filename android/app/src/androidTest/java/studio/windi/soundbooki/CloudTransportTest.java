package studio.windi.soundbooki;
import android.content.Context;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.*;
import org.junit.runner.RunWith;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import static org.junit.Assert.*;

/** Transport fixture only: no production gateway, payment or GPU is contacted. */
@RunWith(AndroidJUnit4.class)
public class CloudTransportTest {
 @org.junit.Before public void isolateLibrary(){android.content.Context c=androidx.test.platform.app.InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore.fixtureRoot=new java.io.File(c.getFilesDir(),".qa/cloud");BookStore.fixtureRoot.mkdirs();}
 @org.junit.After public void releaseLibrary(){BookStore.fixtureRoot=null;}
 static Queue<byte[]> replies=new ArrayDeque<>();static List<FakeConnection> requests=new ArrayList<>();
 @BeforeClass public static void fixture() {
  URL.setURLStreamHandlerFactory(protocol->protocol.equals("https")?new URLStreamHandler(){protected URLConnection openConnection(URL url)throws IOException {if(!url.getHost().equals("example.invalid"))throw new IOException("Fixture blocks all external hosts");FakeConnection c=new FakeConnection(url);requests.add(c);return c;}}:null);
 }
 static class FakeConnection extends HttpURLConnection {
  ByteArrayOutputStream sent=new ByteArrayOutputStream();FakeConnection(URL url){super(url);}
  public void disconnect(){}public boolean usingProxy(){return false;}public void connect(){}
  public OutputStream getOutputStream(){return sent;}public int getResponseCode(){return 200;}
  public InputStream getInputStream()throws IOException {byte[] reply=replies.poll();if(reply==null)throw new IOException("No fixture response");return new ByteArrayInputStream(reply);}
 }
 @Test public void quoteReceiveAndFailClosed() throws Exception {
  Context c=InstrumentationRegistry.getInstrumentation().getTargetContext();BookStore store=new BookStore(c);
  JSONObject book=new JSONObject().put("id",BookStore.id()).put("title","Cloud fixture").put("text","Đây là bản chữ nguyên văn, gồm số 42.");
  JSONObject snapshot=CloudClient.snapshot(book,CloudClient.VOICE_IDS[0],false);String sid=snapshot.getJSONArray("segments").getJSONObject(0).getString("id");String oid=UUID.randomUUID().toString(),key=BookStore.id();
  JSONObject order=new JSONObject().put("id",oid).put("kind","book").put("state","awaiting_payment").put("amountVND",25000).put("paymentCode","SB"+"A".repeat(32));JSONObject bank=new JSONObject().put("bin","970423").put("account","1234567890");
  replies.add(new JSONObject().put("order",order).put("bank",bank).toString().getBytes(StandardCharsets.UTF_8));CloudClient client=new CloudClient(c,"https://example.invalid/functions/v1/wsn-books");
  JSONObject result=client.post("quote",new JSONObject().put("snapshot",snapshot).put("requestKey",key).put("consent",true));CloudClient.validateOrder(result.getJSONObject("order"));assertEquals(25000,result.getJSONObject("order").getInt("amountVND"));
  FakeConnection sent=requests.get(requests.size()-1);assertFalse(sent.getInstanceFollowRedirects());assertEquals("POST",sent.getRequestMethod());assertTrue(sent.getRequestProperty("Authorization").matches("Bearer wsn_book_[a-f0-9]{64}"));JSONObject packet=new JSONObject(sent.sent.toString("UTF-8"));assertEquals(key,packet.getString("requestKey"));assertEquals("Đây là bản chữ nguyên văn, gồm số 42.",packet.getJSONObject("snapshot").getJSONArray("segments").getJSONObject(0).getString("text"));
  File wave=new File(c.getFilesDir(),".qa/cloud-fixture.wav");float[] samples=new float[2400];for(int i=0;i<samples.length;i++)samples[i]=(float)Math.sin(i*.2)*.2f;AudioFiles.wav(wave,samples);byte[] bytes=Files.readAllBytes(wave.toPath());String hash=BookStore.hash(bytes);
  JSONObject entry=new JSONObject().put("order",order).put("snapshot",snapshot);JSONObject item=new JSONObject().put("id",sid).put("sha256",hash).put("url","https://example.invalid/storage/v1/object/sign/wsn-book-audio/"+oid+"/"+sid+".wav?token=fixture");
  JSONObject response=new JSONObject().put("order",new JSONObject(order.toString()).put("state","ready")).put("audio",new JSONArray().put(item));
  int before=requests.size();try{client.receive(store,entry,new JSONObject(response.toString()).put("order",order),()->true);fail("Unpaid order downloaded audio");}catch(IOException expected){}assertEquals(before,requests.size());
  JSONObject alien=new JSONObject(response.toString());alien.getJSONArray("audio").getJSONObject(0).put("url","https://other.invalid/storage/v1/object/sign/wsn-book-audio/"+oid+"/"+sid+".wav");try{client.receive(store,entry,alien,()->true);fail("External origin allowed");}catch(IOException expected){}assertEquals(before,requests.size());
  replies.add(Arrays.copyOf(bytes,bytes.length-10));try{client.receive(store,entry,response,()->true);fail("Truncated WAV accepted");}catch(IOException expected){}assertFalse(store.cloudAudio(oid,sid).exists());
  replies.add(bytes);assertEquals(1,client.receive(store,entry,response,()->true).length());assertTrue(AudioFiles.valid(store.cloudAudio(oid,sid)));assertArrayEquals(bytes,Files.readAllBytes(store.cloudAudio(oid,sid).toPath()));
  assertNull(requests.get(requests.size()-1).getRequestProperty("Authorization")); // signed storage never gets device bearer
  try{client.receive(store,entry,response,()->false);fail("Download continued after popup close");}catch(InterruptedException expected){}
 }
}
