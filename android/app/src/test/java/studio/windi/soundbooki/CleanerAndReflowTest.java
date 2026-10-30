package studio.windi.soundbooki;

import org.junit.Test;
import java.util.*;
import static org.junit.Assert.*;

public class CleanerAndReflowTest {

    @Test
    public void testContentCleanerRemovesArtifactsAndRepairsOcr() {
        String dirtyDoc =
            "Dòng tiêu đề trang lặp lại\n" +
            "***\n" +
            "- 12 -\n" +
            "Mục lục\n" +
            "Chương 1: Khởi đầu ............... 15\n" +
            "Chương 2: Tiếp theo ............... 30\n" +
            "Chương 3: Kết thúc ............... 45\n" +
            "Đây là một cuốn sách tiếng Việt có dấu.\n" +
            "Người đọc 1àm việc rất chăm chỉ và kh0ng bao giờ bỏ cuộc.\n" +
            "Dòng tiêu đề trang lặp lại\n";

        ContentCleaner.Options options = new ContentCleaner.Options();
        Set<String> repeated = Set.of("Dòng tiêu đề trang lặp lại");

        ContentCleaner.CleanResult result = ContentCleaner.clean(dirtyDoc, options, repeated);

        // Verification:
        // 1. Dividers like *** removed
        assertFalse(result.text.contains("***"));
        // 2. Standalone page numbers like - 12 - removed
        assertFalse(result.text.contains("- 12 -"));
        // 3. Repeated headers removed
        assertFalse(result.text.contains("Dòng tiêu đề trang lặp lại"));
        // 4. TOC dot leaders removed
        assertFalse(result.text.contains("Mục lục"));
        assertFalse(result.text.contains("............... 15"));
        // 5. OCR typos fixed (1àm -> làm, kh0ng -> không)
        assertTrue(result.text.contains("làm việc"));
        assertTrue(result.text.contains("không bao giờ"));
        assertTrue(result.ocrFixCount >= 2);
        assertTrue(result.totalChanges >= 5);
    }

    @Test
    public void testPdfReflowJoinsHyphensAndUnwrapsLines() {
        String pdfText =
            "Cuốn sách này giúp chúng ta hiểu rõ hơn về văn hóa truyền-\n" +
            "thống của người Việt Nam qua từng thời kỳ.\n\n" +
            "Chương 1: Đất nước\n" +
            "Đoạn văn mở đầu cho chương một được viết rất mạch lạc và sáng\n" +
            "rõ để người nghe có thể cảm nhận sâu sắc nhất.\n\n" +
            "Chương 2: Con người\n" +
            "Tiếp nối là chương thứ hai kể về con người và cuộc sống thường nhật.\n";

        PdfReflow.ReflowResult result = PdfReflow.process(pdfText);

        // 1. Hyphen unwrapped: "truyền- \n thống" -> "truyền thống"
        assertTrue(result.text.contains("truyền thống"));
        assertFalse(result.text.contains("truyền-"));

        // 2. Wrapped lines within paragraph unwrapped smoothly
        assertTrue(result.text.contains("sáng rõ"));

        // 3. Chapters recognized correctly
        assertEquals(3, result.chapters.size()); // Preface/All or Preface + Ch1 + Ch2
        assertTrue(result.chapters.stream().anyMatch(c -> c.title.contains("Chương 1")));
        assertTrue(result.chapters.stream().anyMatch(c -> c.title.contains("Chương 2")));
    }

    @Test
    public void testSpokenPartsVerbatimAndBounded() {
        String source = "Đây là câu thứ nhất có dấu tiếng Việt. Còn đây là câu thứ hai, ngắn gọn.";
        List<String> parts = BookStore.spokenParts(source);
        assertFalse(parts.isEmpty());
        assertEquals(source, String.join("", parts));
    }
    @Test public void cleanupPreservesSourceChapterNumberAndReanchorsAfterRemovals() {
        String source = "***\n1\nFIRST TITLE\nNội dung mở đầu.\n- 12 -\n2\nSECOND TITLE\nNội dung kế tiếp.";
        int first = source.indexOf("1\n"), second = source.indexOf("2\nSECOND");
        ContentCleaner.Options options = new ContentCleaner.Options();
        options.protectedOffsets = Set.of(first, second);
        ContentCleaner.CleanResult result = ContentCleaner.clean(source, options, Set.of());
        assertFalse(result.text.contains("***")); assertFalse(result.text.contains("- 12 -"));
        assertTrue(result.text.startsWith("1\nFIRST"));
        assertEquals("2\nSECOND TITLE\nNội dung kế tiếp.", result.text.substring(result.mapOffset(second)));
        assertEquals(0, result.mapOffset(first));
    }
    @Test public void longUnicodePartitionIsVerbatimAndNeverCutsSurrogates() {
        String source = "  Tiếng Việt 👋 giữ dấu.\n\n".repeat(6000) + " ".repeat(250) + "Kết thúc.";
        List<String> parts = TextChunks.split(source);
        assertEquals(source, String.join("", parts));
        assertEquals(source, String.join("", BookStore.spokenParts(source)));
        for (String part : parts) {
            assertTrue(part.codePointCount(0, part.length()) <= 120);
            assertFalse(Character.isLowSurrogate(part.charAt(0)));
            assertFalse(Character.isHighSurrogate(part.charAt(part.length()-1)));
        }
    }

}
