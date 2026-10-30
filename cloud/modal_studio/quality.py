"""Validate model review as evidence, never as permission to rewrite a book."""
import hashlib
import math
import re

REVISION='cloud-quality-v1'

def validated_issues(text,proposals):
    if not isinstance(proposals,list) or len(proposals)>12:raise ValueError('Invalid review list')
    result=[]
    for item in proposals:
        if not isinstance(item,dict):raise ValueError('Invalid review item')
        before=item.get('before');after=item.get('after');reason=item.get('reason','')
        if not isinstance(before,str) or not 1<=len(before)<=100 or not isinstance(after,str) or not 1<=len(after)<=100 or not isinstance(reason,str):raise ValueError('Invalid review span')
        # Unique literal source span only. No global replacement, invented
        # quote, empty deletion, long paraphrase or ambiguous occurrence.
        if text.count(before)!=1 or before==after:continue
        result.append(dict(start=text.index(before),end=text.index(before)+len(before),before=before,after=after,reason=reason[:200],requiresReview=True))
    result.sort(key=lambda x:x['start'])
    if any(a['end']>b['start'] for a,b in zip(result,result[1:])):raise ValueError('Overlapping review spans')
    return result

def review_report(texts,metas):
    if len(metas)!=len(texts) or any(m.get('review_checked') is not True for m in metas):raise ValueError('Cloud text review did not complete')
    return dict(revision=REVISION,checkedUnits=len(texts),sourceSHA256=hashlib.sha256(''.join(texts).encode()).hexdigest(),
                textChanged=False,issues=[dict(unit=i,**issue) for i,(text,meta) in enumerate(zip(texts,metas)) for issue in validated_issues(text,meta.get('text_issues'))])

def check_audio(audio,sample_rate,characters):
    """Reject broken, silent, non-finite or implausibly short/long narration.

    This is a signal QA gate, not an ASR or pronunciation guarantee.
    """
    import numpy as np
    data=np.asarray(audio)
    duration=len(data)/sample_rate
    if not data.size or not np.isfinite(data).all():raise ValueError('Cloud returned empty or non-finite audio')
    rms=float(np.sqrt(np.mean(data.astype(float)**2)))
    clipped=float(np.mean(np.abs(data)>=.999))
    count=max(1,len(re.sub(r'\s','',characters))) if isinstance(characters,str) else max(1,characters)
    if rms<.0001 or clipped>.02 or not max(.08,count*.012)<=duration<=max(15,count*.8):raise ValueError('Cloud audio failed duration, silence or clipping QA')
    return dict(duration=round(duration,3),rms=round(rms,6),clippedRatio=round(clipped,6),passed=True)
