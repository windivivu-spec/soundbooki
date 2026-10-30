"""Index only the user's music folders; never compose or add demo tracks."""
import json
from pathlib import Path
from music_library import prepare
ROOT=Path(__file__).resolve().parents[1]

def main():
    dest=ROOT/'assets/music';dest.mkdir(parents=True,exist_ok=True)
    items=prepare()
    demo=dest/'demo-catalog.json'
    if demo.exists():items += [x for x in json.loads(demo.read_text()) if x.get('origin')=='user-demo' and (dest/x['file']).is_file()]
    (dest/'catalog.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
    print(f'Sẵn sàng {len(items)} bài nhạc bạn đã thêm.')
if __name__=='__main__':main()
