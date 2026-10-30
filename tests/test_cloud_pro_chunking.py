import io
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.narration_text import (
    split_smart_vietnamese_sentences,
    split_long_sentence_by_clauses,
    pack_sentences_into_chunks,
    split_text_into_safe_chunks,
)
from cloud.heygen_studio.synthesize_book_heygen import split_into_audiobook_paragraphs
from cloud.heygen_studio.heygen_client import HeyGenClient


class CloudProChunkingTests(unittest.TestCase):
    def test_sentence_splitting_protects_abbreviations_and_decimals(self):
        text = (
            "GS.TS. Nguyễn Văn A hiện đang giảng dạy tại trường ĐH ở TP.HCM. "
            "Ông đã hoàn thành hơn 15.5 năm nghiên cứu về mô hình AI! "
            "Bạn có biết dự án này tiêu tốn 3.14 triệu USD không? "
            "“Tất nhiên là có rồi,” - một sinh viên hào hứng đáp… "
            "Các chi tiết khác bao gồm số liệu v.v. đã được lưu trữ."
        )
        sents = split_smart_vietnamese_sentences(text)
        self.assertEqual(len(sents), 5)
        self.assertEqual(sents[0], "GS.TS. Nguyễn Văn A hiện đang giảng dạy tại trường ĐH ở TP.HCM.")
        self.assertEqual(sents[1], "Ông đã hoàn thành hơn 15.5 năm nghiên cứu về mô hình AI!")
        self.assertEqual(sents[2], "Bạn có biết dự án này tiêu tốn 3.14 triệu USD không?")
        self.assertEqual(sents[3], "“Tất nhiên là có rồi,” - một sinh viên hào hứng đáp…")
        self.assertEqual(sents[4], "Các chi tiết khác bao gồm số liệu v.v. đã được lưu trữ.")

    def test_split_long_sentence_by_clauses_preserves_words(self):
        long_sentence = (
            "Trong một buổi chiều mưa tại vùng quê yên bình; khi ánh hoàng hôn dần buông xuống chân đồi: "
            "người nghệ sĩ già ngồi trầm ngâm suy ngẫm về cuộc đời của mình, nhưng trong lòng ông vẫn luôn "
            "cháy bỏng một ngọn lửa đam mê nghệ thuật mãnh liệt mà không có thử thách nào có thể dập tắt được."
        )
        chunks = split_long_sentence_by_clauses(long_sentence, max_chars=80)
        self.assertTrue(len(chunks) >= 3)
        for c in chunks:
            self.assertLessEqual(len(c), 80)
            self.assertTrue(len(c.strip()) > 0)
        # Verify no words are severed mid-character
        all_words = set(long_sentence.replace(';', ' ').replace(':', ' ').replace(',', ' ').split())
        for c in chunks:
            for w in c.replace(';', ' ').replace(':', ' ').replace(',', ' ').split():
                self.assertIn(w, all_words)

    def test_pack_sentences_respects_max_chars(self):
        sentences = [
            f"Đây là câu văn số {i+1} kể về hành trình chinh phục đỉnh cao của những người trẻ."
            for i in range(40)
        ]
        packed = pack_sentences_into_chunks(sentences, max_chars=500)
        self.assertTrue(len(packed) > 1)
        for chunk in packed:
            self.assertLessEqual(len(chunk), 500)
            # Each chunk should end with full sentence punctuation
            self.assertTrue(chunk.rstrip().endswith("."))

    def test_paragraph_splitting_under_5k_preserves_integral_paragraph(self):
        text = (
            "CHƯƠNG 1: KHỞI ĐẦU MỚI\n\n"
            "Mỗi buổi sáng thức dậy là một cơ hội để bạn bắt đầu lại từ đầu. "
            "Hãy hít một hơi thật sâu và mỉm cười với cuộc sống.\n\n"
            "- Khuyết danh -\n\n"
            "Bạn đã sẵn sàng bước tiếp chưa?\n\n"
            "Hãy vững tin vào tương lai phía trước."
        )
        items = split_into_audiobook_paragraphs(text, max_chunk_chars=3500)
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0]["type"], "heading")
        self.assertEqual(items[0]["pause_s"], 0.8)
        self.assertEqual(items[1]["type"], "body")
        self.assertEqual(items[1]["pause_s"], 0.9)
        self.assertEqual(items[2]["type"], "attribution")
        self.assertEqual(items[2]["pause_s"], 0.8)
        self.assertEqual(items[3]["type"], "question")
        self.assertEqual(items[3]["pause_s"], 1.0)
        self.assertEqual(items[4]["type"], "final")
        self.assertEqual(items[4]["pause_s"], 1.0)
        for it in items:
            self.assertFalse(it["is_sub_chunk"])

    def test_paragraph_over_5k_chars_automatically_splits_by_sentence_with_emotional_pauses(self):
        # Create a massive paragraph of 8,000 characters
        sentences = [
            f"Câu văn thứ {i+1} trong đoạn văn dài này trình bày chi tiết về các nguyên lý tâm lý học sâu sắc của con người. "
            f"Chúng ta luôn tìm kiếm sự bình yên trong tâm hồn giữa thế giới bận rộn này."
            for i in range(45)
        ]
        long_paragraph = " ".join(sentences)
        self.assertGreater(len(long_paragraph), 7000)

        book_text = f"CHƯƠNG 1: TRIẾT LÝ SỐNG\n\n{long_paragraph}\n\nĐoạn văn ngắn kết thúc chương một.\n\nCHƯƠNG 2: HÀNH ĐỘNG"
        items = split_into_audiobook_paragraphs(book_text, max_chunk_chars=3000)

        # Heading 1, sub-chunks of long paragraph, body paragraph, Heading 2
        self.assertTrue(len(items) >= 5)
        self.assertEqual(items[0]["type"], "heading")

        # The sub-chunks for long_paragraph
        sub_items = [it for it in items if it.get("para_idx") == 2 and it.get("chapter_idx") == 1]
        self.assertTrue(len(sub_items) >= 3)
        for sub in sub_items:
            self.assertTrue(sub["is_sub_chunk"])
            self.assertLessEqual(len(sub["text"]), 3000)
            self.assertTrue(sub["text"].endswith("."))
            # Must start capitalized
            self.assertTrue(sub["text"][0].isupper())

        # Sub-chunks except last have sentence_continuation pause (0.4s)
        for sub in sub_items[:-1]:
            self.assertEqual(sub["type"], "sentence_continuation")
            self.assertEqual(sub["pause_s"], 0.40)

        # Last sub-chunk has paragraph-end pause (0.9s)
        self.assertEqual(sub_items[-1]["type"], "body")
        self.assertEqual(sub_items[-1]["pause_s"], 0.90)

    def test_heygen_client_synthesize_auto_chunks_over_5000_chars(self):
        client = HeyGenClient(api_key="mock_key")
        long_text = " ".join([
            f"Đây là câu văn dài số {i+1} để kiểm tra tính năng tự động chia nhỏ khi văn bản vượt quá 5.000 ký tự. "
            f"Giọng đọc HeyGen cần phải liền mạch và không bị lỗi."
            for i in range(40)
        ])
        self.assertGreater(len(long_text), 5000)

        # Mock self._request to return fake audio response
        fake_audio_wav = (
            b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00"
            + b"\x00\x00" * 1024
        )

        with patch.object(client, "_request") as mock_req, \
             patch("urllib.request.urlopen") as mock_url:
            mock_req.return_value = {
                "data": {"audio_url": "https://resource.heygen.ai/audio123.wav", "duration": 5.0}
            }
            fake_resp = Mock()
            fake_resp.read.return_value = fake_audio_wav
            mock_url.return_value.__enter__.return_value = fake_resp

            res = client.synthesize(text=long_text, voice_id="3414fd7fdaa64e619fb8b021534ce368")

            # Should have called _request multiple times for each sub-chunk
            self.assertTrue(mock_req.call_count >= 2)
            for call_args in mock_req.call_args_list:
                payload = call_args[0][2]
                self.assertLessEqual(len(payload["text"]), 5000)

            # Combined duration should include sub-chunks + 0.4s pauses
            self.assertEqual(res["duration"], 5.0 * mock_req.call_count)
            self.assertTrue(len(res["audio_bytes"]) > 0)
            self.assertEqual(res["char_count"], len(long_text))

    def test_oversized_sentence_is_preserved_even_for_legacy_drop_callers(self):
        # A runaway sentence of 6,000 characters without punctuation
        huge_sentence = "Từ này lặp lại " * 400 + "."  # ~6,000 chars
        normal_sentence = "Đây là một câu văn hoàn toàn bình thường và giàu cảm xúc."
        sentences = [normal_sentence, huge_sentence, "Câu văn cuối cùng."]

        # When drop_oversized=True (default), the 6k sentence is omitted for safety
        packed = pack_sentences_into_chunks(sentences, max_chars=4800, drop_oversized=True)
        self.assertGreaterEqual(len(packed), 2)
        self.assertIn("hoàn toàn bình thường", "".join(packed))
        self.assertIn("Câu văn cuối cùng.", "".join(packed))
        self.assertEqual("".join(packed), " ".join(sentences))

    def test_pack_maximizes_near_5k_limit_without_breaking_sentences(self):
        # Create 10,000 chars of coherent sentences
        sentences = [
            f"Câu số {i+1}: Cuộc sống luôn mang lại những bài học quý giá cho mỗi chúng ta khi biết nỗ lực."
            for i in range(120)
        ]
        total_len = sum(len(s) for s in sentences)
        self.assertGreater(total_len, 9000)

        chunks = pack_sentences_into_chunks(sentences, max_chars=4800)
        self.assertTrue(len(chunks) >= 2)
        for c in chunks:
            self.assertLessEqual(len(c), 4800)
            # Must end with complete sentence punctuation
            self.assertTrue(c.rstrip().endswith("."))
        # First chunk should utilize a large portion close to 4,800 chars
        self.assertGreater(len(chunks[0]), 4200)


if __name__ == "__main__":
    unittest.main()
