"""Ephemeral hidden-input SSH transport; credentials never enter files or logs."""
from __future__ import annotations
import base64
import ctypes
from ctypes import wintypes
import getpass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import uuid

HERE = Path(__file__).resolve().parent
PLINK = r"D:\Applications\PuTTY\plink.exe"
REMOTE = "/output/agenticAI/budget_recourse_gpu2_smoke_v1"
RELATIVE = "RL_Personal_Assistant_Design/experiments/2026-09-22_family3_next_stage/stage_b"
PACKAGE = HERE / "evidence/b2_server_package_v2/budget_recourse_source_v2.zip"


def remote_python(source: str) -> str:
    encoded = base64.b64encode(source.encode()).decode()
    return 'python3 -c "import base64;exec(base64.b64decode(\'' + encoded + '\'))"'


def command(auth: tuple[str, str, str, str], source: str, data: bytes | None = None,
            timeout: int = 45) -> subprocess.CompletedProcess:
    host, port, user, password = auth
    pipe_name = "\\\\.\\pipe\\agenticAI_" + uuid.uuid4().hex
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                       wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    kernel.CreateNamedPipeW.restype = wintypes.HANDLE
    kernel.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    kernel.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateNamedPipeW(pipe_name, 2 | 0x00080000, 0, 1, 4096, 4096, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise RuntimeError("hidden authentication pipe unavailable")
    def feed() -> None:
        try:
            connected = kernel.ConnectNamedPipe(handle, None)
            if connected or ctypes.get_last_error() == 535:
                raw = (password + "\n").encode()
                written = wintypes.DWORD()
                kernel.WriteFile(handle, raw, len(raw), ctypes.byref(written), None)
                kernel.FlushFileBuffers(handle)
                kernel.DisconnectNamedPipe(handle)
        finally:
            kernel.CloseHandle(handle)
    threading.Thread(target=feed, daemon=True).start()
    # Cached host key is required; batch mode never accepts a new/changed host key.
    args = [PLINK, "-ssh", "-batch", "-noagent", "-noshare", "-T", "-P", port, "-l", user,
            "-pwfile", pipe_name, host, remote_python(source)]
    return subprocess.run(args, input=data, capture_output=True, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW)


PROBE = r'''
import os,json,subprocess,sys
from pathlib import Path
query=subprocess.run(["nvidia-smi","--id=2","--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True).stdout.strip().split(",")
apps=subprocess.run(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],capture_output=True,text=True,check=True).stdout
busy=sum(line.split(",")[0].strip()==query[1].strip() for line in apps.splitlines())
os.environ["CUDA_VISIBLE_DEVICES"]="2"
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
import torch
visible=str(getattr(torch.cuda.get_device_properties(0),"uuid",""))
print(json.dumps({"project_exists":Path("/output/agenticAI").is_dir(),"target_exists":Path("REMOTE").exists(),
 "gpu_index":int(query[0]),"gpu_uuid":query[1].strip(),"gpu_name":query[2].strip(),
 "memory_used_mib":int(query[3]),"memory_total_mib":int(query[4]),"utilization":int(query[5]),
 "compute_processes":busy,"visible_uuid":visible,"torch_version":str(torch.__version__),
 "cuda_version":torch.version.cuda,"python_version":sys.version.split()[0]}))
'''.replace("REMOTE", REMOTE)

UPLOAD = r'''
import sys,json,hashlib,io,zipfile
from pathlib import Path
root=Path("REMOTE")
root.mkdir(exist_ok=False)
data=sys.stdin.buffer.read()
if hashlib.sha256(data).hexdigest()!="EXPECTED": raise RuntimeError("upload hash mismatch")
(root/"source.zip").write_bytes(data)
bundle=root/"bundle"
bundle.mkdir()
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 for info in archive.infolist():
  if not (bundle/info.filename).resolve().is_relative_to(bundle.resolve()): raise RuntimeError("unsafe archive path")
 archive.extractall(bundle)
manifest=json.loads((bundle/"package_manifest.json").read_text())
for entry in manifest["files"]:
 if hashlib.sha256((bundle/entry["path"]).read_bytes()).hexdigest()!=entry["sha256"]: raise RuntimeError("remote member hash mismatch")
print(json.dumps({"uploaded":True,"members_verified":len(manifest["files"]),"package_sha256":hashlib.sha256(data).hexdigest()}))
'''.replace("REMOTE", REMOTE)

SUPERVISOR = r'''
import os,subprocess,sys,json,time
from pathlib import Path
root=Path("REMOTE"); bundle=root/"bundle"
env=dict(os.environ,CUDA_VISIBLE_DEVICES="2",CUDA_DEVICE_ORDER="PCI_BUS_ID",PA_RL_DEVICE="cuda:0",CUBLAS_WORKSPACE_CONFIG=":4096:8",PYTHONDONTWRITEBYTECODE="1")
started=time.time()
proc=subprocess.Popen([sys.executable,"-B",str(bundle/"RELATIVE/run_learner_pilot.py"),"--mode","smoke","--output",str(root/"run_v1"),"--manifest",str(bundle/"package_manifest.json")],env=env)
(root/"child_receipt.json").write_text(json.dumps({"pid":proc.pid,"started_epoch":started,"mode":"NON_EVIDENCE_SMOKE","physical_gpu":2}))
code=proc.wait()
(root/"exit_receipt.json").write_text(json.dumps({"exit_code":code,"wall_seconds":time.time()-started,"test_opened":False}))
'''.replace("REMOTE", REMOTE).replace("RELATIVE", RELATIVE)

POLL = r'''
import json,os
from pathlib import Path
root=Path("REMOTE"); result={}
for name in ("launch_receipt","child_receipt","exit_receipt"):
 p=root/(name+".json")
 if p.exists(): result[name]=json.loads(p.read_text())
p=root/"run_v1/status.json"
if p.exists(): result["status"]=json.loads(p.read_text())
if "child_receipt" in result:
 proc=Path("/proc")/str(result["child_receipt"]["pid"])
 result["child_exists"]=proc.exists()
 if (proc/"cmdline").exists():
  result["child_is_expected_runner"]="run_learner_pilot.py" in (proc/"cmdline").read_bytes().decode(errors="replace")
print(json.dumps(result))
'''.replace("REMOTE", REMOTE)

DOWNLOAD = r'''
import io,zipfile,sys
from pathlib import Path
root=Path("REMOTE")
if not (root/"exit_receipt.json").is_file(): raise RuntimeError("run has not exited")
out=io.BytesIO()
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
 for path in root.rglob("*"):
  if path.is_file() and "bundle" not in path.relative_to(root).parts and path.name!="source.zip":
   z.write(path,path.relative_to(root).as_posix())
 z.write(root/"bundle/package_manifest.json","package_manifest.json")
sys.stdout.buffer.write(out.getvalue())
'''.replace("REMOTE", REMOTE)


def main() -> None:
    auth = tuple(getpass.getpass(prompt + " (hidden): ") for prompt in ("Endpoint","Port","Account","Authentication"))
    if not auth[1].isdigit() or not re.fullmatch(r"[A-Za-z0-9.-]+",auth[0]) or not re.fullmatch(r"[A-Za-z0-9_-]+",auth[2]):
        print(json.dumps({"status":"INVALID_HIDDEN_INPUT"}),flush=True)
        return
    print(json.dumps({"status":"AUTH_IN_MEMORY_READY"}),flush=True)
    for line in sys.stdin:
        operation=json.loads(line)["operation"]
        if operation=="quit": break
        try:
            if operation=="probe":
                result=command(auth,PROBE)
            elif operation=="upload":
                result=command(auth,UPLOAD.replace("EXPECTED",hashlib.sha256(PACKAGE.read_bytes()).hexdigest()),PACKAGE.read_bytes())
            elif operation=="launch":
                source="import subprocess,sys,json,time\nfrom pathlib import Path\nroot=Path("+repr(REMOTE)+")\n"
                source+="assert not (root/'launch_receipt.json').exists() and not (root/'run_v1').exists()\n"
                source+="log=(root/'run.log').open('xb')\n"
                source+="p=subprocess.Popen([sys.executable,'-B','-c',"+repr(SUPERVISOR)+"],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)\n"
                source+="receipt={'supervisor_pid':p.pid,'launched_epoch':time.time(),'physical_gpu':2,'mode':'NON_EVIDENCE_SMOKE'}\n"
                source+="(root/'launch_receipt.json').write_text(json.dumps(receipt))\nprint(json.dumps(receipt))"
                result=command(auth,source)
            elif operation=="poll":
                result=command(auth,POLL)
            elif operation=="download":
                result=command(auth,DOWNLOAD)
                if result.returncode==0:
                    target=HERE/"evidence/b2_gpu2_smoke_v1"
                    target.mkdir(exist_ok=False)
                    path=target/"server_evidence.zip"
                    path.write_bytes(result.stdout)
                    print(json.dumps({"downloaded":True,"bytes":len(result.stdout),
                                      "sha256":hashlib.sha256(result.stdout).hexdigest()}),flush=True)
                    continue
            else:
                raise ValueError("unknown operation")
            if result.returncode:
                # Never print client/server error strings that might echo coordinates.
                detail=result.stderr.decode(errors="replace").lower()
                category="HOST_KEY_REVIEW_REQUIRED" if "host key" in detail else "CONNECTION_OR_REMOTE_COMMAND_FAILED"
                print(json.dumps({"status":category,"exit_code":result.returncode}),flush=True)
            else:
                value=json.loads(result.stdout)
                print(json.dumps(value),flush=True)
        except Exception as error:
            print(json.dumps({"status":"TRANSPORT_HELPER_ERROR","error_type":type(error).__name__}),flush=True)


if __name__=="__main__":
    main()
