"""Inspect only the selected release ZIP. Emits no secret values."""
import json,os,sys,zipfile,hashlib,unicodedata
from pathlib import Path
path=Path(sys.argv[1]).resolve()
base='Windi Sách Nói.app/Contents/Resources/App/'
with zipfile.ZipFile(path) as z:
 def canonical(info):
  name=info.filename
  if not info.flag_bits & 0x800:
   try:name=name.encode('cp437').decode('utf-8')
   except (UnicodeEncodeError,UnicodeDecodeError):pass
  return unicodedata.normalize('NFC',name)
 aliases={canonical(info):info.filename for info in z.infolist()}
 names=list(aliases)
 def read(name):return z.read(aliases[name])
 forbidden=[n for n in names if any(part in n for part in ('/tts-f5-private/','/training/','/.library/','/commerce/private/','/assets/welcome/')) or n.rsplit('/',1)[-1] in ('.env','.env.local')]
 assert not forbidden,'Private data/resource path in archive'
 config=json.loads(read(base+'release.json'))
 assert config['channel']=='consumer' and config.get('heygenDispatchOnly') is True and not config.get('privateVoiceAvailable')
 assert config.get('booksBaseURL')=='https://zpjphixcttehkkgxlmsn.supabase.co/functions/v1/wsn-books'
 assert not config.get('checkoutURL'),'Do not bundle the old annual checkout'
 assert json.loads(read(base+'assets/music/catalog.json'))==[],'Owner music must stay local'
 assert not any(n.startswith(base+'assets/music/') and not n.endswith(('/','catalog.json')) for n in names),'Audio in public music folder'
 assert any('/tts-nano/' in n for n in names) and any('/tts-kitten/' in n for n in names)
 assert b'WindiProjectRoot' not in read('Windi Sách Nói.app/Contents/Info.plist')
 keys=[v.encode() for k,v in os.environ.items() if len(v)>16 and any(marker in k for marker in ('SECRET','TOKEN','SERVICE_ROLE','API_KEY','ACCESS_KEY'))]
 checked=0
 for item in z.infolist():
  if item.is_dir() or item.file_size>8*1024*1024 or not item.filename.endswith(('.json','.js','.py','.html','.css','.txt','.md','.plist')):continue
  data=z.read(item);assert not any(value in data for value in keys),'Credential material in '+item.filename;checked+=1
 print(json.dumps(dict(passed=True,archiveEntries=len(names),textFilesChecked=checked,dispatchOnly=True,ownerMusicIncluded=False,privateF5Included=False,freeModelsIncluded=True,notarized=False)))
