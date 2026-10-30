"""Conservative, deterministic narration cleanup. No model, rewrite or network."""
import re
import unicodedata

def normalize_all_caps_lines(text):
    """Sentence case for fully uppercase lines, retaining spacing and offsets.

    Mixed-case prose is untouched. Only case changes are authorized here;
    source text, numbers, spelling, punctuation and abbreviations stay intact.
    """
    from narration_text import ACRONYMS
    acronyms=ACRONYMS|{'ĐH','GS','TS','BS','THS','PGS','NFC','PDF','EPUB','OCR'}
    result=[]
    for line in text.splitlines(keepends=True):
        letters=[ch for ch in line if ch.isalpha() and ch.lower()!=ch.upper()]
        if len(letters)<2 or not all(ch.isupper() for ch in letters):
            result.append(line);continue
        def convert(match):
            token=match.group()
            if token in acronyms or all(part in acronyms for part in token.split('.')) or re.fullmatch(r'[IVXLCDM]{1,8}',token):return token
            return ''.join(ch.lower() if len(ch.lower())==1 else ch for ch in token)
        value=re.sub(r'[^\W\d_]+(?:\.[^\W\d_]+)*',convert,line)
        for at,ch in enumerate(value):
            if ch.isalpha() and ch.lower()!=ch.upper():
                upper=ch.upper()
                if len(upper)==1:value=value[:at]+upper+value[at+1:]
                break
        result.append(value)
    return ''.join(result)

def roman_number(token):
    """Accept canonical Roman numerals only, never arbitrary I/V/X words."""
    token=token.upper()
    if not token or not re.fullmatch(r'M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})',token):return None
    values=dict(I=1,V=5,X=10,L=50,C=100,D=500,M=1000)
    return sum(-values[ch] if at+1<len(token) and values[ch]<values[token[at+1]] else values[ch] for at,ch in enumerate(token))

def roman_edits(text,language='vi'):
    """Structural numerals: chapters, centuries, numbered headings/list items.

    Leave prose, acronyms and English I intact. Offsets refer to the input so
    changed-length digits can be mapped back to the original reader segments.
    """
    edits={}
    patterns=[
        r'(?i)\b(?:chương|phần|mục|quyển|tập|hồi|cuốn|thiên|tiết|phụ lục|thế kỷ|thế kỉ|chapter|part|volume|book|section|act)\s+([IVXLCDM]+)(?!\w)',
        r'(?m)^[ \t]*([IVXLCDM]+)(?=[.)](?:\s|$)|[ \t]+[—–-][ \t]+)',
        r'(?m)^[ \t]*([IVXLCDM]+)[ \t]*(?=\r?$)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern,text):
            token=match.group(1)
            # A bare I line is ambiguous with the English first-person pronoun.
            if language=='en' and token=='I' and match.group(0).strip()=='I' and not text[match.end(1):].split('\n',1)[0].strip():continue
            number=roman_number(token)
            if number is not None:edits[match.span(1)]=str(number)
    return [(start,end,value) for (start,end),value in sorted(edits.items())]

def normalize_import_text(text,language='vi'):
    edits=roman_edits(text,language)
    for start,end,value in reversed(edits):text=text[:start]+value+text[end:]
    return normalize_all_caps_lines(text),edits

def narratable(text):
    return any(ch.isalnum() for ch in text)

def decoration(line):
    core=''.join(ch for ch in line if not ch.isspace())
    return len(core)>=3 and not narratable(core) and all(unicodedata.category(ch)[0] in 'PS' for ch in core)

def clean_text(text, options=None, repeated=()):
    options=options or {}
    lines=text.splitlines(keepends=True)
    # A TOC is removed only when explicitly selected and identified by its title
    # followed by at least three dotted leaders. Chapter prose stays untouched.
    toc=set()
    if options.get('toc'):
        for i,line in enumerate(lines):
            if line.strip().casefold() in ('mục lục','contents','table of contents'):
                block=[];leaders=0
                for n in range(i+1,len(lines)):
                    value=lines[n].strip()
                    if not value or decoration(value):block.append(n);continue
                    if re.search(r'(?:\.{3,}|…{2,}|·{3,})\s*\d+\s*$',value):block.append(n);leaders+=1
                    else:break
                if leaders>=3:toc.update([i,*block])
    removed=[];kept=[]
    for i,line in enumerate(lines):
        value=line.strip();reason=None
        if options.get('decorations',True) and decoration(value):reason='decoration'
        elif options.get('pageNumbers') and re.fullmatch(r'(?:[-–—]\s*)?\d{1,5}(?:\s*[-–—])?',value):reason='pageNumber'
        elif options.get('repeatedHeaders') and value in repeated:reason='repeatedHeader'
        elif i in toc:reason='toc'
        if reason:removed.append(dict(line=i+1,text=line.rstrip('\r\n'),reason=reason))
        else:kept.append(line)
    return dict(text=''.join(kept),removed=removed,count=len(removed))

def repeated_headers(book):
    from collections import Counter
    counts=Counter()
    for page in book['pages']:
        lines=[v.strip() for v in page['text'].splitlines() if v.strip()]
        counts.update(set(lines[:1]+lines[-1:]))
    return {line for line,count in counts.items() if count>=3 and 2<len(line)<120}
