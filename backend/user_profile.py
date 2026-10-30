"""Local profile. Display data never authorizes cloud generation."""
import json
from core import atomic_json
from book_pricing import TRIAL_LIMIT,TRIAL_CHARACTERS
from book_cloud import cached_trials_remaining,endpoint
import entitlements

def info(lib,name=None):
    path=lib.root.parent/'profile.json'
    try:profile=json.loads(path.read_text())
    except (OSError,ValueError):profile={}
    if not isinstance(profile,dict):profile={}
    if name is not None:
        if not isinstance(name,str) or len(name)>80:raise ValueError('Tên hồ sơ tối đa 80 ký tự.')
        profile={'name':name.strip()};atomic_json(path,profile)
    try:state=json.loads((lib.root.parent/'book-cloud-state.json').read_text())
    except (OSError,ValueError):state={}
    if not isinstance(state,dict):state={}
    return dict(name=profile.get('name',''),deviceCode=entitlements.device_code(),trialLimit=TRIAL_LIMIT,
        trialCharacters=TRIAL_CHARACTERS,trialsRemaining=cached_trials_remaining(state),
        cached=bool(state),configured=bool(endpoint()))
