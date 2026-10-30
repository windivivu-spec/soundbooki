"""Optional Docling layout/OCR pipeline. Separate from the lightweight Mac path.

No remote URLs or rewriting. May run in a prepared offline environment, or in
the owner's authenticated cloud container. Heavy dependencies import on demand.
"""
import hashlib
import os
from pathlib import Path
import re
import time

REVISION='docling-pdf-v1'
MAX_BYTES=25*1024*1024
MAX_PAGES=2000

def converter(language='vi',allow_model_download=False):
    if language not in ('vi','en'):raise ValueError('Unsupported document language')
    if not allow_model_download:
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions,TesseractCliOcrOptions,HeadingHierarchyOptions
    from docling.document_converter import DocumentConverter,PdfFormatOption
    options=PdfPipelineOptions()
    options.do_ocr=True;options.do_table_structure=False
    options.enable_remote_services=False
    options.heading_hierarchy_options=HeadingHierarchyOptions(enabled=True)
    options.generate_parsed_pages=True
    # Hybrid OCR: don't discard good embedded Vietnamese text on every page.
    options.ocr_options=TesseractCliOcrOptions(lang=['vie','eng'] if language=='vi' else ['eng'])
    return DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})

def pack_document(document):
    """Carry source blocks/coordinates and real section labels into review JSON."""
    pages={int(n):dict(page=int(n)-1,text='',blocks=[],method='cloud-layout',warning='') for n in document.pages}
    issues=[]
    for item,_ in document.iterate_items():
        text=getattr(item,'text',None);provenance=getattr(item,'prov',[])
        label=getattr(getattr(item,'label',None),'value',str(getattr(item,'label','text')))
        if not isinstance(text,str) or not text or not provenance:
            if label in ('table','formula','code'):
                issues.append(dict(label=label,pages=[int(p.page_no)-1 for p in provenance],reason='Khối không có chữ đọc được; đối chiếu bản gốc trước khi tạo giọng.'))
            continue
        spans=[]
        for p in provenance:
            page=int(p.page_no)
            if page not in pages:raise ValueError('Layout returned an unknown page')
            bounds=getattr(p,'charspan',None)
            if len(provenance)>1:
                if not bounds or len(bounds)!=2 or not 0<=bounds[0]<bounds[1]<=len(text):raise ValueError('Review multi-page block provenance before import')
                start,end=bounds
            else:start,end=0,len(text)
            if any(max(start,a)<min(end,b) for a,b in spans):raise ValueError('Overlapping layout spans')
            spans.append((start,end))
            value=text[start:end];target=pages[page]
            offset=len(target['text']);target['text']+=value+'\n\n'
            bbox=p.bbox
            target['blocks'].append(dict(text=value,label=label,start=offset,end=offset+len(value),
                bbox=dict(l=bbox.l,t=bbox.t,r=bbox.r,b=bbox.b,origin=str(bbox.coord_origin))))
    result=[pages[n] for n in sorted(pages)]
    if len(result)>MAX_PAGES or sum(len(p['text']) for p in result)>2_000_000:raise ValueError('Document exceeds review limit')
    if not result or not any(p['text'].strip() for p in result):raise ValueError('No readable text; do not create narration from an empty conversion')
    # Do not turn every subheading/caption into a chapter. Preserve the detected
    # labels as review candidates; final boundaries require source verification.
    candidates=[dict(page=p['page'],offset=b['start'],title=b['text'],origin='cloud-section-header') for p in result for b in p['blocks'] if b['label']=='section_header']
    return dict(pages=result,headingCandidates=candidates,issues=issues,requiresReview=True)

def process_pdf(path,language='vi',prepared_converter=None,allow_model_download=False):
    path=Path(path)
    if path.suffix.lower()!='.pdf' or not path.is_file() or not 0<path.stat().st_size<=MAX_BYTES:raise ValueError('Select one PDF up to 25 MiB')
    raw=path.read_bytes()
    if not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF signature')
    started=time.monotonic()
    engine=prepared_converter or converter(language,allow_model_download)
    converted=engine.convert(path,max_num_pages=MAX_PAGES,max_file_size=MAX_BYTES)
    status=getattr(converted.status,'value',str(converted.status))
    if status!='success':raise ValueError('Cloud layout/OCR is incomplete; retain the local book')
    result=pack_document(converted.document)
    return dict(revision=REVISION,sourceSHA256=hashlib.sha256(raw).hexdigest(),language=language,
                elapsedSeconds=round(time.monotonic()-started,2),**result)

if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf');p.add_argument('--output',required=True);p.add_argument('--language',choices=['vi','en'],default='vi')
    p.add_argument('--allow-model-download',action='store_true',help='Explicit dependency/model setup only')
    args=p.parse_args()
    result=process_pdf(args.pdf,args.language,allow_model_download=args.allow_model_download)
    dest=Path(args.output);part=dest.with_suffix('.partial');part.write_text(json.dumps(result,ensure_ascii=False,indent=2));part.replace(dest)
