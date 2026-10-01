"""Server-only paid entry point. A key can arrive on encrypted, non-echo stdin."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
from .sqstn_pilot import run_pilot

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--live',required=True,action='store_true')
    p.add_argument('--key-stdin',action='store_true')
    args=p.parse_args()
    if args.key_stdin:
        key=sys.stdin.readline(16385).strip()
        if not key or len(key)>16384 or any(c.isspace() for c in key):
            raise SystemExit('Invalid credential input; no request sent.')
        os.environ['OPENAI_API_KEY']=key
        del key
    if not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('Missing API credential; no request sent.')
    os.umask(0o077)
    def timeout(signum,frame):
        raise TimeoutError('approved_wall_time_exceeded')
    signal.signal(signal.SIGALRM,timeout)
    signal.signal(signal.SIGTERM,timeout)
    signal.alarm(1800)
    result=run_pilot(args.output,device=args.device,live=True)
    signal.alarm(0)
    os.environ.pop('OPENAI_API_KEY',None)
    print(json.dumps({k:result[k] for k in (
        'status','completed_train','completed_eval','diagnostic_episodes','cost')}),flush=True)
    return 0 if result['status']=='completed' else 2

if __name__=='__main__':
    raise SystemExit(main())
