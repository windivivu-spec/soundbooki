package studio.windi.soundbooki;

import android.animation.ValueAnimator;
import android.content.Context;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.*;
import android.graphics.drawable.*;
import android.view.View;
import android.widget.LinearLayout;

/** Shared Mac-synchronized design tokens, local typography, vector icons and glassmorphic surfaces. */
public final class UiTheme {
    public final boolean dark;
    public final int canvas, surface, glass, card, ink, muted, quiet, accent, accentInk;
    public final int primaryTop, primaryBottom, blueWash, warmWash, edge, line;
    public final int tourSurface, tourArt, tourPaper, tourBlue, tourBlueInk;
    public final int launchBg, launchInk, launchMuted, launchRule;
    public final Typeface display, regular, bold, serif;
    private final float density;

    public UiTheme(Context c) {
        density = c.getResources().getDisplayMetrics().density;
        dark = (c.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        canvas = Color.parseColor(dark ? "#151C28" : "#F3F6FB");
        surface = Color.parseColor(dark ? "#202A3A" : "#FFFFFF");
        glass = Color.parseColor(dark ? "#263347" : "#F8FAFE");
        card = Color.parseColor(dark ? "#1C2534" : "#FAFBFD");
        ink = Color.parseColor(dark ? "#EDF1F8" : "#1E2634");
        muted = Color.parseColor(dark ? "#A8B3C5" : "#566173");
        quiet = Color.parseColor(dark ? "#8E9CB2" : "#687385");
        accent = Color.parseColor(dark ? "#7BB0FF" : "#2563C9");
        accentInk = Color.parseColor(dark ? "#122B50" : "#FFFFFF");
        primaryTop = Color.parseColor(dark ? "#5895F0" : "#508CE9");
        primaryBottom = Color.parseColor(dark ? "#3573D2" : "#316ECE");
        blueWash = Color.parseColor(dark ? "#233652" : "#E5EFFD");
        warmWash = Color.parseColor(dark ? "#2D292C" : "#F7EDE2");
        edge = Color.parseColor(dark ? "#384B67" : "#D8E4F5");
        line = Color.parseColor(dark ? "#2F4058" : "#DCE6F4");

        tourSurface = Color.parseColor(dark ? "#202A39" : "#F7F9FD");
        tourArt = Color.parseColor(dark ? "#26364D" : "#EAF0FA");
        tourPaper = Color.parseColor(dark ? "#303E52" : "#FFFFFF");
        tourBlue = Color.parseColor(dark ? "#B7D3FC" : "#235DA8");
        tourBlueInk = Color.parseColor(dark ? "#16345C" : "#FFFFFF");

        launchBg = Color.parseColor(dark ? "#263852" : "#E6EFFC");
        launchInk = Color.parseColor(dark ? "#DFECFF" : "#174B91");
        launchMuted = Color.parseColor(dark ? "#AAC0E0" : "#405E86");
        launchRule = Color.parseColor(dark ? "#3E587D" : "#B7CCEB");

        display = loadFont(c, "fonts/SFProRounded-Black.otf", Typeface.DEFAULT_BOLD);
        // Avo keeps long Vietnamese copy and preview excerpts readable at mobile sizes.
        regular = loadFont(c, "fonts/SVN-Avo.ttf", Typeface.DEFAULT);
        bold = loadFont(c, "fonts/SVN-Nexa-Bold.ttf", Typeface.DEFAULT_BOLD);
        serif = loadFont(c, "fonts/SVN-Georgia.otf", Typeface.SERIF);
    }

    private static Typeface loadFont(Context c, String path, Typeface fallback) {
        try {
            return Typeface.createFromAsset(c.getAssets(), path);
        } catch (Exception ignored) {
            return fallback;
        }
    }

    public int dp(float v) {
        return Math.round(v * density);
    }

    public static boolean reducedMotion() {
        return !ValueAnimator.areAnimatorsEnabled();
    }

    public GradientDrawable card(int fill, int strokeColor, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(dp(radiusDp));
        if (strokeColor != 0) d.setStroke(Math.max(1, dp(1)), strokeColor);
        return d;
    }

    public Drawable buttonBackground(boolean primary, int radiusDp) {
        GradientDrawable enabled = new GradientDrawable();
        enabled.setCornerRadius(dp(radiusDp));
        if (primary) {
            enabled.setOrientation(GradientDrawable.Orientation.TOP_BOTTOM);
            enabled.setColors(new int[]{primaryTop, primaryBottom});
            enabled.setStroke(Math.max(1, dp(1)), Color.parseColor(dark ? "#78AEFF" : "#2969CB"));
        } else {
            enabled.setColor(surface);
            enabled.setStroke(Math.max(1, dp(1)), edge);
        }
        GradientDrawable disabled = new GradientDrawable();
        disabled.setCornerRadius(dp(radiusDp));
        disabled.setColor(line);
        disabled.setStroke(Math.max(1, dp(1)), edge);

        StateListDrawable states = new StateListDrawable();
        states.addState(new int[]{android.R.attr.state_enabled}, enabled);
        states.addState(new int[]{}, disabled);

        GradientDrawable mask = new GradientDrawable();
        mask.setCornerRadius(dp(radiusDp));
        mask.setColor(Color.WHITE);
        int rippleColor = Color.parseColor(primary ? "#38FFFFFF" : (dark ? "#3086B8FF" : "#22235DA8"));
        return new RippleDrawable(ColorStateList.valueOf(rippleColor), states, mask);
    }

    public Drawable chipBackground(int fill, int stroke, int radiusDp) {
        GradientDrawable base = card(fill, stroke, radiusDp);
        GradientDrawable mask = card(Color.WHITE, 0, radiusDp);
        int ripple = Color.parseColor(dark ? "#3086B8FF" : "#22235DA8");
        return new RippleDrawable(ColorStateList.valueOf(ripple), base, mask);
    }

    public Drawable icon(String kind, int color, int sizeDp) {
        int px = dp(sizeDp);
        return new VectorIconDrawable(kind, color, px, density);
    }

    /** Ambient canvas container with soft Mac-style blue & warm radial glow orbs. */
    public static final class AmbientRootLayout extends LinearLayout {
        private final Paint orbPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final boolean dark;
        private final int bgColor;

        public AmbientRootLayout(Context c, UiTheme theme) {
            super(c);
            this.dark = theme.dark;
            this.bgColor = theme.canvas;
            setWillNotDraw(false);
        }

        @Override protected void onDraw(Canvas canvas) {
            canvas.drawColor(bgColor);
            float w = getWidth(), h = getHeight();
            if (w <= 0 || h <= 0) return;
            float r1 = Math.max(w, h) * 0.55f;
            orbPaint.setShader(new RadialGradient(
                w * 0.12f, h * 0.06f, r1,
                dark ? 0x383A72C4 : 0x33629EF0,
                0x00000000, Shader.TileMode.CLAMP));
            canvas.drawCircle(w * 0.12f, h * 0.06f, r1, orbPaint);

            float r2 = Math.max(w, h) * 0.50f;
            orbPaint.setShader(new RadialGradient(
                w * 0.88f, h * 0.85f, r2,
                dark ? 0x248A6E58 : 0x2EE8C19E,
                0x00000000, Shader.TileMode.CLAMP));
            canvas.drawCircle(w * 0.88f, h * 0.85f, r2, orbPaint);
        }
    }

    /** Mac-inspired 3D tilted book cover + headphone bubble + waveform pill illustration. */
    public static final class HeroIllustrationView extends View {
        private final UiTheme theme;
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();

        public HeroIllustrationView(Context c, UiTheme theme) {
            super(c);
            this.theme = theme;
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
        }

        @Override protected void onDraw(Canvas c) {
            float w = getWidth(), h = getHeight();
            if (w <= 0 || h <= 0) return;
            float d = getResources().getDisplayMetrics().density;

            // Soft radial halo
            p.setStyle(Paint.Style.FILL);
            p.setShader(new RadialGradient(w * 0.5f, h * 0.52f, w * 0.46f,
                theme.dark ? 0x385895F0 : 0x3578A9F0, 0x00000000, Shader.TileMode.CLAMP));
            c.drawCircle(w * 0.5f, h * 0.52f, w * 0.46f, p);
            p.setShader(null);

            // Tilted book pages & cover
            c.save();
            c.rotate(-9f, w * 0.46f, h * 0.50f);
            float bw = 72 * d, bh = 96 * d;
            float bx = w * 0.46f - bw * 0.5f, by = h * 0.50f - bh * 0.5f;

            // Pages stack shadow
            p.setColor(theme.dark ? 0xFFCBD6E6 : 0xFFDCE4F0);
            rect.set(bx + 4 * d, by + 3 * d, bx + bw + 4 * d, by + bh + 3 * d);
            c.drawRoundRect(rect, 8 * d, 8 * d, p);

            // Book cover gradient
            p.setShader(new LinearGradient(bx, by, bx + bw, by + bh,
                0xFF6793C8, 0xFF2E5A94, Shader.TileMode.CLAMP));
            rect.set(bx, by, bx + bw, by + bh);
            c.drawRoundRect(rect, 8 * d, 8 * d, p);
            p.setShader(null);

            // Book spine highlight
            p.setColor(0x30FFFFFF);
            rect.set(bx + 4 * d, by + 2 * d, bx + 7 * d, by + bh - 2 * d);
            c.drawRoundRect(rect, 2 * d, 2 * d, p);

            // Wave circle mark on cover
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.2f * d);
            p.setColor(0x88DCEAFD);
            c.drawCircle(bx + 18 * d, by + 18 * d, 9 * d, p);
            p.setStrokeCap(Paint.Cap.ROUND);
            p.setColor(0xFFF3F7FC);
            float cx = bx + 18 * d, cy = by + 18 * d;
            c.drawLine(cx - 4 * d, cy - 2 * d, cx - 4 * d, cy + 2 * d, p);
            c.drawLine(cx, cy - 5 * d, cx, cy + 5 * d, p);
            c.drawLine(cx + 4 * d, cy - 3 * d, cx + 4 * d, cy + 3 * d, p);

            // Cover title text
            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(8.5f * d);
            p.setColor(0xFFF5F9FF);
            c.drawText("Một trang", bx + 10 * d, by + 48 * d, p);
            c.drawText("sách mới.", bx + 10 * d, by + 60 * d, p);
            p.setTextSize(5.5f * d);
            p.setColor(0xCCE2EEFF);
            c.drawText("WINDI · AUDIO", bx + 10 * d, by + bh - 10 * d, p);
            c.restore();

            // Floating headphone glass bubble (top right)
            c.save();
            float hx = w * 0.76f, hy = h * 0.27f, hr = 18 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.surface);
            rect.set(hx - hr, hy - hr, hx + hr, hy + hr);
            c.drawRoundRect(rect, 12 * d, 12 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.2f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 12 * d, 12 * d, p);
            VectorIconDrawable.drawGlyph(c, "headphones", hx - 9 * d, hy - 9 * d, 18 * d, theme.accent, 1.7f * d);
            c.restore();

            // Floating mini-wave glass pill (bottom left)
            c.save();
            float wx = w * 0.10f, wy = h * 0.66f, ww = 46 * d, wh = 24 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.surface);
            rect.set(wx, wy, wx + ww, wy + wh);
            c.drawRoundRect(rect, 9 * d, 9 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.2f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 9 * d, 9 * d, p);

            p.setStyle(Paint.Style.STROKE);
            p.setStrokeCap(Paint.Cap.ROUND);
            p.setStrokeWidth(2.2f * d);
            p.setColor(theme.accent);
            float[] bars = {0.35f, 0.75f, 0.45f, 0.9f, 0.5f};
            for (int i = 0; i < bars.length; i++) {
                float x = wx + 10 * d + i * 6.5f * d;
                float bh2 = wh * 0.52f * bars[i];
                c.drawLine(x, wy + wh * 0.5f - bh2 * 0.5f, x, wy + wh * 0.5f + bh2 * 0.5f, p);
            }
            c.restore();
        }
    }

    /** Player book art badge with animated 4-bar equalizer when narration is playing. */
    public static final class PlayerArtView extends View {
        private final UiTheme theme;
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();
        private boolean playing = false;
        private float phase = 0f;
        private ValueAnimator anim;

        public PlayerArtView(Context c, UiTheme theme) {
            super(c);
            this.theme = theme;
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
        }

        public void setPlaying(boolean active) {
            if (this.playing == active) return;
            this.playing = active;
            if (active && !reducedMotion()) {
                if (anim == null) {
                    anim = ValueAnimator.ofFloat(0f, (float) (Math.PI * 2));
                    anim.setDuration(1100);
                    anim.setRepeatCount(ValueAnimator.INFINITE);
                    anim.addUpdateListener(a -> {
                        phase = (float) a.getAnimatedValue();
                        invalidate();
                    });
                }
                if (!anim.isStarted()) anim.start();
            } else {
                if (anim != null) anim.cancel();
                phase = 0.8f;
                invalidate();
            }
        }

        @Override protected void onDetachedFromWindow() {
            if (anim != null) anim.cancel();
            super.onDetachedFromWindow();
        }

        @Override protected void onDraw(Canvas c) {
            float w = getWidth(), h = getHeight(), d = getResources().getDisplayMetrics().density;
            rect.set(0, 0, w, h);
            p.setStyle(Paint.Style.FILL);
            p.setShader(new LinearGradient(0, 0, w, h, 0xFF7CA4D6, 0xFF4F79B0, Shader.TileMode.CLAMP));
            c.drawRoundRect(rect, 11 * d, 11 * d, p);
            p.setShader(null);

            p.setColor(0x33FFFFFF);
            rect.set(3 * d, 2 * d, 6 * d, h - 2 * d);
            c.drawRoundRect(rect, 2 * d, 2 * d, p);

            if (playing) {
                p.setColor(0xFFFFFFFF);
                p.setStrokeCap(Paint.Cap.ROUND);
                p.setStrokeWidth(2.6f * d);
                float[] offsets = {0f, 1.3f, 2.5f, 0.7f};
                float startX = w * 0.27f, step = w * 0.155f, cy = h * 0.5f;
                for (int i = 0; i < 4; i++) {
                    float ratio = reducedMotion() ? (0.4f + (i % 2) * 0.35f)
                        : (0.32f + 0.62f * Math.abs((float) Math.sin(phase + offsets[i])));
                    float half = h * 0.26f * ratio;
                    float x = startX + i * step;
                    c.drawLine(x, cy - half, x, cy + half, p);
                }
            } else {
                VectorIconDrawable.drawGlyph(c, "book", w * 0.5f - 10 * d, h * 0.5f - 10 * d, 20 * d, Color.WHITE, 1.6f * d);
            }
        }
    }

    /** Crisp vector icon drawable matching Mac SVG symbols (#i-*). */
    public static final class VectorIconDrawable extends Drawable {
        private final String kind;
        private final int color, size;
        private final float density;

        VectorIconDrawable(String kind, int color, int size, float density) {
            this.kind = kind;
            this.color = color;
            this.size = size;
            this.density = density;
            setBounds(0, 0, size, size);
        }

        @Override public int getIntrinsicWidth() { return size; }
        @Override public int getIntrinsicHeight() { return size; }
        @Override public void setAlpha(int alpha) {}
        @Override public void setColorFilter(ColorFilter cf) {}
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }

        @Override public void draw(Canvas c) {
            Rect b = getBounds();
            float s = Math.min(b.width(), b.height());
            float x = b.left + (b.width() - s) * 0.5f;
            float y = b.top + (b.height() - s) * 0.5f;
            drawGlyph(c, kind, x, y, s, color, 1.85f * density);
        }

        public static void drawGlyph(Canvas c, String kind, float x, float y, float s, int color, float stroke) {
            Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
            p.setColor(color);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(stroke);
            p.setStrokeCap(Paint.Cap.ROUND);
            p.setStrokeJoin(Paint.Join.ROUND);
            Path path = new Path();
            float u = s / 24f;

            switch (kind) {
                case "home" -> {
                    path.moveTo(x+3*u,y+11*u);path.lineTo(x+12*u,y+3*u);path.lineTo(x+21*u,y+11*u);path.moveTo(x+6*u,y+10*u);path.lineTo(x+6*u,y+21*u);path.lineTo(x+10*u,y+21*u);path.lineTo(x+10*u,y+15*u);path.lineTo(x+14*u,y+15*u);path.lineTo(x+14*u,y+21*u);path.lineTo(x+18*u,y+21*u);path.lineTo(x+18*u,y+10*u);c.drawPath(path,p);
                }
                case "filter" -> {for(int i=0;i<3;i++)c.drawLine(x+(4+i*3)*u,y+(6+i*6)*u,x+(20-i*3)*u,y+(6+i*6)*u,p);}
                case "search" -> { c.drawCircle(x+10*u,y+10*u,6*u,p);c.drawLine(x+15*u,y+15*u,x+21*u,y+21*u,p); }
                case "close" -> { c.drawLine(x+6*u,y+6*u,x+18*u,y+18*u,p);c.drawLine(x+18*u,y+6*u,x+6*u,y+18*u,p); }
                case "more" -> { p.setStyle(Paint.Style.FILL);for(int i=0;i<3;i++)c.drawCircle(x+12*u,y+(6+i*6)*u,1.3f*u,p); }
                case "edit" -> { path.moveTo(x+4*u,y+16*u);path.lineTo(x+15*u,y+5*u);path.lineTo(x+19*u,y+9*u);path.lineTo(x+8*u,y+20*u);path.lineTo(x+4*u,y+20*u);path.close();c.drawPath(path,p);c.drawLine(x+13*u,y+7*u,x+17*u,y+11*u,p); }
                case "list" -> {for(int i=0;i<3;i++){c.drawPoint(x+4*u,y+(6+i*6)*u,p);c.drawLine(x+9*u,y+(6+i*6)*u,x+21*u,y+(6+i*6)*u,p);}}
                case "chevron" -> {path.moveTo(x+9*u,y+5*u);path.lineTo(x+16*u,y+12*u);path.lineTo(x+9*u,y+19*u);c.drawPath(path,p);}
                case "next" -> {path.moveTo(x+5*u,y+5*u);path.lineTo(x+15*u,y+12*u);path.lineTo(x+5*u,y+19*u);path.close();c.drawPath(path,p);c.drawLine(x+19*u,y+5*u,x+19*u,y+19*u,p);}
                case "clock", "speed" -> {c.drawCircle(x+12*u,y+12*u,9*u,p);c.drawLine(x+12*u,y+12*u,x+12*u,y+6*u,p);c.drawLine(x+12*u,y+12*u,x+17*u,y+14*u,p);}
                case "rewind", "forward" -> {
                    c.save();if(kind.equals("rewind"))c.scale(-1,1,x+12*u,y+12*u);
                    // A clockwise arc ending at twelve o'clock; the arrow follows its tangent.
                    c.drawArc(new RectF(x+3*u,y+4*u,x+21*u,y+22*u),-45,315,false,p);
                    path.moveTo(x+8.5f*u,y+1*u);path.lineTo(x+12*u,y+4*u);path.lineTo(x+8.5f*u,y+7*u);c.drawPath(path,p);c.restore();
                    p.setStyle(Paint.Style.FILL);p.setTextSize(8.5f*u);p.setTypeface(Typeface.DEFAULT_BOLD);p.setTextAlign(Paint.Align.CENTER);
                    Paint.FontMetrics fm=p.getFontMetrics();c.drawText("15",x+12*u,y+13*u-(fm.ascent+fm.descent)/2,p);
                }
                case "expand" -> {for(int i=0;i<4;i++){c.save();c.rotate(i*90,x+12*u,y+12*u);path.reset();path.moveTo(x+4*u,y+9*u);path.lineTo(x+4*u,y+4*u);path.lineTo(x+9*u,y+4*u);c.drawPath(path,p);c.restore();}}
                case "back" -> {
                    path.moveTo(x+14*u,y+5*u);path.lineTo(x+7*u,y+12*u);path.lineTo(x+14*u,y+19*u);c.drawPath(path,p);
                }
                case "bookmark", "bookmark-filled" -> {
                    if(kind.equals("bookmark-filled"))p.setStyle(Paint.Style.FILL);
                    path.moveTo(x+6*u,y+3*u);path.lineTo(x+18*u,y+3*u);path.lineTo(x+18*u,y+21*u);path.lineTo(x+12*u,y+17*u);path.lineTo(x+6*u,y+21*u);path.close();c.drawPath(path,p);
                }
                case "plus" -> {
                    c.drawLine(x + 12 * u, y + 5 * u, x + 12 * u, y + 19 * u, p);
                    c.drawLine(x + 5 * u, y + 12 * u, x + 19 * u, y + 12 * u, p);
                }
                case "book" -> {
                    path.moveTo(x + 12 * u, y + 6 * u);
                    path.cubicTo(x + 9 * u, y + 4 * u, x + 6 * u, y + 4 * u, x + 3 * u, y + 5 * u);
                    path.lineTo(x + 3 * u, y + 19 * u);
                    path.cubicTo(x + 6 * u, y + 18 * u, x + 9 * u, y + 18 * u, x + 12 * u, y + 20 * u);
                    path.cubicTo(x + 15 * u, y + 18 * u, x + 18 * u, y + 18 * u, x + 21 * u, y + 19 * u);
                    path.lineTo(x + 21 * u, y + 5 * u);
                    path.cubicTo(x + 18 * u, y + 4 * u, x + 15 * u, y + 4 * u, x + 12 * u, y + 6 * u);
                    c.drawPath(path, p);
                    c.drawLine(x + 12 * u, y + 6 * u, x + 12 * u, y + 20 * u, p);
                }
                case "folder" -> {
                    path.moveTo(x + 3 * u, y + 7 * u);
                    path.lineTo(x + 3 * u, y + 19 * u);
                    path.lineTo(x + 21 * u, y + 19 * u);
                    path.lineTo(x + 21 * u, y + 8 * u);
                    path.lineTo(x + 11 * u, y + 8 * u);
                    path.lineTo(x + 9 * u, y + 5 * u);
                    path.lineTo(x + 3 * u, y + 5 * u);
                    path.close();
                    c.drawPath(path, p);
                }
                case "headphones" -> {
                    RectF arc = new RectF(x + 4 * u, y + 4 * u, x + 20 * u, y + 20 * u);
                    c.drawArc(arc, 180, 180, false, p);
                    RectF left = new RectF(x + 3 * u, y + 12 * u, x + 7 * u, y + 19 * u);
                    RectF right = new RectF(x + 17 * u, y + 12 * u, x + 21 * u, y + 19 * u);
                    c.drawRoundRect(left, 2 * u, 2 * u, p);
                    c.drawRoundRect(right, 2 * u, 2 * u, p);
                }
                case "wave" -> {
                    c.drawLine(x + 4 * u, y + 10 * u, x + 4 * u, y + 14 * u, p);
                    c.drawLine(x + 8 * u, y + 6 * u, x + 8 * u, y + 18 * u, p);
                    c.drawLine(x + 12 * u, y + 3 * u, x + 12 * u, y + 21 * u, p);
                    c.drawLine(x + 16 * u, y + 6 * u, x + 16 * u, y + 18 * u, p);
                    c.drawLine(x + 20 * u, y + 10 * u, x + 20 * u, y + 14 * u, p);
                }
                case "play" -> {
                    p.setStyle(Paint.Style.FILL);
                    path.moveTo(x + 8 * u, y + 5 * u);
                    path.lineTo(x + 19 * u, y + 12 * u);
                    path.lineTo(x + 8 * u, y + 19 * u);
                    path.close();
                    c.drawPath(path, p);
                }
                case "pause" -> {
                    p.setStyle(Paint.Style.FILL);
                    c.drawRoundRect(new RectF(x + 6.5f * u, y + 5 * u, x + 10.5f * u, y + 19 * u), 1.5f * u, 1.5f * u, p);
                    c.drawRoundRect(new RectF(x + 13.5f * u, y + 5 * u, x + 17.5f * u, y + 19 * u), 1.5f * u, 1.5f * u, p);
                }
                case "stop" -> {
                    p.setStyle(Paint.Style.FILL);
                    c.drawRoundRect(new RectF(x + 6.5f * u, y + 6.5f * u, x + 17.5f * u, y + 17.5f * u), 2.5f * u, 2.5f * u, p);
                }
                case "export" -> {
                    c.drawLine(x + 12 * u, y + 4 * u, x + 12 * u, y + 15 * u, p);
                    path.moveTo(x + 8 * u, y + 11 * u);
                    path.lineTo(x + 12 * u, y + 15 * u);
                    path.lineTo(x + 16 * u, y + 11 * u);
                    c.drawPath(path, p);
                    path.reset();
                    path.moveTo(x + 4 * u, y + 15 * u);
                    path.lineTo(x + 4 * u, y + 20 * u);
                    path.lineTo(x + 20 * u, y + 20 * u);
                    path.lineTo(x + 20 * u, y + 15 * u);
                    c.drawPath(path, p);
                }
                case "original" -> {
                    path.moveTo(x + 13 * u, y + 4 * u);
                    path.lineTo(x + 5 * u, y + 4 * u);
                    path.lineTo(x + 5 * u, y + 20 * u);
                    path.lineTo(x + 19 * u, y + 20 * u);
                    path.lineTo(x + 19 * u, y + 12 * u);
                    c.drawPath(path, p);
                    path.reset();
                    path.moveTo(x + 14 * u, y + 4 * u);
                    path.lineTo(x + 20 * u, y + 4 * u);
                    path.lineTo(x + 20 * u, y + 10 * u);
                    c.drawPath(path, p);
                    c.drawLine(x + 20 * u, y + 4 * u, x + 11 * u, y + 13 * u, p);
                }
                case "settings" -> {
                    c.drawCircle(x + 12 * u, y + 12 * u, 3.2f * u, p);
                    c.drawCircle(x + 12 * u, y + 12 * u, 7.2f * u, p);
                    for (int i = 0; i < 8; i++) {
                        double a = i * Math.PI / 4.0;
                        float x1 = x + (12 + 7.2f * (float) Math.cos(a)) * u;
                        float y1 = y + (12 + 7.2f * (float) Math.sin(a)) * u;
                        float x2 = x + (12 + 9.4f * (float) Math.cos(a)) * u;
                        float y2 = y + (12 + 9.4f * (float) Math.sin(a)) * u;
                        c.drawLine(x1, y1, x2, y2, p);
                    }
                }
                case "compass" -> {
                    c.drawCircle(x + 12 * u, y + 12 * u, 8.8f * u, p);
                    path.moveTo(x + 15.5f * u, y + 8.5f * u);
                    path.lineTo(x + 13.5f * u, y + 13.5f * u);
                    path.lineTo(x + 8.5f * u, y + 15.5f * u);
                    path.lineTo(x + 10.5f * u, y + 10.5f * u);
                    path.close();
                    c.drawPath(path, p);
                }
                case "music" -> {
                    path.moveTo(x + 9 * u, y + 17 * u);
                    path.lineTo(x + 9 * u, y + 6 * u);
                    path.lineTo(x + 19 * u, y + 4 * u);
                    path.lineTo(x + 19 * u, y + 15 * u);
                    c.drawPath(path, p);
                    c.drawCircle(x + 6.5f * u, y + 17.5f * u, 2.5f * u, p);
                    c.drawCircle(x + 16.5f * u, y + 15.5f * u, 2.5f * u, p);
                }
                case "sound-on", "sound-off" -> {
                    path.moveTo(x + 5 * u, y + 9.5f * u);
                    path.lineTo(x + 8.5f * u, y + 9.5f * u);
                    path.lineTo(x + 13 * u, y + 5.5f * u);
                    path.lineTo(x + 13 * u, y + 18.5f * u);
                    path.lineTo(x + 8.5f * u, y + 14.5f * u);
                    path.lineTo(x + 5 * u, y + 14.5f * u);
                    path.close();
                    c.drawPath(path, p);
                    if ("sound-on".equals(kind)) {
                        c.drawArc(new RectF(x + 11 * u, y + 8 * u, x + 17.5f * u, y + 16 * u), -50, 100, false, p);
                        c.drawArc(new RectF(x + 10 * u, y + 5.5f * u, x + 20.5f * u, y + 18.5f * u), -55, 110, false, p);
                    } else {
                        c.drawLine(x + 16 * u, y + 9.5f * u, x + 20.5f * u, y + 14.5f * u, p);
                        c.drawLine(x + 20.5f * u, y + 9.5f * u, x + 16 * u, y + 14.5f * u, p);
                    }
                }
                case "check" -> {
                    path.moveTo(x + 5 * u, y + 12.5f * u);
                    path.lineTo(x + 9.5f * u, y + 17 * u);
                    path.lineTo(x + 19 * u, y + 7.5f * u);
                    c.drawPath(path, p);
                }
                case "sparkles" -> {
                    path.moveTo(x + 12 * u, y + 3 * u);
                    path.quadTo(x + 12 * u, y + 12 * u, x + 21 * u, y + 12 * u);
                    path.quadTo(x + 12 * u, y + 12 * u, x + 12 * u, y + 21 * u);
                    path.quadTo(x + 12 * u, y + 12 * u, x + 3 * u, y + 12 * u);
                    path.quadTo(x + 12 * u, y + 12 * u, x + 12 * u, y + 3 * u);
                    c.drawPath(path, p);
                }
                case "reflow" -> {
                    c.drawLine(x + 4 * u, y + 6 * u, x + 20 * u, y + 6 * u, p);
                    c.drawLine(x + 4 * u, y + 11 * u, x + 16 * u, y + 11 * u, p);
                    c.drawLine(x + 4 * u, y + 16 * u, x + 20 * u, y + 16 * u, p);
                    path.moveTo(x + 13.5f * u, y + 13.5f * u);
                    path.lineTo(x + 16.5f * u, y + 11 * u);
                    path.lineTo(x + 13.5f * u, y + 8.5f * u);
                    c.drawPath(path, p);
                }
            }
        }
    }
}
