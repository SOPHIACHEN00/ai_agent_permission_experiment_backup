"""Hidden-input formal-run transport, with no saved connection credentials."""
from __future__ import annotations
import getpass
import hashlib
import json
import re
import sys
from pathlib import Path
import secure_server_session as transport

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "formal_gpu01_v1"
REMOTE = "/output/agenticAI/budget_recourse_gpu1_formal_v1"
PACKAGE = LOCAL / "package/budget_recourse_formal_v1.zip"
RELATIVE = transport.RELATIVE
GPU = 1

PROBE = r'''
import json,subprocess
from pathlib import Path
lines=subprocess.run(["nvidia-smi","--id=0,1","--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True).stdout.splitlines()
apps=subprocess.run(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],capture_output=True,text=True,check=True).stdout.splitlines()
gpus=[]
for line in lines:
 q=[v.strip() for v in line.split(",")]
 gpus.append(dict(index=int(q[0]),uuid=q[1],name=q[2],memory_used_mib=int(q[3]),memory_total_mib=int(q[4]),utilization=int(q[5]),compute_processes=sum(a.split(",")[0].strip()==q[1] for a in apps)))
print(json.dumps(dict(gpus=gpus,project_exists=Path("/output/agenticAI").is_dir(),target_exists=Path("REMOTE").exists())))
'''.replace("REMOTE", REMOTE)
UPLOAD = transport.UPLOAD.replace(transport.REMOTE, REMOTE)
SUPERVISOR = r'''
import os,subprocess,sys,json,time
from pathlib import Path
root=Path("REMOTE");bundle=root/"bundle"
env=dict(os.environ,CUDA_VISIBLE_DEVICES="1",CUDA_DEVICE_ORDER="PCI_BUS_ID",PA_RL_DEVICE="cuda:0",CUBLAS_WORKSPACE_CONFIG=":4096:8",PYTHONDONTWRITEBYTECODE="1")
started=time.time()
proc=subprocess.Popen([sys.executable,"-B",str(bundle/"RELATIVE/run_learner_pilot.py"),"--mode","train-validate","--output",str(root/"run_v1"),"--manifest",str(bundle/"package_manifest.json")],env=env)
(root/"child_receipt.json").write_text(json.dumps(dict(pid=proc.pid,started_epoch=started,mode="FORMAL_TRAIN_VALIDATE",physical_gpu=1)))
code=proc.wait()
(root/"exit_receipt.json").write_text(json.dumps(dict(exit_code=code,wall_seconds=time.time()-started,test_opened=False)))
'''.replace("REMOTE", REMOTE).replace("RELATIVE", RELATIVE)
POLL = transport.POLL.replace(transport.REMOTE, REMOTE)
DOWNLOAD = transport.DOWNLOAD.replace(transport.REMOTE, REMOTE)


def main() -> None:
    auth = tuple(getpass.getpass(p + " (hidden): ") for p in ("Endpoint", "Port", "Account", "Authentication"))
    if not auth[1].isdigit() or not re.fullmatch(r"[A-Za-z0-9.-]+", auth[0]) or not re.fullmatch(r"[A-Za-z0-9_-]+", auth[2]):
        print('{"status":"INVALID_HIDDEN_INPUT"}', flush=True)
        return
    print('{"status":"AUTH_IN_MEMORY_READY"}', flush=True)
    for line in sys.stdin:
        operation = json.loads(line)["operation"]
        if operation == "quit":
            break
        try:
            if operation == "probe":
                result = transport.command(auth, PROBE)
            elif operation == "upload":
                data = PACKAGE.read_bytes()
                result = transport.command(auth, UPLOAD.replace("EXPECTED", hashlib.sha256(data).hexdigest()), data)
            elif operation == "launch":
                source = "import subprocess,sys,json,time\nfrom pathlib import Path\nroot=Path(" + repr(REMOTE) + ")\n"
                source += "assert not (root/'launch_receipt.json').exists() and not (root/'run_v1').exists()\n"
                source += "q=subprocess.run(['nvidia-smi','--id=1','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip().split(',')\n"
                source += "apps=subprocess.run(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.splitlines()\n"
                source += "assert not any(a.split(',')[0].strip()==q[0].strip() for a in apps) and int(q[1])<128 and int(q[2])==0,'selected GPU is occupied; launch refused'\n"
                source += "log=(root/'run.log').open('xb')\n"
                source += "p=subprocess.Popen([sys.executable,'-B','-c'," + repr(SUPERVISOR) + "],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)\n"
                source += "receipt=dict(supervisor_pid=p.pid,launched_epoch=time.time(),physical_gpu=1,mode='FORMAL_TRAIN_VALIDATE')\n"
                source += "(root/'launch_receipt.json').write_text(json.dumps(receipt))\nprint(json.dumps(receipt))"
                result = transport.command(auth, source)
            elif operation == "poll":
                result = transport.command(auth, POLL)
            elif operation == "download":
                result = transport.command(auth, DOWNLOAD, timeout=60)
                if result.returncode == 0:
                    target = LOCAL / "server_evidence"
                    target.mkdir(exist_ok=False)
                    (target / "server_evidence.zip").write_bytes(result.stdout)
                    value = dict(downloaded=True, bytes=len(result.stdout), sha256=hashlib.sha256(result.stdout).hexdigest())
                    (LOCAL / "download_receipt.json").write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")
                    print(json.dumps(value), flush=True)
                    continue
            else:
                raise ValueError("unknown operation")
            if result.returncode:
                detail = result.stderr.decode(errors="replace").lower()
                category = "HOST_KEY_REVIEW_REQUIRED" if "host key" in detail else "CONNECTION_OR_REMOTE_COMMAND_FAILED"
                print(json.dumps(dict(status=category, exit_code=result.returncode)), flush=True)
            else:
                value = json.loads(result.stdout)
                from datetime import datetime, timezone
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
                directory = LOCAL / "monitoring"
                directory.mkdir(exist_ok=True)
                with (directory / (stamp + "_" + operation + ".json")).open("x", encoding="utf-8") as output:
                    json.dump(dict(at_utc=stamp, operation=operation, result=value), output, indent=2)
                print(json.dumps(value), flush=True)
        except Exception as error:
            print(json.dumps(dict(status="TRANSPORT_HELPER_ERROR", error_type=type(error).__name__)), flush=True)


if __name__ == "__main__":
    main()
