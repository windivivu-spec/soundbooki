package studio.windi.soundbooki;

import ai.onnxruntime.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.util.*;
import java.util.function.BooleanSupplier;

/** Android/desktop shared inference: same four graphs, CFG=3, 16 Euler steps. */
public final class NanoEngine implements AutoCloseable {
    public static final int SAMPLE_RATE=24000;
    public static final String REVISION="nano-aba295eb-java-cfg3-16-v2-real";
    private final OrtEnvironment env=OrtEnvironment.getEnvironment();
    private OrtSession text,duration,vector,decoder;
    private final JSONObject config,voices;
    private final Phonemizer phonemizer;
    private OnnxTensor nullContext,nullMask,nullSpeaker,nullStyle;
    private final int bos,eos,pad;
    private final double fps;
    public final double loadSeconds;

    public NanoEngine(File directory,int threads) throws Exception {
        long begin=System.nanoTime();
        File encoder=new File(directory,"text_encoder.onnx");
        if(!encoder.exists()) throw new IOException("Bản cài chưa có model giọng đọc. Hãy dùng APK Lite đầy đủ.");
        env.setTelemetry(false);
        config=read(new File(directory,"config.json"));voices=read(new File(directory,"voices.json"));
        bos=config.getInt("bos_id");eos=config.getInt("eos_id");pad=config.getInt("pad_id");fps=config.getDouble("flow_fps");
        phonemizer=new Phonemizer(new File(directory,"sea_g2p.bin").getAbsolutePath());
        try(OrtSession.SessionOptions options=new OrtSession.SessionOptions()) {
            options.setIntraOpNumThreads(Math.max(1,Math.min(4,threads)));options.setInterOpNumThreads(1);
            options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
            options.addConfigEntry("session.intra_op.allow_spinning","0");
            try {
                text=env.createSession(new File(directory,"text_encoder.onnx").getPath(),options);
                duration=env.createSession(new File(directory,"duration_predictor.onnx").getPath(),options);
                vector=env.createSession(new File(directory,"vector_estimator.onnx").getPath(),options);
                decoder=env.createSession(new File(directory,"codec_decoder.onnx").getPath(),options);
                JSONObject constants=read(new File(directory,"constants.json"));
                nullSpeaker=floats(flat(constants.getJSONArray("null_spk")),1,192);
                nullStyle=floats(flat(constants.getJSONArray("null_style")),1,50,256);
                nullMask=OnnxTensor.createTensor(env,new boolean[][]{{bos!=pad,eos!=pad}});
                try(OnnxTensor ids=OnnxTensor.createTensor(env,new long[][]{{bos,eos}});
                    OrtSession.Result result=text.run(Map.of("ids",ids,"style",nullStyle))) {
                    OnnxTensor out=(OnnxTensor)result.get(0);
                    nullContext=floats(values(out),out.getInfo().getShape());
                }
            } catch(Exception error) { close();throw error; }
        }
        loadSeconds=(System.nanoTime()-begin)/1e9;
    }
    public static JSONObject read(File f) throws Exception { return new JSONObject(new String(Files.readAllBytes(f.toPath()),java.nio.charset.StandardCharsets.UTF_8)); }
    static float[] flat(JSONArray a) throws JSONException {
        ArrayList<Float> out=new ArrayList<>();flatten(a,out);float[] result=new float[out.size()];for(int i=0;i<result.length;i++)result[i]=out.get(i);return result;
    }
    private static void flatten(JSONArray array,List<Float> out) throws JSONException {
        for(int i=0;i<array.length();i++) { Object v=array.get(i);if(v instanceof JSONArray)flatten((JSONArray)v,out);else out.add(((Number)v).floatValue()); }
    }
    private OnnxTensor floats(float[] v,long... shape) throws OrtException { return OnnxTensor.createTensor(env,FloatBuffer.wrap(v),shape); }
    private static float[] values(OnnxTensor t) { FloatBuffer b=t.getFloatBuffer();float[] out=new float[b.remaining()];b.get(out);return out; }
    public List<String> voiceNames() throws JSONException { ArrayList<String> names=new ArrayList<>();voices.getJSONObject("presets").keys().forEachRemaining(names::add);names.sort(String::compareTo);names.remove("Đức Trí");names.add(0,"Đức Trí");return names; }
    private static void active(BooleanSupplier cancel) throws InterruptedException { if(cancel.getAsBoolean()||Thread.currentThread().isInterrupted())throw new InterruptedException("Đã dừng; audio hoàn tất được giữ lại."); }
    public synchronized float[] synthesize(String original,String voice,BooleanSupplier cancelled) throws Exception {
        active(cancelled);
        // Split expanded/number-heavy phonemes again rather than clipping at the 15 s training limit.
        String phones=phonemizer.phones(original);
        if(phones.codePointCount(0,phones.length())>330 && original.codePointCount(0,original.length())>8) {
            int middle=original.length()/2;
            int split=original.lastIndexOf(' ',middle);if(split<original.length()/4)split=original.indexOf(' ',middle);
            if(split>0&&split<original.length()-1) {
                float[] a=synthesize(original.substring(0,split),voice,cancelled),b=synthesize(original.substring(split),voice,cancelled);
                float[] both=Arrays.copyOf(a,a.length+b.length+2400);System.arraycopy(b,0,both,a.length+2400,b.length);return both;
            }
        }
        JSONObject v=voices.getJSONObject("presets").getJSONObject(voice),vocab=config.getJSONObject("vocab");
        JSONObject tags=config.getJSONObject("emotion_tags");for(Iterator<String> it=tags.keys();it.hasNext();){String key=it.next();phones=phones.replace(key,tags.getString(key));}
        ArrayList<Long> tokenList=new ArrayList<>();tokenList.add((long)bos);
        for(int cp:phones.codePoints().toArray()){String c=new String(Character.toChars(cp));if(vocab.has(c))tokenList.add(vocab.getLong(c));}
        tokenList.add((long)eos);long[][] ids=new long[1][tokenList.size()];boolean[][] mask=new boolean[1][tokenList.size()];
        for(int i=0;i<tokenList.size();i++){ids[0][i]=tokenList.get(i);mask[0][i]=ids[0][i]!=pad;}
        try(OnnxTensor tokens=OnnxTensor.createTensor(env,ids);
            OnnxTensor ctxMask=OnnxTensor.createTensor(env,mask);
            OnnxTensor spk=floats(flat(v.getJSONArray("speaker_emb")),1,192);
            OnnxTensor style=floats(flat(v.getJSONArray("style")),1,50,256);
            OrtSession.Result encoded=text.run(Map.of("ids",tokens,"style",style))) {
            OnnxTensor ctx=(OnnxTensor)encoded.get(0);
            int frames;
            try(OrtSession.Result predicted=duration.run(Map.of("ctx",ctx,"ctx_mask",ctxMask,"spk",spk))) {
                double log=values((OnnxTensor)predicted.get(0))[0];
                frames=Math.max(2,(int)Math.rint(Math.min(Math.exp(log),15.0)*fps));
            }
            float[] x=new float[144*frames];Random noise=new Random(42);for(int i=0;i<x.length;i++)x[i]=(float)noise.nextGaussian();
            for(int step=0;step<16;step++) {
                active(cancelled);
                try(OnnxTensor xt=floats(x,1,144,frames);OnnxTensor time=floats(new float[]{step/16f},1);
                    OrtSession.Result conditional=vector.run(Map.of("x",xt,"t",time,"ctx",ctx,"ctx_mask",ctxMask,"spk",spk,"style",style));
                    OrtSession.Result unconditional=vector.run(Map.of("x",xt,"t",time,"ctx",nullContext,"ctx_mask",nullMask,"spk",nullSpeaker,"style",nullStyle))) {
                    float[] velocity=values((OnnxTensor)conditional.get(0)),uncond=values((OnnxTensor)unconditional.get(0));
                    for(int j=0;j<x.length;j++)x[j]+=(uncond[j]+3f*(velocity[j]-uncond[j]))/16f;
                }
            }
            active(cancelled);
            try(OnnxTensor latent=floats(x,1,144,frames);OrtSession.Result decoded=decoder.run(Map.of("x",latent))) {
                return finish(values((OnnxTensor)decoded.get(0)));
            }
        }
    }
    static float[] finish(float[] raw) throws IOException {
        float peak=0;for(float v:raw){if(!Float.isFinite(v))throw new IOException("Audio chưa hợp lệ.");peak=Math.max(peak,Math.abs(v));}
        if(peak<0.0001f)throw new IOException("Đoạn này chưa tạo được tiếng. Hãy kiểm tra chữ.");
        int start=0,end=raw.length;float threshold=(float)Math.pow(10,-42.0/20);
        while(start<end&&Math.abs(raw[start])<threshold)start++;
        while(end>start&&Math.abs(raw[end-1])<threshold)end--;
        start=Math.max(0,start-960);end=Math.min(raw.length,end+960);
        float[] out=Arrays.copyOfRange(raw,start,end);int fade=Math.min(240,out.length/2);
        for(int i=0;i<out.length;i++)out[i]=Math.max(-1,Math.min(1,out[i]));
        for(int i=0;i<fade;i++){float ramp=(float)(.5-.5*Math.cos(Math.PI*i/Math.max(1,fade-1)));out[i]*=ramp;out[out.length-1-i]*=ramp;}
        return out;
    }
    @Override public synchronized void close() {
        for(AutoCloseable c:new AutoCloseable[]{nullContext,nullMask,nullSpeaker,nullStyle,text,duration,vector,decoder,phonemizer})if(c!=null)try{c.close();}catch(Exception ignored){}
    }
}
