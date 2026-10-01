"""Hidden-input read-only status snapshot for the single GPU0 experiment."""
import getpass, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from secure_server_session import command
REMOTE="/output/agenticAI/budget_recourse_seed307_replay_extension_gpu0_v1"
SOURCE=r'''
import json,subprocess
from pathlib import Path
root=Path("REMOTE")
out={}
for name in ("preflight_receipt","upload_receipt","launch_receipt","launch_retry_receipt","child_receipt","exit_receipt","status","completion","failure"):
 p=root/(name+".json")
 if p.is_file(): out[name]=json.loads(p.read_text())
if "child_receipt" in out:
 p=Path("/proc")/str(out["child_receipt"]["pid"])
 out["child_alive"]=p.exists()
 if p.exists():
  lines=(p/"status").read_text().splitlines() if (p/"status").exists() else []
  out["child_proc"]={x.split(":",1)[0]:x.split(":",1)[1].strip() for x in lines if x.startswith(("State:","VmRSS:","VmHWM:"))}
for name in ("run.log","retry1_run.log"):
 p=root/name
 if p.is_file(): out[name+"_tail"]=p.read_text(errors="replace")[-6000:]
q=subprocess.run(["nvidia-smi","--id=0","--query-gpu=index,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True).stdout.strip()
out["gpu0"]=q
print(json.dumps(out))
'''.replace('"REMOTE"','"'+REMOTE+'"')

def main():
    auth=tuple(getpass.getpass(p+" (hidden): ") for p in ("Endpoint","Port","Account","Authentication"))
    result=command(auth,SOURCE,timeout=60)
    if result.returncode:
        print(json.dumps({"status":"CONNECTION_OR_REMOTE_COMMAND_FAILED","exit_code":result.returncode}))
        return
    value=json.loads(result.stdout)
    now=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    (HERE/("live_status_"+now+".json")).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(value))

if __name__=="__main__": main()
