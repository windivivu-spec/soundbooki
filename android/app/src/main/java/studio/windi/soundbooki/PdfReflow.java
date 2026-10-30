package studio.windi.soundbooki;

import java.util.*;
import java.util.regex.*;

/**
 * Intelligent reflow for extracted PDF text synchronized with Mac's pdf_layout.py.
 * Restores natural reading flow without reordering or inventing text:
 * - Re-joins lines wrapped by PDF fixed-width columns into smooth paragraphs.
 * - Re-joins hyphenated words split at line ends.
 * - Preserves authentic paragraph breaks and dialog indentation.
 * - Detects numbered chapter headings ("Chương 1", "Chương 2", "Chapter 1", etc.).
 */
public final class PdfReflow {

    public static final class ReflowResult {
        public final String text;
        public final List<ChapterItem> chapters;
        public final int joinedLines;
        public final int joinedHyphens;

        public ReflowResult(String text, List<ChapterItem> chapters, int joinedLines, int joinedHyphens) {
            this.text = text;
            this.chapters = chapters;
            this.joinedLines = joinedLines;
            this.joinedHyphens = joinedHyphens;
        }
    }

    public static final class ChapterItem {
        public final String id;
        public final String title;
        public final int startChar;
        public final int endChar;
        public final String text;

        public ChapterItem(String id, String title, int startChar, int endChar) {
            this(id, title, startChar, endChar, "");
        }

        public ChapterItem(String id, String title, int startChar, int endChar, String text) {
            this.id = id;
            this.title = title;
            this.startChar = startChar;
            this.endChar = endChar;
            this.text = text;
        }
    }

    private static final Pattern CHAPTER_HEADING_PAT = Pattern.compile(
        "(?m)^[ \\t]*(?:CHƯƠNG|Chương|HỒI|Hồi|BÀI|Bài|PHẦN|Phần|TIẾT|Tiết|CHAPTER|Chapter)\\s+([0-9IVXLCDM]+)(?:[.: -]+(.*))?$"
    );

    private static final Pattern HYPHEN_END_PAT = Pattern.compile(
        "([a-zà-ỹA-ZÀ-Ỹ]+)[-–—]\\s*\\n\\s*([a-zà-ỹA-ZÀ-Ỹ]+)"
    );

    public static ReflowResult process(String rawText) {
        if (rawText == null || rawText.trim().isEmpty()) {
            return new ReflowResult("", Collections.emptyList(), 0, 0);
        }

        // 1. Re-join hyphenated words across line breaks: "tiếng-\nViệt" -> "tiếng Việt" or "audio-\nbook" -> "audiobook"
        int joinedHyphens = 0;
        Matcher hypMatcher = HYPHEN_END_PAT.matcher(rawText);
        StringBuffer hypBuffer = new StringBuffer();
        while (hypMatcher.find()) {
            joinedHyphens++;
            String w1 = hypMatcher.group(1);
            String w2 = hypMatcher.group(2);
            // In Vietnamese, compounds are usually separated by space, or single words joined
            hypMatcher.appendReplacement(hypBuffer, w1 + " " + w2);
        }
        hypMatcher.appendTail(hypBuffer);
        String unhyphenated = hypBuffer.toString();

        // 2. Reflow lines: join wrapped sentences inside paragraphs
        String[] lines = unhyphenated.split("\r?\n");
        StringBuilder sb = new StringBuilder();
        int joinedLines = 0;

        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.isEmpty()) {
                // Paragraph boundary
                if (sb.length() > 0 && !endsParagraph(sb)) {
                    sb.append("\n\n");
                }
                continue;
            }

            if (sb.length() == 0 || endsParagraph(sb)) {
                sb.append(line);
                continue;
            }

            // Check if current line is a new chapter heading or dialog line
            boolean isHeading = CHAPTER_HEADING_PAT.matcher(line).matches();
            boolean previousHeading = i > 0 && CHAPTER_HEADING_PAT.matcher(lines[i - 1].trim()).matches();
            boolean isDialog = line.startsWith("-") || line.startsWith("–") || line.startsWith("—") || line.startsWith("“") || line.startsWith("\"");
            char lastChar = sb.charAt(sb.length() - 1);
            boolean lastIsTerminal = (lastChar == '.' || lastChar == '!' || lastChar == '?' || lastChar == ':' || lastChar == '…');

            if (isHeading || previousHeading || (lastIsTerminal && isDialog)) {
                // New paragraph/section
                sb.append("\n\n").append(line);
            } else if (!lastIsTerminal && !isDialog) {
                // Wrapped sentence in column: join with single space
                sb.append(" ").append(line);
                joinedLines++;
            } else {
                sb.append("\n\n").append(line);
            }
        }

        String reflowedText = sb.toString().replaceAll("\\n{3,}", "\n\n").trim();

        // 3. Extract chapters based on detected headings
        List<ChapterItem> chapters = extractChapters(reflowedText);

        return new ReflowResult(reflowedText, chapters, joinedLines, joinedHyphens);
    }

    private static boolean endsParagraph(StringBuilder s) { return s.length()>=2 && s.charAt(s.length()-1)=='\n' && s.charAt(s.length()-2)=='\n'; }

    public static List<ChapterItem> extractChapters(String text) {
        List<ChapterItem> list = new ArrayList<>();
        if (text == null || text.trim().isEmpty()) return list;

        Matcher m = CHAPTER_HEADING_PAT.matcher(text);
        List<int[]> headingRanges = new ArrayList<>();
        List<String> titles = new ArrayList<>();

        while (m.find()) {
            headingRanges.add(new int[]{m.start(), m.end()});
            String fullTitle = m.group(0).trim();
            titles.add(fullTitle);
        }

        if (headingRanges.isEmpty()) {
            // No explicit chapter headings found, single chapter for entire text
            list.add(new ChapterItem("all", "Toàn bộ sách", 0, text.length(), text));
            return list;
        }

        // Add preface if text precedes the first chapter heading
        if (headingRanges.get(0)[0] > 0) {
            String preface = text.substring(0, headingRanges.get(0)[0]);
            if (!preface.isEmpty()) {
                list.add(new ChapterItem("preface", "Phần mở đầu", 0, headingRanges.get(0)[0], preface));
            }
        }

        for (int i = 0; i < headingRanges.size(); i++) {
            int start = headingRanges.get(i)[0];
            int end = (i + 1 < headingRanges.size()) ? headingRanges.get(i + 1)[0] : text.length();
            String chapterText = text.substring(start, end);
            String title = titles.get(i);
            list.add(new ChapterItem("chapter-" + (i + 1), title, start, end, chapterText));
        }

        return list;
    }
}
