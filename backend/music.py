import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def catalog():
    p=ROOT/'assets/music/catalog.json'
    items=[]
    for x in json.loads(p.read_text()) if p.exists() else []:
        path=(ROOT/'assets/music'/x['file']).resolve()
        if path.is_relative_to((ROOT/'assets/music').resolve()) and path.is_file():
            items.append(dict(x,path=str(path),category=x.get('category','Thư giãn')))
    return items

def music_settings(value, *, allow_unavailable=False):
    value=value or {};track=value.get('track','none')
    items={x['id']:x for x in catalog()}
    if not allow_unavailable and track!='none' and track not in items:raise ValueError('Bản nhạc nền không có trong thư viện.')
    volume=float(value.get('volume',.12))
    if not math.isfinite(volume) or not 0<=volume<=.5:raise ValueError('Âm lượng nhạc cần từ 0 đến 50%.')
    result=dict(track=track,volume=volume)
    # Keep legacy single-track settings intact. New choices store the actual
    # shuffled order so playback, reopening and every export use the same mix.
    if any(key in value for key in ('mode','playlist','loop','category')):
        mode=value.get('mode','single');loop=value.get('loop',True)
        if mode not in ('single','shuffle') or not isinstance(loop,bool):raise ValueError('Tùy chọn nhạc nền không hợp lệ.')
        category=value.get('category',items.get(track,{}).get('category',''))
        order=value.get('playlist',[track] if track!='none' else [])
        if not isinstance(order,list) or len(order)>500 or any(not isinstance(x,str) for x in order) or len(set(order))!=len(order):raise ValueError('Danh sách nhạc không hợp lệ.')
        if track=='none':order=[]
        elif mode=='single':order=[track]
        elif not order or order[0]!=track:raise ValueError('Danh sách nhạc không hợp lệ.')
        if not allow_unavailable and any(x not in items or items[x]['category']!=category for x in order):raise ValueError('Một bài trong danh sách chưa có trên máy. Hãy chọn lại thể loại nhạc.')
        result.update(mode=mode,category=category,playlist=order,loop=loop)
    return result

def music_playlist(settings):
    items={x['id']:x for x in catalog()}
    ids=settings.get('playlist',[settings['track']]) if settings.get('mode')=='shuffle' else [settings['track']]
    return [items[x] for x in ids if x!='none' and x in items]

def music_unavailable(settings):
    if settings['track']=='none':return False
    ids=settings.get('playlist',[settings['track']]) if settings.get('mode')=='shuffle' else [settings['track']]
    known={x['id'] for x in catalog()}
    return not ids or any(x not in known for x in ids)

def music_file(settings):
    return next((Path(x['path']) for x in catalog() if x['id']==settings['track']),None)
