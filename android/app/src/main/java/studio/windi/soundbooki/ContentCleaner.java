package studio.windi.soundbooki;

import java.util.*;
import java.util.regex.*;

/**
 * Conservative, deterministic text cleanup synchronized with Mac's backend/cleanup.py
 * and backend/narration_text.py proofread_audiobook_text().
 * No remote services or LLM rewriting: only removes chosen structural artifacts
 * (decorative dividers, standalone page numbers, repeated headers/footers, TOC dot leaders)
 * and repairs common OCR scan typos.
 */
public final class ContentCleaner {

    public static final class Options {
        public boolean decorations = true;
        public boolean pageNumbers = true;
        public boolean repeatedHeaders = true;
        public boolean toc = true;
        public boolean ocrFixes = true;
        public Set<Integer> protectedOffsets = Collections.emptySet();
    }

    public static final class CleanResult {
        public final String text;
        public final List<CleanedLine> removedLines;
        public final int ocrFixCount;
        public final int totalChanges;
        public int[] sourceStarts = new int[0], outputStarts = new int[0];
        public int mapOffset(int offset) {
            int i = Arrays.binarySearch(sourceStarts, offset);
            if (i < 0) i = Math.max(0, -i - 2);
            if (i >= sourceStarts.length) return 0;
            return Math.min(text.length(), outputStarts[i] + Math.max(0, offset - sourceStarts[i]));
        }

        public CleanResult(String text, List<CleanedLine> removedLines, int ocrFixCount) {
            this.text = text;
            this.removedLines = removedLines;
            this.ocrFixCount = ocrFixCount;
            this.totalChanges = removedLines.size() + ocrFixCount;
        }
    }

    public static final class CleanedLine {
        public final int lineNumber;
        public final String text;
        public final String reason;

        public CleanedLine(int lineNumber, String text, String reason) {
            this.lineNumber = lineNumber;
            this.text = text;
            this.reason = reason;
        }
    }

    private static boolean isNarratable(String text) {
        for (int i = 0; i < text.length(); i++) {
            if (Character.isLetterOrDigit(text.charAt(i))) return true;
        }
        return false;
    }

    private static boolean isDecoration(String line) {
        String core = line.replaceAll("\\s+", "");
        if (core.length() < 3 || isNarratable(core)) return false;
        for (int i = 0; i < core.length(); i++) {
            int type = Character.getType(core.charAt(i));
            boolean isPunctOrSymbol = type == Character.DASH_PUNCTUATION ||
                type == Character.START_PUNCTUATION ||
                type == Character.END_PUNCTUATION ||
                type == Character.CONNECTOR_PUNCTUATION ||
                type == Character.OTHER_PUNCTUATION ||
                type == Character.MATH_SYMBOL ||
                type == Character.OTHER_SYMBOL;
            if (!isPunctOrSymbol) return false;
        }
        return true;
    }

    private static final Pattern PAGE_NUMBER_PAT = Pattern.compile(
        "^(?:[-–—\\*•]\\s*)?\\d{1,5}(?:\\s*[-–—\\*•])?$|^(?:Trang|Page)\\s+\\d{1,5}$", Pattern.CASE_INSENSITIVE);

    private static final Pattern TOC_LEADER_PAT = Pattern.compile(
        "(?:\\.{3,}|…{2,}|·{3,}|-{3,})\\s*\\d+\\s*$");

    public static Set<String> findRepeatedHeaders(String text) {
        if (text == null || text.trim().isEmpty()) return Collections.emptySet();
        return findRepeatedHeaders(Arrays.asList(text.split("\n\n+")));
    }

    public static Set<String> findRepeatedHeaders(List<String> pages) {
        if (pages == null || pages.size() < 3) return Collections.emptySet();
        Map<String, Integer> counts = new HashMap<>();
        for (String page : pages) {
            if (page == null) continue;
            String[] lines = page.split("\r?\n");
            Set<String> pageCandidates = new HashSet<>();
            for (int i = 0; i < lines.length; i++) {
                String trim = lines[i].trim();
                if ((i == 0 || i == lines.length - 1) && trim.length() > 2 && trim.length() < 120) {
                    pageCandidates.add(trim);
                }
            }
            for (String c : pageCandidates) {
                counts.put(c, counts.getOrDefault(c, 0) + 1);
            }
        }
        Set<String> repeated = new HashSet<>();
        for (Map.Entry<String, Integer> entry : counts.entrySet()) {
            if (entry.getValue() >= 3) {
                repeated.add(entry.getKey());
            }
        }
        return repeated;
    }

    public static CleanResult clean(String source, Options opts, Set<String> repeatedHeaders) {
        if (source == null) return new CleanResult("", Collections.emptyList(), 0);
        if (opts == null) opts = new Options();
        if (repeatedHeaders == null) repeatedHeaders = Collections.emptySet();

        String[] lines = source.split("\r?\n", -1);
        Set<Integer> tocIndices = new HashSet<>();

        if (opts.toc) {
            for (int i = 0; i < lines.length; i++) {
                String trim = lines[i].trim().toLowerCase(Locale.ROOT);
                if (trim.equals("mục lục") || trim.equals("contents") || trim.equals("table of contents")) {
                    List<Integer> block = new ArrayList<>();
                    int leaders = 0;
                    for (int n = i + 1; n < lines.length; n++) {
                        String val = lines[n].trim();
                        if (val.isEmpty() || isDecoration(val)) {
                            block.add(n);
                            continue;
                        }
                        if (TOC_LEADER_PAT.matcher(val).find()) {
                            block.add(n);
                            leaders++;
                        } else {
                            break;
                        }
                    }
                    if (leaders >= 2) {
                        tocIndices.add(i);
                        tocIndices.addAll(block);
                    }
                }
            }
        }

        List<CleanedLine> removed = new ArrayList<>();
        StringBuilder kept = new StringBuilder();
        int[] sourceStarts = new int[lines.length], outputStarts = new int[lines.length];
        Set<Integer> protectedLines = new HashSet<>(); int sourceAt = 0;
        for (int i = 0; i < lines.length; i++) {
            sourceStarts[i] = sourceAt;
            int newline = source.indexOf('\n', sourceAt);
            int end = newline < 0 ? source.length() : newline + 1;
            for (int offset : opts.protectedOffsets) if (sourceAt <= offset && offset < end) protectedLines.add(i);
            sourceAt = end;
        }
        int ocrFixCount = 0;
        boolean anyKept = false;

        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            String val = line.trim();
            String reason = null;

            if (opts.decorations && isDecoration(val)) {
                reason = "Dòng ký hiệu / phân cách trang trí";
            } else if (opts.pageNumbers && PAGE_NUMBER_PAT.matcher(val).matches()) {
                reason = "Dòng chỉ chứa số trang";
            } else if (opts.repeatedHeaders && repeatedHeaders.contains(val)) {
                reason = "Đầu / cuối trang lặp lại";
            } else if (tocIndices.contains(i)) {
                reason = "Dòng mục lục chấm số trang";
            }

            if (protectedLines.contains(i)) reason = null;
            outputStarts[i] = kept.length() + (anyKept ? 1 : 0);
            if (reason != null) {
                removed.add(new CleanedLine(i + 1, line, reason));
            } else {
                if (anyKept) kept.append("\n");
                if (opts.ocrFixes) { OcrFixResult fix = fixOcrArtifacts(line); kept.append(fix.text); ocrFixCount += fix.replacements; }
                else kept.append(line);
                anyKept = true;
            }
        }

        CleanResult result = new CleanResult(kept.toString(), removed, ocrFixCount);
        result.sourceStarts = sourceStarts; result.outputStarts = outputStarts;
        return result;
    }

    private static final class OcrFixResult {
        final String text;
        final int replacements;
        OcrFixResult(String text, int replacements) {
            this.text = text;
            this.replacements = replacements;
        }
    }

    /**
     * Deterministic Vietnamese OCR typo proofreading matching Mac's narration_text.py.
     */
    private static OcrFixResult fixOcrArtifacts(String text) {
        int count = 0;
        String cur = text;

        // Fix scan artifact: digit 1 replacing 'l' in common Vietnamese prefixes (1àm -> làm, 1ại -> lại)
        String before = cur;
        cur = cur.replaceAll("\\b1([àáạảãaâầấậẩẫăằắặẳẵèéẹẻẽeêềếệểễòóọỏõoôồốộổỗơờớợởỡùúụủũuưừứựửữìíịỉĩiyýỵỷỹ])", "l$1");
        cur = cur.replaceAll("\\b1([ÀÁẠẢÃAÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼEÊỀẾỆỂỄÒÓỌỎÕOÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨUƯỪỨỰỬỮÌÍỊỈĨIYÝỴỶỸ])", "L$1");
        if (!cur.equals(before)) count++;

        // Fix digit 0 replacing 'o' or 'ô' in Vietnamese words (kh0ng -> không, c0ng -> công)
        before = cur;
        cur = cur.replaceAll("(?i)\\bkh0ng\\b", "không");
        cur = cur.replaceAll("(?i)\\bc0ng\\b", "công");
        cur = cur.replaceAll("(?i)\\btr0ng\\b", "trong");
        if (!cur.equals(before)) count++;

        // Fix digit 1 replacing 'i' at word end (ngườ1 -> người, mớ1 -> mới, trờ1 -> trời)
        before = cur;
        cur = cur.replaceAll("([a-zà-ỹA-ZÀ-Ỹ])1\\b", "$1i");
        if (!cur.equals(before)) count++;

        // Fix digit 9 replacing 'g' (nhữn9 -> những, trườn9 -> trường)
        before = cur;
        cur = cur.replaceAll("([a-zà-ỹA-ZÀ-Ỹ])9\\b", "$1g");
        if (!cur.equals(before)) count++;

        // Fix Roman numerals in chapter headings: "Chương I" -> "Chương 1", "Chương II" -> "Chương 2"
        before = cur;
        Pattern chPat = Pattern.compile("(?i)(Chương|Hồi|Phần|Tiết|Chapter)\\s+([IVXLCDM]+)\\b");
        Matcher m = chPat.matcher(cur);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String prefix = m.group(1);
            String roman = m.group(2).toUpperCase(Locale.ROOT);
            int arabic = romanToArabic(roman);
            if (arabic > 0 && arabic <= 200) {
                m.appendReplacement(sb, prefix + " " + arabic);
                count++;
            } else {
                m.appendReplacement(sb, m.group(0));
            }
        }
        m.appendTail(sb);
        cur = sb.toString();

        return new OcrFixResult(cur, count);
    }

    private static int romanToArabic(String roman) {
        Map<Character, Integer> vals = Map.of(
            'I', 1, 'V', 5, 'X', 10, 'L', 50, 'C', 100, 'D', 500, 'M', 1000
        );
        int total = 0, prev = 0;
        for (int i = roman.length() - 1; i >= 0; i--) {
            char c = roman.charAt(i);
            if (!vals.containsKey(c)) return -1;
            int cur = vals.get(c);
            if (cur < prev) total -= cur;
            else { total += cur; prev = cur; }
        }
        return total;
    }
}
