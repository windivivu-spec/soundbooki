"""Stage only public, pinned Nano runtime assets; no private voices or user books."""
from pathlib import Path
import hashlib, json, os, shutil, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'android/app/src/main/assets/nano'
OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'backend/models.json').read_text())
config=json.loads((ROOT/'.resources/config.json').read_text())
source_args=[arg for arg in sys.argv[1:] if not arg.startswith("--")]
source=Path(source_args[0]) if source_args else Path(config['models'])
# Full Lite model by default. Lightweight UI-only builds require explicit opt-out.
include_models = ('--include-models' in sys.argv) or (os.environ.get('INCLUDE_NANO_MODELS', '1') == '1')
if include_models:
    for item in manifest['files']:
        path=source/item['file']
        if path.stat().st_size!=item['size'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise SystemExit('Model checksum mismatch: '+item['file'])
        shutil.copyfile(path,OUT/item['file'])
else:
    # Remove any existing heavy onnx models from assets so APK is lightweight
    for item in manifest['files']:
        p = OUT / item['file']
        if p.exists():
            p.unlink()
sdk=ROOT/'.runtime/lib/python3.12/site-packages'
voices=json.loads((sdk/'vieneu/assets/voices_v3_nano.json').read_text())
voices['presets']={k:v for k,v in voices['presets'].items() if k not in {'Adam','Ái Hân','Xuân Tiên','Minh Quân'}}
voices['default_voice']='Đức Trí'
(OUT/'voices.json').write_text(json.dumps(voices,ensure_ascii=False,separators=(',',':')))
constants=np.load(source/'constants.npz')
(OUT/'constants.json').write_text(json.dumps({k:constants[k].tolist() for k in ('null_spk','null_style')},separators=(',',':')))
shutil.copyfile(sdk/'sea_g2p/sea_g2p.bin',OUT/'sea_g2p.bin')
entries=[]
for p in sorted(OUT.iterdir()):
    if p.name=='manifest.json':continue
    entries.append(dict(file=p.name,size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(OUT/'manifest.json').write_text(json.dumps(dict(revision=manifest['revision'],sdk='vieneu==3.8.1',seaG2p='0.10.0',files=entries),indent=2))
drawable=ROOT/'android/app/src/main/res/drawable-nodpi'
drawable.mkdir(exist_ok=True)
for src,dest in [('logo.png','brand_logo.png'),('wordmark.png','brand_wordmark.png'),('app-icon-master.png','app_icon.png')]:
    shutil.copyfile(ROOT/'ui/brand'/src,drawable/dest)
fonts_dir=ROOT/'android/app/src/main/assets/fonts'
fonts_dir.mkdir(parents=True,exist_ok=True)
for src,dest in [
    ('SFProRounded-Black.otf','SFProRounded-Black.otf'),
    ('SVN-Avo.ttf','SVN-Avo.ttf'),
    ('SVN-Nexa Light.ttf','SVN-Nexa-Light.ttf'),
    ('SVN-Nexa Bold.ttf','SVN-Nexa-Bold.ttf'),
    ('SVN-Georgia Regular.otf','SVN-Georgia.otf'),
]:
    shutil.copyfile(ROOT/'ui/fonts'/src,fonts_dir/dest)
welcome_meta=json.loads((ROOT/'assets/welcome/source.json').read_text())
welcome_wav=ROOT/'assets/welcome/welcome.wav'
if hashlib.sha256(welcome_wav.read_bytes()).hexdigest()!=welcome_meta['sha256']:
    raise SystemExit('Welcome audio checksum mismatch')
welcome_dir=ROOT/'android/app/src/main/assets/welcome'
welcome_dir.mkdir(parents=True,exist_ok=True)
debug_welcome=ROOT/'android/app/src/debug/assets/welcome'
debug_welcome.mkdir(parents=True,exist_ok=True)
shutil.copyfile(welcome_wav,debug_welcome/'welcome.wav')
shutil.copyfile(ROOT/'assets/music/Piano podcast/1.mp3',welcome_dir/'piano_podcast_1.mp3')
music_dir=ROOT/'android/app/src/main/assets/music'
music_dir.mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/'assets/music/Piano podcast/1.mp3',music_dir/'piano_podcast_1.mp3')
if (ROOT/'assets/music/.originals-whitenoise/rain.MP3').is_file():
    shutil.copyfile(ROOT/'assets/music/.originals-whitenoise/rain.MP3',music_dir/'rain.mp3')
if (ROOT/'assets/music/Late Night/1.MP3').is_file():
    shutil.copyfile(ROOT/'assets/music/Late Night/1.MP3',music_dir/'late_night.mp3')
from importlib.metadata import distribution
lic=ROOT/'android/app/src/main/assets/licenses'
lic.mkdir(exist_ok=True)
for name in ('vieneu','sea-g2p'):
    dist=distribution(name)
    candidates=[p for p in dist.files or [] if str(p).endswith('LICENSE')]
    if candidates:shutil.copyfile(dist.locate_file(candidates[0]),lic/(name+'-Apache-2.0.txt'))
(lic/'NOTICE.txt').write_text('VieNeu-TTS v3 Nano and SEA-G2P © Phạm Nguyễn Ngọc Bảo.\nModel: https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Nano\nSEA-G2P: https://github.com/pnnbao97/sea-g2p\nONNX Runtime © Microsoft, MIT.\nPDFBox Android © Tom Roush and Apache Software Foundation, Apache-2.0.\njsoup © Jonathan Hedley, MIT.\nZXing © ZXing authors, Apache-2.0.\nPublic Nano presets only. No private F5 weights or recordings.\n')
print('Staged verified Nano, 7 Vietnamese voices, dictionary and branding. No English TTS model.')

# Owner-local preview recordings: stage only the seven explicitly named Pro samples.
# No provider calls, no private F5 assets. Public distribution rights remain separate.
import wave, array, math
preview_out=ROOT/'android/app/src/debug/assets/voice-previews'
preview_out.mkdir(parents=True,exist_ok=True)
catalog=[]
for index,name in enumerate(('Đình Mạnh','Đình Gia','Minh Bùi','Minh Tài','Kim Thoa','Ngân Quỳnh','Thanh Thảo')):
    path=ROOT/'assets/voice-previews/pro-cloud'/(name+'.wav')
    with wave.open(str(path),'rb') as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2:raise SystemExit('Invalid voice demo: '+name)
        samples=array.array('h',w.readframes(w.getnframes()))
        size=max(1,len(samples)//72)
        peaks=[max(abs(v) for v in samples[at:at+size])/32768 for at in range(0,len(samples),size)][:72]
        item=dict(name=name,file='pro-'+str(index)+'.wav',durationMs=round(w.getnframes()*1000/w.getframerate()),waveform=peaks,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),usage='owner-local-demo')
    shutil.copyfile(path,preview_out/item['file']);catalog.append(item)
(preview_out/'pro.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
