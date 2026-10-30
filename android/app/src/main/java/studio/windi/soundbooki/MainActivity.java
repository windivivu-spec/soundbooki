package studio.windi.soundbooki;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.res.ColorStateList;
import android.graphics.*;
import android.graphics.drawable.*;
import android.net.Uri;
import android.os.*;
import android.text.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends Activity {
    private static final int IMPORT = 31, EXPORT = 32;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final WelcomeAudioPlayer welcomeAudio = new WelcomeAudioPlayer();

    private UiTheme theme;
    private BookStore store;
    private JSONObject book;
    private EditText title, editor;
    private Spinner voices, chapterSpinner;
    private TextView subtitle, status, metrics, counts, speedBadge;
    private ProgressBar progress;
    private Button play, pause, stop, cloudButton, export, resumeImport, walkthroughHeroBtn;
    private Button openReaderBtn, cleanupBtn, reflowBtn, audioLibraryBtn;
    private ImageButton walkthroughHeaderBtn, readerHeaderBtn, audioHeaderBtn;
    private UiTheme.PlayerArtView playerArt;
    private LinearLayout root, body, heroCard;
    private ScrollView scroll;
    private boolean binding = false;
    private volatile boolean working = false, resumed = false;
    private List<String> voiceNames;
    private List<PdfReflow.ChapterItem> currentChapters = new ArrayList<>();
    private String lastStatus = "";
    private int ink, muted, surface, blue, bg, line;
    private AlertDialog cloudDialog;
    private CloudPanel cloudPanel;
    private WalkthroughDialog walkthroughDialog;
    private List<File> exportFiles;
    private boolean exportM4b=false;
    private volatile boolean exportCancelled=false;
    private JSONObject exportSnapshot;
    private List<Mp4BookMetadata.Chapter> exportChapters=new ArrayList<>();
    private AppShell appShell;
    private Dialog voiceDialog;
    private ReaderDialog readerDialog;
    private LinearLayout editorHeader,editorTransport;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        store = new BookStore(this);
        com.tom_roush.pdfbox.android.PDFBoxResourceLoader.init(getApplicationContext());
        theme = new UiTheme(this);
        ink = theme.ink;
        muted = theme.muted;
        surface = theme.surface;
        bg = theme.canvas;
        line = theme.line;
        blue = theme.accent;

        getWindow().setStatusBarColor(bg);
        getWindow().setNavigationBarColor(bg);
        if (!theme.dark) {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }

        root = new UiTheme.AmbientRootLayout(this, theme);
        root.setOrientation(LinearLayout.VERTICAL);
        setContentView(root);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            Insets safe = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
            v.setPadding(dp(16), safe.top + dp(8), dp(16), safe.bottom + dp(8));
            return insets;
        });

        // 1. Glassmorphic Brand Header
        LinearLayout header = row();
        editorHeader = header;
        header.setBackground(theme.card(theme.glass, theme.edge, 22));
        header.setPadding(dp(14), dp(10), dp(10), dp(10));
        header.setElevation(dp(2));

        ImageView mark = new ImageView(this);
        mark.setImageResource(R.drawable.brand_logo);
        mark.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        header.addView(mark, new LinearLayout.LayoutParams(dp(34), dp(38)));

        ImageView name = new ImageView(this);
        name.setImageResource(R.drawable.brand_wordmark);
        name.setContentDescription("Soundbooki");
        name.setScaleType(ImageView.ScaleType.FIT_START);
        LinearLayout.LayoutParams nameSize = new LinearLayout.LayoutParams(0, dp(28), 1f);
        nameSize.setMargins(dp(10), 0, dp(8), 0);
        header.addView(name, nameSize);

        readerHeaderBtn = new ImageButton(this);
        readerHeaderBtn.setImageDrawable(theme.icon("book", blue, 20));
        readerHeaderBtn.setBackground(theme.chipBackground(surface, theme.edge, 15));
        readerHeaderBtn.setContentDescription("Mở view đọc sách");
        LinearLayout.LayoutParams readerBtnLp = new LinearLayout.LayoutParams(dp(44), dp(44));
        readerBtnLp.rightMargin = dp(6);
        header.addView(readerHeaderBtn, readerBtnLp);
        readerHeaderBtn.setOnClickListener(v -> openReader());

        audioHeaderBtn = new ImageButton(this);
        audioHeaderBtn.setImageDrawable(theme.icon("headphones", blue, 20));
        audioHeaderBtn.setBackground(theme.chipBackground(surface, theme.edge, 15));
        audioHeaderBtn.setContentDescription("Sách nói đã tạo");
        LinearLayout.LayoutParams audioBtnLp = new LinearLayout.LayoutParams(dp(44), dp(44));
        audioBtnLp.rightMargin = dp(6);
        header.addView(audioHeaderBtn, audioBtnLp);
        audioHeaderBtn.setOnClickListener(v -> openAudioLibrary());

        walkthroughHeaderBtn = new ImageButton(this);
        walkthroughHeaderBtn.setImageDrawable(theme.icon("compass", blue, 20));
        walkthroughHeaderBtn.setBackground(theme.chipBackground(surface, theme.edge, 15));
        walkthroughHeaderBtn.setContentDescription("Khám phá ứng dụng · 5 bước");
        LinearLayout.LayoutParams tourBtnLp = new LinearLayout.LayoutParams(dp(44), dp(44));
        tourBtnLp.rightMargin = dp(6);
        header.addView(walkthroughHeaderBtn, tourBtnLp);
        walkthroughHeaderBtn.setOnClickListener(v -> openWalkthrough());

        ImageButton settings = new ImageButton(this);
        settings.setImageDrawable(theme.icon("settings", blue, 20));
        settings.setBackground(theme.chipBackground(surface, theme.edge, 15));
        settings.setContentDescription("Cài đặt nghe và Cloud");
        header.addView(settings, new LinearLayout.LayoutParams(dp(44), dp(44)));
        settings.setOnClickListener(v -> settings());
        root.addView(header);

        // 2. Scrollable Document & Controls Surface
        scroll = new ScrollView(this);
        scroll.setFillViewport(false);
        scroll.setVerticalScrollBarEnabled(true);
        scroll.setScrollbarFadingEnabled(true);
        body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(0, dp(10), 0, dp(14));
        scroll.addView(body);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1f));

        // 3. Hero Banner Card (Mac-synchronized book illustration + typography + 5-step tour button)
        heroCard = new LinearLayout(this);
        heroCard.setVisibility(View.GONE);
        heroCard.setOrientation(LinearLayout.VERTICAL);
        heroCard.setBackground(theme.card(theme.glass, theme.edge, 22));
        heroCard.setPadding(dp(14), dp(12), dp(14), dp(12));

        LinearLayout heroTop = row();
        LinearLayout heroCopy = new LinearLayout(this);
        heroCopy.setOrientation(LinearLayout.VERTICAL);

        TextView eyebrow = text("GÓC ĐỌC & NGHE RIÊNG", 10, true);
        eyebrow.setTextColor(blue);
        eyebrow.setLetterSpacing(0.08f);
        heroCopy.addView(eyebrow);

        TextView headline = display("Một khoảng riêng\nđể lắng nghe.", 23);
        LinearLayout.LayoutParams headLp = new LinearLayout.LayoutParams(-1, -2);
        headLp.topMargin = dp(2);
        heroCopy.addView(headline, headLp);

        subtitle = text("Lite tiếng Việt trên điện thoại. Chọn sách hoặc dán chữ, rồi bấm Nghe.", 12, false);
        subtitle.setTextColor(muted);
        LinearLayout.LayoutParams subLp = new LinearLayout.LayoutParams(-1, -2);
        subLp.topMargin = dp(4);
        heroCopy.addView(subtitle, subLp);

        heroTop.addView(heroCopy, new LinearLayout.LayoutParams(0, -2, 1f));

        UiTheme.HeroIllustrationView heroArt = new UiTheme.HeroIllustrationView(this, theme);
        LinearLayout.LayoutParams artLp = new LinearLayout.LayoutParams(dp(96), dp(96));
        artLp.leftMargin = dp(8);
        heroTop.addView(heroArt, artLp);
        heroCard.addView(heroTop);

        walkthroughHeroBtn = new Button(this);
        walkthroughHeroBtn.setText("Khám phá ứng dụng · 5 bước");
        walkthroughHeroBtn.setAllCaps(false);
        walkthroughHeroBtn.setTextSize(13.5f);
        walkthroughHeroBtn.setTypeface(theme.bold);
        walkthroughHeroBtn.setTextColor(theme.tourBlue);
        walkthroughHeroBtn.setBackground(theme.chipBackground(theme.blueWash, theme.edge, 14));
        walkthroughHeroBtn.setCompoundDrawablesWithIntrinsicBounds(theme.icon("compass", theme.tourBlue, 18), null, null, null);
        walkthroughHeroBtn.setCompoundDrawablePadding(dp(8));
        walkthroughHeroBtn.setPadding(dp(14), 0, dp(14), 0);
        walkthroughHeroBtn.setMinHeight(dp(48));
        LinearLayout.LayoutParams wtLp = new LinearLayout.LayoutParams(-1, dp(48));
        wtLp.topMargin = dp(10);
        heroCard.addView(walkthroughHeroBtn, wtLp);
        walkthroughHeroBtn.setOnClickListener(v -> openWalkthrough());

        body.addView(heroCard);

        resumeImport = button("Tiếp tục nhập các trang còn lại", false, "book");
        LinearLayout.LayoutParams resumeLp = new LinearLayout.LayoutParams(-1, dp(48));
        resumeLp.bottomMargin = dp(8);
        body.addView(resumeImport, resumeLp);
        resumeImport.setOnClickListener(v -> resumeImport());

        // 5. Book Editor Surface Card
        LinearLayout docCard = new LinearLayout(this);
        docCard.setOrientation(LinearLayout.VERTICAL);
        docCard.setBackground(theme.card(surface, theme.edge, 20));
        docCard.setPadding(dp(14), dp(12), dp(14), dp(12));

        TextView titleLabel = text("TÊN SÁCH", 10, true);
        titleLabel.setLetterSpacing(0.10f);
        titleLabel.setTextColor(muted);
        docCard.addView(titleLabel);

        title = new EditText(this);
        title.setSingleLine(true);
        title.setTextColor(ink);
        title.setHintTextColor(muted);
        title.setTextSize(17.5f);
        title.setTypeface(theme.display);
        title.setHint("Tên cuốn sách");
        title.setContentDescription("Tên cuốn sách");
        title.setBackground(theme.card(theme.card, theme.edge, 14));
        title.setPadding(dp(12), dp(8), dp(12), dp(8));
        LinearLayout.LayoutParams titleInputLp = new LinearLayout.LayoutParams(-1, dp(48));
        titleInputLp.topMargin = dp(4);
        docCard.addView(title, titleInputLp);

        // Chapter selector
        LinearLayout chapterRow = row();
        LinearLayout.LayoutParams crLp = new LinearLayout.LayoutParams(-1, -2);
        crLp.topMargin = dp(10);
        TextView chLabel = text("CHƯƠNG", 10, true);
        chLabel.setLetterSpacing(0.10f);
        chLabel.setTextColor(muted);
        chapterRow.addView(chLabel, new LinearLayout.LayoutParams(dp(72), dp(44)));

        chapterSpinner = new Spinner(this);
        new MobileUi(this,theme).styleSpinner(chapterSpinner);
        chapterSpinner.setContentDescription("Chọn chương sách");
        chapterSpinner.setBackground(theme.card(theme.card, theme.edge, 14));
        chapterSpinner.setPadding(dp(10), 0, dp(10), 0);
        chapterRow.addView(chapterSpinner, new LinearLayout.LayoutParams(0, dp(44), 1f));
        docCard.addView(chapterRow, crLp);
        Button markChapter = button("Đặt mốc chương tại con trỏ", false, "book");
        markChapter.setOnClickListener(v -> markChapter());
        docCard.addView(markChapter, new LinearLayout.LayoutParams(-1, dp(48)));

        chapterSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onNothingSelected(AdapterView<?> p) {}
            public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
                if (binding || at <= 0 || at - 1 >= currentChapters.size()) return;
                PdfReflow.ChapterItem ch = currentChapters.get(at - 1);
                int pos = Math.min(ch.startChar, editor.getText().length());
                editor.setSelection(pos);
            }
        });

        // Reading view button (Full screen reader)
        openReaderBtn = button("Đọc sách toàn màn hình", true, "book");
        openReaderBtn.setContentDescription("Mở giao diện đọc sách toàn màn hình");
        LinearLayout.LayoutParams orbLp = new LinearLayout.LayoutParams(-1, dp(48));
        orbLp.topMargin = dp(10);
        docCard.addView(openReaderBtn, orbLp);
        openReaderBtn.setOnClickListener(v -> openReader());

        // 3-Utility Tools Strip: Cleanup, Reflow, Audio Library
        LinearLayout toolStrip = row();
        LinearLayout.LayoutParams tsLp = new LinearLayout.LayoutParams(-1, -2);
        tsLp.topMargin = dp(8);

        cleanupBtn = button("Dọn nội dung", false, "sparkles");
        cleanupBtn.setContentDescription("Dọn tiêu đề, số trang và lỗi OCR");
        toolStrip.addView(cleanupBtn, new LinearLayout.LayoutParams(0, dp(44), 1f));

        reflowBtn = button("Bố cục PDF", false, "reflow");
        reflowBtn.setContentDescription("Nối dòng ngắt đoạn và sắp xếp chương");
        LinearLayout.LayoutParams rfLp = new LinearLayout.LayoutParams(0, dp(44), 1f);
        rfLp.leftMargin = dp(8);
        toolStrip.addView(reflowBtn, rfLp);

        audioLibraryBtn = button("Sách nói", false, "headphones");
        audioLibraryBtn.setContentDescription("Thư viện audio đã tạo");
        LinearLayout.LayoutParams alLp = new LinearLayout.LayoutParams(0, dp(44), 1f);
        alLp.leftMargin = dp(8);
        toolStrip.addView(audioLibraryBtn, alLp);

        docCard.addView(toolStrip, tsLp);

        cleanupBtn.setOnClickListener(v -> openCleanup());
        reflowBtn.setOnClickListener(v -> reflowPdfLayout());
        audioLibraryBtn.setOnClickListener(v -> openAudioLibrary());

        LinearLayout contentHeader = row();
        LinearLayout.LayoutParams chLp = new LinearLayout.LayoutParams(-1, -2);
        chLp.topMargin = dp(10);
        chLp.bottomMargin = dp(4);
        TextView label = text("NỘI DUNG", 10, true);
        label.setLetterSpacing(0.10f);
        label.setTextColor(muted);
        contentHeader.addView(label, new LinearLayout.LayoutParams(0, -2, 1f));
        counts = text("", 11, false);
        counts.setTextColor(muted);
        contentHeader.addView(counts);
        docCard.addView(contentHeader, chLp);

        editor = new EditText(this);
        editor.setTextColor(ink);
        editor.setHintTextColor(muted);
        editor.setTextSize(15.5f);
        editor.setTypeface(theme.regular);
        editor.setGravity(Gravity.TOP);
        editor.setMinLines(6);
        editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        editor.setBackground(theme.card(theme.card, theme.edge, 16));
        editor.setPadding(dp(12), dp(10), dp(12), dp(10));
        editor.setHint("Dán một đoạn tiếng Việt để nghe thử…");
        editor.setContentDescription("Nội dung sách, có thể chỉnh sửa");
        editor.setLineSpacing(dp(3), 1.04f);
        editor.setNestedScrollingEnabled(false);
        docCard.addView(editor, new LinearLayout.LayoutParams(-1, -2));

        // Voice selector row inside Document Card
        LinearLayout voiceRow = row();
        LinearLayout.LayoutParams vrLp = new LinearLayout.LayoutParams(-1, -2);
        vrLp.topMargin = dp(10);
        TextView voiceLabel = text("Giọng Lite", 13, true);
        voiceLabel.setGravity(Gravity.CENTER_VERTICAL);
        voiceLabel.setCompoundDrawablesWithIntrinsicBounds(theme.icon("wave", blue, 17), null, null, null);
        voiceLabel.setCompoundDrawablePadding(dp(6));
        voiceRow.addView(voiceLabel, new LinearLayout.LayoutParams(dp(106), dp(48)));

        voices = new Spinner(this);
        new MobileUi(this,theme).styleSpinner(voices);
        voices.setContentDescription("Giọng Lite tiếng Việt");
        voices.setBackground(theme.card(theme.card, theme.edge, 14));
        voices.setPadding(dp(10), 0, dp(10), 0);
        voiceRow.addView(voices, new LinearLayout.LayoutParams(0, dp(48), 1f));
        docCard.addView(voiceRow, vrLp);

        try (InputStream in = getAssets().open("nano/voices.json")) {
            JSONObject preset = new JSONObject(new String(in.readAllBytes(), StandardCharsets.UTF_8)).getJSONObject("presets");
            voiceNames = new ArrayList<>();
            preset.keys().forEachRemaining(voiceNames::add);
            voiceNames.sort(String::compareTo);
            voiceNames.remove("Đức Trí");
            voiceNames.add(0, "Đức Trí");
        } catch (Exception e) {
            voiceNames = List.of("Đức Trí");
        }
        ArrayAdapter<String> adapter = new MobileUi(this,theme).spinnerAdapter(voiceNames.toArray(new String[0]));
        voices.setAdapter(adapter);

        body.addView(docCard);

        // 6. Cloud, Export & Original Text Actions (Large 50dp buttons, visible above fold)
        LinearLayout actions = row();
        LinearLayout.LayoutParams actLp = new LinearLayout.LayoutParams(-1, -2);
        actLp.topMargin = dp(10);
        cloudButton = button("Pro Cloud", false, "headphones");
        export = button("Xuất WAV", false, "export");
        actions.addView(cloudButton, new LinearLayout.LayoutParams(0, dp(50), 1f));
        LinearLayout.LayoutParams half2 = new LinearLayout.LayoutParams(0, dp(50), 1f);
        half2.leftMargin = dp(10);
        actions.addView(export, half2);
        body.addView(actions, actLp);
        cloudButton.setOnClickListener(v -> openCloud());
        export.setOnClickListener(v -> export());

        Button original = button("Xem chữ gốc", false, "original");
        LinearLayout.LayoutParams origLp = new LinearLayout.LayoutParams(-1, dp(48));
        origLp.topMargin = dp(8);
        body.addView(original, origLp);
        original.setOnClickListener(v -> {
            if (book != null) {
                MobileUi.showAlert(this,theme,new AlertDialog.Builder(this)
                    .setTitle("Bản chữ gốc")
                    .setMessage(book.optString("originalText"))
                    .setPositiveButton("Đóng", null)
                );
            }
        });

        // 7. Sticky Glassmorphic Player Dock
        LinearLayout player = new LinearLayout(this);
        editorTransport = player;
        player.setOrientation(LinearLayout.VERTICAL);
        player.setPadding(dp(16), dp(14), dp(16), dp(14));
        player.setBackground(theme.card(theme.glass, theme.edge, 24));
        player.setElevation(dp(6));
        root.addView(player, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout playerHead = row();
        playerArt = new UiTheme.PlayerArtView(this, theme);
        playerHead.addView(playerArt, new LinearLayout.LayoutParams(dp(44), dp(44)));

        LinearLayout statusCol = new LinearLayout(this);
        statusCol.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams scLp = new LinearLayout.LayoutParams(0, -2, 1f);
        scLp.leftMargin = dp(12);
        scLp.rightMargin = dp(8);

        status = text("Sẵn sàng để nghe", 14, true);
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        statusCol.addView(status);

        metrics = text("Nano · 16 bước · Audio lưu trên máy", 11, false);
        metrics.setTextColor(muted);
        LinearLayout.LayoutParams metLp = new LinearLayout.LayoutParams(-1, -2);
        metLp.topMargin = dp(2);
        statusCol.addView(metrics, metLp);
        playerHead.addView(statusCol, scLp);

        speedBadge = text(formatSpeed(getSharedPreferences("settings", MODE_PRIVATE).getFloat("speed", 1f)), 12, true);
        speedBadge.setTextColor(theme.tourBlue);
        speedBadge.setBackground(theme.chipBackground(theme.blueWash, theme.edge, 99));
        speedBadge.setPadding(dp(10), dp(6), dp(10), dp(6));
        speedBadge.setContentDescription("Tốc độ phát hiện tại, bấm để mở cài đặt");
        speedBadge.setOnClickListener(v -> settings());
        playerHead.addView(speedBadge, new LinearLayout.LayoutParams(-2, -2));
        player.addView(playerHead);

        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgressTintList(ColorStateList.valueOf(blue));
        progress.setProgressBackgroundTintList(ColorStateList.valueOf(line));
        LinearLayout.LayoutParams progLp = new LinearLayout.LayoutParams(-1, dp(8));
        progLp.topMargin = dp(10);
        progLp.bottomMargin = dp(10);
        player.addView(progress, progLp);

        LinearLayout controls = row();
        play = button("Nghe", true, "play");
        pause = button("Tạm dừng", false, "pause");
        stop = button("Dừng", false, "stop");
        Button[] transport = {play, pause, stop};
        float[] weights = {1.2f, 1.05f, 0.9f};
        for (int i = 0; i < transport.length; i++) {
            Button b = transport[i];
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(52), weights[i]);
            if (i > 0) p.leftMargin = dp(8);
            controls.addView(b, p);
        }
        player.addView(controls);

        play.setOnClickListener(v -> listen(false));
        play.setOnLongClickListener(v -> { listen(true); return true; });
        play.setContentDescription("Nghe tiếp sách. Nhấn giữ để nghe từ đầu.");
        pause.setOnClickListener(v -> command("pause"));
        stop.setOnClickListener(v -> command("stop"));

        TextWatcher watcher = new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int c, int f) {}
            public void onTextChanged(CharSequence s, int a, int before, int count) {
                if (binding) return;
                if (PlaybackService.running && book != null && book.optString("id").equals(PlaybackService.bookId)) {
                    command("stop");
                }
                handler.removeCallbacks(saveTask);
                handler.postDelayed(saveTask, 450);
                counts.setText(editor.getText().toString().codePointCount(0, editor.length()) + " ký tự · Tự lưu trên máy");
            }
            public void afterTextChanged(Editable e) {}
        };
        title.addTextChangedListener(watcher);
        editor.addTextChangedListener(watcher);

        voices.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onNothingSelected(AdapterView<?> p) {}
            public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
                if (binding || book == null || voiceNames.get(at).equals(book.optString("voice"))) return;
                if (PlaybackService.running) command("stop");
                saveCurrent();
            }
        });

        String saved = getPreferences(MODE_PRIVATE).getString("book", "");
        boolean hadSavedBook = !saved.isEmpty();
        try {
            if (hadSavedBook) book = store.load(saved);
        } catch (Exception ignored) {}
        boolean emptyLibraryAtLaunch = false;
        if (book == null) {
            try {
                List<JSONObject> books = store.books();
                emptyLibraryAtLaunch = books.isEmpty() && !hadSavedBook;
                book = books.isEmpty() ? store.create("Một trang sách mới", "", null) : books.get(0);
            } catch (Exception e) {
                error(e);
            }
        }
        bindBook();
        editorHeader.setVisibility(View.GONE);
        editorTransport.setVisibility(View.GONE);
        root.setOnApplyWindowInsetsListener(null);
        root.setPadding(0, 0, 0, 0);
        if (root.getParent() != null) ((ViewGroup)root.getParent()).removeView(root);
        appShell = new AppShell(this, theme, store, root);
        setContentView(appShell);
        getOnBackInvokedDispatcher().registerOnBackInvokedCallback(0, () -> { if (!appShell.back()) finish(); });

        Bundle reading=state==null?null:state.getBundle("readerState");
        if(reading!=null&&book!=null&&book.optString("id").equals(reading.getString("book"))&&BookStore.hash(book.optString("text")).equals(reading.getString("hash"))){
            handler.post(()->{if(!isFinishing()&&!isDestroyed()){ReaderDialog reader=new ReaderDialog(this,theme,store,book,c->appPlay(c,false,false)).startAt(reading.getInt("offset",0));reader.show();reader.restoreChrome(reading.getBoolean("chrome",true));}});
        }

        // Auto-open 5-step Walkthrough on first-ever empty-library launch (matches Mac behavior)
        SharedPreferences settingsPrefs = getSharedPreferences("settings", MODE_PRIVATE);
        if (emptyLibraryAtLaunch && !settingsPrefs.getBoolean(WalkthroughDialog.PREF_SEEN, false) && !isIncomingFileIntent(getIntent())) {
            handler.postDelayed(this::openWalkthrough, 250);
        }
        handleIncomingIntent(getIntent());
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncomingIntent(intent);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        Uri uri = Intent.ACTION_VIEW.equals(action) ? intent.getData() : null;
        if (Intent.ACTION_SEND.equals(action)) {
            uri = (Uri) intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (uri == null && intent.getClipData() != null && intent.getClipData().getItemCount() > 0) uri = intent.getClipData().getItemAt(0).getUri();
        }
        if (uri != null) beginImport(uri);
    }

    private static boolean isIncomingFileIntent(Intent intent) {
        return intent != null && (Intent.ACTION_VIEW.equals(intent.getAction()) || Intent.ACTION_SEND.equals(intent.getAction()));
    }

    private static String formatSpeed(float rate) {
        if (Math.abs(rate - Math.round(rate)) < 0.01f) {
            return Math.round(rate) + "×";
        }
        return String.valueOf(rate).replace('.', ',') + "×";
    }

    public WalkthroughDialog openWalkthrough() {
        if (walkthroughDialog != null && walkthroughDialog.isShowing()) {
            return walkthroughDialog;
        }
        if (PlaybackService.running) {
            command("stop");
        }
        walkthroughDialog = new WalkthroughDialog(
            this,
            theme,
            welcomeAudio,
            () -> {
                if (book == null || book.optString("text").trim().isEmpty()) {
                    editor.requestFocus();
                    status.setText("Chọn Thêm sách hoặc dán chữ tiếng Việt để nghe ngay.");
                } else {
                    listen(false);
                }
            },
            this::openCloud
        );
        walkthroughDialog.show();
        return walkthroughDialog;
    }

    public WalkthroughDialog getWalkthroughDialog() {
        return walkthroughDialog;
    }

    private int dp(float n) {
        return Math.round(n * getResources().getDisplayMetrics().density);
    }

    private TextView display(String s, int size) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setTextColor(ink);
        t.setTypeface(theme.display);
        t.setLineSpacing(dp(2), 1.02f);
        return t;
    }

    private TextView text(String s, int size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setTextColor(ink);
        t.setTypeface(bold ? theme.bold : theme.regular);
        t.setLineSpacing(dp(2), 1.05f);
        return t;
    }

    private LinearLayout row() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        return r;
    }

    private Button button(String label, boolean primary) {
        return button(label, primary, null);
    }

    private Button button(String label, boolean primary, String iconKind) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(14f);
        b.setTypeface(theme.bold);
        b.setAllCaps(false);
        int[][] states = {new int[]{android.R.attr.state_enabled}, new int[]{}};
        int enabledColor = primary ? Color.WHITE : blue;
        b.setTextColor(new ColorStateList(states, new int[]{enabledColor, muted}));
        b.setBackground(theme.buttonBackground(primary, 16));
        b.setMinHeight(dp(50));
        b.setPadding(dp(12), 0, dp(12), 0);
        if (iconKind != null) {
            b.setCompoundDrawablesWithIntrinsicBounds(theme.icon(iconKind, enabledColor, 17), null, null, null);
            b.setCompoundDrawablePadding(dp(6));
        }
        return b;
    }

    private void margin(View v, int top, int bottom) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.topMargin = dp(top);
        p.bottomMargin = dp(bottom);
        v.setLayoutParams(p);
    }

    private void bindBook() {
        if (book == null) return;
        binding = true;
        boolean complete = "ready".equals(book.optString("status", "ready"));
        editor.setEnabled(complete);
        resumeImport.setVisibility(complete ? View.GONE : View.VISIBLE);
        title.setText(book.optString("title"));
        editor.setText(book.optString("text"));
        int at = voiceNames.indexOf(book.optString("voice"));
        voices.setSelection(Math.max(0, at));
        updateChapterSpinner();
        counts.setText(editor.getText().toString().codePointCount(0, editor.length()) + " ký tự · Tự lưu trên máy");
        binding = false;
        if (!BookChapters.REVISION.equals(book.optString("chapterRevision")) &&
                ("pdf".equals(book.optString("sourceFormat")) || book.optJSONArray("sourceHeadings") != null)) {
            String id = book.optString("id");
            status.setText("Đang đọc mốc chương từ file gốc trên máy…");
            io.execute(() -> {
                try {
                    BookImporter.refreshChapters(store, id);
                    runOnUiThread(() -> { if (book != null && id.equals(book.optString("id"))) { saveCurrent(); updateChapterSpinner(); status.setText("Đã cập nhật " + currentChapters.size() + " phần từ mốc trong sách."); } });
                } catch (Exception e) { runOnUiThread(() -> status.setText("Chưa đọc được mốc chương từ nguồn. Có thể đặt mốc thủ công tại con trỏ.")); }
            });
        }
        getPreferences(MODE_PRIVATE).edit().putString("book", book.optString("id")).apply();
    }

    private final Runnable saveTask = this::saveCurrent;

    private void saveCurrent() {
        if (binding || book == null) return;
        try {
            synchronized (BookStore.LOCK) {
                JSONObject latest = store.load(book.getString("id"));
                String text = editor.getText().toString(), voice = voiceNames.get(voices.getSelectedItemPosition());
                boolean complete = "ready".equals(latest.optString("status", "ready"));
                if (!complete) {
                    latest.put("title", title.getText().toString());
                    store.save(latest);
                    book = latest;
                    return;
                }
                boolean changed = !text.equals(latest.optString("text")) || !voice.equals(latest.optString("voice"));
                latest.put("title", title.getText().toString().trim().isEmpty() ? "Sách của tôi" : title.getText().toString().trim())
                    .put("text", text)
                    .put("voice", voice);
                if (!text.equals(book.optString("text"))) {
                    latest.remove("chaptersTextHash"); latest.remove("chapters"); latest.remove("readerOffset");
                }
                if (changed) latest.put("position", 0).put("positionMs", 0).put("positionChar", 0);
                store.save(latest);
                book = latest;
            }
        } catch (Exception e) {
            error(e);
        }
    }

    private void pick() {
        saveCurrent();
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType("*/*");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/epub+zip", "application/pdf", "text/plain", "text/markdown"});
        startActivityForResult(i, IMPORT);
    }

    private void beginImport(Uri uri) {
        if (working) {
            Toast.makeText(this, "App đang xử lý một tác vụ. Vui lòng thử lại sau.", Toast.LENGTH_LONG).show();
            return;
        }
        saveCurrent();
        working = true;
        status.setText("Đang nhập sách trên điện thoại…");
        io.submit(() -> {
            try {
                JSONObject imported = BookImporter.importFile(this, uri, store);
                runOnUiThread(() -> {
                    book = imported;
                    bindBook();
                    if (appShell != null) appShell.showImported();
                    status.setText("Đã nhập. Bạn có thể sửa chữ rồi bấm Nghe.");
                });
            } catch (Exception e) {
                runOnUiThread(() -> error(e));
            } finally {
                working = false;
            }
        });
    }

    private void library() {
        saveCurrent();
        List<JSONObject> list = store.books();
        String[] names = new String[list.size()+1];
        for(int n=0;n<list.size();n++)names[n]=list.get(n).optString("title");
        names[list.size()]="＋ Sách trống mới";
        MobileUi.options(this,theme,"Thư viện trên máy",names,which->{
            if(which<list.size()){book=list.get(which);bindBook();if(appShell!=null)appShell.showImported();}
            else try{book=store.create("Sách mới","",null);bindBook();if(appShell!=null)appShell.showEditor();}
            catch(Exception e){error(e);}
        });
    }

    private void resumeImport() {
        if (book == null || working) return;
        working = true;
        status.setText("Đang tiếp tục từ trang đã lưu…");
        JSONObject pending = book;
        io.submit(() -> {
            try {
                JSONObject ready = BookImporter.resume(pending, store);
                runOnUiThread(() -> {
                    book = ready;
                    bindBook();
                    status.setText("Đã nhập xong sách.");
                });
            } catch (Exception e) {
                runOnUiThread(() -> error(e));
            } finally {
                working = false;
            }
        });
    }

    private void listen(boolean beginning) {
        ((android.view.inputmethod.InputMethodManager) getSystemService(INPUT_METHOD_SERVICE))
            .hideSoftInputFromWindow(editor.getWindowToken(), 0);
        saveCurrent();
        int selectedChapter = chapterSpinner == null ? -1 : chapterSpinner.getSelectedItemPosition() - 1;
        updateChapterSpinner();
        if (selectedChapter >= 0 && selectedChapter < currentChapters.size()) chapterSpinner.setSelection(selectedChapter + 1);
        if (book == null || !"ready".equals(book.optString("status", "ready")) || book.optString("text").trim().isEmpty()) {
            status.setText("Thêm sách hoặc dán chữ để bắt đầu.");
            return;
        }
        if (book.optString("text").codePointCount(0, book.optString("text").length()) > 2_000_000) {
            error(new IOException("Sách vượt 2 triệu ký tự."));
            return;
        }
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 42);
        }
        startForegroundService(new Intent(this, PlaybackService.class)
            .setAction("local")
            .putExtra("book", book.optString("id"))
            .putExtra("beginning", beginning)
            .putExtra("chapter", !beginning && chapterSpinner != null ? chapterSpinner.getSelectedItemPosition() - 1 : -1));
    }

    private void command(String action) {
        if (!PlaybackService.running) return;
        startService(new Intent(this, PlaybackService.class).setAction(action));
    }

    private final Runnable refresh = new Runnable() {
        public void run() {
            if (book != null && book.optString("id").equals(PlaybackService.bookId)) {
                String now = PlaybackService.message;
                if (!now.equals(lastStatus)) {
                    status.setText(now);
                    lastStatus = now;
                }
                if (!PlaybackService.metrics.isEmpty()) metrics.setText(PlaybackService.metrics);
                progress.setProgress(PlaybackService.total > 0 ? PlaybackService.ready * 100 / PlaybackService.total : 0);
                pause.setEnabled(PlaybackService.running);
                stop.setEnabled(PlaybackService.running);
                pause.setText(PlaybackService.paused ? "Nghe tiếp" : "Tạm dừng");
                playerArt.setPlaying(PlaybackService.playing && !PlaybackService.paused);
            } else {
                pause.setEnabled(false);
                stop.setEnabled(false);
                playerArt.setPlaying(false);
            }
            play.setEnabled(!working);
            if (appShell != null) appShell.refreshPlayer();
            handler.postDelayed(this, 500);
        }
    };

    void appExport(){
        saveCurrent();if(book==null)return;
        List<PdfReflow.ChapterItem> chapters=BookChapters.get(book);String[] choices=new String[chapters.size()+1];choices[0]="Toàn bộ sách";for(int i=0;i<chapters.size();i++)choices[i+1]=chapters.get(i).title;
        MobileUi.options(this,theme,"Phạm vi xuất sách nói",choices,i->{chapterSpinner.setSelection(i);export();});
    }
    private void export() {
        saveCurrent();if(book==null)return;
        MobileUi.options(this,theme,"Định dạng sách nói",new String[]{"M4B · Chương và bìa","WAV · Âm thanh chưa nén"},format->{
            try{
                exportM4b=format==0;exportSnapshot=new JSONObject(book.toString());
                SharedPreferences prefs=getSharedPreferences("settings",MODE_PRIVATE);
                if(!exportSnapshot.has("bgmTrack"))exportSnapshot.put("bgmTrack",prefs.getString("bgmTrack","none")).put("bgmVolume",prefs.getFloat("bgmVolume",.18f));
                int selected=chapterSpinner.getSelectedItemPosition()-1;BookChapters.Plan plan=new BookChapters.Plan(exportSnapshot);exportFiles=new ArrayList<>();exportChapters=new ArrayList<>();long elapsed=0;
                for(int c=0;c<plan.chapters.size();c++){if(selected>=0&&selected!=c)continue;long begin=elapsed;for(int i=plan.starts.get(c);i<plan.ends.get(c);i++){File file=store.audio(plan.parts.get(i),exportSnapshot);if(!AudioFiles.valid(file))throw new IOException("Hãy tạo xong audio trong phạm vi đã chọn trước khi xuất.");exportFiles.add(file);long[] info=AudioFiles.inspect(file);elapsed+=info[1]*1000000/(info[2]*2);}exportChapters.add(new Mp4BookMetadata.Chapter(plan.chapters.get(c).title,begin/1000,elapsed/1000));}
                if(exportFiles.isEmpty())throw new IOException("Phạm vi chưa có audio.");
                String ext=exportM4b?"m4b":"wav";startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(exportM4b?"audio/mp4":"audio/wav").putExtra(Intent.EXTRA_TITLE,"Soundbooki-"+book.optString("title").replaceAll("[^\\p{L}\\p{N} _-]","")+"."+ext),EXPORT);
            }catch(Exception e){error(e);}
        });
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (request == IMPORT) {
            beginImport(uri);
            return;
        }
        working = true;
        status.setText(exportM4b?"Đang xuất M4B…":"Đang xuất WAV…");
        final List<File> files=new ArrayList<>(exportFiles);final JSONObject snapshot=exportSnapshot;final List<Mp4BookMetadata.Chapter> marks=new ArrayList<>(exportChapters);final boolean m4b=exportM4b;
        exportCancelled=false;
        AlertDialog exportProgress=MobileUi.showAlert(this,theme,new AlertDialog.Builder(this).setTitle("Đang xuất sách nói").setMessage("Chuẩn bị âm thanh…").setNegativeButton("Hủy",(d,w)->exportCancelled=true));exportProgress.setCanceledOnTouchOutside(false);exportProgress.setOnCancelListener(d->exportCancelled=true);
        io.submit(() -> {
            try {
                if (request == EXPORT) {
                    File prepared=null;
                    try {
                        if(m4b)prepared=M4bExport.create(this,store,snapshot,files,marks,()->exportCancelled,p->runOnUiThread(()->exportProgress.setMessage("Đang tạo M4B · "+p+"%")));
                        else {prepared=File.createTempFile("soundbooki-",".wav",getCacheDir());try(OutputStream out=new FileOutputStream(prepared)){AudioFiles.export(files,new FilterOutputStream(out){@Override public void write(byte[] b,int a,int n)throws IOException{if(exportCancelled)throw new InterruptedIOException("Đã hủy xuất.");out.write(b,a,n);}});}}
                        if(exportCancelled)throw new InterruptedIOException("Đã hủy xuất.");
                        try(OutputStream out=getContentResolver().openOutputStream(uri,"wt");InputStream in=new FileInputStream(prepared)){if(out==null)throw new IOException("Chưa mở được nơi lưu.");in.transferTo(out);}
                        runOnUiThread(()->status.setText(m4b?"Đã lưu M4B có chương và bìa.":"Đã lưu bản WAV."));
                    }finally{if(prepared!=null)prepared.delete();}
                }
            } catch (Exception e) {
                runOnUiThread(() -> error(e));
            } finally {
                working = false;runOnUiThread(exportProgress::dismiss);
            }
        });
    }

    public void openReader() {
        saveCurrent();
        if (book == null || book.optString("text").trim().isEmpty()) {
            Toast.makeText(this, "Thêm nội dung sách để mở view đọc.", Toast.LENGTH_SHORT).show();
            return;
        }
        new ReaderDialog(this, theme, store, book, chapter -> {
            saveCurrent();
            startForegroundService(new Intent(this, PlaybackService.class).setAction("local")
                .putExtra("book", book.optString("id")).putExtra("chapter", chapter));
        }).show();
    }

    public void openAudioLibrary() {
        saveCurrent();
        new AudioLibraryDialog(this, theme, store, book).show();
    }

    public void openCleanup() {
        saveCurrent();
        if (book == null || book.optString("text").trim().isEmpty()) {
            Toast.makeText(this, "Chưa có nội dung để dọn dẹp.", Toast.LENGTH_SHORT).show();
            return;
        }
        String currentText = editor.getText().toString();
        Set<String> repeated = java.util.Collections.emptySet();
        List<PdfReflow.ChapterItem> sourceChapters = BookChapters.get(book);
        CleanupDialog[] dialog = new CleanupDialog[1];
        dialog[0] = new CleanupDialog(this, theme, currentText, repeated, cleanedText -> {
            ContentCleaner.CleanResult result = dialog[0].result();
            editor.setText(cleanedText);
            saveCurrent();
            List<PdfReflow.ChapterItem> remapped = new ArrayList<>();
            for (int i = 0; i < sourceChapters.size(); i++) {
                PdfReflow.ChapterItem c = sourceChapters.get(i);
                int start = i == 0 ? 0 : result.mapOffset(c.startChar);
                int end = i + 1 < sourceChapters.size() ? result.mapOffset(sourceChapters.get(i + 1).startChar) : cleanedText.length();
                if (end > start) remapped.add(new PdfReflow.ChapterItem(c.id, c.title, start, end, cleanedText.substring(start, end)));
            }
            try { BookChapters.set(book, remapped); store.save(book); } catch (Exception e) { error(e); }
            updateChapterSpinner();
            Toast.makeText(this, "Đã áp dụng bản dọn nội dung; bản gốc được giữ lại.", Toast.LENGTH_SHORT).show();
        });
        Set<Integer> protectedOffsets = new HashSet<>();
        for (PdfReflow.ChapterItem c : sourceChapters) if (!"all".equals(c.id) && !"preface".equals(c.id)) protectedOffsets.add(c.startChar);
        dialog[0].protectedOffsets = protectedOffsets;
        JSONArray pages = book.optJSONArray("pages"); String raw = book.optString("originalText");
        List<String> sourcePages = new ArrayList<>();
        if (pages != null) for (int i = 0; i < pages.length(); i++) { JSONObject p = pages.optJSONObject(i); if (p == null) continue;
            int start = p.optInt("startOffset", -1), end = p.optInt("endOffset", -1);
            if (start >= 0 && end >= start && end <= raw.length()) sourcePages.add(raw.substring(start, end)); }
        dialog[0].sourcePages = sourcePages;
        dialog[0].show();
    }

    public void reflowPdfLayout() {
        saveCurrent();
        if (book == null || book.optString("text").trim().isEmpty()) {
            Toast.makeText(this, "Chưa có nội dung để sắp xếp bố cục.", Toast.LENGTH_SHORT).show();
            return;
        }
        String currentText = editor.getText().toString();
        PdfReflow.ReflowResult result = PdfReflow.process(currentText);
        if (result.text.equals(currentText)) {
            Toast.makeText(this, "Bố cục văn bản đã chuẩn, không có dòng ngắt quãng cần nối.", Toast.LENGTH_SHORT).show();
            return;
        }
        MobileUi.showAlert(this,theme,new AlertDialog.Builder(this)
            .setTitle("Sắp xếp lại bố cục PDF")
            .setMessage("Đã nối " + result.joinedLines + " dòng bị ngắt và nhận diện " + result.chapters.size() + " chương.\n\nBạn có muốn cập nhật vào sách không?")
            .setPositiveButton("Cập nhật", (d, w) -> {
                editor.setText(result.text);
                try {
                    saveCurrent();
                    BookChapters.set(book, BookChapters.fromSource(book, book.optJSONArray("sourceHeadings")));
                    store.save(book);
                    updateChapterSpinner();
                    Toast.makeText(this, "Đã sắp xếp lại bố cục văn bản.", Toast.LENGTH_SHORT).show();
                } catch (Exception e) {
                    error(e);
                }
            })
            .setNegativeButton("Hủy", null)
        );
    }

    private void updateChapterSpinner() {
        if (book == null || chapterSpinner == null) return;
        String fullText = editor != null ? editor.getText().toString() : book.optString("text");
        currentChapters = BookChapters.get(book);
        List<String> names = new ArrayList<>();
        int count = fullText.codePointCount(0, fullText.length());
        names.add("Toàn bộ sách (" + count + " ký tự)");
        for (PdfReflow.ChapterItem ch : currentChapters) {
            names.add(ch.title);
        }
        ArrayAdapter<String> chAdapter = new MobileUi(this,theme).spinnerAdapter(names.toArray(new String[0]));
        chapterSpinner.setAdapter(chAdapter);
        if (appShell != null) appShell.bookChanged();
    }

    private void markChapter() {
        saveCurrent(); if (book == null || editor.length() == 0) return;
        int at = Math.max(0, editor.getSelectionStart());
        EditText name = new EditText(this); name.setHint("Tên chương trong sách");MobileUi.styleControl(name,theme);
        MobileUi.showAlert(this,theme,new AlertDialog.Builder(this).setTitle("Đặt mốc tại vị trí đang chọn").setView(name)
            .setPositiveButton("Lưu mốc", (d, w) -> {
                String label = name.getText().toString().trim(); if (label.isEmpty()) return;
                TreeMap<Integer, String> cuts = new TreeMap<>();
                for (PdfReflow.ChapterItem c : BookChapters.get(book)) cuts.put(c.startChar, c.title);
                cuts.put(at, label); ArrayList<Integer> offsets = new ArrayList<>(cuts.keySet());
                List<PdfReflow.ChapterItem> chapters = new ArrayList<>(); String full = book.optString("text");
                for (int i = 0; i < offsets.size(); i++) { int start = offsets.get(i), end = i + 1 < offsets.size() ? offsets.get(i + 1) : full.length();
                    if (end > start) chapters.add(new PdfReflow.ChapterItem("manual-" + start, cuts.get(start), start, end, full.substring(start, end))); }
                try { BookChapters.set(book, chapters); store.save(book); updateChapterSpinner(); } catch (Exception e) { error(e); }
            }).setNegativeButton("Hủy", null));
    }

    private void settings() {
        SharedPreferences prefs = getSharedPreferences("settings", MODE_PRIVATE);
        ScrollView sv = new ScrollView(this);
        LinearLayout p = new LinearLayout(this);
        p.setOrientation(LinearLayout.VERTICAL);
        p.setPadding(dp(22), dp(12), dp(22), dp(16));
        sv.addView(p);

        // Section 1: Quản lý sách
        TextView bookMgmtTitle = text("Quản lý sách", 14, true);
        p.addView(bookMgmtTitle);

        Button addFromSettings = button("Thêm sách mới (EPUB, PDF, TXT)", true, "plus");
        LinearLayout.LayoutParams afsLp = new LinearLayout.LayoutParams(-1, dp(48));
        afsLp.topMargin = dp(6);
        afsLp.bottomMargin = dp(6);
        p.addView(addFromSettings, afsLp);

        Button libFromSettings = button("Thư viện sách trên máy", false, "folder");
        LinearLayout.LayoutParams lfsLp = new LinearLayout.LayoutParams(-1, dp(48));
        lfsLp.bottomMargin = dp(14);
        p.addView(libFromSettings, lfsLp);

        // Section 2: Nhạc nền
        TextView bgmTitle = text("Nhạc nền khi nghe", 14, true);
        p.addView(bgmTitle);
        Spinner bgmTrackSpinner = new Spinner(this);
        MobileUi mobileUi = new MobileUi(this,theme);
        mobileUi.styleSpinner(bgmTrackSpinner);
        bgmTrackSpinner.setAdapter(mobileUi.spinnerAdapter(new String[]{
                "Không dùng nhạc nền",
                "Piano podcast (du dương nhẹ)",
                "Whitenoise mưa nhẹ (tập trung)",
                "Late night (thư giãn acoustic)"
            }));
        String currentTrack = book==null?prefs.getString("bgmTrack", "none"):book.optString("bgmTrack",prefs.getString("bgmTrack", "none"));
        int trackIdx = "piano".equals(currentTrack) ? 1 : "rain".equals(currentTrack) ? 2 : "late_night".equals(currentTrack) ? 3 : 0;
        bgmTrackSpinner.setSelection(trackIdx);
        p.addView(bgmTrackSpinner);

        TextView bgmVolTitle = text("Âm lượng nhạc nền", 14, true);
        margin(bgmVolTitle, 10, 4);
        p.addView(bgmVolTitle);
        Spinner bgmVolSpinner = new Spinner(this);
        mobileUi.styleSpinner(bgmVolSpinner);
        bgmVolSpinner.setAdapter(mobileUi.spinnerAdapter(new String[]{"10% · Rất nhẹ", "18% · Vừa vặn (khuyên dùng)", "25% · Rõ hơn", "35% · Đậm đà"}));
        float currentVol = book==null?prefs.getFloat("bgmVolume", 0.18f):(float)book.optDouble("bgmVolume",prefs.getFloat("bgmVolume", 0.18f));
        float[] volOptions = {0.10f, 0.18f, 0.25f, 0.35f};
        int volIdx = 1;
        for (int i = 0; i < volOptions.length; i++) {
            if (Math.abs(volOptions[i] - currentVol) < 0.03f) volIdx = i;
        }
        bgmVolSpinner.setSelection(volIdx);
        p.addView(bgmVolSpinner);

        // Section 3: Cấu hình phát
        TextView cpu = text("Luồng CPU cho lần nghe tiếp theo", 14, true);
        margin(cpu, 14, 4);
        p.addView(cpu);
        Spinner thread = new Spinner(this);
        mobileUi.styleSpinner(thread);
        thread.setAdapter(mobileUi.spinnerAdapter(new String[]{"2 luồng · tiết kiệm hơn", "4 luồng · thử tốc độ"}));
        thread.setSelection(prefs.getInt("threads", 2) == 4 ? 1 : 0);
        p.addView(thread);

        TextView speedTitle = text("Tốc độ phát", 14, true);
        margin(speedTitle, 12, 4);
        p.addView(speedTitle);
        Spinner speed = new Spinner(this);
        mobileUi.styleSpinner(speed);
        speed.setAdapter(mobileUi.spinnerAdapter(new String[]{"0,8×", "1×", "1,2×", "1,5×", "2×"}));
        float[] rates = {.8f, 1f, 1.2f, 1.5f, 2f};
        int selected = 1;
        for (int i = 0; i < rates.length; i++) {
            if (rates[i] == prefs.getFloat("speed", 1)) selected = i;
        }
        speed.setSelection(selected);
        p.addView(speed);

        TextView cloudTitle = text("Địa chỉ dịch vụ Pro Cloud", 14, true);
        margin(cloudTitle, 12, 4);
        p.addView(cloudTitle);
        EditText url = new EditText(this);
        url.setSingleLine(true);
        url.setTypeface(theme.regular);
        url.setHint("https://…/functions/v1/wsn-books");
        url.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        url.setText(prefs.getString("cloudURL", ""));
        url.setContentDescription("URL HTTPS gateway Cloud");
        p.addView(url);

        TextView help = text("Chỉ kết nối khi bạn chọn tạo thử, báo giá hoặc nhận audio. Lite hoạt động trên máy.", 12, false);
        help.setTextColor(muted);
        margin(help, 6, 12);
        p.addView(help);

        Button replayTour = button("Xem lại giới thiệu 5 bước (có âm thanh)", false, "compass");
        p.addView(replayTour, new LinearLayout.LayoutParams(-1, dp(48)));

        AlertDialog dialog = new AlertDialog.Builder(this)
            .setTitle("Cài đặt và Quản lý sách")
            .setView(sv)
            .setPositiveButton("Lưu", null)
            .setNeutralButton("Giấy phép", (d, w) -> licenses())
            .setNegativeButton("Đóng", null)
            .create();

        addFromSettings.setOnClickListener(v -> {
            dialog.dismiss();
            pick();
        });
        libFromSettings.setOnClickListener(v -> {
            dialog.dismiss();
            library();
        });
        replayTour.setOnClickListener(v -> {
            dialog.dismiss();
            openWalkthrough();
        });
        dialog.setOnShowListener(d -> dialog.getButton(DialogInterface.BUTTON_POSITIVE).setOnClickListener(v -> {
            try {
                String value = url.getText().toString().trim();
                if (!value.isEmpty()) value = CloudClient.validateBase(value);
                float rate = rates[speed.getSelectedItemPosition()];
                String[] tracks = {"none", "piano", "rain", "late_night"};
                String selectedBgm = tracks[bgmTrackSpinner.getSelectedItemPosition()];
                float selectedVol = volOptions[bgmVolSpinner.getSelectedItemPosition()];
                prefs.edit()
                    .putString("cloudURL", value)
                    .putInt("threads", thread.getSelectedItemPosition() == 0 ? 2 : 4)
                    .putFloat("speed", rate)
                    .putString("bgmTrack", selectedBgm)
                    .putFloat("bgmVolume", selectedVol)
                    .apply();
                if(book!=null)synchronized(BookStore.LOCK){JSONObject latest=store.load(book.getString("id"));latest.put("bgmTrack",selectedBgm).put("bgmVolume",selectedVol);store.save(latest);book=latest;}
                speedBadge.setText(formatSpeed(rate));
                if (PlaybackService.running) {
                    startService(new Intent(this, PlaybackService.class).setAction("music"));
                    startService(new Intent(this, PlaybackService.class).setAction("speed").putExtra("speed", rate));
                }
                dialog.dismiss();
            } catch (Exception e) {
                url.setError(e.getMessage());
            }
        }));
        dialog.show();
        MobileUi.styleAlert(dialog,theme);
    }

    private void licenses() {
        try (InputStream in = getAssets().open("licenses/NOTICE.txt")) {
            MobileUi.showAlert(this,theme,new AlertDialog.Builder(this)
                .setTitle("Soundbooki Android · Bản thử 0.2.0")
                .setMessage(new String(in.readAllBytes(), StandardCharsets.UTF_8))
                .setPositiveButton("Đóng", null)
            );
        } catch (Exception e) {
            error(e);
        }
    }

    private void error(Throwable error) {
        String m = PlaybackService.friendly(error);
        status.setText(m);
        Toast.makeText(this, m, Toast.LENGTH_LONG).show();
    }

    @Override protected void onResume() {
        super.onResume();
        resumed = true;
        handler.post(refresh);
    }

    @Override protected void onPause() {
        resumed = false;
        saveCurrent();
        handler.removeCallbacks(refresh);
        welcomeAudio.stop(true);
        VoicePreview.stopDialog(voiceDialog);
        if (cloudPanel != null) cloudPanel.suspend();
        super.onPause();
    }

    void readerOpened(ReaderDialog reader){readerDialog=reader;}
    void readerClosed(ReaderDialog reader){if(readerDialog==reader)readerDialog=null;}
    @Override protected void onSaveInstanceState(Bundle out){if(readerDialog!=null&&readerDialog.isShowing())out.putBundle("readerState",readerDialog.readerSnapshot());super.onSaveInstanceState(out);}
    @Override protected void onDestroy() {
        if(readerDialog!=null)readerDialog.dismiss();
        handler.removeCallbacksAndMessages(null);
        welcomeAudio.stop(true);
        if (walkthroughDialog != null && walkthroughDialog.isShowing()) walkthroughDialog.dismiss();
        if (cloudDialog != null) cloudDialog.dismiss();
        if (voiceDialog != null) voiceDialog.dismiss();
        if (appShell != null) appShell.close();
        io.shutdown();
        super.onDestroy();
    }

    JSONObject appBook() { return book == null ? new JSONObject() : book; }
    AppShell appShell() { return appShell; }
    void appSave() { saveCurrent(); }
    void appSelectBook(JSONObject incoming) {
        saveCurrent();
        try { synchronized (BookStore.LOCK) {
            book = store.load(incoming.getString("id")); book.put("lastOpened", System.currentTimeMillis()); store.save(book);
        } bindBook(); } catch (Exception e) { error(e); }
    }
    void appImport() { pick(); }
    void appPasteText(){
        saveCurrent();LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(20),dp(8),dp(20),dp(8));EditText name=new EditText(this);name.setHint("Tên văn bản");name.setContentDescription("Tên văn bản");content.addView(name);EditText input=new EditText(this);input.setHint("Dán văn bản vào đây…");input.setContentDescription("Nội dung văn bản");input.setMinLines(5);input.setMaxLines(10);input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(1000000)});content.addView(input);
        AlertDialog dialog=MobileUi.showAlert(this,theme,new AlertDialog.Builder(this).setTitle("Dán văn bản để nghe").setView(content).setPositiveButton("Thêm vào thư viện",null).setNegativeButton("Đóng",null));dialog.getButton(DialogInterface.BUTTON_POSITIVE).setOnClickListener(v->{String value=input.getText().toString();if(value.trim().isEmpty()){input.setError("Dán nội dung trước khi thêm.");return;}try{book=store.create(name.getText().toString().trim().isEmpty()?"Văn bản của tôi":name.getText().toString().trim(),value,null);bindBook();dialog.dismiss();if(appShell!=null)appShell.showEditor();}catch(Exception e){error(e);}});
    }
    void appBilingual(){
        saveCurrent();if(book==null)return;final String id=book.optString("id");
        if(book.optBoolean("bilingual")){try{synchronized(BookStore.LOCK){JSONObject latest=store.load(id);latest.put("bilingual",false).put("positionMs",0);store.save(latest);book=latest;}startService(new Intent(this,PlaybackService.class).setAction("stop"));bindBook();if(appShell!=null)appShell.showImported();Toast.makeText(this,"Đã tắt đọc Việt–Anh",Toast.LENGTH_SHORT).show();}catch(Exception e){error(e);}return;}
        MobileUi.showAlert(this,theme,new AlertDialog.Builder(this).setTitle("Đọc Việt–Anh trên máy").setMessage("Câu Việt dùng Lite. Câu Anh dùng giọng Anh offline đã cài trong hệ thống Android. Tên riêng hoặc câu quá ngắn có thể cần kiểm tra lại. Không gửi chữ lên mạng.").setPositiveButton("Bật cho sách này",(d,w)->{io.submit(()->{try(EnglishSpeech speech=new EnglishSpeech(this)){String voice=speech.select(""),revision=speech.revision();synchronized(BookStore.LOCK){JSONObject latest=store.load(id);latest.put("bilingual",true).put("englishVoice",voice).put("englishRevision",revision).put("positionMs",0);store.save(latest);runOnUiThread(()->{if(book.optString("id").equals(id)){book=latest;startService(new Intent(this,PlaybackService.class).setAction("stop"));bindBook();if(appShell!=null)appShell.showImported();Toast.makeText(this,"Đã bật Việt–Anh · "+voice,Toast.LENGTH_LONG).show();}});}}catch(Exception e){runOnUiThread(()->error(e));}});}).setNegativeButton("Đóng",null));
    }
    void appNewBook() {
        saveCurrent();
        try { book = store.create("Sách mới", "", null); bindBook(); if (appShell != null) appShell.showEditor(); editor.requestFocus(); }
        catch (Exception e) { error(e); }
    }
    void appListenEditor() { listen(false); }
    void appPlay(int chapter, boolean continuous, boolean beginning) {
        saveCurrent();
        if (book == null || book.optString("text").trim().isEmpty() || !"ready".equals(book.optString("status","ready"))) {
            Toast.makeText(this,"Thêm nội dung sách trước khi nghe.",Toast.LENGTH_SHORT).show(); return;
        }
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 42);
        startForegroundService(new Intent(this,PlaybackService.class).setAction("local").putExtra("book",book.optString("id"))
            .putExtra("chapter",chapter).putExtra("continuous",continuous).putExtra("beginning",beginning));
    }
    void appCommand(String action, String key, int value) {
        if (!PlaybackService.running && !"sleep".equals(action)) return;
        Intent intent = new Intent(this,PlaybackService.class).setAction(action); if (key != null) intent.putExtra(key,value); startService(intent);
    }
    void appResumeGeneration(JSONObject checkpoint) {
        saveCurrent();
        JSONObject valid=GenerationProgress.pending(store,book);
        if(checkpoint==null||valid==null||!BookStore.contentSignature(book).equals(checkpoint.optString("signature")))return;
        if(checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},42);
        startForegroundService(new Intent(this,PlaybackService.class).setAction("local").putExtra("book",book.optString("id"))
            .putExtra("chapter",valid.optInt("chapter",-1)).putExtra("continuous",valid.optBoolean("continuous"))
            .putExtra("pausePlayback",true).putExtra("resumeGeneration",true));
    }
    void appTake(JSONObject take) { startForegroundService(new Intent(this,PlaybackService.class).setAction("take").putExtra("book",book.optString("id")).putExtra("take",take.optString("id"))); }
    void appShare(File file) {
        try { Uri uri=androidx.core.content.FileProvider.getUriForFile(this,getPackageName()+".fileprovider",file);
            startActivity(Intent.createChooser(new Intent(Intent.ACTION_SEND).setType("audio/wav").putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION),"Chia sẻ chương sách nói"));
        } catch (Exception e) { error(e); }
    }
    void appEditAt(int offset) { editor.setSelection(Math.max(0,Math.min(editor.length(),offset))); editor.requestFocus(); }
    void appReadChapter(int chapter) {
        saveCurrent(); List<PdfReflow.ChapterItem> chapters=BookChapters.get(book); if(chapters.isEmpty())return;
        new ReaderDialog(this,theme,store,book,c->appPlay(c,false,false)).startAt(chapters.get(Math.max(0,Math.min(chapter,chapters.size()-1))).startChar).show();
    }
    void appReadAlong() {
        if (!PlaybackService.running) { openReader(); return; }
        if (!PlaybackService.sourceTextMatches) { Toast.makeText(this,"Bản audio này dùng nội dung cũ đã lưu. Hãy mở trang sách từ Chi tiết sách để xem bản hiện tại.",Toast.LENGTH_LONG).show(); return; }
        saveCurrent(); new ReaderDialog(this,theme,store,book,c->appPlay(c,false,false)).startAt(PlaybackService.currentCharOffset).show();
    }
    void appSettings() { settings(); }
    void appCloud() { openCloud(); }
    void appProfile() { ProfileDialog.show(this,theme); }
    void appCombo() { ProfileDialog.combo(this,theme); }
    void appCloudChapter(int chapter) { openCloud(chapter); }
    void appProVoices() {
        if (voiceDialog != null) voiceDialog.dismiss();
        voiceDialog = VoicePreview.show(this,theme,index->{openCloud();if(cloudPanel!=null&&cloudDialog!=null&&cloudDialog.isShowing())cloudPanel.voice.setSelection(index);});
    }
    void appVoices() {
        String[] labels=new String[voiceNames.size()+1];for(int i=0;i<voiceNames.size();i++)labels[i]="Lite · "+voiceNames.get(i);labels[voiceNames.size()]="Nghe thử 7 giọng Pro";
        MobileUi.options(this,theme,"Giọng đọc",labels,i->{if(i==voiceNames.size())appProVoices();else{voices.setSelection(i);saveCurrent();}});
    }

    private void openCloud() { openCloud(chapterSpinner==null?-1:chapterSpinner.getSelectedItemPosition()-1); }
    private void openCloud(int chapter) {
        saveCurrent();
        if (book == null || !"ready".equals(book.optString("status", "ready")) || book.optString("text").trim().isEmpty()) {
            error(new IOException("Thêm nội dung sách trước khi mở Cloud."));
            return;
        }
        cloudPanel = new CloudPanel(book.optString("id"),chapter);
        cloudPanel.show();
    }

    private final class CloudPanel {
        final String bid;
        final int sampleChapter;
        int sampleUnits=1;
        final RadioGroup trialChoice;
        final String sampleTextHash;
        final TextView excerpt;
        final LinearLayout pane;
        final TextView detail, orderInfo, payment;
        final CheckBox consent;
        final Spinner voice, history;
        final Button trial, quote, check, listen, cloudExport;
        final ImageView qr;
        final VoicePreview.Card samplePreview;
        final Handler poll = new Handler(Looper.getMainLooper());
        JSONObject entry;
        boolean busy = false, initial = true;
        volatile boolean visible = true;
        int polls = 0;

        CloudPanel(String bookId,int chapter) {
            bid = bookId;
            sampleChapter=chapter;
            
            sampleTextHash=BookStore.hash(book.optString("text"));
            pane = new LinearLayout(MainActivity.this);
            pane.setOrientation(LinearLayout.VERTICAL);
            pane.setPadding(dp(20), dp(10), dp(20), dp(14));

            detail = text(ProfileDialog.quota(MainActivity.this)+"\n5.000 ký tự/lượt · Gộp tối đa 4 lượt cho một chương. Giá toàn bộ sách do máy chủ báo trước khi thanh toán.", 14, false);
            detail.setTextColor(muted);
            pane.addView(detail);

            voice = new Spinner(MainActivity.this);
            MobileUi mobileUi = new MobileUi(MainActivity.this,theme);
            mobileUi.styleSpinner(voice);
            voice.setAdapter(mobileUi.spinnerAdapter(CloudClient.VOICES));
            voice.setContentDescription("Giọng Pro Cloud");
            voice.setBackground(theme.card(theme.card, theme.edge, 14));
            LinearLayout.LayoutParams vLp = new LinearLayout.LayoutParams(-1, dp(50));
            vLp.topMargin = dp(10);
            pane.addView(voice, vLp);
            samplePreview = new VoicePreview.Card(MainActivity.this, theme);
            LinearLayout.LayoutParams sampleLp = new LinearLayout.LayoutParams(-1, -2);
            sampleLp.topMargin = dp(12);
            pane.addView(samplePreview, sampleLp);

            consent = new CheckBox(MainActivity.this);
            consent.setText("Tôi đồng ý gửi phần chữ đã chọn lên Cloud để tạo giọng.");
            consent.setTextColor(ink);
            consent.setTypeface(theme.regular);
            LinearLayout.LayoutParams cLp = new LinearLayout.LayoutParams(-1, -2);
            cLp.topMargin = dp(8);
            pane.addView(consent, cLp);

            excerpt=text("",13,false);excerpt.setMaxLines(5);excerpt.setEllipsize(android.text.TextUtils.TruncateAt.END);pane.addView(excerpt);
            trialChoice=new RadioGroup(MainActivity.this);trialChoice.setOrientation(RadioGroup.HORIZONTAL);trialChoice.setContentDescription("Cách tạo Pro");
            RadioButton single=new RadioButton(MainActivity.this);single.setId(View.generateViewId());single.setText("Tạo thử · 1 lượt");single.setTextColor(ink);single.setTypeface(theme.regular);trialChoice.addView(single,new RadioGroup.LayoutParams(0,dp(64),1));
            RadioButton chapterChoice=new RadioButton(MainActivity.this);chapterChoice.setId(View.generateViewId());chapterChoice.setText("Tạo chương · Tối đa 4 lượt");chapterChoice.setTextColor(ink);chapterChoice.setTypeface(theme.regular);chapterChoice.setEnabled(sampleChapter>=0);trialChoice.addView(chapterChoice,new RadioGroup.LayoutParams(0,dp(64),1));
            trialChoice.check(single.getId());pane.addView(trialChoice);updateTrialExcerpt();
            trialChoice.setOnCheckedChangeListener((group,id)->{
                if(busy)return;
                poll.removeCallbacksAndMessages(null);polls=0;entry=null;
                sampleUnits=1;if(id==chapterChoice.getId())try{sampleUnits=CloudClient.chapterTrialUnits(store.load(bid),sampleChapter);}catch(Exception e){showError(e);}
                updateTrialExcerpt();display();
            });
            trial = button(sampleChapter>=0?"Tạo thử chương này · Pro":"Tạo thử phần đầu · Pro", true, "headphones");
            LinearLayout.LayoutParams tLp = new LinearLayout.LayoutParams(-1, dp(52));
            tLp.topMargin = dp(10);
            pane.addView(trial, tLp);

            quote = button("Báo giá toàn bộ sách", false, "book");
            LinearLayout.LayoutParams qLp = new LinearLayout.LayoutParams(-1, dp(52));
            qLp.topMargin = dp(8);
            pane.addView(quote, qLp);

            history = new Spinner(MainActivity.this);
            mobileUi.styleSpinner(history);
            history.setContentDescription("Các đơn Cloud của sách này");
            history.setBackground(theme.card(theme.card, theme.edge, 14));
            LinearLayout.LayoutParams hLp = new LinearLayout.LayoutParams(-1, dp(50));
            hLp.topMargin = dp(12);
            pane.addView(history, hLp);

            orderInfo = text("", 13, false);
            margin(orderInfo, 8, 8);
            pane.addView(orderInfo);

            payment = text("", 14, true);
            payment.setTextIsSelectable(true);
            pane.addView(payment);

            qr = new ImageView(MainActivity.this);
            qr.setContentDescription("QR thanh toán đúng đơn, số tiền và tài khoản máy chủ trả về");
            LinearLayout.LayoutParams qp = new LinearLayout.LayoutParams(dp(220), dp(220));
            qp.gravity = Gravity.CENTER_HORIZONTAL;
            qp.topMargin = dp(12);
            pane.addView(qr, qp);
            qr.setVisibility(View.GONE);

            check = button("Kiểm tra và nhận audio", false);
            LinearLayout.LayoutParams ckLp = new LinearLayout.LayoutParams(-1, dp(50));
            ckLp.topMargin = dp(8);
            pane.addView(check, ckLp);

            listen = button("Nghe audio đã nhận", true, "play");
            LinearLayout.LayoutParams lsLp = new LinearLayout.LayoutParams(-1, dp(52));
            lsLp.topMargin = dp(8);
            pane.addView(listen, lsLp);

            cloudExport = button("Xuất WAV của đơn này", false, "export");
            LinearLayout.LayoutParams ceLp = new LinearLayout.LayoutParams(-1, dp(50));
            ceLp.topMargin = dp(8);
            pane.addView(cloudExport, ceLp);
            cloudExport.setOnClickListener(v -> exportOrder());

            trial.setOnClickListener(v -> confirmTrial());
            quote.setOnClickListener(v -> submit("quote"));
            check.setOnClickListener(v -> { polls = 0; refreshOrder(); });
            listen.setOnClickListener(v -> {
                if (entry != null && entry.optJSONObject("order") != null) {
                    startForegroundService(new Intent(MainActivity.this, PlaybackService.class)
                        .setAction("cloud")
                        .putExtra("book", bid)
                        .putExtra("order", entry.optJSONObject("order").optString("id")));
                    cloudDialog.dismiss();
                }
            });
            consent.setOnCheckedChangeListener((b, value) -> updateButtons());
            voice.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                public void onNothingSelected(AdapterView<?> p) {}
                public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
                    samplePreview.select(at, true);
                    updateTrialExcerpt();
                    if (!initial) {
                        entry = null;
                        orderInfo.setText("Chọn Tạo thử hoặc Báo giá để tạo yêu cầu cho giọng này.");
                        payment.setText("");
                    }
                    updateButtons();
                }
            });
            reloadHistory();
            history.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                public void onNothingSelected(AdapterView<?> p) {}
                public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
                    if (initial) return;
                    try {
                        List<JSONObject> entries = entries();
                        entry = at == 0 ? null : entries.get(at - 1);
                        display();
                    } catch (Exception e) {
                        showError(e);
                    }
                }
            });
        }

        List<JSONObject> entries() throws Exception {
            JSONObject b = store.load(bid);
            JSONArray a = b.getJSONArray("cloudOrders");
            ArrayList<JSONObject> list = new ArrayList<>();
            for (int i = a.length() - 1; i >= 0; i--) list.add(a.getJSONObject(i));
            return list;
        }

        void reloadHistory() {
            try {
                List<JSONObject> entries = entries();
                ArrayList<String> labels = new ArrayList<>();
                labels.add("Nội dung hiện tại · yêu cầu mới");
                for (JSONObject e : entries) {
                    JSONObject o = e.optJSONObject("order");
                    labels.add((e.optString("kind").equals("trial") ? "Mẫu" : "Sách Pro") + " · "
                        + (o == null ? "Chờ gửi lại" : o.optString("state")) + " · "
                        + e.getJSONObject("snapshot").optString("voice").substring(0, 8));
                }
                initial = true;
                history.setAdapter(new MobileUi(MainActivity.this,theme).spinnerAdapter(labels.toArray(new String[0])));
                handler.post(() -> initial = false);
            } catch (Exception e) {
                showError(e);
            }
        }

        void show() {
            ScrollView scroll = new ScrollView(MainActivity.this);
            scroll.addView(pane);
            cloudDialog = new AlertDialog.Builder(MainActivity.this)
                .setTitle("Pro Cloud · theo từng cuốn")
                .setView(scroll)
                .setNegativeButton("Đóng", null)
                .create();
            cloudDialog.setOnDismissListener(d -> {
                visible = false;
                samplePreview.stop();
                poll.removeCallbacksAndMessages(null);
            });
            cloudDialog.show();MobileUi.styleAlert(cloudDialog,theme);MobileUi.styleControl(consent,theme);
            String url = getSharedPreferences("settings", MODE_PRIVATE).getString("cloudURL", "");
            if (url.isEmpty()) {
                detail.setText("Pro Cloud chưa kết nối dịch vụ. Vào Cài đặt để nhập URL gateway được cung cấp. Bạn vẫn có thể nghe bằng Lite trên máy.");
            }
            display();
        }

        void suspend() {
            samplePreview.stop();
            poll.removeCallbacksAndMessages(null);
        }

        void exportOrder() {
            if (entry == null) return;
            try {
                JSONObject order = entry.getJSONObject("order");
                if (!"book".equals(order.getString("kind")) || !"ready".equals(order.getString("state"))) {
                    throw new IOException("Đơn sách chưa tạo xong.");
                }
                ArrayList<File> files = new ArrayList<>();
                JSONArray parts = entry.getJSONObject("snapshot").getJSONArray("segments");
                for (int i = 0; i < parts.length(); i++) {
                    File f = store.cloudAudio(order.getString("id"), parts.getJSONObject(i).getString("id"));
                    if (!AudioFiles.valid(f)) throw new IOException("Chọn Nhận audio để tải đủ trước khi xuất.");
                    files.add(f);
                }
                MobileUi.options(MainActivity.this,theme,"Xuất audio đã nhận",new String[]{"M4B · Bìa và bản audio đã nhận","WAV"},format->{try{
                    exportFiles=files;exportM4b=format==0;exportSnapshot=new JSONObject(book.toString());exportSnapshot.put("title",entry.getJSONObject("snapshot").optString("title",book.optString("title")));long micros=0;for(File file:files){long[] info=AudioFiles.inspect(file);micros+=info[1]*1000000/(info[2]*2);}exportChapters=List.of(new Mp4BookMetadata.Chapter(exportSnapshot.optString("title"),0,micros/1000));
                    // Legacy cloud snapshots do not carry trustworthy chapter timings.
                    String ext=exportM4b?"m4b":"wav";startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(exportM4b?"audio/mp4":"audio/wav").putExtra(Intent.EXTRA_TITLE,"Soundbooki-Pro-"+order.getString("id").substring(0,8)+"."+ext),EXPORT);
                }catch(Exception e){showError(e);}});
            } catch (Exception e) {
                showError(e);
            }
        }

        void updateTrialExcerpt(){
            try{JSONObject current=store.load(bid);JSONObject sample=CloudClient.snapshot(current,CloudClient.VOICE_IDS[voice.getSelectedItemPosition()],true,sampleChapter,sampleUnits);StringBuilder copy=new StringBuilder();JSONArray segments=sample.getJSONArray("segments");for(int i=0;i<segments.length();i++)copy.append(segments.getJSONObject(i).getString("text"));int count=copy.codePointCount(0,copy.length());String title=sampleChapter>=0?BookChapters.get(current).get(sampleChapter).title:"Phần mở đầu";int total=sampleChapter>=0?BookChapters.get(current).get(sampleChapter).text.codePointCount(0,BookChapters.get(current).get(sampleChapter).text.length()):count;excerpt.setText(title+" · "+count+"/"+total+" ký tự · "+CloudClient.trialUnits(sample)+" lượt"+(total>20000&&sampleUnits==4?" · Chưa hết chương (tối đa 20.000 ký tự)":"")+"\n"+copy);}catch(Exception e){excerpt.setText(e.getMessage());}
        }

        void updateButtons() {
            boolean configured = !getSharedPreferences("settings", MODE_PRIVATE).getString("cloudURL", "").isEmpty();
            boolean reusable=false;
            try{JSONObject planned=CloudClient.snapshot(store.load(bid),CloudClient.VOICE_IDS[voice.getSelectedItemPosition()],true,sampleChapter,sampleUnits);String base=getSharedPreferences("settings",MODE_PRIVATE).getString("cloudURL","");for(JSONObject saved:entries())if(saved.optString("kind").equals("trial")&&saved.optString("base").equals(base)&&CloudClient.sameTrialPrefix(saved.getJSONObject("snapshot"),planned)){reusable=true;break;}}catch(Exception ignored){}
            trial.setEnabled(configured && consent.isChecked() && !busy && (reusable||ProfileDialog.remaining(MainActivity.this)>=sampleUnits));
            quote.setEnabled(configured && consent.isChecked() && !busy);
            voice.setEnabled(!busy);
            for(int i=0;i<trialChoice.getChildCount();i++)trialChoice.getChildAt(i).setEnabled(!busy&&(i==0||sampleChapter>=0));
            history.setEnabled(!busy);
            check.setEnabled(entry != null && entry.optJSONObject("order") != null && !busy);
            listen.setEnabled(entry != null && entry.optJSONObject("order") != null && !busy);
            boolean canExport = entry != null && entry.optJSONObject("order") != null
                && "book".equals(entry.optJSONObject("order").optString("kind"))
                && "ready".equals(entry.optJSONObject("order").optString("state"));
            cloudExport.setVisibility(canExport ? View.VISIBLE : View.GONE);
            cloudExport.setEnabled(canExport && !busy);
        }

        void confirmTrial() {
            if(busy||!consent.isChecked())return;
            try{
                JSONObject current=store.load(bid);
                if(!sampleTextHash.equals(BookStore.hash(current.optString("text"))))throw new IOException("Nội dung đã thay đổi. Mở lại Pro để xem mẫu và xác nhận.");
                JSONObject snap=CloudClient.snapshot(current,CloudClient.VOICE_IDS[voice.getSelectedItemPosition()],true,sampleChapter,sampleUnits);
                int units=CloudClient.trialUnits(snap);String endpoint=getSharedPreferences("settings",MODE_PRIVATE).getString("cloudURL","");
                boolean retry=false;
                for(JSONObject saved:entries()){
                    if(saved.optString("kind").equals("trial")&&saved.optString("base").equals(endpoint)&&CloudClient.sameTrialPrefix(saved.getJSONObject("snapshot"),snap)){
                        if(saved.optJSONObject("order")!=null){entry=saved;display();refreshOrder();return;}
                        retry=true;
                    }
                }
                if(ProfileDialog.remaining(MainActivity.this)<units&&!retry)throw new IOException("Không đủ lượt Pro để tạo phần đã chọn.");
                String title=sampleChapter>=0?BookChapters.get(current).get(sampleChapter).title:"phần đầu sách";
                String extent=sampleChapter>=0&&BookChapters.get(current).get(sampleChapter).text.codePointCount(0,BookChapters.get(current).get(sampleChapter).text.length())<=units*CloudClient.TRIAL_CHARACTERS?"Tạo trọn chương trên cloud.":"Tạo tối đa "+(units*CloudClient.TRIAL_CHARACTERS)+" ký tự đầu phần đã chọn.";
                MobileUi.showAlert(MainActivity.this,theme,new AlertDialog.Builder(MainActivity.this).setTitle("Dùng "+units+" lượt Pro?").setMessage(title+" · "+CloudClient.VOICES[voice.getSelectedItemPosition()]+"\n\n"+extent).setPositiveButton("Xác nhận",(d,w)->submit("trial")).setNegativeButton("Để sau",null));
            }catch(Exception e){showError(e);}
        }

        void submit(String action) {
            if (busy || !consent.isChecked()) return;
            try {
                String endpoint = getSharedPreferences("settings", MODE_PRIVATE).getString("cloudURL", "");
                CloudClient.validateBase(endpoint);
                JSONObject b = store.load(bid);
                if(!sampleTextHash.equals(BookStore.hash(b.optString("text"))))throw new IOException("Nội dung đã thay đổi. Mở lại Pro để xem mẫu và xác nhận.");
                JSONObject snap = CloudClient.snapshot(b, CloudClient.VOICE_IDS[voice.getSelectedItemPosition()], action.equals("trial"),sampleChapter,sampleUnits);
                // Resume an uncertain submission with its persisted key and immutable body.
                JSONObject pending = null;
                JSONArray all = b.getJSONArray("cloudOrders");
                for (int i = all.length() - 1; i >= 0; i--) {
                    JSONObject e = all.getJSONObject(i);
                    if (e.optString("kind").equals(action)
                        && (e.getJSONObject("snapshot").toString().equals(snap.toString()) || (action.equals("trial") && CloudClient.sameTrialPrefix(e.getJSONObject("snapshot"),snap)))
                        && e.optString("base").equals(endpoint)
                        && e.optJSONObject("order") == null) {
                        pending = e;
                        break;
                    }
                }
                if (pending == null) {
                    pending = new JSONObject()
                        .put("requestKey", BookStore.id())
                        .put("snapshot", snap)
                        .put("kind", action)
                        .put("base", endpoint);
                    all.put(pending);
                    store.save(b);
                }
                entry = pending;
                if (action.equals("quote")) {
                    MobileUi.showAlert(MainActivity.this,theme,new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Gửi toàn bộ chữ để báo giá?")
                        .setMessage("Chỉ xác nhận báo giá. Bạn thanh toán sau khi xem đúng số tiền và đơn do máy chủ trả về.")
                        .setPositiveButton("Gửi để báo giá", (d, w) -> send(action))
                        .setNegativeButton("Để sau", null)
                    );
                } else {
                    send(action);
                }
            } catch (Exception e) {
                showError(e);
            }
        }

        void send(String action) {
            if (entry == null || busy) return;
            busy = true;
            updateButtons();
            orderInfo.setText("Đang gửi yêu cầu…");
            JSONObject request = entry;
            io.submit(() -> {
                try {
                    CloudClient client = new CloudClient(MainActivity.this, request.getString("base"));
                    String path=action.equals("trial")&&request.getJSONObject("snapshot").optInt("trialUnits",1)>1?"trial-group":action;
                    JSONObject response = client.post(path, new JSONObject()
                        .put("snapshot", request.getJSONObject("snapshot"))
                        .put("requestKey", request.getString("requestKey"))
                        .put("consent", true));
                    CloudClient.validateOrder(response.getJSONObject("order"));
                    request.put("order", response.getJSONObject("order"));
                    if (response.has("bank")) request.put("bank", response.getJSONObject("bank"));
                    saveEntry(request);
                    ProfileDialog.remember(MainActivity.this,response,request.getString("base"));
                    runOnUiThread(() -> {
                        busy = false;
                        if (!visible) return;
                        entry = request;
                        detail.setText("Còn " + ProfileDialog.remaining(MainActivity.this) + " / " + CloudClient.TRIAL_LIMIT + " lượt thử trên thiết bị này (máy chủ xác nhận).");
                        reloadHistory();
                        display();
                        schedule();
                    });
                } catch (Exception e) {
                    runOnUiThread(() -> {
                        busy = false;
                        if (visible) showError(e);
                    });
                }
            });
        }

        void saveEntry(JSONObject saved) throws Exception {
            synchronized (BookStore.LOCK) {
                JSONObject b = store.load(bid);
                JSONArray all = b.getJSONArray("cloudOrders");
                boolean found = false;
                for (int i = 0; i < all.length(); i++) {
                    if (all.getJSONObject(i).optString("requestKey").equals(saved.getString("requestKey"))) {
                        all.put(i, saved);
                        found = true;
                        break;
                    }
                }
                if (!found) throw new IOException("Yêu cầu không thuộc sách này.");
                store.save(b);
            }
        }

        void refreshOrder() {
            if (entry == null || entry.optJSONObject("order") == null || busy || !visible) return;
            busy = true;
            updateButtons();
            JSONObject request = entry;
            io.submit(() -> {
                try {
                    CloudClient client = new CloudClient(MainActivity.this, request.getString("base"));
                    JSONObject old = request.getJSONObject("order");
                    JSONArray known = new JSONArray(), segments = request.getJSONObject("snapshot").getJSONArray("segments");
                    for (int i = 0; i < segments.length(); i++) {
                        String sid = segments.getJSONObject(i).getString("id");
                        if (AudioFiles.valid(store.cloudAudio(old.getString("id"), sid))) known.put(sid);
                    }
                    JSONObject result = client.post("status", new JSONObject().put("orderId", old.getString("id")).put("knownSegments", known));
                    if (!visible || !resumed) throw new InterruptedException();
                    client.receive(store, request, result, () -> visible && resumed);
                    request.put("order", result.getJSONObject("order"));
                    saveEntry(request);
                    ProfileDialog.remember(MainActivity.this,result,request.getString("base"));
                    runOnUiThread(() -> {
                        busy = false;
                        if (!visible) return;
                        entry = request;
                        display();
                        schedule();
                    });
                } catch (Exception e) {
                    runOnUiThread(() -> {
                        busy = false;
                        if (visible) showError(e);
                    });
                }
            });
        }

        void display() {
            payment.setText("");
            qr.setVisibility(View.GONE);
            if (entry == null) {
                orderInfo.setText("Tạo thử phần mở đầu hoặc yêu cầu báo giá cuốn sách.");
                updateButtons();
                return;
            }
            JSONObject order = entry.optJSONObject("order");
            if (order == null) {
                orderInfo.setText("Yêu cầu đã lưu. Bấm lại cùng thao tác để gửi lại đúng yêu cầu này.");
                updateButtons();
                return;
            }
            String state = order.optString("state");
            String label = switch (state) {
                case "awaiting_payment" -> "Chờ thanh toán";
                case "queued" -> "Đã vào hàng đợi";
                case "processing" -> "Đang tạo audio";
                case "ready" -> "Audio đã sẵn sàng";
                case "expired" -> "Đơn đã hết hạn";
                default -> "Cần kiểm tra lại đơn";
            };
            orderInfo.setText(label + " · " + order.optInt("done") + " / " + order.optInt("total") + " phần\nĐơn: " + order.optString("id"));
            if ("awaiting_payment".equals(state) && "book".equals(order.optString("kind"))) {
                JSONObject bank = entry.optJSONObject("bank");
                if (bank == null) bank = order.optJSONObject("bank");
                payment.setText(String.format(new Locale("vi", "VN"), "%,dđ\n", order.optLong("amountVND"))
                    + (bank == null ? "Đang thiếu tài khoản nhận; hãy kiểm tra lại đơn." : bank.optString("name") + " · " + bank.optString("account") + "\n" + bank.optString("holder"))
                    + "\nNội dung: " + order.optString("paymentCode")
                    + "\nChỉ máy chủ xác nhận giao dịch mới mở audio.");
                if (bank != null) {
                    try {
                        qr.setImageBitmap(PaymentQR.image(bank, order));
                        qr.setVisibility(View.VISIBLE);
                    } catch (Exception e) {
                        payment.append("\nQR chưa sẵn sàng. Kiểm tra lại thông tin trước khi thanh toán.");
                    }
                }
            }
            updateButtons();
        }

        void schedule() {
            poll.removeCallbacksAndMessages(null);
            if (!visible || isFinishing() || !resumed || cloudDialog == null || !cloudDialog.isShowing() || polls >= 30 || entry == null || entry.optJSONObject("order") == null) return;
            String state = entry.optJSONObject("order").optString("state");
            if (Set.of("expired", "failed").contains(state)) return;
            if ("ready".equals(state)) return;
            poll.postDelayed(() -> {
                polls++;
                refreshOrder();
            }, 10000);
        }

        void showError(Exception e) {
            orderInfo.setText(e.getMessage() == null ? "Chưa kết nối Cloud. Yêu cầu đã được giữ để thử lại." : e.getMessage());
            updateButtons();
        }
    }
}
