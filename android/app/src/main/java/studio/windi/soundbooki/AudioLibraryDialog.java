package studio.windi.soundbooki;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import java.util.concurrent.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.File;
import java.util.*;

/**
 * Audio library dialog ("Sách nói của bạn") synchronized with Mac's #audiobooksPanel.
 * Lists all generated audio files for the current book and previous books,
 * allowing instant local listening, WAV export / sharing, and cache management.
 */
public final class AudioLibraryDialog extends Dialog {
    private final Activity host;
    private final UiTheme theme;
    private final BookStore store;
    private final JSONObject book;
    private TextView emptyHint;
    private ListView audioList;
    private ChapterAudio library;
    private List<JSONObject> takes = new ArrayList<>();
    private final ExecutorService loader = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private boolean closed = false;

    public AudioLibraryDialog(Activity host, UiTheme theme, BookStore store, JSONObject book) {
        super(host, android.R.style.Theme_DeviceDefault_NoActionBar);
        this.host = host;
        this.theme = theme;
        this.store = store;
        this.book = book;
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        Window w = getWindow();
        if (w != null) {
            w.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
            w.setBackgroundDrawable(new ColorDrawable(Color.parseColor(theme.dark ? "#D80B111A" : "#B8121E31")));
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
        shell.setBackground(theme.card(theme.tourSurface, theme.edge, 26));
        shell.setPadding(theme.dp(18), theme.dp(16), theme.dp(18), theme.dp(16));
        shell.setElevation(theme.dp(16));
        FrameLayout.LayoutParams shellLp = new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        backdrop.addView(shell, shellLp);

        // Header
        LinearLayout header = new LinearLayout(host);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        ImageView mark = new ImageView(host);
        mark.setImageDrawable(theme.icon("headphones", theme.accent, 26));
        header.addView(mark, new LinearLayout.LayoutParams(theme.dp(32), theme.dp(32)));

        LinearLayout titleCol = new LinearLayout(host);
        titleCol.setOrientation(LinearLayout.VERTICAL);
        titleCol.setPadding(theme.dp(10), 0, 0, 0);

        TextView title = new TextView(host);
        title.setText("Sách nói của bạn");
        title.setTextSize(18f);
        title.setTypeface(theme.display);
        title.setTextColor(theme.ink);
        titleCol.addView(title);

        TextView sub = new TextView(host);
        sub.setText("Mỗi chương hoàn tất là một bản nghe · Giữ các giọng và bản chữ đã tạo.");
        sub.setTextSize(11.5f);
        sub.setTypeface(theme.regular);
        sub.setTextColor(theme.muted);
        titleCol.addView(sub);

        header.addView(titleCol, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        Button closeBtn = new Button(host);
        closeBtn.setText("Đóng");
        closeBtn.setAllCaps(false);
        closeBtn.setTextSize(13f);
        closeBtn.setTypeface(theme.bold);
        closeBtn.setTextColor(theme.ink);
        closeBtn.setBackground(theme.chipBackground(theme.surface, theme.edge, 999));
        closeBtn.setMinWidth(theme.dp(64));
        closeBtn.setMinHeight(theme.dp(44));
        closeBtn.setOnClickListener(v -> dismiss());
        header.addView(closeBtn, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, theme.dp(44)));
        shell.addView(header);

        audioList = new ListView(host);
        audioList.setDivider(null);
        audioList.setDividerHeight(theme.dp(10));
        LinearLayout.LayoutParams listLp = new LinearLayout.LayoutParams(-1, 0, 1f);
        listLp.topMargin = theme.dp(14); shell.addView(audioList, listLp);
        emptyHint = new TextView(host);
        emptyHint.setText("Đang mở các chương đã tạo…"); emptyHint.setTextColor(theme.muted);
        emptyHint.setPadding(0, theme.dp(24), 0, theme.dp(24)); shell.addView(emptyHint);
        audioList.setEmptyView(emptyHint);
        setContentView(backdrop);
        setOnDismissListener(d -> { closed = true; loader.shutdownNow(); ui.removeCallbacksAndMessages(null); });
        if (book != null) library = new ChapterAudio(store, book.optString("id"));
        loadAudioFiles();
    }

    private void loadAudioFiles() {
        if (library == null || closed) return;
        loader.submit(() -> {
            List<JSONObject> result = library.list();
            ui.post(() -> {
                if (closed) return;
                takes = result;
                emptyHint.setText("Chưa có chương hoàn tất. Bấm Nghe để tạo; audio sẽ lưu ở đây khi tạo xong cả chương.");
                audioList.setAdapter(new BaseAdapter() {
                    public int getCount() { return takes.size(); }
                    public Object getItem(int p) { return takes.get(p); }
                    public long getItemId(int p) { return p; }
                    public View getView(int p, View recycled, ViewGroup parent) {
                        JSONObject take = takes.get(p);
                        return createAudioRow(p + 1, library.file(take), take.optString("title"), take.optString("voice"));
                    }
                });
            });
        });
    }

    private View createAudioRow(int index, File file, String snippet, String voice) {
        LinearLayout row = new LinearLayout(host);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setBackground(theme.card(theme.surface, theme.edge, 16));
        row.setPadding(theme.dp(14), theme.dp(12), theme.dp(14), theme.dp(12));
        LinearLayout.LayoutParams rowLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        rowLp.bottomMargin = theme.dp(10);
        row.setLayoutParams(rowLp);

        LinearLayout topRow = new LinearLayout(host);
        topRow.setOrientation(LinearLayout.HORIZONTAL);
        topRow.setGravity(Gravity.CENTER_VERTICAL);

        TextView numBadge = new TextView(host);
        numBadge.setText("Chương đã tạo");
        numBadge.setTextSize(11f);
        numBadge.setTypeface(theme.bold);
        numBadge.setTextColor(theme.accent);
        numBadge.setBackground(theme.card(theme.blueWash, theme.edge, 99));
        numBadge.setPadding(theme.dp(8), theme.dp(3), theme.dp(8), theme.dp(3));
        topRow.addView(numBadge);

        TextView meta = new TextView(host);
        long kb = file.length() / 1024;
        meta.setText("WAV · " + kb + " KB · " + voice);
        meta.setTextSize(11f);
        meta.setTypeface(theme.regular);
        meta.setTextColor(theme.muted);
        row.addView(meta);

        row.addView(topRow);

        TextView text = new TextView(host);
        text.setText(snippet);
        text.setTextSize(13.5f);
        text.setTypeface(theme.regular);
        text.setTextColor(theme.ink);
        text.setPadding(0, theme.dp(6), 0, theme.dp(10));
        row.addView(text);

        // Actions: Nghe thử, Chia sẻ
        LinearLayout actions = new LinearLayout(host);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.CENTER_VERTICAL);

        Button playBtn = new Button(host);
        playBtn.setText("Nghe");
        playBtn.setAllCaps(false);
        playBtn.setTextSize(12.5f);
        playBtn.setTypeface(theme.bold);
        playBtn.setTextColor(Color.WHITE);
        playBtn.setBackground(theme.buttonBackground(true, 12));
        playBtn.setCompoundDrawablesWithIntrinsicBounds(theme.icon("play", Color.WHITE, 14), null, null, null);
        playBtn.setCompoundDrawablePadding(theme.dp(4));
        playBtn.setMinWidth(theme.dp(88));
        playBtn.setMinHeight(theme.dp(48));
        playBtn.setOnClickListener(v -> togglePlay(file));
        actions.addView(playBtn, new LinearLayout.LayoutParams(0, theme.dp(48), 1f));

        Button shareBtn = new Button(host);
        shareBtn.setText("Chia sẻ WAV");
        shareBtn.setAllCaps(false);
        shareBtn.setTextSize(12.5f);
        shareBtn.setTypeface(theme.bold);
        shareBtn.setTextColor(theme.accent);
        shareBtn.setBackground(theme.buttonBackground(false, 12));
        shareBtn.setCompoundDrawablesWithIntrinsicBounds(theme.icon("export", theme.accent, 14), null, null, null);
        shareBtn.setCompoundDrawablePadding(theme.dp(4));
        shareBtn.setMinWidth(theme.dp(100));
        shareBtn.setMinHeight(theme.dp(48));
        LinearLayout.LayoutParams shLp = new LinearLayout.LayoutParams(0, theme.dp(48), 1f);
        shLp.leftMargin = theme.dp(8);
        shareBtn.setOnClickListener(v -> shareFile(file));
        actions.addView(shareBtn, shLp);

        row.addView(actions);
        return row;
    }

    private void togglePlay(File file) {
        String id = file.getName().replace(".wav", "");
        host.startForegroundService(new Intent(host, PlaybackService.class).setAction("take")
            .putExtra("book", book.optString("id")).putExtra("take", id));
        Toast.makeText(host, "Đang nghe chương đã lưu", Toast.LENGTH_SHORT).show();
    }

    private void shareFile(File file) {
        try {
            Uri uri = androidx.core.content.FileProvider.getUriForFile(
                host, host.getPackageName() + ".fileprovider", file);
            Intent share = new Intent(Intent.ACTION_SEND);
            share.setType("audio/wav");
            share.putExtra(Intent.EXTRA_STREAM, uri);
            share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            host.startActivity(Intent.createChooser(share, "Chia sẻ file WAV"));
        } catch (Exception e) {
            Toast.makeText(host, "Lỗi chia sẻ: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }
}
