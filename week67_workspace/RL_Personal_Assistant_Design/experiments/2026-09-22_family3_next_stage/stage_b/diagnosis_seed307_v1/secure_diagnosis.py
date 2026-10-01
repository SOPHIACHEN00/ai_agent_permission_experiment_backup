"""Hidden-input, one-off read-only GPU diagnostic transport; no training operation."""
import getpass
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from secure_server_session import command

REMOTE = '/output/agenticAI/budget_recourse_seed307_diagnosis_v1'
FORMAL = '/output/agenticAI/budget_recourse_gpu1_formal_v1'
PROBE = '''
import json,subprocess
from pathlib import Path
q=[s.strip() for s in subprocess.run(['nvidia-smi','--id=1','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip().split(',')]
apps=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.splitlines()
print(json.dumps(dict(gpu_index=int(q[0]),memory_used_mib=int(q[2]),utilization=int(q[3]),compute_processes=sum(a.split(',')[0].strip()==q[1] for a in apps),formal_exists=Path(FORMAL).is_dir(),diagnosis_exists=Path(REMOTE).exists())))
'''.replace('FORMAL',repr(FORMAL)).replace('REMOTE',repr(REMOTE))

def main():
    auth=tuple(getpass.getpass(p+' (hidden): ') for p in ('Endpoint','Port','Account','Authentication'))
    print('{"status":"AUTH_IN_MEMORY_READY"}',flush=True)
    for line in sys.stdin:
        op=json.loads(line)['operation']
        if op=='quit':
            break
        try:
            if op=='probe':
                r=command(auth,PROBE)
            elif op=='diagnose':
                code=(HERE/'diagnose.py').read_bytes()
                src="import os,sys,json,subprocess,hashlib\nfrom pathlib import Path\n"
                src+="q=subprocess.run(['nvidia-smi','--id=1','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip().split(',')\n"
                src+="apps=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.splitlines()\n"
                src+="assert not any(a.split(',')[0].strip()==q[0].strip() for a in apps) and int(q[1])<128 and int(q[2])==0,'GPU occupied'\n"
                src+='root=Path('+repr(REMOTE)+');formal=Path('+repr(FORMAL)+')\n'
                src+="data=sys.stdin.buffer.read()\nassert hashlib.sha256(data).hexdigest()=="+repr(hashlib.sha256(code).hexdigest())+'\n'
                src+="root.mkdir(exist_ok=False)\n(root/'diagnose.py').write_bytes(data)\n"
                src+="env=dict(os.environ,CUDA_VISIBLE_DEVICES='1',CUDA_DEVICE_ORDER='PCI_BUS_ID',PA_RL_DEVICE='cuda:0',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')\n"
                src+="p=subprocess.run([sys.executable,'-B',str(root/'diagnose.py'),'--workspace',str(formal/'bundle'),'--evidence',str(formal/'run_v1'),'--mode','gpu','--output',str(root/'q_diagnosis.json')],env=env,capture_output=True,timeout=55)\n"
                src+="(root/'diagnostic_stdout.log').write_bytes(p.stdout)\n(root/'diagnostic_stderr.log').write_bytes(p.stderr)\n"
                src+="if p.returncode: print(json.dumps(dict(status='DIAGNOSTIC_FAILED',exit_code=p.returncode)))\nelse: sys.stdout.buffer.write((root/'q_diagnosis.json').read_bytes())\n"
                r=command(auth,src,code,timeout=60)
            else:
                raise ValueError('unknown operation')
            if r.returncode:
                print(json.dumps(dict(status='CONNECTION_OR_REMOTE_COMMAND_FAILED',exit_code=r.returncode)),flush=True)
                continue
            value=json.loads(r.stdout)
            if op=='diagnose':
                with (HERE/'q_diagnosis.json').open('x',encoding='utf-8') as f:
                    json.dump(value,f,indent=2)
            print(json.dumps(value),flush=True)
        except Exception as error:
            print(json.dumps(dict(status='TRANSPORT_HELPER_ERROR',error_type=type(error).__name__)),flush=True)

if __name__=='__main__':
    main()
