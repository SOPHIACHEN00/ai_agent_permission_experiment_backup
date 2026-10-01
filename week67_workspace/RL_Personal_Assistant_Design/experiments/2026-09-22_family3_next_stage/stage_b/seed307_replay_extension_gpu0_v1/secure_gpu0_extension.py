"""Hidden-input SSH driver for the single GPU0 replay-extension diagnostic."""
from __future__ import annotations

import getpass
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import io

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from secure_server_session import command

REMOTE = "/output/agenticAI/budget_recourse_seed307_replay_extension_gpu0_v1"
FORMAL = "/output/agenticAI/budget_recourse_gpu1_formal_v1"
SCRIPT = HERE / "replay_extension.py"

PREFLIGHT = r'''
import json,hashlib,subprocess,os,sys,shutil
from pathlib import Path
REMOTE=Path(@REMOTE@); FORMAL=Path(@FORMAL@); BUNDLE=FORMAL/"bundle"; RUN=FORMAL/"run_v1"
def fail(reason): print(json.dumps({"status":"PREFLIGHT_BLOCKED","reason":reason})); raise SystemExit(0)
if REMOTE.exists(): fail("fresh diagnostic destination already exists; will not overwrite")
if not BUNDLE.is_dir() or not RUN.is_dir(): fail("prior formal source/results not found on this host")
query=subprocess.run(["nvidia-smi","--id=0","--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True,timeout=15).stdout.strip().split(",")
query=[v.strip() for v in query]
if len(query)!=6 or query[0]!="0": fail("cannot verify physical GPU0")
apps=subprocess.run(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],capture_output=True,text=True,check=True,timeout=15).stdout.splitlines()
busy=[s for s in apps if s.split(",")[0].strip().lower()==query[1].lower()]
if busy or int(query[3])>=256 or int(query[5])!=0: fail("GPU0 has a compute process, memory use >=256 MiB, or nonzero utilization")
os.environ.update(CUDA_VISIBLE_DEVICES="0",CUDA_DEVICE_ORDER="PCI_BUS_ID",PA_RL_DEVICE="cuda:0",CUBLAS_WORKSPACE_CONFIG=":4096:8")
import torch
if not torch.cuda.is_available() or torch.cuda.device_count()!=1: fail("CUDA-visible device count is not exactly one")
visible=str(getattr(torch.cuda.get_device_properties(0),"uuid",""))
norm=lambda x:x.lower().removeprefix("gpu-")
if norm(visible)!=norm(query[1]): fail("visible CUDA UUID does not match physical GPU0")
mem={}
for line in Path("/proc/meminfo").read_text().splitlines():
 k,v=line.split(":",1); mem[k]=int(v.split()[0])*1024
cgroup={}
for name in ("memory.current","memory.max","cpu.max","cpu.stat"):
 p=Path("/sys/fs/cgroup")/name
 if p.exists(): cgroup[name]=p.read_text().strip()
host_free=mem.get("MemAvailable",0)
cg_free=None
if cgroup.get("memory.max","").isdigit(): cg_free=int(cgroup["memory.max"])-int(cgroup["memory.current"])
headroom=min(host_free,cg_free) if cg_free is not None else host_free
if headroom < 4*1024**3: fail("host/container memory headroom below 4 GiB after CUDA preflight")
manifest=json.loads((RUN/"source_manifest.json").read_text())
checked=0
for e in manifest["files"]:
 p=BUNDLE/e["path"]
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 if h!=e["sha256"]: fail("frozen source hash mismatch: "+e["path"])
 checked+=1
meta=json.loads((RUN/"ddqn_seed307_gamma1.json").read_text())
cp=RUN/"ddqn_seed307_gamma1.pt"
if hashlib.sha256(cp.read_bytes()).hexdigest()!=meta["sha256"]: fail("seed307 checkpoint hash mismatch")
if meta["context"]["seed"]!=307 or meta["context"]["gamma"]!=1 or meta["context"]["test_opened"] is not False: fail("unexpected checkpoint identity/test state")
done=json.loads((RUN/"completion.json").read_text())
if done.get("test_opened") is not False: fail("formal test-closed receipt missing")
disk=shutil.disk_usage("/output/agenticAI")
result={"status":"PREFLIGHT_PASS","gpu_index":0,"gpu_uuid":query[1],"gpu_name":query[2],
 "gpu_memory_used_mib":int(query[3]),"gpu_memory_total_mib":int(query[4]),"gpu_utilization":int(query[5]),
 "visible_cuda_uuid":visible,"torch_version":str(torch.__version__),"cuda_version":str(torch.version.cuda),
 "host_mem_available_bytes":host_free,"cgroup_memory_current":cgroup.get("memory.current"),
 "cgroup_memory_max":cgroup.get("memory.max"),"cgroup_memory_headroom_bytes":cg_free,
 "effective_memory_headroom_bytes":headroom,"cpu_max":cgroup.get("cpu.max"),"cpu_stat":cgroup.get("cpu.stat"),
 "verified_frozen_source_files":checked,"seed307_checkpoint_sha256":meta["sha256"],
 "checkpoint_bytes":cp.stat().st_size,"formal_test_opened":False,"output_free_bytes":disk.free}
REMOTE.mkdir(exist_ok=False)
(REMOTE/"preflight_receipt.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
'''.replace("@REMOTE@",repr(REMOTE)).replace("@FORMAL@",repr(FORMAL))

def main():
    auth=tuple(getpass.getpass(p+" (hidden): ") for p in ("Endpoint","Port","Account","Authentication"))
    print('{"status":"AUTH_IN_MEMORY_READY"}',flush=True)
    script=SCRIPT.read_bytes()
    script_sha=hashlib.sha256(script).hexdigest()
    for line in sys.stdin:
        op=json.loads(line)["operation"]
        if op=="quit": break
        try:
            if op=="preflight":
                result=command(auth,PREFLIGHT,timeout=90)
            elif op=="upload":
                src=("import json,hashlib\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\n"
                     "assert root.is_dir() and json.loads((root/'preflight_receipt.json').read_text()).get('status')=='PREFLIGHT_PASS','valid preflight receipt required'\n"
                     "data=__import__('sys').stdin.buffer.read()\n"
                     "assert hashlib.sha256(data).hexdigest()=="+repr(script_sha)+",'local script hash mismatch'\n"
                     "(root/'replay_extension.py').write_bytes(data)\n"
                     "(root/'upload_receipt.json').write_text(json.dumps({'script_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'test_opened':False}))\n"
                     "print(json.dumps({'status':'UPLOADED','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))")
                result=command(auth,src,script,timeout=90)
            elif op=="launch":
                supervisor=("import os,subprocess,sys,json,time\nfrom pathlib import Path\n"
                    "root=Path("+repr(REMOTE)+")\nformal=Path("+repr(FORMAL)+")\n"
                    "up=json.loads((root/'upload_receipt.json').read_text())\n"
                    "assert up['script_sha256']=="+repr(script_sha)+",'uploaded script mismatch'\n"
                    "prior=json.loads((root/'launch_receipt.json').read_text())\n"
                    "assert not (Path('/proc')/str(prior['supervisor_pid'])).exists(),'previous supervisor still active'\n"
                    "assert not (root/'child_receipt.json').exists() and not (root/'status.json').exists() and not (root/'completion.json').exists(),'learner already started; refusing duplicate'\n"
                    "q=subprocess.run(['nvidia-smi','--id=0','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip().split(',')\n"
                    "apps=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.splitlines()\n"
                    "assert not any(a.split(',')[0].strip().lower()==q[0].strip().lower() for a in apps) and int(q[1])<256 and int(q[2])==0,'GPU0 occupied at launch; no fallback'\n"
                    "log=(root/'retry1_run.log').open('xb')\n"
                    "env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',CUDA_DEVICE_ORDER='PCI_BUS_ID',PA_RL_DEVICE='cuda:0',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')\n"
                    "child=subprocess.Popen([sys.executable,'-B',str(root/'replay_extension.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env)\n"
                    "(root/'child_receipt.json').write_text(json.dumps({'pid':child.pid,'mode':'REPLAY_ONLY_EXTENSION','physical_gpu':0,'started_epoch':time.time(),'recovered_empty_supervisor_attempt':True}))\n"
                    "code=child.wait()\n"
                    "(root/'exit_receipt.json').write_text(json.dumps({'exit_code':code,'ended_epoch':time.time(),'test_opened':False}))\n")
                src=("import subprocess,sys,json,time\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\n"
                     "proc=subprocess.Popen([sys.executable,'-B','-c',"+repr(supervisor)+"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\n"
                     "receipt={'supervisor_pid':proc.pid,'launched_epoch':time.time(),'physical_gpu':0,'mode':'REPLAY_ONLY_EXTENSION'}\n"
                     "(root/'launch_retry_receipt.json').write_text(json.dumps(receipt))\nprint(json.dumps(receipt))")
                result=command(auth,src,timeout=60)
            elif op=="poll":
                src=("import json,time\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\nout={}\n"
                     "for name in ('preflight_receipt','upload_receipt','launch_receipt','child_receipt','exit_receipt','status','completion','failure'):\n"
                     " p=root/(name+'.json')\n if p.exists(): out[name]=json.loads(p.read_text())\n"
                     "if 'child_receipt' in out:\n p=Path('/proc')/str(out['child_receipt']['pid'])\n out['child_alive']=p.exists()\n"
                     "print(json.dumps(out))")
                result=command(auth,src,timeout=60)
            elif op=="download":
                src=("import io,zipfile,sys\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\n"
                     "if not (root/'exit_receipt.json').is_file(): raise RuntimeError('child has not exited')\n"
                     "b=io.BytesIO()\n"
                     "with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:\n"
                     " for p in sorted(root.rglob('*')):\n"
                     "  if p.is_file(): z.write(p,p.relative_to(root).as_posix())\n"
                     "sys.stdout.buffer.write(b.getvalue())")
                result=command(auth,src,timeout=180)
                if result.returncode==0:
                    evidence=HERE/"server_evidence"
                    evidence.mkdir(exist_ok=False)
                    archive=evidence/"server_evidence.zip"
                    archive.write_bytes(result.stdout)
                    with zipfile.ZipFile(io.BytesIO(result.stdout)) as z:
                        if z.testzip() is not None: raise ValueError("server evidence zip integrity failure")
                        z.extractall(evidence/"unpacked")
                    receipt={"downloaded":True,"bytes":len(result.stdout),"sha256":hashlib.sha256(result.stdout).hexdigest()}
                    (evidence/"download_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
                    print(json.dumps(receipt),flush=True)
                    continue
            else:
                raise ValueError("unknown operation")
            if result.returncode:
                detail=result.stderr.decode(errors="replace").lower()
                code="HOST_KEY_REVIEW_REQUIRED" if "host key" in detail else "CONNECTION_OR_REMOTE_COMMAND_FAILED"
                print(json.dumps({"status":code,"exit_code":result.returncode}),flush=True)
                continue
            value=json.loads(result.stdout)
            if op=="preflight" and value.get("status")=="PREFLIGHT_PASS":
                # Preserve a redacted snapshot remotely only after all gates pass.
                src=("import json\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\n"
                     "value=json.loads("+repr(json.dumps(value))+" )\n"
                     "(root/'preflight_receipt.json').write_text(json.dumps(value,indent=2)+'\\n')\n")
                saved=command(auth,src,timeout=45)
                if saved.returncode: raise RuntimeError("preflight receipt write failed")
                (HERE/"preflight_receipt.json").write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
            elif op=="preflight":
                (HERE/"preflight_blocked.json").write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
            print(json.dumps(value),flush=True)
        except Exception as error:
            print(json.dumps({"status":"TRANSPORT_HELPER_ERROR","error_type":type(error).__name__}),flush=True)

if __name__=="__main__":
    main()
