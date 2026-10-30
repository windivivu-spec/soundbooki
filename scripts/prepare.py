"""Explicit first-time model setup. Does not read books or generate audio."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from model_manager import install,PROFILES,manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-cache',type=Path)
    parser.add_argument('--model',choices=list(PROFILES),default='nano')
    args=parser.parse_args()
    def progress(**event):print(event['phase'],event['file'],event['done'],'/',event['total'],flush=True)
    path=install(args.model,progress,args.reuse_cache)
    print('Sẵn sàng chạy offline:',args.model,path,sum(i['size'] for i in manifest(args.model)['files']),'bytes model')

if __name__=='__main__':main()
