"""Stage only the new folder-based music packs. No network or credentials."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from music import catalog

def prepare():
    dest=ROOT/'.release-assets/music';dest.mkdir(parents=True,exist_ok=True)
    groups={}
    for item in catalog():
        if item.get('origin')=='user-library':groups.setdefault(item['category'],[]).append(item)
    objects=[]
    for category,items in sorted(groups.items()):
        group=hashlib.sha256(category.encode()).hexdigest()[:12]
        temporary=dest/(group+'.partial.zip')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            tracks=[]
            for item in items:
                path=Path(item['path']);name='tracks/'+path.name
                data=path.read_bytes();info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,data)
                tracks.append({key:item[key] for key in ('id','title','category','duration')}|dict(file=name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
            info=zipfile.ZipInfo('catalog.json',date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,json.dumps(dict(schema=1,category=category,tracks=tracks),ensure_ascii=False,indent=2))
        with temporary.open('rb') as file:digest=hashlib.file_digest(file,'sha256').hexdigest()
        filename=f'{group}-{digest[:16]}.zip';target=dest/filename;temporary.replace(target)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip():raise ValueError('Damaged staged pack: '+category)
        objects.append(dict(category=category,tracks=len(items),file=filename,key='sachnoi/music/v1/'+filename,bytes=target.stat().st_size,sha256=digest))
    plan=dict(schema=1,scope='New folder-based background music only',objects=objects)
    (dest/'upload-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(packs=len(objects),tracks=sum(x['tracks'] for x in objects),bytes=sum(x['bytes'] for x in objects),plan=str(dest/'upload-plan.json'),uploaded=False),ensure_ascii=False))

if __name__=='__main__':prepare()
