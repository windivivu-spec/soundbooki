"""Build a relocatable local candidate; never upload, publish or notarize."""
import argparse
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from urllib.parse import urlparse, urljoin

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import model_manager as models

def normalize_bundle_names(root):
    """Seal decomposed names so HFS+ transfer cannot change CodeResources paths."""
    for path in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        name=unicodedata.normalize('NFD',path.name)
        if name==path.name:continue
        # APFS compares canonical equivalents; use an intermediate ASCII name to
        # ensure the stored spelling changes rather than treating rename as a no-op.
        intermediate=path.with_name('.normalize-'+uuid.uuid4().hex)
        path.rename(intermediate)
        intermediate.rename(path.with_name(name))

def bundle_free_models(target):
    """Ship only pinned public inference files, with no cache paths or user config."""
    for model_id in ('nano','kitten'):
        source=models.verified_location(model_id)
        for item in models.manifest(model_id)['files']:
            destination=target/'.resources'/('tts-'+model_id)/item['file']
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/item['file'],destination)
            if not models.verify(destination,item):
                raise ValueError('Bundled Free model checksum failed: '+model_id+'/'+item['file'])

def package(output,public_key,checkout='',license_base='',checkout_mode='page',include_f5=False,books_api='',include_owner_music=False):
    import base64
    if len(base64.b64decode(public_key,validate=True))!=32:raise ValueError('Ed25519 public key must be 32 bytes.')
    if books_api:
        url=urlparse(books_api)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:raise ValueError('Use the selected HTTPS book API URL.')
    if checkout:
        url=urlparse(checkout)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.fragment:raise ValueError('Use the selected HTTPS checkout URL.')
    if license_base:
        url=urlparse(license_base)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.fragment or url.query or not license_base.endswith('/'):
            raise ValueError('Use an HTTPS license base URL ending in /.')
    if checkout_mode=='qr' and (not checkout or urlparse(checkout).hostname!='img.vietqr.io'):
        raise ValueError('Direct QR checkout must use the configured VietQR image URL.')
    # Fail before building a candidate if its included Free voices are incomplete.
    for model_id in ('nano','kitten'):models.verified_location(model_id)
    # Rebuild through the project's required build entry point.
    subprocess.run([str(ROOT/'scripts/build.sh')],cwd=ROOT,check=True)
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'dist'):raise ValueError('Candidate output must stay inside project dist/.')
    if output.exists():raise ValueError('Output already exists; choose a new candidate directory.')
    output.mkdir(parents=True)
    app=output/'WindiSachNoi.app'
    shutil.copytree(ROOT/'dist/Windi Sách Nói.app',app)
    signature=app/'Contents/_CodeSignature'
    if signature.exists():shutil.rmtree(signature)
    target=app/'Contents/Resources/App';target.mkdir()
    ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store')
    for folder in ('backend','ui','licenses'):shutil.copytree(ROOT/folder,target/folder,ignore=ignore)
    # The optional Pro edition receives only manifest-listed inference assets; training sets and demos stay local.
    (target/'.build').mkdir()
    for name in ('windi-extract','windi-cover','windi-ebook-assets','windi-license','windi-cloud-keychain'):shutil.copy2(ROOT/'.build'/name,target/'.build'/name)
    (target/'assets/music').mkdir(parents=True)
    music=[]
    for item in json.loads((ROOT/'assets/music/catalog.json').read_text()):
        if not include_owner_music or item.get('origin')!='user-library':continue
        source=ROOT/'assets/music'/item['file'];destination=target/'assets/music'/item['file']
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination);music.append(item)
    (target/'assets/music/catalog.json').write_text(json.dumps(music,ensure_ascii=False,indent=2))
    # A fresh install can generate Vietnamese and English speech without setup.
    # Do not copy absolute cache config or retired Turbo weights.
    bundle_free_models(target)
    if include_f5:
        if not models.ready('f5-private'):
            raise ValueError('Sáu giọng F5 chưa đủ hoặc checksum không khớp.')
        source=models.verified_location('f5-private')
        for item in models.manifest('f5-private')['files']:
            src=source/item['file'];dst=target/'.resources'/'tts-f5-private'/item['file']
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    base=Path(subprocess.check_output([str(ROOT/'.runtime/bin/python'),'-c','import sys;print(sys.base_prefix)'],text=True).strip()).resolve()
    runtime=target/'.runtime'
    shutil.copytree(base,runtime,symlinks=True,ignore=ignore)
    # Merge project-owned dependencies into the bundled standalone CPython, not the development venv.
    shutil.copytree(ROOT/'.runtime/lib/python3.12/site-packages',runtime/'lib/python3.12/site-packages',dirs_exist_ok=True,symlinks=True,ignore=ignore)
    for path in runtime.rglob('*'):
        if path.is_symlink() and (path.readlink().is_absolute() or not path.resolve().is_relative_to(runtime)):
            raise ValueError('Runtime contains an external symlink: '+str(path.relative_to(runtime)))
    if include_f5:
        f5_site=target/'.runtime-f5/lib/python3.12/site-packages'
        shutil.copytree(ROOT/'.runtime-f5/lib/python3.12/site-packages',f5_site,symlinks=True,ignore=ignore)
        wrapper=target/'.runtime-f5/bin/python'
        wrapper.parent.mkdir(parents=True,exist_ok=True)
        wrapper.write_text('#!/bin/sh\nset -eu\nF5_BIN="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nAPP_ROOT="$(CDPATH= cd -- "$F5_BIN/../.." && pwd)"\nPYTHONPATH="$APP_ROOT/.runtime-f5/lib/python3.12/site-packages"\nexport PYTHONPATH PYTHONNOUSERSITE=1\nexec "$APP_ROOT/.runtime/bin/python3.12" "$@"\n')
        wrapper.chmod(0o755)
        for path in f5_site.rglob('*'):
            if path.is_symlink() and (path.readlink().is_absolute() or not path.resolve().is_relative_to(f5_site)):
                raise ValueError('F5 runtime contains an external symlink: '+str(path.relative_to(f5_site)))
    for name in ('THIRD_PARTY.md','README.md'):shutil.copy2(ROOT/name,target/name)
    (target/'release.json').write_text(json.dumps(dict(channel='consumer',licenseMode='device',licensePublicKey=public_key,checkoutURL=checkout,checkoutMode=checkout_mode,licenseBaseURL=license_base or (urljoin(checkout,'licenses/') if checkout and checkout_mode=='page' else ''),pricingMode='per-book',booksBaseURL=books_api,privateVoiceAvailable=include_f5,heygenDispatchOnly=True),indent=2))
    info_path=app/'Contents/Info.plist';info=plistlib.loads(info_path.read_bytes());info.pop('WindiProjectRoot',None)
    # Keep the side-by-side internal Pro preview distinct from the Free preview in LaunchServices.
    # A real mutually exclusive Free/Pro release can share the production bundle identifier.
    preview_id='studio.windi.sachnoi.preview.'+re.sub(r'[^a-z0-9]+','',output.name.lower())
    info.update(WindiPortable=True,CFBundleIdentifier=preview_id)
    info_path.write_bytes(plistlib.dumps(info))
    normalize_bundle_names(app)
    # Sign nested native binaries ad hoc for local candidate QA only. Public distribution needs Developer ID.
    code_roots=[runtime]+([target/'.runtime-f5'] if include_f5 else [])
    for code_root in code_roots:
      for path in code_root.rglob('*'):
        if not path.is_file() or path.is_symlink():continue
        with path.open('rb') as f:magic=f.read(4)
        if magic in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf',b'\xbe\xba\xfe\xca'):
            subprocess.run(['codesign','--force','--sign','-',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for name in ('windi-extract','windi-cover','windi-ebook-assets','windi-license','windi-cloud-keychain'):subprocess.run(['codesign','--force','--sign','-',str(target/'.build'/name)],check=True)
    (app/'Contents/MacOS/WindiSachNoi').chmod(0o755)
    subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    # copytree preserves old directory dates; refresh them after changing bundle metadata.
    for directory in (app/'Contents',app):__import__('os').utime(directory,None)
    # Basic relocation/worker protocol check from inside the bundle.
    env=__import__('os').environ.copy();env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None);env['PYTHONNOUSERSITE']='1'
    with tempfile.TemporaryDirectory(prefix='bundled-free-',dir=ROOT/'.qa') as fresh_home:
        env['WINDI_SACH_HOME']=str(Path(fresh_home)/'library')
        result=subprocess.run([str(runtime/'bin/python3.12'),'-B',str(target/'backend/worker.py')],input='{"action":"init"}\n{"action":"shutdown"}\n',text=True,capture_output=True,env=env,check=True,timeout=120)
    events=[json.loads(line) for line in result.stdout.splitlines()]
    catalog=next(e for e in events if e.get('event')=='models')
    if catalog['entitlement']['tier']!='free' or not all(next(m for m in catalog['models'] if m['id']==mid)['ready'] for mid in ('nano','kitten')):raise ValueError('A fresh Free install must include verified Nano and Kitten models.')
    if include_f5:
        probe="import sys;sys.path.insert(0,sys.argv[1]);import model_manager as m;assert m.ready('f5-private');assert len(m.voices('f5-private'))==6"
        subprocess.run([str(runtime/'bin/python3.12'),'-B','-c',probe,str(target/'backend')],env=env,check=True,timeout=180)
        subprocess.run([str(target/'.runtime-f5/bin/python'),'-B','-c','import torch,f5_tts;from vocos import Vocos;print("F5 runtime ready")'],env=env,check=True,timeout=180,capture_output=True,text=True)
        f5=next(m for m in catalog['models'] if m['id']=='f5-private')
        if f5['entitled'] or f5['voices']:raise ValueError('Free must not unlock Pro F5 voices.')
    if any(e.get('event')=='error' for e in events):raise ValueError('Worker reported an error.')
    edition='Pro includes 6 private Vietnamese F5 voices.\n' if include_f5 else 'F5 voice resources are not included in this Free candidate.\n'
    (output/'CANDIDATE.txt').write_text('INTERNAL QA CANDIDATE ONLY\nApple Silicon / macOS 15+\nFree: Lite (Nano local) + KittenTTS English. Pro Cloud: priced per book from 10000 VND.\n'+edition+'Nano (about 269 MB) and Kitten English (about 78 MB) are bundled, verified and ready on a fresh install. Turbo is retired and is not offered or bundled.\n'+('Includes F5 inference dependencies and all 6 voice checkpoints; no full training dataset, demo music or library.\n' if include_f5 else 'No F5 inference dependencies, checkpoints, training data, demo music or library.\n')+'Ad-hoc signed, not notarized. Checkout configuration depends on the selected build options. Not a public release.\n')
    print(app)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--public-key-file',type=Path,required=True);parser.add_argument('--checkout-url',default='');parser.add_argument('--license-base-url',default='');parser.add_argument('--checkout-mode',choices=('page','qr'),default='page');parser.add_argument('--include-f5',action='store_true');parser.add_argument('--books-api',default='');parser.add_argument('--include-owner-music',action='store_true',help='Internal local QA only; do not use for public downloads.');args=parser.parse_args()
    package(args.output,args.public_key_file.read_text().strip(),args.checkout_url,args.license_base_url,args.checkout_mode,args.include_f5,args.books_api,args.include_owner_music)
