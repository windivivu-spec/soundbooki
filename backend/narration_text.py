"""Deterministic F5 synthesis input; never written back into the book.

The private voice was trained on lowercase transcripts with simple punctuation.
Keep Vietnamese letters/numbers and sentence punctuation; drop book ornaments.
"""
import re
import unicodedata

DASHES = '-‐‑‒–—−'
BULLETS = '•‣◦▪*'
ACRONYMS = {
    'AI', 'DNA', 'RNA', 'USD', 'VND', 'EUR', 'JPY', 'GBP', 'VIP',
    'CEO', 'CTO', 'CFO', 'COO', 'CMO', 'MBA', 'PHD',
    'TP', 'HCM', 'TP.HCM', 'TPHCM', 'HN', 'SG', 'VN',
    'UBND', 'HĐND', 'CSGT', 'GDP', 'FPT', 'VTV', 'VOV', 'VTC', 'HTV',
    'NASA', 'WHO', 'WTO', 'EU', 'NATO', 'UN', 'ASEAN', 'UNESCO', 'UNICEF',
    'IMF', 'WB', 'APEC', 'OPEC', 'FBI', 'CIA', 'KGB', 'BBC', 'CNN', 'USA', 'UK'
}
ROMAN_NUMERALS_MAP = {
    'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6',
    'vii': '7', 'viii': '8', 'ix': '9', 'x': '10', 'xi': '11', 'xii': '12',
    'xiii': '13', 'xiv': '14', 'xv': '15', 'xvi': '16', 'xvii': '17', 'xviii': '18',
    'xix': '19', 'xx': '20', 'xxi': '21'
}
OCR_COMMON_BLUR_FIXES = {
    'kh0ng': 'không', 'c0': 'có', 'ch0': 'cho', 't0i': 'tôi', 'ngư0i': 'người',
    'đ0': 'đó', 'd0': 'do', 'h0ặc': 'hoặc', 'h0àn': 'hoàn', 'vớ0': 'với', 'nh0': 'nhỏ'
}
VOWELS_VN = 'aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ'
DISCOURSE_MARKERS = (
    'nhưng ', 'tuy nhiên', 'thế nhưng', 'dù vậy', 'mặt khác', 'trái lại', 'ngược lại',
    'vì vậy', 'cho nên', 'do đó', 'bởi vì', 'bởi thế', 'thay vào đó', 'hơn nữa',
    'ngoài ra', 'đồng thời', 'không những', 'hoặc ', 'hay là', 'chẳng hạn', 'ví dụ',
    'cùng với ', 'trước hết', 'cuối cùng', 'nói cách khác', 'thật vậy', 'bạn sẽ ', 'tôi sẽ '
)


def proofread_audiobook_text(text: str) -> str:
    """Pre-synthesis proofreading: fix OCR flaws, lowercase ALL-CAPS words to prevent
    spelling out letters, reconnect broken line-wrap words, normalize Roman chapter numbers,
    and clean scanner junk ornaments."""
    text = unicodedata.normalize('NFC', text)

    # 1. Strip scanner / OCR stray page numbers and divider lines
    text = re.sub(r'(?im)^\s*(trang|page)\s*\d+(\s*/\s*\d+)?\s*$', '', text)
    text = re.sub(r'(?m)^\s*[-=~_]{3,}\s*\d+\s*[-=~_]{3,}\s*$', '', text)

    # 2. Clean scanner ornaments like ***, +++, ===, ---
    text = re.sub(r'(?m)^\s*[*•‣◦▪#`~^|_=+-]{2,}\s*$', '', text)

    # 3. Reconnect broken line-wrap words (e.g. 'doanh-\nnhân' -> 'doanh nhân')
    text = re.sub(r'([a-zA-Zà-ỹÀ-Ỹ]+)[-‐‑‒–—][ \t]*\r?\n[ \t]*([a-zA-Zà-ỹÀ-Ỹ]+)', r'\1 \2', text)

    # 4. Remove speckle dots inside words (e.g. 'k.hông' -> 'không'), preserving acronyms
    def _fix_speckle_dot(m):
        full = m.group(0)
        if full.upper() in ACRONYMS:
            return full
        return m.group(1) + m.group(2)
    text = re.sub(r'\b([a-zA-Zà-ỹÀ-Ỹ]{1,4})\.([a-zA-Zà-ỹÀ-Ỹ]{2,})\b', _fix_speckle_dot, text)

    # 5. Fix common blurred OCR digit-letter mistakes in Vietnamese
    for typo, fix in OCR_COMMON_BLUR_FIXES.items():
        text = re.sub(rf'\b{re.escape(typo)}\b', fix, text, flags=re.IGNORECASE)

    text = re.sub(rf'\b1([{VOWELS_VN}])', r'l\1', text)
    text = re.sub(r'([a-zà-ỹ])1\b', r'\1i', text)
    text = re.sub(r'([a-zà-ỹ])0([a-zà-ỹ])', r'\1o\2', text)

    # 6. Convert Roman numerals in Chapter/Section headings (e.g. 'Chương I' -> 'Chương 1')
    def _replace_roman(m):
        prefix = m.group(1)
        roman = m.group(2).lower()
        num = ROMAN_NUMERALS_MAP.get(roman, m.group(2))
        return f"{prefix} {num}"

    text = re.sub(
        r'(?i)\b(chương|phần|tập|mục|hồi|thế kỷ|thế kỉ)\s+([ivx]+)\b',
        _replace_roman,
        text
    )

    # 7. Normalize ALL-CAPS words to lowercase (preserving standard ACRONYMS)
    # This prevents F5-TTS from spelling out each letter individually
    lines = []
    for line in text.splitlines():
        letters = [c for c in line if c.isalpha()]
        if len(letters) >= 3 and sum(1 for c in letters if c.isupper()) / len(letters) > 0.6:
            words = line.split()
            norm = []
            for w in words:
                clean_w = re.sub(r'^\W+|\W+$', '', w)
                if clean_w.upper() in ACRONYMS:
                    norm.append(w.replace(clean_w, clean_w.upper()))
                else:
                    norm.append(w.lower())
            lines.append(' '.join(norm))
        else:
            def _replace_word(m):
                w = m.group(0)
                clean_w = re.sub(r'^\W+|\W+$', '', w)
                if clean_w.upper() in ACRONYMS:
                    return w.replace(clean_w, clean_w.upper())
                return w.lower()
            line = re.sub(r'\b[A-ZÀ-ỸĐ]{2,}\b', _replace_word, line)
            lines.append(line)
    text = '\n'.join(lines)

    # 8. Clean OCR junk ornaments, brackets, duplicate punctuation
    text = re.sub(r'[{}\[\]|<>~^`#_]+', ' ', text)
    text = re.sub(r'[-‐‑‒–—]{2,}', ' ', text)
    text = re.sub(r'\s+([,.:;?!])', r'\1', text)
    text = re.sub(r'\?{2,}', '?', text)
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r',\s*,+', ', ', text)
    text = re.sub(r'\.{4,}', '...', text)
    return text.strip()


def prepare_f5_text(text):
    text = unicodedata.normalize('NFC', text)
    lines = []
    for original in text.splitlines():
        stripped = original.strip()
        letters = [c for c in stripped if c.isalpha()]
        heading = len(letters) > 1 and all(c.isupper() for c in letters)
        attribution = bool(stripped and stripped[0] in DASHES and stripped[-1] in DASHES
                           and any(c.isalpha() for c in stripped))
        bullet = bool(stripped and stripped[0] in BULLETS)
        line = stripped.lower().replace('…', '.').replace(';', ',').replace(':', ',')
        # Keep an explicit negative sign meaningful; ornaments around author
        # names and dialogue must not become spoken "gạch ngang" tokens.
        line = re.sub(r'(?<!\w)[−-]\s*(?=\d)', 'âm ', line)
        line = re.sub('['+re.escape(DASHES)+']', ' ', line)
        # Remove book ornaments, without discarding meaningful signs such as
        # percent/plus or changing numbers outside this pronunciation fix.
        line = re.sub(r'["“”‘’«»•‣◦▪*_`#]', ' ', line)
        line = re.sub(r'\s+', ' ', line).strip()
        if not any(c.isalnum() for c in line):
            lines.append('')
            continue
        if (heading or attribution or bullet) and line[-1] not in '.?!,':
            line += '.'
        lines.append(line)
    return '\n'.join(lines).strip()


SYNTACTIC_PIVOTS = (
    'thay vì', 'chứ không phải', 'không những', 'mà còn',
    'nhưng lại', 'cho nên', 'vì vậy', 'do đó', 'để rồi'
)


def _add_syntactic_pivots(norm_sent):
    """For long comma-less spans (>= 24 words), insert a prosodic comma before discourse
    pivots so F5-TTS breathes at the grammatical boundary."""
    clauses = norm_sent.split(',')
    out = []
    for cl in clauses:
        words = cl.strip().split()
        if len(words) >= 24:
            mid_str = ' ' + ' '.join(words[6:-6]) + ' '
            for pv in SYNTACTIC_PIVOTS:
                if f' {pv} ' in mid_str:
                    cl = re.sub(rf'\b({re.escape(pv)})\b', r', \1', cl, count=1)
                    break
        out.append(cl.strip())
    return ', '.join(out)


def _split_long_sentence(norm_sent, max_chars=165):
    """Keep normal sentences intact so F5-TTS preserves mid-sentence comma intonation;
    split only long sentences (> max_chars) at the most natural comma/discourse boundary."""
    norm_sent = _add_syntactic_pivots(norm_sent)
    if len(norm_sent) <= max_chars:
        return [norm_sent]
    raw_clauses = [p.strip() for p in norm_sent.split(',') if p.strip()]
    if len(raw_clauses) <= 1:
        words = norm_sent.split()
        if len(words) < 10:
            return [norm_sent]
        mid = len(words) // 2
        best_idx = mid
        best_dist = len(words)
        pivots = {'nhưng', 'mà', 'hoặc', 'hay', 'vì', 'bởi', 'do', 'khi', 'để', 'rằng', 'nếu', 'tuy'}
        two_word_pivots = {('hơn', 'là'), ('thay', 'vì'), ('cho', 'nên'), ('vì', 'vậy'), ('do', 'đó'), ('tuy', 'nhiên'), ('thế', 'nhưng')}
        lo = max(4, len(words) // 4)
        hi = min(len(words) - 4, (len(words) * 3) // 4)
        for idx in range(lo, hi):
            w_cur = words[idx].strip('.,;?!')
            w_nxt = words[idx + 1].strip('.,;?!') if idx + 1 < len(words) else ''
            if (w_cur, w_nxt) in two_word_pivots or w_cur in pivots:
                # Never split inside a two-word pivot like 'hơn là'
                if idx > 0 and (words[idx - 1].strip('.,;?!'), w_cur) in two_word_pivots:
                    continue
                dist = abs(idx - mid)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
        if best_idx > 0 and (words[best_idx - 1].strip('.,;?!'), words[best_idx].strip('.,;?!')) in {('hơn', 'là'), ('thay', 'vì'), ('cho', 'nên')}:
            best_idx -= 1
        return [' '.join(words[:best_idx]).rstrip(',.;') + '.', ' '.join(words[best_idx:])]

    clauses = []
    cur = raw_clauses[0]
    for idx_c, nxt in enumerate(raw_clauses[1:]):
        nxt_clean = nxt.lstrip()
        starts_discourse = any(nxt_clean.startswith(m) for m in DISCOURSE_MARKERS)
        cur_words = len(cur.split())
        nxt_words = len(nxt_clean.split())
        rem_words = sum(len(c.split()) for c in raw_clauses[idx_c + 1:])
        combined_len = len(cur) + 2 + len(nxt_clean)
        if combined_len > max_chars or (len(norm_sent) > max_chars and starts_discourse and cur_words >= 5 and rem_words >= 5):
            clauses.append(cur + '.')
            cur = nxt_clean
        else:
            cur = cur + ', ' + nxt_clean
    clauses.append(cur if cur[-1] in '.?!' else cur + '.')
    return clauses


def plan_f5_prosody(text, max_clause_chars=175):
    """Partition text into context-aware prosodic breath units with explicit pause and pace.
    Includes proofreading: OCR repair, all-caps normalization, and stray symbol cleaning."""
    text = proofread_audiobook_text(text)
    units = []
    for original in text.splitlines():
        stripped = original.strip()
        if not stripped:
            if units and units[-1]['pause'] < 0.68:
                units[-1]['pause'] = 0.68
            continue
        letters = [c for c in stripped if c.isalpha()]
        is_chapter = bool(re.match(r'^(chương|hồi|phần|tập)\b', stripped.lower()))
        is_heading = is_chapter or (len(letters) > 1 and all(c.isupper() for c in letters)) or bool(
            re.match(r'^(mục|lời nói đầu|giới thiệu|kết luận|phụ lục)\b', stripped.lower())
            and len(stripped) < 95
        )
        is_bullet = bool(re.match(r'^[•‣◦▪*+\-–—]\s+', stripped))
        is_attr = bool(stripped[0] in DASHES and stripped[-1] in DASHES and any(c.isalpha() for c in stripped))

        # If entering a new chapter, ensure a natural 3.0s pause before it begins
        if is_chapter and units:
            units[-1]['pause'] = 3.0

        line = stripped.lower()
        line = re.sub(r'(?<!\w)[−-]\s*(?=\d)', 'âm ', line)
        line = re.sub(r'\s+[' + re.escape(DASHES) + r']+\s+', '; ', line)
        line = re.sub('[' + re.escape(DASHES) + ']', ' ', line)
        line = re.sub(
            r'\(\s*([^)]+?)\s*\)',
            lambda m: (f", {m.group(1).replace(':', ',')}, " if len(m.group(1).split()) >= 3 else f" {m.group(1)} "),
            line
        )
        line = re.sub(r'["“”‘’«»•‣◦▪*_`#()]', ' ', line)
        line = re.sub(r'\s*,\s*,+\s*', ', ', line)
        line = re.sub(r'\s+', ' ', line).strip(' ,')
        if not any(c.isalnum() for c in line):
            continue
        if line[-1] not in '.?!…,:;':
            line += '.'

        # Split into sentence-level spans without breaking decimal numbers (e.g. 1.5)
        parts = re.split(r'((?:(?<!\d)\.(?!\d)|[?!…:;])+)(?=\s|$)', line)
        sent_spans = []
        for idx in range(0, len(parts) - 1, 2):
            seg = (parts[idx] + parts[idx + 1]).strip()
            if any(c.isalnum() for c in seg):
                sent_spans.append(seg)
        if len(parts) % 2 == 1 and any(c.isalnum() for c in parts[-1]):
            tail = parts[-1].strip()
            sent_spans.append(tail if tail[-1] in '.?!…,:;' else tail + '.')

        for s_idx, sent in enumerate(sent_spans):
            end_punc = sent[-1] if sent[-1] in '.?!…:;,' else '.'
            is_last_in_line = (s_idx == len(sent_spans) - 1)
            if is_chapter:
                base_pause = 1.40 if not is_last_in_line else 1.80
                base_pace = 0.88
            elif is_heading or is_attr:
                base_pause = 0.72
                base_pace = 0.90
            elif is_bullet and is_last_in_line:
                base_pause = 0.56
                base_pace = 0.95
            elif end_punc in '?!':
                base_pause = 0.54 if not is_last_in_line else 0.66
                base_pace = 0.94
            elif end_punc in ':;…':
                base_pause = 0.38 if not is_last_in_line else 0.52
                base_pace = 0.95
            else:
                base_pause = 0.46 if not is_last_in_line else 0.64
                base_pace = 0.96

            norm_sent = sent.replace('…', '.').replace(';', ',').replace(':', ',')
            if norm_sent[-1] == ',':
                norm_sent = norm_sent[:-1] + '.'
            elif norm_sent[-1] not in '.?!':
                norm_sent += '.'
            has_author_comma = (',' in norm_sent[:-1])

            clauses = _split_long_sentence(norm_sent, max_chars=max_clause_chars)
            for c_idx, cl in enumerate(clauses):
                is_last_clause = (c_idx == len(clauses) - 1)
                c_pause = base_pause if is_last_clause else 0.28
                units.append(dict(text=cl, pause=c_pause, pace=base_pace, author_comma=has_author_comma))
    return units


def has_dynamic_prosody(raw_text):
    """Return True if raw_text contains '!', '?' or quoted dialogue."""
    if not raw_text:
        return False
    if '!' in raw_text or '?' in raw_text:
        return True
    if any(q in raw_text for q in ('"', '“', '”', '«', '»')):
        return True
    return False


def _split_sentence_by_words(norm_sent, min_words=25, max_words=40):
    """Split a single sentence > max_words into balanced clauses around 25-40 words."""
    norm_sent = _add_syntactic_pivots(norm_sent)
    words = norm_sent.split()
    if len(words) <= max_words:
        return [norm_sent]
    raw_clauses = [p.strip() for p in norm_sent.split(',') if p.strip()]
    if len(raw_clauses) <= 1:
        # Split at discourse pivot near 25-35 words
        target = min(max_words - 4, max(min_words, len(words) // 2))
        pivots = {'nhưng', 'mà', 'hoặc', 'hay', 'vì', 'bởi', 'do', 'khi', 'để', 'rằng', 'nếu', 'tuy'}
        two_word_pivots = {('hơn', 'là'), ('thay', 'vì'), ('cho', 'nên'), ('vì', 'vậy'), ('do', 'đó'), ('tuy', 'nhiên'), ('thế', 'nhưng')}
        best_idx = target
        best_dist = len(words)
        lo = max(12, target - 10)
        hi = min(len(words) - 8, max_words)
        for idx in range(lo, hi + 1):
            w_cur = words[idx].strip('.,;?!')
            w_nxt = words[idx + 1].strip('.,;?!') if idx + 1 < len(words) else ''
            if (w_cur, w_nxt) in two_word_pivots or w_cur in pivots:
                if idx > 0 and (words[idx - 1].strip('.,;?!'), w_cur) in two_word_pivots:
                    continue
                dist = abs(idx - target)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
        head = ' '.join(words[:best_idx]).rstrip(',.;') + '.'
        tail = ' '.join(words[best_idx:])
        return [head] + _split_sentence_by_words(tail, min_words=min_words, max_words=max_words)

    chunks = []
    cur = raw_clauses[0]
    for nxt in raw_clauses[1:]:
        nxt_clean = nxt.lstrip()
        cand = cur + ', ' + nxt_clean
        if len(cand.split()) <= max_words:
            cur = cand
        else:
            chunks.append(cur if cur[-1] in '.?!' else cur + '.')
            cur = nxt_clean
    if cur:
        chunks.append(cur if cur[-1] in '.?!' else cur + '.')
    return chunks


def chunk_f5_smart(text, min_words=25, max_words=40):
    """Split book text into sentence-aligned chunks (~25-40 words) with dynamic style detection
    and explicit pauses (250ms after sentence chunks, 500ms at paragraph breaks)."""
    text = unicodedata.normalize('NFC', text)
    chunks = []
    for original in text.splitlines():
        stripped = original.strip()
        if not stripped:
            if chunks:
                chunks[-1]['pause'] = 0.50
                chunks[-1]['is_paragraph_end'] = True
            continue

        letters = [c for c in stripped if c.isalpha()]
        is_heading = (len(letters) > 1 and all(c.isupper() for c in letters)) or bool(
            re.match(r'^(chương|phần|mục|lời nói đầu|giới thiệu|kết luận|phụ lục)\b', stripped.lower())
            and len(stripped) < 95
        )
        is_attr = bool(stripped[0] in DASHES and stripped[-1] in DASHES and any(c.isalpha() for c in stripped))
        para_has_quotes = any(q in stripped for q in ('"', '“', '”', '«', '»'))

        # Split raw paragraph into raw sentences first so we preserve quote/!? detection per sentence
        raw_parts = re.split(r'((?:(?<!\d)\.(?!\d)|[?!…])+)(?=\s|$|[”"’\'])', stripped)
        raw_sents = []
        for idx in range(0, len(raw_parts) - 1, 2):
            seg = (raw_parts[idx] + raw_parts[idx + 1]).strip()
            if any(c.isalnum() for c in seg):
                raw_sents.append(seg)
        if len(raw_parts) % 2 == 1 and any(c.isalnum() for c in raw_parts[-1]):
            raw_sents.append(raw_parts[-1].strip())
        if not raw_sents and any(c.isalnum() for c in stripped):
            raw_sents = [stripped]

        # Normalize each sentence
        norm_items = []
        for raw_s in raw_sents:
            dyn = has_dynamic_prosody(raw_s) or para_has_quotes
            line = raw_s.lower()
            line = re.sub(r'(?<!\w)[−-]\s*(?=\d)', 'âm ', line)
            line = re.sub(r'\s+[' + re.escape(DASHES) + r']+\s+', ', ', line)
            line = re.sub('[' + re.escape(DASHES) + ']', ' ', line)
            line = re.sub(
                r'\(\s*([^)]+?)\s*\)',
                lambda m: (f", {m.group(1).replace(':', ',')}, " if len(m.group(1).split()) >= 3 else f" {m.group(1)} "),
                line
            )
            line = re.sub(r'["“”‘’«»•‣◦▪*_`#()]', ' ', line)
            line = line.replace('…', '.').replace(';', ',').replace(':', ',')
            line = re.sub(r'\s*,\s*,+\s*', ', ', line)
            line = re.sub(r'\s+', ' ', line).strip(' ,')
            if not any(c.isalnum() for c in line):
                continue
            if line[-1] not in '.?!':
                line += '.'
            for sub in _split_sentence_by_words(line, min_words=min_words, max_words=max_words):
                norm_items.append(dict(
                    text=sub,
                    raw_text=raw_s,
                    is_dynamic=dyn or ('!' in sub or '?' in sub),
                    words=len(sub.split()),
                ))

        if not norm_items:
            continue

        if is_heading or is_attr:
            combined_text = ' '.join(item['text'] for item in norm_items)
            chunks.append(dict(
                text=combined_text,
                raw_text=stripped,
                is_dynamic=any(item['is_dynamic'] for item in norm_items),
                style='dynamic' if any(item['is_dynamic'] for item in norm_items) else 'calm',
                pause=0.50,
                is_paragraph_end=True,
                author_comma=(',' in combined_text[:-1]),
            ))
            continue

        # Group sentences within paragraph into ~25-40 word chunks
        para_chunks = []
        cur = norm_items[0].copy()
        for nxt in norm_items[1:]:
            if cur['words'] < min_words and (cur['words'] + nxt['words']) <= max_words:
                cur['text'] = cur['text'] + ' ' + nxt['text']
                cur['raw_text'] = cur['raw_text'] + ' ' + nxt['raw_text']
                cur['is_dynamic'] = cur['is_dynamic'] or nxt['is_dynamic']
                cur['words'] += nxt['words']
            else:
                para_chunks.append(cur)
                cur = nxt.copy()
        para_chunks.append(cur)

        for idx_c, pch in enumerate(para_chunks):
            is_para_end = (idx_c == len(para_chunks) - 1)
            chunks.append(dict(
                text=pch['text'],
                raw_text=pch['raw_text'],
                is_dynamic=pch['is_dynamic'],
                style='dynamic' if pch['is_dynamic'] else 'calm',
                pause=0.50 if is_para_end else 0.25,
                is_paragraph_end=is_para_end,
                author_comma=(',' in pch['text'][:-1]),
            ))
    return chunks


# ==============================================================================
# Smart Sentence Splitting & Audio Safe Chunking for Cloud Pro (HeyGen TTS)
# ==============================================================================

ABBREVIATIONS_VN = [
    'TP.HCM', 'TP. HN', 'TP.HN', 'TP.', 'GS.TS.', 'PGS.TS.', 'GS.', 'PGS.',
    'TS.', 'BS.', 'ThS.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'St.',
    'v.v.', 'v..v.', 'v.v..', 'etc.', 'e.g.', 'i.e.', 'No.', 'Co.', 'Ltd.',
    'Corp.', 'Inc.', 'UBND.', 'HĐND.'
]


def split_smart_vietnamese_sentences(text: str) -> list:
    """Split Vietnamese text into coherent, grammatically complete sentences.

    Protects:
    - Decimal numbers (15.5, 3.14).
    - Common abbreviations (TP.HCM, GS.TS., BS., v.v.).
    - Single initials (V. A, J. K. Rowling).
    - Dialogue quotation enclosures (e.g. '“Chào bạn!” - anh nói.').
    """
    text = unicodedata.normalize('NFC', text).strip()
    if not text:
        return []

    # 1. Protect decimals: 15.5, 3.14
    protected = re.sub(r'(?<=\d)\.(?=\d)', '@@DEC@@', text)

    # 2. Protect known abbreviations
    for a in sorted(ABBREVIATIONS_VN, key=len, reverse=True):
        protected = protected.replace(a, a.replace('.', '@@DOT@@'))

    # 3. Protect single initials e.g. 'V. A', 'J. K.'
    protected = re.sub(r'\b([A-ZÀ-Ỹ])\.(?=\s*[A-ZÀ-Ỹ])', r'\1@@DOT@@', protected)

    # 4. Split on sentence boundaries: [.!?…] optionally followed by closing quotes/brackets
    parts = re.split(r'([.!?…]+[”’"\'\)\]]*(?:\s+|$))', protected)
    raw_sents = []
    for i in range(0, len(parts) - 1, 2):
        seg = parts[i] + parts[i + 1]
        if seg.strip():
            raw_sents.append(seg.strip())
    if len(parts) % 2 == 1 and parts[-1].strip():
        raw_sents.append(parts[-1].strip())

    # 5. Restore protected dots & decimals
    cleaned = [
        s.replace('@@DOT@@', '.').replace('@@DEC@@', '.').strip()
        for s in raw_sents if s.strip()
    ]
    return cleaned


def split_long_sentence_by_clauses(sent: str, max_chars: int = 3500) -> list:
    """Split an ultra-long sentence (> max_chars) into logical clauses, preserving
    conjunctions and ensuring words are never cut in half."""
    if len(sent) <= max_chars:
        return [sent]

    delims = [
        r'(?<=[;:—–])\s+',
        r'(?<=,)\s+(?=(?:nhưng|tuy nhiên|vì vậy|do đó|bởi vì|mặc dù|hơn nữa|đồng thời|ngoài ra|hoặc|thay vì|ngược lại)\b)',
        r'(?<=,)\s+',
        r'\s+'
    ]

    parts = [sent]
    for pattern in delims:
        new_parts = []
        for p in parts:
            if len(p) <= max_chars:
                new_parts.append(p)
            else:
                sub = re.split(pattern, p)
                cur = ''
                for s in sub:
                    s = s.strip()
                    if not s:
                        continue
                    if len(cur) + len(s) + 1 <= max_chars:
                        cur = (cur + ' ' + s) if cur else s
                    else:
                        if cur:
                            new_parts.append(cur)
                        cur = s
                if cur:
                    new_parts.append(cur)
        parts = new_parts
        if all(len(p) <= max_chars for p in parts):
            break

    # Hard-boundary safety net: split at spaces if any part still exceeds max_chars
    final_parts = []
    for p in parts:
        while len(p) > max_chars:
            cut = p.rfind(' ', 0, max_chars)
            if cut <= 0:
                cut = max_chars
            final_parts.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            final_parts.append(p)

    return final_parts


def pack_sentences_into_chunks(sentences: list, max_chars: int = 5000, drop_oversized: bool = False) -> list:
    """Pack sentences without losing oversized content.

    The legacy drop_oversized argument remains accepted for old callers, but
    content is always retained and split at a safe clause/word boundary.
    """
    from cloud_chunking import chunks
    return chunks(' '.join(s.strip() for s in sentences if s.strip()), max_chars)


def split_text_into_safe_chunks(text: str, max_chars: int = 5000, drop_oversized: bool = False) -> list:
    """Partition verbatim, packing across paragraphs up to the provider limit."""
    from cloud_chunking import chunks
    return chunks(text, max_chars)
