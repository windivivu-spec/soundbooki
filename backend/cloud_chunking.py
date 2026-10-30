"""Lossless provider request boundaries, independent of local reader segments."""
import hashlib
import json
import re
from narration_text import ABBREVIATIONS_VN

LIMIT = 5000
VERSION = 'heygen-5000-v1'


def sentence_ends(text):
    # Record offsets in the original string: no NFC conversion, stripping or
    # placeholder substitution (which would change Unicode billing/source).
    protected = set()
    for abbreviation in ABBREVIATIONS_VN:
        for match in re.finditer(r'(?<!\w)' + re.escape(abbreviation), text, re.I):
            protected.update(i for i in range(match.start(), match.end()) if text[i] == '.')
    for match in re.finditer(r'(?<=\d)\.(?=\d)|\b[A-ZÀ-ỸĐ]\.(?=\s*[A-ZÀ-ỸĐ])', text):
        protected.add(match.end() - 1)
    for match in re.finditer(r'[.!?…]+[”’"\')\]]*(?:\s+|$)', text):
        punctuation = match.start()
        if text[punctuation] == '.' and punctuation in protected:
            continue
        yield match.end()


def cut_at(text, limit=LIMIT):
    """Use the last complete sentence near capacity, then clause/word fallback.

    Reserve the fallback for long sentences; never discard one or insert text.
    Whitespace belongs to exactly one side, including page/paragraph breaks.
    """
    if len(text) <= limit:
        return len(text)
    floor = int(limit * .85)
    ends = [end for end in sentence_ends(text[:limit + 1]) if floor <= end <= limit]
    if ends:
        return ends[-1]
    for pattern in (r'[,;:—–]\s+', r'\s+'):
        ends = [m.end() for m in re.finditer(pattern, text[:limit + 1]) if floor <= m.end() <= limit]
        if ends:
            return ends[-1]
    # An unbroken token is the only case requiring a character boundary.
    cut = limit
    import unicodedata
    while cut > 1 and (unicodedata.combining(text[cut]) or text[cut] == '\u200d' or text[cut - 1] == '\u200d'):
        cut -= 1
    return cut


def chunks(text, limit=LIMIT):
    if type(limit) is not int or limit < 1:
        raise ValueError('Invalid cloud character limit')
    result = []
    while text:
        cut = cut_at(text, limit)
        result.append(text[:cut])
        text = text[cut:]
    return result


def pack_segments(segments, book):
    """Pack across reader/page boundaries, preserving actual chapter membership."""
    from scopes import chapters
    catalog = chapters(book)
    groups = []
    for segment in segments:
        index = segment['index']
        chapter = next((c['id'] for c in catalog if index in c.get('indices', []) or
                        ('indices' not in c and c['startPage'] <= segment['page'] <= c['endPage'])), 'document')
        if not groups or groups[-1][0] != chapter:
            groups.append((chapter, []))
        groups[-1][1].append(segment)
    result = []
    for _, sources in groups:
        text = ''.join(s['text'] for s in sources)
        offset = 0
        for part in chunks(text):
            end = offset + len(part)
            spans = []
            source_at = 0
            for source in sources:
                source_end = source_at + len(source['text'])
                lo, hi = max(offset, source_at), min(end, source_end)
                if lo < hi:
                    spans.append(dict(id=source['id'], index=source['index'], page=source['page'], start=lo-source_at, end=hi-source_at))
                source_at = source_end
                if source_at >= end:
                    break
            identity = hashlib.sha256(json.dumps([VERSION, spans, part], ensure_ascii=False).encode()).hexdigest()[:32]
            result.append(dict(id=identity, page=spans[0]['page'], index=len(result), text=part, sourceSpans=spans))
            offset = end
    return result


def source_items(data):
    """Compare pre-upgrade immutable orders with the same newly packed source."""
    result = []
    for segment in data['segments']:
        spans = segment.get('sourceSpans') or [dict(id=segment['id'], index=segment['index'], page=segment['page'], start=0, end=len(segment['text']))]
        at = 0
        for span in spans:
            size = span['end'] - span['start']
            identity = (span['id'], span['index'], span['page'])
            text = segment['text'][at:at+size]
            if result and result[-1][0] == identity:
                result[-1] = (identity, result[-1][1] + text)
            else:
                result.append((identity, text))
            at += size
        if at != len(segment['text']):
            result.append((('unmapped', segment['id']), segment['text'][at:]))
    return result
