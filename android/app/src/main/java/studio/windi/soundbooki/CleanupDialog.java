package studio.windi.soundbooki;

import android.app.Activity;
import android.app.Dialog;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.drawable.ColorDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import java.util.concurrent.*;
import android.view.*;
import android.widget.*;
import java.util.*;
import java.util.function.Consumer;

/**
 * Cleanup preview dialog ("Dọn nội dung") synchronized with Mac's #cleanupPanel.
 * Conservative, deterministic text cleanup:
 * Only removes explicitly selected structural flaws (dividers, page numbers, repeated headers, TOC)
 * and repairs Vietnamese OCR scan typos without changing source prose.
 */
public final class CleanupDialog extends Dialog {
    private final Activity host;
    private final UiTheme theme;
    private final String currentText;
    private final Set<String> repeatedHeaders;
    private final Consumer<String> onApply;

    private CheckBox optDecorations, optPageNumbers, optRepeatedHeaders, optTOC, optOcrFixes;
    private TextView summaryView;
    private LinearLayout changesList;
    private Button applyBtn;
    private ContentCleaner.CleanResult lastResult;
    public List<String> sourcePages = Collections.emptyList();
    public Set<Integer> protectedOffsets = Collections.emptySet();
    public ContentCleaner.CleanResult result() { return lastResult; }
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private Future<?> pending;
    private int previewRevision = 0;
    private boolean closed = false;

    public CleanupDialog(Activity host, UiTheme theme, String currentText, Set<String> repeatedHeaders, Consumer<String> onApply) {
        super(host, android.R.style.Theme_DeviceDefault_NoActionBar);
        this.host = host;
        this.theme = theme;
        this.currentText = currentText;
        this.repeatedHeaders = repeatedHeaders;
        this.onApply = onApply;
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
        mark.setImageDrawable(theme.icon("original", theme.accent, 24));
        header.addView(mark, new LinearLayout.LayoutParams(theme.dp(30), theme.dp(30)));

        LinearLayout titleCol = new LinearLayout(host);
        titleCol.setOrientation(LinearLayout.VERTICAL);
        titleCol.setPadding(theme.dp(10), 0, 0, 0);

        TextView title = new TextView(host);
        title.setText("Dọn nội dung trên máy");
        title.setTextSize(18f);
        title.setTypeface(theme.display);
        title.setTextColor(theme.ink);
        titleCol.addView(title);

        TextView sub = new TextView(host);
        sub.setText("Chỉ bỏ những dòng và sửa ký tự được liệt kê. Bản gốc luôn được lưu lại.");
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

        // Options Container
        LinearLayout optionsCard = new LinearLayout(host);
        optionsCard.setOrientation(LinearLayout.VERTICAL);
        optionsCard.setBackground(theme.card(theme.surface, theme.edge, 16));
        optionsCard.setPadding(theme.dp(14), theme.dp(10), theme.dp(14), theme.dp(10));
        LinearLayout.LayoutParams ocLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        ocLp.topMargin = theme.dp(12);

        optDecorations = check("Dòng chấm / ký hiệu trang trí (***, ---)", true);
        optPageNumbers = check("Dòng chỉ có số trang (12, - 12 -)", true);
        optRepeatedHeaders = check("Đầu / cuối trang lặp lại", true);
        optTOC = check("Mục lục có dòng chấm và số trang", true);
        optOcrFixes = check("Sửa lỗi scan OCR số lẫn chữ (1àm → làm, kh0ng → không)", true);

        for (CheckBox cb : new CheckBox[]{optDecorations, optPageNumbers, optRepeatedHeaders, optTOC, optOcrFixes}) {
            optionsCard.addView(cb);
            cb.setOnCheckedChangeListener((b, val) -> updatePreview());
        }
        optionsCard.setLayoutParams(ocLp);

        // Summary
        summaryView = new TextView(host);
        summaryView.setTextSize(12.5f);
        summaryView.setTypeface(theme.bold);
        summaryView.setTextColor(theme.tourBlue);
        summaryView.setBackground(theme.card(theme.blueWash, theme.edge, 10));
        summaryView.setPadding(theme.dp(12), theme.dp(8), theme.dp(12), theme.dp(8));
        LinearLayout.LayoutParams sumLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        sumLp.topMargin = theme.dp(10);
        sumLp.bottomMargin = theme.dp(6);
        summaryView.setLayoutParams(sumLp);

        // Scrollable Changes List
        ScrollView scroll = new ScrollView(host);
        scroll.setFillViewport(true);
        LinearLayout.LayoutParams scrollLp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        scrollLp.bottomMargin = theme.dp(10);

        changesList = new LinearLayout(host);
        changesList.setOrientation(LinearLayout.VERTICAL);
        LinearLayout scrollContent = new LinearLayout(host);
        scrollContent.setOrientation(LinearLayout.VERTICAL);
        scrollContent.addView(optionsCard);
        scrollContent.addView(summaryView);
        scrollContent.addView(changesList);
        scroll.addView(scrollContent);
        shell.addView(scroll, scrollLp);

        // Bottom CTA button
        applyBtn = new Button(host);
        applyBtn.setText("Áp dụng vào ô soạn thảo");
        applyBtn.setAllCaps(false);
        applyBtn.setTextSize(15f);
        applyBtn.setTypeface(theme.bold);
        applyBtn.setTextColor(Color.WHITE);
        applyBtn.setBackground(theme.buttonBackground(true, 18));
        applyBtn.setMinHeight(theme.dp(52));
        applyBtn.setOnClickListener(v -> {
            if (lastResult != null) {
                onApply.accept(lastResult.text);
                dismiss();
            }
        });
        shell.addView(applyBtn, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, theme.dp(52)));

        setContentView(backdrop);
        setOnDismissListener(d -> { closed = true; previewRevision++; if (pending != null) pending.cancel(true); worker.shutdownNow(); ui.removeCallbacksAndMessages(null); });
        updatePreview();
    }

    private CheckBox check(String label, boolean def) {
        CheckBox cb = new CheckBox(host);
        cb.setText(label);
        cb.setChecked(def);
        cb.setTextSize(13f);
        cb.setTypeface(theme.regular);
        cb.setTextColor(theme.ink);
        cb.setPadding(theme.dp(6), theme.dp(4), theme.dp(6), theme.dp(4));
        MobileUi.styleControl(cb,theme);
        return cb;
    }

    private void updatePreview() {
        ContentCleaner.Options opts = new ContentCleaner.Options();
        opts.decorations = optDecorations.isChecked();
        opts.pageNumbers = optPageNumbers.isChecked();
        opts.repeatedHeaders = optRepeatedHeaders.isChecked();
        opts.toc = optTOC.isChecked();
        opts.ocrFixes = optOcrFixes.isChecked();
        opts.protectedOffsets = protectedOffsets;

        int revision = ++previewRevision;
        lastResult = null;
        applyBtn.setEnabled(false);
        summaryView.setText("Đang kiểm tra nội dung trên máy…");
        if (pending != null) pending.cancel(true);
        pending = worker.submit(() -> {
            try {
                ContentCleaner.CleanResult result = ContentCleaner.clean(currentText, opts, sourcePages.isEmpty() ? repeatedHeaders : ContentCleaner.findRepeatedHeaders(sourcePages));
                ui.post(() -> { if (!closed && revision == previewRevision) { lastResult = result; renderPreview(); } });
            } catch (Exception error) {
                ui.post(() -> { if (!closed && revision == previewRevision) summaryView.setText("Chưa kiểm tra được nội dung. Hãy đóng rồi thử lại."); });
            }
        });
    }

    private void renderPreview() {
        changesList.removeAllViews();

        int removedCount = lastResult.removedLines.size();
        int ocrCount = lastResult.ocrFixCount;

        if (removedCount == 0 && ocrCount == 0) {
            summaryView.setText("Nội dung đã sạch; không tìm thấy dòng thừa hay lỗi scan nào.");
            applyBtn.setEnabled(false);
            applyBtn.setAlpha(0.5f);

            TextView empty = new TextView(host);
            empty.setText("Không có dòng nào phù hợp với bộ lọc đã chọn.");
            empty.setTextSize(13f);
            empty.setTypeface(theme.regular);
            empty.setTextColor(theme.muted);
            empty.setGravity(Gravity.CENTER);
            empty.setPadding(0, theme.dp(30), 0, theme.dp(30));
            changesList.addView(empty);
            return;
        }

        summaryView.setText("Sẽ bỏ " + removedCount + " dòng thừa và sửa " + ocrCount + " lỗi scan OCR. Nội dung còn lại giữ nguyên.");
        applyBtn.setEnabled(true);
        applyBtn.setAlpha(1f);

        int shown = 0;
        for (ContentCleaner.CleanedLine line : lastResult.removedLines) {
            if (shown++ >= 100) break;
            LinearLayout item = new LinearLayout(host);
            item.setOrientation(LinearLayout.VERTICAL);
            item.setBackground(theme.card(theme.surface, theme.edge, 10));
            item.setPadding(theme.dp(10), theme.dp(6), theme.dp(10), theme.dp(6));
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.bottomMargin = theme.dp(6);
            item.setLayoutParams(lp);

            TextView top = new TextView(host);
            top.setText("Dòng " + line.lineNumber + " · " + line.reason);
            top.setTextSize(11f);
            top.setTypeface(theme.bold);
            top.setTextColor(theme.accent);
            item.addView(top);

            TextView content = new TextView(host);
            content.setText(line.text.trim());
            content.setTextSize(12.5f);
            content.setTypeface(theme.regular);
            content.setTextColor(theme.muted);
            item.addView(content);

            changesList.addView(item);
        }
        if (removedCount > 100) {
            TextView more = new TextView(host);
            more.setText("Đang hiển thị 100 / " + removedCount + " dòng để mở nhanh. Áp dụng xử lý toàn bộ dòng đã kiểm tra.");
            more.setTextColor(theme.muted);
            changesList.addView(more);
        }
        if (ocrCount > 0) {
            TextView diff = new TextView(host);
            diff.setText("Xem bản sau khi dọn");
            diff.setTextColor(theme.accent);
            diff.setMinHeight(theme.dp(48));
            diff.setOnClickListener(v -> {
                EditText preview = new EditText(host); preview.setText(lastResult.text); preview.setTextSize(14);
                preview.setTextIsSelectable(true); preview.setKeyListener(null); preview.setMaxLines(12);
                MobileUi.styleControl(preview,theme);MobileUi.showAlert(host,theme,new android.app.AlertDialog.Builder(host).setTitle("Bản đề xuất · chưa áp dụng").setView(preview).setPositiveButton("Đóng", null));
            });
            changesList.addView(diff);
        }
    }
}
