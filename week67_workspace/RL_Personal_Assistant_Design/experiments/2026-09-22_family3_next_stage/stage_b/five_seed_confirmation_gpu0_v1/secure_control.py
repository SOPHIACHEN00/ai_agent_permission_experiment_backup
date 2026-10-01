"""Hidden-input transport for the fixed-candidate new-seed confirmation."""
from __future__ import annotations

import getpass
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import zipfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from secure_server_session import command

REMOTE = '/output/agenticAI/budget_recourse_five_seed_confirmation_gpu0_v1'
FORMAL = '/output/agenticAI/budget_recourse_gpu1_formal_v1'
FILES = ('tune_gpu0.py', 'config.json')
PREFIX = 'from pathlib import Path\nimport os,json,sys,time,hashlib,subprocess\nroot=Path(' + repr(REMOTE) + ')\nformal=Path(' + repr(FORMAL) + ')\n'

PREFLIGHT = PREFIX + r'''
def check(ok, message):
 if not ok: raise RuntimeError(message)
check(not root.exists(),'fresh run destination already exists')
check((formal/'bundle').is_dir() and (formal/'run_v1').is_dir(),'frozen formal run unavailable')
q=[x.strip() for x in subprocess.run(['nvidia-smi','--id=0','--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=15).stdout.strip().split(',')]
apps=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],capture_output=True,text=True,check=True,timeout=15).stdout.splitlines()
check(len(q)==6 and q[0]=='0','cannot identify GPU0')
check(not any(x.split(',')[0].strip().lower()==q[1].lower() for x in apps) and int(q[3])<256 and int(q[5])==0,'GPU0 occupied')
mem={x.split(':')[0]:int(x.split(':')[1].split()[0])*1024 for x in Path('/proc/meminfo').read_text().splitlines()}
cg={name:(Path('/sys/fs/cgroup')/name).read_text().strip() for name in ('memory.current','memory.max','cpu.max','memory.events') if (Path('/sys/fs/cgroup')/name).exists()}
room=mem['MemAvailable']
if cg.get('memory.max','').isdigit(): room=min(room,int(cg['memory.max'])-int(cg['memory.current']))
check(room>=4*1024**3,'memory headroom below4GiB')
manifest=json.loads((formal/'run_v1/source_manifest.json').read_text())
for entry in manifest['files']:
 p=(formal/'bundle'/entry['path']).resolve()
 check(p.is_relative_to((formal/'bundle').resolve()) and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],'frozen source mismatch')
check(json.loads((formal/'run_v1/completion.json').read_text()).get('test_opened') is False,'test state mismatch')
os.environ.update(CUDA_VISIBLE_DEVICES='0',CUDA_DEVICE_ORDER='PCI_BUS_ID',PA_RL_DEVICE='cuda:0',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import torch
check(torch.cuda.is_available() and torch.cuda.device_count()==1,'CUDA unavailable')
visible=str(getattr(torch.cuda.get_device_properties(0),'uuid',''))
check(visible.lower().removeprefix('gpu-')==q[1].lower().removeprefix('gpu-'),'CUDA UUID mismatch')
print(json.dumps({'status':'PREFLIGHT_PASS','physical_gpu':0,'gpu_uuid':q[1],'gpu_name':q[2],'gpu_memory_used_mib':int(q[3]),'gpu_memory_total_mib':int(q[4]),'host_available_bytes':mem['MemAvailable'],'effective_headroom_bytes':room,'cgroup':cg,'source_files_verified':len(manifest['files']),'torch_version':str(torch.__version__),'cuda_version':str(torch.version.cuda),'test_opened':False}))
'''

POLL = PREFIX + r'''
out={'connected':True,'checked_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
for name in ('launch_receipt','master_status','exit_receipt','failure','completion'):
 p=root/(name+'.json')
 if p.exists(): out[name]=json.loads(p.read_text())
if (root/'resume_launch_receipt.json').exists():
 for name in ('launch_receipt','master_status','exit_receipt','failure','completion'):
  out.pop(name,None)
  p=root/('resume_'+name+'.json')
  if p.exists(): out[name]=json.loads(p.read_text())
state=out.get('master_status',{})
group=state.get('current_group')
if group:
 p=root/'run_v1'/group/'status.json'
 if p.exists(): out['group_status']=json.loads(p.read_text())
for label,pid,ticks in [('master',out.get('launch_receipt',{}).get('pid'),out.get('launch_receipt',{}).get('start_ticks')),('worker',state.get('worker_pid'),state.get('worker_start_ticks'))]:
 p=Path('/proc')/str(pid)
 alive=p.exists() and bool(pid)
 identity=False
 if alive:
  try:
   cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   stat=(p/'stat').read_text().split()
   expected='resume_master.py' if label=='master' and (root/'resume_launch_receipt.json').exists() else 'tune_gpu0.py'
   identity=str(root/expected) in cmd and stat[21]==str(ticks)
   out[label+'_state']=stat[2]
   out[label+'_memory']=[x for x in (p/'status').read_text().splitlines() if x.startswith(('VmRSS:','VmHWM:'))]
  except OSError: alive=False
 out[label+'_alive']=alive
 out[label+'_identity_matches']=identity
out['gpu0']=subprocess.run(['nvidia-smi','--id=0','--query-gpu=index,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
out['cgroup_memory_current']=(Path('/sys/fs/cgroup')/'memory.current').read_text().strip()
out['cgroup_memory_max']=(Path('/sys/fs/cgroup')/'memory.max').read_text().strip()
print(json.dumps(out))
'''


def save(name: str, value: object) -> None:
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def decode(result) -> dict:
    if result.returncode:
        error=result.stderr.decode(errors='replace').lower()
        category='HOST_KEY_REVIEW_REQUIRED' if 'host key' in error else 'CONNECTION_OR_REMOTE_COMMAND_FAILED'
        return {'status': category, 'exit_code': result.returncode}
    return json.loads(result.stdout)


def poll(auth: tuple[str, str, str, str]) -> dict:
    value=decode(command(auth,POLL,timeout=35))
    now=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    save('monitoring/'+now+'.json',value)
    state=value.get('master_status',{})
    current=value.get('group_status',{})
    completed=state.get('completed',[])
    compact={'status':state.get('status',value.get('status')),'connected':value.get('connected',False),'groups_completed':state.get('groups_completed',0),'total_transitions':sum(r['transitions'] for r in completed)+(current.get('transitions',0) if state.get('status')=='RUNNING' else 0),'current_group':state.get('current_group'),'current_group_transitions':current.get('transitions'),'current_group_stage':current.get('status'),'optimizer_steps':current.get('optimizer_steps'),'first_success_step':current.get('first_success_step'),'master_identity_matches':value.get('master_identity_matches'),'worker_identity_matches':value.get('worker_identity_matches'),'worker_memory':value.get('worker_memory'),'gpu0':value.get('gpu0'),'memory_current':value.get('cgroup_memory_current'),'memory_limit':value.get('cgroup_memory_max'),'latest_completed':None if not completed else {k:completed[-1].get(k) for k in ('group','mean_exact_value','mean_exact_regret','near_optimal')},'exit_receipt':value.get('exit_receipt'),'test_opened':False}
    print(json.dumps(compact,indent=1),flush=True)
    return value


def main() -> None:
    auth=tuple(getpass.getpass(label+' (hidden): ') for label in ('Endpoint','Port','Account','Authentication'))
    print('{"status":"AUTH_IN_MEMORY_READY"}',flush=True)
    for line in sys.stdin:
        try:
            op=json.loads(line)['operation']
            if op.startswith('resume'):
                raise ValueError('training restart operations disabled for this confirmation')
            if op=='quit': break
            if op=='preflight':
                value=decode(command(auth,PREFLIGHT,timeout=90))
                save('preflight_receipt.json',value)
            elif op=='upload':
                receipt=json.loads((HERE/'preflight_receipt.json').read_text())
                if receipt.get('status')!='PREFLIGHT_PASS': raise ValueError('preflight required')
                file_hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in FILES}
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
                    for name in FILES: z.write(HERE/name,name)
                source=PREFIX+'import io,zipfile\nroot.mkdir(exist_ok=False)\ndata=sys.stdin.buffer.read()\nz=zipfile.ZipFile(io.BytesIO(data))\nassert set(z.namelist())=='+repr(set(FILES))+'\nz.extractall(root)\nhashes='+repr(file_hashes)+'\nfor name,h in hashes.items():\n assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h\nr={"files":hashes,"archive_sha256":hashlib.sha256(data).hexdigest(),"test_opened":False}\n(root/"upload_receipt.json").write_text(json.dumps(r))\nprint(json.dumps(r))'
                value=decode(command(auth,source,buffer.getvalue(),timeout=90))
                save('upload_receipt.json',value)
            elif op=='launch':
                source=PREFIX+"assert (root/'upload_receipt.json').exists()\nassert not (root/'launch_receipt.json').exists() and not (root/'run_v1').exists()\n(root/'launch.lock').open('x').close()\nlog=(root/'master.log').open('xb')\nenv=dict(os.environ,CUDA_VISIBLE_DEVICES='0',CUDA_DEVICE_ORDER='PCI_BUS_ID',PA_RL_DEVICE='cuda:0',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')\np=subprocess.Popen([sys.executable,'-B',str(root/'tune_gpu0.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)\nr={'pid':p.pid,'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'launched_epoch':time.time(),'physical_gpu':0}\n(root/'launch_receipt.json').write_text(json.dumps(r))\nprint(json.dumps(r))"
                value=decode(command(auth,source,timeout=40))
                save('launch_receipt.json',value)
            elif op=='poll':
                poll(auth)
                continue
            elif op=='resume_upload':
                data=(HERE/'resume_master.py').read_bytes()
                expected=hashlib.sha256(data).hexdigest()
                source=PREFIX+"assert json.loads((root/'exit_receipt.json').read_text())['exit_code']==1\nassert json.loads((root/'failure.json').read_text())['error']=='GPU0 occupied; no fallback'\nassert not (root/'resume_master.py').exists()\ndata=sys.stdin.buffer.read()\nassert hashlib.sha256(data).hexdigest()=="+repr(expected)+"\n(root/'resume_master.py').write_bytes(data)\nr={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'worker_code_changed':False}\n(root/'resume_upload_receipt.json').write_text(json.dumps(r))\nprint(json.dumps(r))"
                value=decode(command(auth,source,data,timeout=60))
                save('resume_upload_receipt.json',value)
            elif op=='resume_launch':
                source=PREFIX+"assert (root/'resume_upload_receipt.json').exists()\nprior=json.loads((root/'launch_receipt.json').read_text())\np=Path('/proc')/str(prior['pid'])\nassert not p.exists() or str(root/'tune_gpu0.py').encode() not in (p/'cmdline').read_bytes(),'prior master still running'\nassert not (root/'resume_launch_receipt.json').exists()\n(root/'resume_launch.lock').open('x').close()\nlog=(root/'resume_master.log').open('xb')\nenv=dict(os.environ,CUDA_VISIBLE_DEVICES='0',CUDA_DEVICE_ORDER='PCI_BUS_ID',PA_RL_DEVICE='cuda:0',CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')\np=subprocess.Popen([sys.executable,'-B',str(root/'resume_master.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)\nr={'pid':p.pid,'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().split()[21],'launched_epoch':time.time(),'physical_gpu':0,'supervisor_recovery':True}\n(root/'resume_launch_receipt.json').write_text(json.dumps(r))\nprint(json.dumps(r))"
                value=decode(command(auth,source,timeout=40))
                save('resume_launch_receipt.json',value)
            elif op=='watch':
                while True:
                    try:
                        value=poll(auth)
                    except Exception as error:
                        value={'status':'READ_ONLY_MONITOR_ERROR','error_type':type(error).__name__,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
                        save('monitoring/error_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'.json',value)
                        print(json.dumps(value),flush=True)
                        time.sleep(25)
                        continue
                    if 'exit_receipt' in value: break
                    if value.get('master_status',{}).get('status')=='STOPPED_ERROR': break
                    if value.get('connected') and value.get('launch_receipt') and not value.get('master_identity_matches'):
                        print('{"status":"PROCESS_REVIEW_REQUIRED"}',flush=True)
                        break
                    time.sleep(25)
                continue
            elif op=='download':
                source=PREFIX+"import io,zipfile\nreceipt=root/('resume_exit_receipt.json' if (root/'resume_launch_receipt.json').exists() else 'exit_receipt.json')\nassert receipt.exists()\nb=io.BytesIO()\nwith zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:\n for p in sorted(root.rglob('*')):\n  if p.is_file(): z.write(p,p.relative_to(root).as_posix())\nsys.stdout.buffer.write(b.getvalue())"
                result=command(auth,source,timeout=240)
                if result.returncode: value=decode(result)
                else:
                    target=HERE/'server_evidence'
                    target.mkdir(exist_ok=False)
                    (target/'server_evidence.zip').write_bytes(result.stdout)
                    with zipfile.ZipFile(io.BytesIO(result.stdout)) as z:
                        if z.testzip() is not None: raise ValueError('ZIP CRC failure')
                        destination=(target/'unpacked').resolve()
                        if any(not (destination/n).resolve().is_relative_to(destination) for n in z.namelist()): raise ValueError('unsafe ZIP path')
                        z.extractall(destination)
                    value={'downloaded':True,'bytes':len(result.stdout),'sha256':hashlib.sha256(result.stdout).hexdigest()}
                    save('server_evidence/download_receipt.json',value)
            else: raise ValueError('unknown operation')
            print(json.dumps(value),flush=True)
        except Exception as error:
            value={'status':'HELPER_ERROR','error_type':type(error).__name__}
            save('helper_error_'+datetime.now(timezone.utc).strftime('%H%M%S')+'.json',value)
            print(json.dumps(value),flush=True)


if __name__=='__main__':
    main()
