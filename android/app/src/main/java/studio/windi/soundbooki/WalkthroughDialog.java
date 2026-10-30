package studio.windi.soundbooki;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.*;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.*;
import android.view.animation.DecelerateInterpolator;
import android.widget.*;

/**
 * Five-step mobile Walkthrough dialog synchronized with Mac's walkthrough.js & walkthrough.css.
 * Local-only discovery: plays owner-authorized welcome greeting (80%) + Piano podcast Bài 01 (40%)
 * + gentle acoustic harmonic chimes on page transitions when unmuted.
 * Never triggers cloud, payment or synthesis during navigation.
 */
public final class WalkthroughDialog extends Dialog {
    public static final String PREF_SEEN = "windi-walkthrough-v1";
    public static final String PREF_MUTED = "windi-walkthrough-muted";

    public static final class Page {
        public final String label, tag, title, body, tip, scene;
        Page(String label, String tag, String title, String body, String tip, String scene) {
            this.label = label;
            this.tag = tag;
            this.title = title;
            this.body = body;
            this.tip = tip;
            this.scene = scene;
        }
    }

    public static final Page[] PAGES = {
        new Page(
            "Sách nói miễn phí",
            "MIỄN PHÍ · NGAY TRÊN ĐIỆN THOẠI",
            "Sách của bạn.\nNghe hoàn toàn miễn phí.",
            "Biến PDF, EPUB, TXT thành sách nói với giọng Lite tiếng Việt. Tạo và nghe ngay trên điện thoại của bạn, không cần mạng.",
            "Lite tiếng Việt · 7 giọng đọc tự nhiên",
            "import"
        ),
        new Page(
            "Giọng Pro trên cloud",
            "PRO CLOUD · TỪ 10.000Đ / CUỐN",
            "Giọng đọc giàu cảm xúc.\nTự nhiên như người kể.",
            "Để Pro kể lại cuốn sách bạn yêu thích bằng giọng đọc tự nhiên, giàu cảm xúc. Tạo trên cloud theo từng cuốn khi bạn chọn.",
            "Thử miễn phí 5 lượt / máy · Tối đa 5.000 ký tự / lượt",
            "cloud"
        ),
        new Page(
            "Đọc và chỉnh sửa",
            "KHÔNG GIAN ĐỌC SÁCH RIÊNG",
            "Một góc đọc và sửa chữ.\nNgay trong tầm tay.",
            "Xem toàn bộ chữ, chỉnh sửa trực tiếp hoặc đối chiếu bản chữ gốc bất kỳ lúc nào. Tự lưu vị trí đang nghe để lần sau tiếp tục đúng chỗ.",
            "Giữ nguyên văn bản gốc · Tự nhớ vị trí nghe",
            "reader"
        ),
        new Page(
            "Nghe nền & xuất WAV",
            "LƯU VỀ MÁY · NGHE MỌI LÚC",
            "Tắt màn hình. Thả lỏng.\nĐể câu chuyện tiếp tục.",
            "Phát nền ổn định với điều khiển trên thanh thông báo và lưu trọn cuốn sách ra file WAV chuẩn 24kHz để nghe mọi lúc.",
            "Phát nền mượt mà · Xuất WAV lưu trên máy",
            "export"
        ),
        new Page(
            "Bắt đầu thư viện",
            "SẴN SÀNG TRÊN ĐIỆN THOẠI",
            "Mỗi trang sách mở ra\nmột thế giới mới.",
            "Chọn một cuốn EPUB, PDF có chữ hoặc dán đoạn văn tiếng Việt bạn yêu thích. Bấm Nghe để bắt đầu hành trình lắng nghe ngay hôm nay.",
            "Lite miễn phí trên máy · Pro Cloud theo từng cuốn",
            "pro"
        )
    };

    private final Activity host;
    private final UiTheme theme;
    private final WelcomeAudioPlayer audio;
    private final Runnable onStartListen;
    private final Runnable onOpenPro;

    private int pageIndex = 0;
    private boolean muted = false;

    private Button soundBtn, skipBtn, backBtn, nextBtn, proBtn;
    private WalkthroughSceneView sceneView;
    private TextView tagView, countView, titleView, bodyView, tipView;
    private LinearLayout cardContent, stepsRow;
    private final View[] stepPills = new View[PAGES.length];

    public WalkthroughDialog(Activity host, UiTheme theme, WelcomeAudioPlayer audio, Runnable onStartListen, Runnable onOpenPro) {
        super(host, android.R.style.Theme_DeviceDefault_NoActionBar);
        this.host = host;
        this.theme = theme;
        this.audio = audio;
        this.onStartListen = onStartListen;
        this.onOpenPro = onOpenPro;
    }

    public int getPageIndex() {
        return pageIndex;
    }

    public WelcomeAudioPlayer getAudioPlayer() {
        return audio;
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        SharedPreferences prefs = host.getSharedPreferences("settings", Context.MODE_PRIVATE);
        muted = prefs.getBoolean(PREF_MUTED, false);

        Window w = getWindow();
        if (w != null) {
            w.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
            w.setBackgroundDrawable(new ColorDrawable(Color.parseColor(theme.dark ? "#D80A101A" : "#B8121E31")));
            w.setStatusBarColor(Color.TRANSPARENT);
            w.setNavigationBarColor(Color.TRANSPARENT);
        }

        FrameLayout backdrop = new FrameLayout(host);
        backdrop.setPadding(theme.dp(12), theme.dp(18), theme.dp(12), theme.dp(14));
        backdrop.setOnApplyWindowInsetsListener((v, insets) -> {
            Insets safe = insets.getInsets(WindowInsets.Type.systemBars());
            v.setPadding(theme.dp(12), safe.top + theme.dp(10), theme.dp(12), safe.bottom + theme.dp(10));
            return insets;
        });

        LinearLayout shell = new LinearLayout(host);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setBackground(theme.card(theme.tourSurface, theme.edge, 28));
        shell.setPadding(theme.dp(18), theme.dp(16), theme.dp(18), theme.dp(16));
        shell.setElevation(theme.dp(16));
        FrameLayout.LayoutParams shellLp = new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        shellLp.gravity = Gravity.CENTER;
        backdrop.addView(shell, shellLp);

        // Top Bar: Brand + Mute/Unmute + Skip
        LinearLayout top = new LinearLayout(host);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);

        ImageView mark = new ImageView(host);
        mark.setImageResource(R.drawable.brand_logo);
        mark.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        top.addView(mark, new LinearLayout.LayoutParams(theme.dp(30), theme.dp(33)));

        ImageView word = new ImageView(host);
        word.setImageResource(R.drawable.brand_wordmark);
        word.setScaleType(ImageView.ScaleType.FIT_START);
        word.setContentDescription("Soundbooki");
        LinearLayout.LayoutParams wordLp = new LinearLayout.LayoutParams(0, theme.dp(24), 1f);
        wordLp.setMargins(theme.dp(8), 0, theme.dp(6), 0);
        top.addView(word, wordLp);

        soundBtn = makeTopButton("", true);
        soundBtn.setOnClickListener(v -> toggleMute());
        top.addView(soundBtn, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, theme.dp(48)));

        skipBtn = makeTopButton("Bỏ qua", false);
        LinearLayout.LayoutParams skipLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, theme.dp(48));
        skipLp.leftMargin = theme.dp(8);
        skipBtn.setOnClickListener(v -> finishTour(null));
        top.addView(skipBtn, skipLp);

        shell.addView(top, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        // Scrollable stage + copy area with swipe support
        ScrollView scroll = new ScrollView(host);
        scroll.setFillViewport(true);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout.LayoutParams scrollLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        scrollLp.topMargin = theme.dp(12);
        scrollLp.bottomMargin = theme.dp(10);

        cardContent = new LinearLayout(host);
        cardContent.setOrientation(LinearLayout.VERTICAL);

        // Visual stage
        sceneView = new WalkthroughSceneView(host, theme);
        LinearLayout.LayoutParams sceneLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, theme.dp(218));
        cardContent.addView(sceneView, sceneLp);

        // Meta row: Eyebrow pill + Step counter
        LinearLayout metaRow = new LinearLayout(host);
        metaRow.setOrientation(LinearLayout.HORIZONTAL);
        metaRow.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams metaLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        metaLp.topMargin = theme.dp(16);

        tagView = new TextView(host);
        tagView.setTextSize(11f);
        tagView.setTypeface(theme.bold);
        tagView.setTextColor(theme.tourBlue);
        tagView.setLetterSpacing(0.06f);
        tagView.setBackground(theme.card(theme.blueWash, theme.edge, 999));
        tagView.setPadding(theme.dp(12), theme.dp(6), theme.dp(12), theme.dp(6));
        metaRow.addView(tagView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        View spacer = new View(host);
        metaRow.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1f));

        countView = new TextView(host);
        countView.setTextSize(12.5f);
        countView.setTypeface(theme.bold);
        countView.setTextColor(theme.muted);
        metaRow.addView(countView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        cardContent.addView(metaRow, metaLp);

        // Headline
        titleView = new TextView(host);
        titleView.setTextSize(26f);
        titleView.setTypeface(theme.display);
        titleView.setTextColor(theme.ink);
        titleView.setLineSpacing(theme.dp(2), 1.02f);
        LinearLayout.LayoutParams titleLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        titleLp.topMargin = theme.dp(12);
        cardContent.addView(titleView, titleLp);

        // Body copy
        bodyView = new TextView(host);
        bodyView.setTextSize(15.5f);
        bodyView.setTypeface(theme.regular);
        bodyView.setTextColor(theme.muted);
        bodyView.setLineSpacing(theme.dp(4), 1.12f);
        LinearLayout.LayoutParams bodyLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bodyLp.topMargin = theme.dp(10);
        cardContent.addView(bodyView, bodyLp);

        // Tip callout card
        tipView = new TextView(host);
        tipView.setTextSize(13.5f);
        tipView.setTypeface(theme.bold);
        tipView.setTextColor(theme.ink);
        tipView.setBackground(theme.card(theme.surface, theme.edge, 16));
        tipView.setPadding(theme.dp(14), theme.dp(12), theme.dp(14), theme.dp(12));
        tipView.setCompoundDrawablesWithIntrinsicBounds(theme.icon("check", theme.accent, 18), null, null, null);
        tipView.setCompoundDrawablePadding(theme.dp(10));
        LinearLayout.LayoutParams tipLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        tipLp.topMargin = theme.dp(14);
        cardContent.addView(tipView, tipLp);

        // Optional Pro Cloud button on final step
        proBtn = new Button(host);
        proBtn.setText("Xem chương trình Pro");
        proBtn.setAllCaps(false);
        proBtn.setTextSize(14.5f);
        proBtn.setTypeface(theme.bold);
        proBtn.setTextColor(theme.accent);
        proBtn.setBackground(theme.buttonBackground(false, 16));
        proBtn.setCompoundDrawablesWithIntrinsicBounds(theme.icon("headphones", theme.accent, 18), null, null, null);
        proBtn.setCompoundDrawablePadding(theme.dp(8));
        proBtn.setPadding(theme.dp(16), 0, theme.dp(16), 0);
        LinearLayout.LayoutParams proLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, theme.dp(50));
        proLp.topMargin = theme.dp(12);
        proBtn.setOnClickListener(v -> finishTour(onOpenPro));
        cardContent.addView(proBtn, proLp);

        scroll.addView(cardContent);
        attachSwipeGesture(scroll);
        shell.addView(scroll, scrollLp);

        // Step dots row (each 48dp x 48dp touch target)
        stepsRow = new LinearLayout(host);
        stepsRow.setOrientation(LinearLayout.HORIZONTAL);
        stepsRow.setGravity(Gravity.CENTER);
        for (int i = 0; i < PAGES.length; i++) {
            final int stepIdx = i;
            FrameLayout hit = new FrameLayout(host);
            hit.setContentDescription("Trang " + (i + 1) + ": " + PAGES[i].label);
            hit.setClickable(true);
            hit.setFocusable(true);
            View pill = new View(host);
            stepPills[i] = pill;
            FrameLayout.LayoutParams pillLp = new FrameLayout.LayoutParams(theme.dp(8), theme.dp(8), Gravity.CENTER);
            hit.addView(pill, pillLp);
            hit.setOnClickListener(v -> setPage(stepIdx));
            stepsRow.addView(hit, new LinearLayout.LayoutParams(theme.dp(48), theme.dp(44)));
        }
        shell.addView(stepsRow, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        // Large thumb-zone navigation buttons (54dp height)
        LinearLayout navRow = new LinearLayout(host);
        navRow.setOrientation(LinearLayout.HORIZONTAL);
        navRow.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams navLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        navLp.topMargin = theme.dp(6);

        backBtn = new Button(host);
        backBtn.setText("Quay lại");
        backBtn.setAllCaps(false);
        backBtn.setTextSize(15f);
        backBtn.setTypeface(theme.bold);
        int[][] states = {new int[]{android.R.attr.state_enabled}, new int[]{}};
        backBtn.setTextColor(new android.content.res.ColorStateList(states, new int[]{theme.ink, theme.quiet}));
        backBtn.setBackground(theme.buttonBackground(false, 18));
        backBtn.setOnClickListener(v -> setPage(pageIndex - 1));
        navRow.addView(backBtn, new LinearLayout.LayoutParams(0, theme.dp(54), 0.9f));

        nextBtn = new Button(host);
        nextBtn.setText("Tiếp theo");
        nextBtn.setAllCaps(false);
        nextBtn.setTextSize(15.5f);
        nextBtn.setTypeface(theme.bold);
        nextBtn.setTextColor(Color.WHITE);
        nextBtn.setBackground(theme.buttonBackground(true, 18));
        LinearLayout.LayoutParams nextLp = new LinearLayout.LayoutParams(0, theme.dp(54), 1.45f);
        nextLp.leftMargin = theme.dp(10);
        nextBtn.setOnClickListener(v -> {
            if (pageIndex < PAGES.length - 1) {
                setPage(pageIndex + 1);
            } else {
                audio.playEffect("complete");
                v.performHapticFeedback(HapticFeedbackConstants.CONFIRM);
                finishTour(onStartListen);
            }
        });
        navRow.addView(nextBtn, nextLp);

        shell.addView(navRow, navLp);
        setContentView(backdrop);

        setOnCancelListener(d -> finishTour(null));
        setOnDismissListener(d -> audio.stop(false));

        renderSoundButton();
        renderPage(true);
        startWelcomeAudio();
    }

    private Button makeTopButton(String text, boolean withSoundIcon) {
        Button b = new Button(host);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13.5f);
        b.setTypeface(theme.bold);
        b.setTextColor(theme.ink);
        b.setBackground(theme.chipBackground(theme.surface, theme.edge, 999));
        b.setMinimumWidth(theme.dp(48));
        b.setMinHeight(theme.dp(48));
        b.setPadding(theme.dp(14), 0, theme.dp(14), 0);
        if (withSoundIcon) {
            b.setCompoundDrawablePadding(theme.dp(6));
        }
        return b;
    }

    private void startWelcomeAudio() {
        try {
            audio.start(host, muted);
        } catch (Exception e) {
            soundBtn.setText("Âm thanh chưa sẵn sàng");
        }
    }

    public void toggleMute() {
        muted = !muted;
        host.getSharedPreferences("settings", Context.MODE_PRIVATE)
            .edit().putBoolean(PREF_MUTED, muted).apply();
        audio.setMuted(muted);
        renderSoundButton();
    }

    private void renderSoundButton() {
        soundBtn.setText(muted ? "Bật âm" : "Tắt âm");
        soundBtn.setContentDescription(muted ? "Bật lời chào và nhạc nền" : "Tắt lời chào và nhạc nền");
        soundBtn.setCompoundDrawablesWithIntrinsicBounds(
            theme.icon(muted ? "sound-off" : "sound-on", theme.accent, 17), null, null, null);
    }

    public void setPage(int target) {
        int clamped = Math.max(0, Math.min(PAGES.length - 1, target));
        if (clamped == pageIndex) return;
        boolean forward = clamped > pageIndex;
        pageIndex = clamped;
        audio.playEffect(forward ? "page" : "back");
        if (nextBtn != null) {
            nextBtn.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK);
        }
        renderPage(false);
        animateTransition(forward ? 1 : -1);
    }

    private void renderPage(boolean initial) {
        Page p = PAGES[pageIndex];
        sceneView.setScene(p.scene);
        tagView.setText(p.tag);
        countView.setText((pageIndex + 1) + " / " + PAGES.length);
        titleView.setText(p.title);
        bodyView.setText(p.body);
        tipView.setText(p.tip);

        backBtn.setEnabled(pageIndex > 0);
        backBtn.setAlpha(pageIndex > 0 ? 1f : 0.48f);
        nextBtn.setText(pageIndex == PAGES.length - 1 ? "Nghe Sách của bạn Ngay" : "Tiếp theo");
        proBtn.setVisibility(pageIndex == PAGES.length - 1 ? View.VISIBLE : View.GONE);

        for (int i = 0; i < stepPills.length; i++) {
            View pill = stepPills[i];
            boolean active = i == pageIndex;
            boolean done = i < pageIndex;
            int w = theme.dp(active ? 28 : 8);
            int h = theme.dp(8);
            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(w, h, Gravity.CENTER);
            pill.setLayoutParams(lp);
            GradientDrawable d = new GradientDrawable();
            d.setCornerRadius(theme.dp(99));
            d.setColor(active ? theme.accent : (done ? Color.parseColor(theme.dark ? "#5A88CC" : "#7FA9E8") : theme.edge));
            pill.setBackground(d);
        }
        if (initial && !UiTheme.reducedMotion()) {
            animateTransition(1);
        }
    }

    private void animateTransition(int dir) {
        if (UiTheme.reducedMotion()) return;
        float offset = theme.dp(16) * dir;
        sceneView.setAlpha(0f);
        sceneView.setTranslationX(offset);
        sceneView.animate()
            .alpha(1f).translationX(0f)
            .setDuration(320)
            .setInterpolator(new DecelerateInterpolator())
            .start();

        View[] copyViews = {tagView, titleView, bodyView, tipView};
        for (int i = 0; i < copyViews.length; i++) {
            View v = copyViews[i];
            v.setAlpha(0f);
            v.setTranslationY(theme.dp(8));
            v.animate()
                .alpha(1f).translationY(0f)
                .setStartDelay(45L * i)
                .setDuration(280)
                .setInterpolator(new DecelerateInterpolator())
                .start();
        }
    }

    private void attachSwipeGesture(View target) {
        GestureDetector detector = new GestureDetector(host, new GestureDetector.SimpleOnGestureListener() {
            @Override public boolean onFling(MotionEvent e1, MotionEvent e2, float vx, float vy) {
                if (e1 == null || e2 == null) return false;
                float dx = e2.getX() - e1.getX();
                float dy = e2.getY() - e1.getY();
                if (Math.abs(dx) > theme.dp(48) && Math.abs(dx) > Math.abs(dy) * 1.25f) {
                    setPage(pageIndex + (dx < 0 ? 1 : -1));
                    return true;
                }
                return false;
            }
        });
        target.setOnTouchListener((v, event) -> {
            detector.onTouchEvent(event);
            return false;
        });
    }

    private void finishTour(Runnable after) {
        host.getSharedPreferences("settings", Context.MODE_PRIVATE)
            .edit().putBoolean(PREF_SEEN, true).apply();
        audio.stop(false);
        dismiss();
        if (after != null) {
            after.run();
        }
    }

    /** Custom vector artwork stage matching the 5 Mac Walkthrough scenes. */
    public static final class WalkthroughSceneView extends View {
        private final UiTheme theme;
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF rect = new RectF();
        private String scene = "import";

        public WalkthroughSceneView(Context c, UiTheme theme) {
            super(c);
            this.theme = theme;
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
        }

        public void setScene(String s) {
            this.scene = s;
            invalidate();
        }

        @Override protected void onDraw(Canvas c) {
            float w = getWidth(), h = getHeight(), d = getResources().getDisplayMetrics().density;
            if (w <= 0 || h <= 0) return;

            // Stage container background
            rect.set(0, 0, w, h);
            p.setStyle(Paint.Style.FILL);
            p.setShader(new LinearGradient(0, 0, w, h,
                theme.tourArt, theme.dark ? 0xFF1F2B3E : 0xFFF3F6FC, Shader.TileMode.CLAMP));
            c.drawRoundRect(rect, 22 * d, 22 * d, p);
            p.setShader(null);

            // Soft radial glow inside stage
            p.setShader(new RadialGradient(w * 0.22f, h * 0.20f, w * 0.55f,
                theme.dark ? 0x355895F0 : 0x3376AAFA, 0x00000000, Shader.TileMode.CLAMP));
            c.drawRoundRect(rect, 22 * d, 22 * d, p);
            p.setShader(null);

            // Border stroke
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 22 * d, 22 * d, p);

            switch (scene) {
                case "import" -> drawImportScene(c, w, h, d);
                case "cloud" -> drawCloudScene(c, w, h, d);
                case "reader" -> drawReaderScene(c, w, h, d);
                case "export" -> drawExportScene(c, w, h, d);
                default -> drawStartScene(c, w, h, d);
            }
        }

        private void drawImportScene(Canvas c, float w, float h, float d) {
            // Dashed orbit circle
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.2f * d);
            p.setColor(theme.edge);
            c.drawCircle(w * 0.5f, h * 0.52f, Math.min(w, h) * 0.40f, p);

            // Left floating PDF card
            c.save();
            c.rotate(-8f, w * 0.22f, h * 0.36f);
            drawFileChip(c, w * 0.08f, h * 0.20f, 88 * d, 56 * d, "PDF", "Bản gốc", d);
            c.restore();

            // Center 3D Book Cover
            float bw = 112 * d, bh = 148 * d;
            float bx = (w - bw) * 0.5f, by = (h - bh) * 0.5f;
            p.setStyle(Paint.Style.FILL);
            p.setShader(new LinearGradient(bx, by, bx + bw, by + bh, 0xFF3969AC, 0xFF214273, Shader.TileMode.CLAMP));
            rect.set(bx, by, bx + bw, by + bh);
            c.drawRoundRect(rect, 16 * d, 16 * d, p);
            p.setShader(null);

            p.setColor(0x28FFFFFF);
            rect.set(bx + 6 * d, by + 4 * d, bx + 10 * d, by + bh - 4 * d);
            c.drawRoundRect(rect, 3 * d, 3 * d, p);

            p.setTypeface(theme.bold);
            p.setTextSize(8.5f * d);
            p.setColor(0xCCEAF2FF);
            c.drawText("WINDI · SÁCH NÓI", bx + 15 * d, by + 24 * d, p);

            UiTheme.VectorIconDrawable.drawGlyph(c, "wave", bx + 15 * d, by + 46 * d, 26 * d, 0xFFDCEBFF, 2f * d);

            p.setTypeface(theme.display);
            p.setTextSize(12.5f * d);
            p.setColor(Color.WHITE);
            c.drawText("Một trang sách.", bx + 15 * d, by + bh - 30 * d, p);
            c.drawText("Một thế giới.", bx + 15 * d, by + bh - 14 * d, p);

            // Right floating EPUB card
            c.save();
            c.rotate(7f, w * 0.78f, h * 0.68f);
            drawFileChip(c, w - 104 * d, h * 0.54f, 92 * d, 56 * d, "EPUB", "Sẵn sàng nghe", d);
            c.restore();
        }

        private void drawFileChip(Canvas c, float x, float y, float cw, float ch, String title, String sub, float d) {
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(x, y, x + cw, y + ch);
            c.drawRoundRect(rect, 14 * d, 14 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 14 * d, 14 * d, p);

            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.display);
            p.setTextSize(15f * d);
            p.setColor(theme.tourBlue);
            c.drawText(title, x + 12 * d, y + 26 * d, p);

            p.setTypeface(theme.bold);
            p.setTextSize(9.5f * d);
            p.setColor(theme.muted);
            c.drawText(sub, x + 12 * d, y + 43 * d, p);
        }

        private void drawCloudScene(Canvas c, float w, float h, float d) {
            // Left headphone symbol card
            float sx = 18 * d, sy = (h - 76 * d) * 0.5f, sw = 76 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(sx, sy, sx + sw, sy + sw);
            c.drawRoundRect(rect, 22 * d, 22 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 22 * d, 22 * d, p);

            UiTheme.VectorIconDrawable.drawGlyph(c, "headphones", sx + 22 * d, sy + 14 * d, 32 * d, theme.tourBlue, 2.1f * d);
            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(9.5f * d);
            p.setColor(theme.tourBlue);
            c.drawText("PRO", sx + 27 * d, sy + 64 * d, p);

            // Center acoustic waveform bars
            float waveLeft = sx + sw + 12 * d, waveRight = w - 134 * d;
            int bars = 15;
            float span = Math.max(40 * d, waveRight - waveLeft);
            float step = span / bars;
            p.setStrokeCap(Paint.Cap.ROUND);
            p.setStrokeWidth(3.2f * d);
            p.setColor(theme.accent);
            for (int i = 0; i < bars; i++) {
                float ratio = 0.25f + 0.65f * Math.abs((float) Math.sin(i * 0.55f));
                float bh = 74 * d * ratio;
                float x = waveLeft + i * step;
                c.drawLine(x, h * 0.5f - bh * 0.5f, x, h * 0.5f + bh * 0.5f, p);
            }

            // Right price card
            float pw = 118 * d, ph = 104 * d;
            float px = w - pw - 14 * d, py = (h - ph) * 0.5f;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(px, py, px + pw, py + ph);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);

            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(8.2f * d);
            p.setColor(theme.muted);
            c.drawText("GIỌNG PRO CLOUD", px + 12 * d, py + 24 * d, p);

            p.setTypeface(theme.display);
            p.setTextSize(17.5f * d);
            p.setColor(theme.tourBlue);
            c.drawText("Từ 10.000đ", px + 12 * d, py + 54 * d, p);

            p.setTypeface(theme.regular);
            p.setTextSize(10f * d);
            p.setColor(theme.muted);
            c.drawText("Cho một cuốn sách", px + 12 * d, py + 76 * d, p);
            c.drawText("của riêng bạn", px + 12 * d, py + 90 * d, p);
        }

        private void drawReaderScene(Canvas c, float w, float h, float d) {
            float rx = 20 * d, ry = 18 * d, rw = w - 40 * d, rh = h - 36 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(rx, ry, rx + rw, ry + rh);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);

            // Top mini toolbar
            UiTheme.VectorIconDrawable.drawGlyph(c, "book", rx + 14 * d, ry + 12 * d, 15 * d, theme.tourBlue, 1.6f * d);
            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(9.5f * d);
            p.setColor(theme.muted);
            c.drawText("CHƯƠNG 01", rx + 34 * d, ry + 23 * d, p);
            p.setColor(theme.tourBlue);
            c.drawText("Đã lưu vị trí nghe", rx + rw - 102 * d, ry + 23 * d, p);

            // Chapter heading
            p.setTypeface(theme.display);
            p.setTextSize(17f * d);
            p.setColor(theme.ink);
            c.drawText("Chậm lại một chút", rx + 14 * d, ry + 52 * d, p);

            // Highlighted sentence pill
            p.setColor(theme.blueWash);
            rect.set(rx + 12 * d, ry + 64 * d, rx + rw - 12 * d, ry + 92 * d);
            c.drawRoundRect(rect, 8 * d, 8 * d, p);

            p.setTypeface(theme.bold);
            p.setTextSize(11.5f * d);
            p.setColor(theme.ink);
            c.drawText("Có những câu chuyện đáng để lắng nghe thật chậm.", rx + 18 * d, ry + 82 * d, p);

            // Bottom mini player pill
            float py = ry + rh - 42 * d;
            p.setColor(theme.blueWash);
            rect.set(rx + 14 * d, py, rx + rw - 14 * d, py + 30 * d);
            c.drawRoundRect(rect, 99 * d, 99 * d, p);

            UiTheme.VectorIconDrawable.drawGlyph(c, "pause", rx + 24 * d, py + 7 * d, 16 * d, theme.tourBlue, 1.8f * d);
            p.setTypeface(theme.bold);
            p.setTextSize(10.5f * d);
            p.setColor(theme.ink);
            c.drawText("Đang đọc cùng bạn", rx + 46 * d, py + 19 * d, p);
            p.setColor(theme.tourBlue);
            c.drawText("1.0×", rx + rw - 48 * d, py + 19 * d, p);
        }

        private void drawExportScene(Canvas c, float w, float h, float d) {
            // Left vinyl/audio disc
            float cx = 66 * d, cy = h * 0.5f, r = 44 * d;
            p.setStyle(Paint.Style.FILL);
            p.setShader(new RadialGradient(cx, cy, r, 0xFF3969AC, 0xFF1E3B68, Shader.TileMode.CLAMP));
            c.drawCircle(cx, cy, r, p);
            p.setShader(null);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1.2f * d);
            p.setColor(0x55FFFFFF);
            c.drawCircle(cx, cy, r * 0.68f, p);
            UiTheme.VectorIconDrawable.drawGlyph(c, "music", cx - 13 * d, cy - 13 * d, 26 * d, Color.WHITE, 2f * d);

            // Right export card
            float kx = 124 * d, ky = 22 * d, kw = w - kx - 16 * d, kh = h - 44 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(kx, ky, kx + kw, ky + kh);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 18 * d, 18 * d, p);

            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(8.5f * d);
            p.setColor(theme.tourBlue);
            c.drawText("BẢN NGHE CỦA BẠN", kx + 14 * d, ky + 24 * d, p);

            p.setTypeface(theme.display);
            p.setTextSize(14.5f * d);
            p.setColor(theme.ink);
            c.drawText("Câu chuyện, luôn bên mình.", kx + 14 * d, ky + 46 * d, p);

            // Progress tracks
            p.setColor(theme.blueWash);
            rect.set(kx + 14 * d, ky + 62 * d, kx + kw - 14 * d, ky + 70 * d);
            c.drawRoundRect(rect, 4 * d, 4 * d, p);
            p.setColor(theme.accent);
            rect.set(kx + 14 * d, ky + 62 * d, kx + 14 * d + (kw - 28 * d) * 0.82f, ky + 70 * d);
            c.drawRoundRect(rect, 4 * d, 4 * d, p);

            // Format badges
            String[] tags = {"WAV 24kHz", "NGHE NỀN", "OFFLINE"};
            float tx = kx + 14 * d, ty = ky + kh - 34 * d;
            for (String t : tags) {
                float tw = p.measureText(t) + 18 * d;
                p.setColor(theme.blueWash);
                rect.set(tx, ty, tx + tw, ty + 22 * d);
                c.drawRoundRect(rect, 99 * d, 99 * d, p);
                p.setTypeface(theme.bold);
                p.setTextSize(9f * d);
                p.setColor(theme.tourBlue);
                c.drawText(t, tx + 9 * d, ty + 14.5f * d, p);
                tx += tw + 6 * d;
            }
        }

        private void drawStartScene(Canvas c, float w, float h, float d) {
            float tx = 20 * d, ty = 18 * d, tw = w - 40 * d, th = h - 36 * d;
            p.setStyle(Paint.Style.FILL);
            p.setColor(theme.tourPaper);
            rect.set(tx, ty, tx + tw, ty + th);
            c.drawRoundRect(rect, 20 * d, 20 * d, p);
            p.setStyle(Paint.Style.STROKE);
            p.setStrokeWidth(1f * d);
            p.setColor(theme.edge);
            c.drawRoundRect(rect, 20 * d, 20 * d, p);

            p.setStyle(Paint.Style.FILL);
            p.setTypeface(theme.bold);
            p.setTextSize(9f * d);
            p.setColor(theme.tourBlue);
            c.drawText("THƯ VIỆN SÁCH NÓI CỦA BẠN", tx + 16 * d, ty + 26 * d, p);

            // 5 mini book icons row matching Mac's 5-book shelf
            int count = 5;
            float gap = 8 * d;
            float cellW = (tw - 32 * d - gap * (count - 1)) / count;
            float cellY = ty + 38 * d, cellH = 54 * d;
            for (int i = 0; i < count; i++) {
                float cx = tx + 16 * d + i * (cellW + gap);
                p.setStyle(Paint.Style.FILL);
                p.setColor(theme.tourArt);
                rect.set(cx, cellY, cx + cellW, cellY + cellH);
                c.drawRoundRect(rect, 11 * d, 11 * d, p);
                UiTheme.VectorIconDrawable.drawGlyph(c, "book", cx + cellW * 0.5f - 9 * d, cellY + 9 * d, 18 * d, theme.tourBlue, 1.6f * d);
                p.setTypeface(theme.bold);
                p.setTextSize(9f * d);
                p.setColor(theme.muted);
                c.drawText("0" + (i + 1), cx + cellW * 0.5f - 6 * d, cellY + 44 * d, p);
            }

            p.setTypeface(theme.display);
            p.setTextSize(18f * d);
            p.setColor(theme.ink);
            c.drawText("Lite miễn phí · Pro theo cuốn", tx + 16 * d, ty + 122 * d, p);

            p.setTypeface(theme.regular);
            p.setTextSize(11.5f * d);
            p.setColor(theme.muted);
            c.drawText("5 lượt thử mở đầu miễn phí (tối đa 5.000 ký tự / lượt)", tx + 16 * d, ty + 144 * d, p);
        }
    }
}
