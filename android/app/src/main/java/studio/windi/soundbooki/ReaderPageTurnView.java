package studio.windi.soundbooki;

import android.animation.*;
import android.app.ActivityManager;
import android.content.Context;
import android.graphics.*;
import android.view.View;
import android.view.animation.PathInterpolator;

/** Only two viewport snapshots, never a bitmap for every page. No layout during frames. */
final class ReaderPageTurnView extends View {
    private Bitmap from,to;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
    private final Path front=new Path(),back=new Path(),shadowPath=new Path();
    private final RectF destination=new RectF();
    private final Matrix mirror=new Matrix();
    private ValueAnimator animator;
    private float progress;
    private int direction=1,paperColor;
    private String mode="curl";
    ReaderPageTurnView(Context context){super(context);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);setVisibility(GONE);setClickable(false);}
    static Bitmap snapshot(View view,int background){
        int w=view.getWidth(),h=view.getHeight();if(w<=0||h<=0)return null;
        ActivityManager manager=(ActivityManager)view.getContext().getSystemService(Context.ACTIVITY_SERVICE);
        int maxPixels=manager!=null&&manager.isLowRamDevice()?1_000_000:2_500_000;
        float scale=Math.min(1f,(float)Math.sqrt(maxPixels/(double)((long)w*h)));
        Bitmap bitmap=null;
        try{bitmap=Bitmap.createBitmap(Math.max(1,(int)(w*scale)),Math.max(1,(int)(h*scale)),Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(bitmap);canvas.drawColor(background);canvas.scale(scale,scale);view.measure(MeasureSpec.makeMeasureSpec(w,MeasureSpec.EXACTLY),MeasureSpec.makeMeasureSpec(h,MeasureSpec.EXACTLY));view.layout(view.getLeft(),view.getTop(),view.getRight(),view.getBottom());view.draw(canvas);return bitmap;}catch(OutOfMemoryError ignored){if(bitmap!=null)bitmap.recycle();return null;}
    }
    boolean prepare(Bitmap oldPage,Bitmap newPage,int dir,int paper,String style){
        clear();if(oldPage==null||newPage==null){if(oldPage!=null)oldPage.recycle();if(newPage!=null)newPage.recycle();return false;}
        from=oldPage;to=newPage;direction=dir<0?-1:1;paperColor=paper;mode=style;progress=0;setVisibility(VISIBLE);invalidate();return true;
    }
    void progress(float value){progress=Math.max(0,Math.min(1,value));invalidate();}
    boolean hasSnapshots(){return from!=null&&to!=null;}
    void settle(boolean complete,Runnable done){
        if(!hasSnapshots()){done.run();return;}
        animator=ValueAnimator.ofFloat(progress,complete?1:0);animator.setDuration(Math.max(80,(long)(260*Math.abs((complete?1:0)-progress))));animator.setInterpolator(new PathInterpolator(.2f,.75f,.2f,1));
        animator.addUpdateListener(a->progress((float)a.getAnimatedValue()));animator.addListener(new AnimatorListenerAdapter(){@Override public void onAnimationEnd(Animator a){animator=null;release();done.run();}});animator.start();
    }
    void clear(){if(animator!=null){animator.removeAllListeners();animator.cancel();animator=null;}release();}
    private void release(){if(from!=null){from.recycle();from=null;}if(to!=null){to.recycle();to=null;}setVisibility(GONE);invalidate();}
    @Override protected void onDetachedFromWindow(){clear();super.onDetachedFromWindow();}
    @Override protected void onDraw(Canvas c){
        super.onDraw(c);if(!hasSnapshots())return;float w=getWidth(),h=getHeight();destination.set(0,0,w,h);paint.setShader(null);paint.setAlpha(255);c.drawBitmap(to,null,destination,paint);
        if(mode.equals("slide")){c.save();c.translate(-direction*progress*w,0);c.drawBitmap(from,null,destination,paint);c.restore();return;}
        if(progress<=0){c.drawBitmap(from,null,destination,paint);return;}if(progress>=1)return;
        float edge=w*(1-progress),fold=(float)(Math.sin(Math.PI*progress)*Math.min(w*.22f,160*getResources().getDisplayMetrics().density));
        front.reset();front.moveTo(0,0);front.lineTo(edge,0);front.quadTo(edge+fold*.16f,h*.5f,edge,h);front.lineTo(0,h);front.close();
        back.reset();back.moveTo(edge,0);back.cubicTo(edge+fold*.45f,h*.12f,edge+fold,h*.30f,edge+fold,h*.5f);back.cubicTo(edge+fold,h*.70f,edge+fold*.45f,h*.88f,edge,h);back.quadTo(edge+fold*.16f,h*.5f,edge,0);back.close();
        float actualEdge=edge,actualTip=edge+fold;
        if(direction<0){mirror.setScale(-1,1);mirror.postTranslate(w,0);front.transform(mirror);back.transform(mirror);actualEdge=w-edge;actualTip=w-edge-fold;}
        // Shadow falls on the revealed page, not on the document text layer.
        float shadow=Math.max(8,fold*.14f),outer=actualTip+direction*shadow;
        shadowPath.set(back);shadowPath.offset(direction*shadow*.55f,0);paint.setShader(new LinearGradient(actualEdge,0,outer,0,0x40000000,0x00000000,Shader.TileMode.CLAMP));c.drawPath(shadowPath,paint);paint.setShader(null);
        c.save();c.clipPath(front);c.drawBitmap(from,null,destination,paint);c.restore();
        int dim=blend(paperColor,Color.BLACK,.17f),light=blend(paperColor,Color.WHITE,.10f);
        paint.setShader(new LinearGradient(actualEdge,0,actualTip,0,new int[]{dim,light,paperColor},new float[]{0,.45f,1},Shader.TileMode.CLAMP));c.drawPath(back,paint);paint.setShader(null);
    }
    private static int blend(int a,int b,float amount){return Color.rgb((int)(Color.red(a)*(1-amount)+Color.red(b)*amount),(int)(Color.green(a)*(1-amount)+Color.green(b)*amount),(int)(Color.blue(a)*(1-amount)+Color.blue(b)*amount));}
}
