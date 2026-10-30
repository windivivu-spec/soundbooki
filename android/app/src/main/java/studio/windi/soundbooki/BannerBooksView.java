package studio.windi.soundbooki;

import android.content.Context;
import android.graphics.*;
import android.view.View;

/** Five independently drawn vector jackets. Scales from the view's measured bounds, no bitmaps. */
final class BannerBooksView extends View {
    private final UiTheme theme;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path=new Path();
    BannerBooksView(Context context,UiTheme theme){
        super(context);this.theme=theme;setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
    }
    @Override protected void onMeasure(int widthSpec,int heightSpec){
        int width=MeasureSpec.getSize(widthSpec);
        int desired=Math.round(Math.min(theme.dp(230),width*.53f));
        setMeasuredDimension(resolveSize(width,widthSpec),resolveSize(desired,heightSpec));
    }
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);
        // Keep the complete fan inside an 80% area, including rotated page edges.
        float scale=Math.min(getWidth()*.8f/550f,getHeight()*.88f/280f);
        canvas.save();canvas.translate((getWidth()-520*scale)/2,(getHeight()-280*scale)/2);canvas.scale(scale,scale);
        fill(0x25a9c5e7);canvas.drawOval(4,248,534,277,paint);
        book(canvas,16,55,125,-13,0);
        book(canvas,395,55,125,13,4);
        book(canvas,110,48,125,-9,1);
        book(canvas,302,48,125,8,3);
        book(canvas,203,30,135,-5,2);
        canvas.save();canvas.rotate(-9,174,259);fill(0xff377bd0);canvas.drawRoundRect(151,235,207,291,15,15,paint);
        android.graphics.drawable.Drawable headphones=theme.icon("headphones",Color.WHITE,32);headphones.setBounds(163,247,195,279);headphones.draw(canvas);canvas.restore();
        canvas.save();canvas.rotate(12,466,259);fill(0xfff4f8ff);canvas.drawRoundRect(402,237,530,281,15,15,paint);
        float[] heights={14,28,20,32,15,26,12};fill(0xff8ab5e8);
        for(int i=0;i<heights.length;i++)canvas.drawRoundRect(423+i*12,259-heights[i]/2,427+i*12,259+heights[i]/2,2,2,paint);canvas.restore();canvas.restore();
    }
    private void book(Canvas c,float x,float y,float w,float rotation,int kind){
        float h=w*1.5f; // Published-book ratio 2:3; never stretch the cover or its lettering.
        c.save();c.translate(x,y);c.rotate(rotation,w/2,h*.9f);c.scale(w/120,w/120);
        fill(0xffb6cbe5);c.drawRoundRect(3,3,123,183,5,5,paint);fill(0xfff6f9ff);c.drawRoundRect(1,1,121,181,5,5,paint);
        int[] covers={0xfff3f1e9,0xff1d345e,0xff76a2cf,0xfff4dfd0,0xff1c2b52};
        fill(covers[kind]);c.drawRoundRect(0,0,120,180,5,5,paint);
        c.save();path.reset();path.addRoundRect(new RectF(0,0,120,180),5,5,Path.Direction.CW);c.clipPath(path);
        if(kind==0){
            polygon(c,0xffbdcfdb,0,125,22,105,40,117,60,96,82,113,103,99,120,112,120,180,0,180);
            polygon(c,0xff829fb6,0,147,25,127,46,140,68,115,91,135,120,123,120,180,0,180);
            polygon(c,0xffd7e5ed,51,138,70,138,48,180,14,180);
            polygon(c,0xff577e9b,0,152,19,146,37,154,15,180,0,180);
            title(c,new String[]{"TÂM LÝ HỌC","VỀ TIỀN"},0xff40596d,12.5f,40,true);
            stroke(0xff829b9e,1.4f);c.drawLine(60,102,60,90,paint);c.drawOval(52,84,60,94,paint);c.drawOval(60,81,68,91,paint);
        }else if(kind==1){
            polygon(c,0xff244b82,0,133,25,111,56,133,85,109,120,130,120,180,0,180);
            polygon(c,0xff183863,0,159,35,136,68,151,102,133,120,143,120,180,0,180);
            title(c,new String[]{"TƯ DUY","PHẢN BIỆN"},0xffeff4fc,13,40,true);
            stroke(0xffcedcf0,1.2f);c.drawCircle(60,96,8,paint);c.drawLine(56,105,64,105,paint);c.drawLine(57,109,63,109,paint);
        }else if(kind==2){
            wave(c,0xff83afd6,142,128);wave(c,0xff6798c6,159,140);wave(c,0xff5787b9,177,154);
            stroke(0xffe1ecf7,1);c.drawCircle(29,28,13,paint);
            for(int i=0;i<5;i++){float size=4+(2-Math.abs(2-i))*3;c.drawLine(21+i*4,28-size/2,21+i*4,28+size/2,paint);}
            fill(Color.WHITE);paint.setTypeface(theme.regular);paint.setTextSize(16);
            c.drawText("Một trang",14,70,paint);c.drawText("sách.",14,94,paint);c.drawText("Một thế giới.",14,118,paint);
        }else if(kind==3){
            fill(0xfffff3cb);c.drawCircle(60,112,12,paint);
            polygon(c,0xffd8b3a3,0,136,23,122,44,131,66,114,94,130,120,122,120,180,0,180);
            polygon(c,0xffbdacae,0,151,30,134,53,145,89,129,120,144,120,180,0,180);
            fill(0xffd7cfcd);c.drawRect(0,157,120,180,paint);stroke(0xfffff3cf,1.5f);
            for(int i=0;i<3;i++)c.drawLine(40-i*8,162+i*6,75+i*8,162+i*6,paint);
            title(c,new String[]{"THÓI QUEN","TỐI GIẢN"},0xff4b617a,13,40,true);
        }else{
            fill(0xffb2c9ee);c.drawCircle(17,74,.7f,paint);c.drawCircle(96,86,1,paint);c.drawCircle(32,149,.8f,paint);c.drawCircle(98,152,.6f,paint);
            fill(0xff7185bf);c.drawCircle(62,119,18,paint);c.save();c.rotate(-22,62,121);stroke(0xffa2a6d6,3);c.drawOval(27,114,97,128,paint);c.restore();
            polygon(c,0xff25375e,0,164,38,149,72,163,120,147,120,180,0,180);
            title(c,new String[]{"KHÁM PHÁ","VŨ TRỤ"},0xffafc9ec,13,40,true);
        }
        fill(0x22ffffff);c.drawRect(0,0,4,180,paint);stroke(0x99ffffff,1);c.drawLine(5,0,5,180,paint);c.restore();c.restore();
    }
    private void title(Canvas c,String[] lines,int color,float size,float y,boolean bold){
        fill(color);paint.setTypeface(bold?theme.bold:theme.regular);paint.setTextSize(size);
        float largest=0;for(String line:lines)largest=Math.max(largest,paint.measureText(line));
        if(largest>104)paint.setTextSize(size*104/largest);
        for(String line:lines){c.drawText(line,(120-paint.measureText(line))/2,y,paint);y+=size*1.5f;}
    }
    private void wave(Canvas c,int color,float y,float control){
        path.reset();path.moveTo(0,y);path.cubicTo(28,control,45,control,65,y);path.cubicTo(85,y+12,100,y-12,120,y-8);path.lineTo(120,180);path.lineTo(0,180);path.close();fill(color);c.drawPath(path,paint);
    }
    private void polygon(Canvas c,int color,float... points){path.reset();path.moveTo(points[0],points[1]);for(int i=2;i<points.length;i+=2)path.lineTo(points[i],points[i+1]);path.close();fill(color);c.drawPath(path,paint);}
    private void fill(int color){paint.setStyle(Paint.Style.FILL);paint.setColor(color);}
    private void stroke(int color,float width){paint.setStyle(Paint.Style.STROKE);paint.setColor(color);paint.setStrokeWidth(width);paint.setStrokeCap(Paint.Cap.ROUND);}
}
