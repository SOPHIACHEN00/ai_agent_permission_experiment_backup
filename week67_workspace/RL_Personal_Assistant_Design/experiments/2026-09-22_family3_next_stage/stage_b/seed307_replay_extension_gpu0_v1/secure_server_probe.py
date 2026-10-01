"""Hidden-input, read-only probe for GPU0 and the location of the sealed checkpoint."""
import getpass
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from secure_server_session import command

SOURCE = r'''
import json,os,subprocess,shutil,socket
from pathlib import Path
paths=[
 "/output/agenticAI",
 "/output/agenticAI/budget_recourse_gpu1_formal_v1",
 "/output/agenticAI/budget_recourse_gpu1_formal_v1/bundle",
 "/output/agenticAI/budget_recourse_gpu1_formal_v1/run_v1/ddqn_seed307_gamma1.pt",
 "/hyperai/home/gradpred_exp",
 "/hyperai/home/gradpred_exp/attack",
 "/hyperai/home/gradpred_exp/agenticAI",
 "/hyperai/home/agenticAI",
 "/root/agenticAI",
]
query=subprocess.run(["nvidia-smi","--id=0","--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
apps=subprocess.run(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],capture_output=True,text=True,check=True,timeout=15).stdout.splitlines()
q=[x.strip() for x in query.split(",")]
gpu0_apps=[x for x in apps if x.split(",")[0].strip().lower()==q[1].lower()]
mem={}
for line in Path("/proc/meminfo").read_text().splitlines():
 k,v=line.split(":",1); mem[k]=int(v.split()[0])*1024
cg={}
for name in ("memory.current","memory.max","cpu.max","cpu.stat"):
 p=Path("/sys/fs/cgroup")/name
 if p.exists(): cg[name]=p.read_text().strip()
print(json.dumps({"hostname":socket.gethostname(),"cwd":os.getcwd(),"paths":{p:Path(p).exists() for p in paths},
 "gpu0":{"query":q,"compute_apps":gpu0_apps},"host_mem_available_bytes":mem.get("MemAvailable"),
 "cgroup":cg,"output_free_bytes":shutil.disk_usage("/output").free if Path("/output").exists() else None}))
'''

def main():
    auth = tuple(getpass.getpass(p + " (hidden): ") for p in ("Endpoint", "Port", "Account", "Authentication"))
    result = command(auth, SOURCE, timeout=60)
    if result.returncode:
        print(json.dumps({"status": "CONNECTION_OR_REMOTE_COMMAND_FAILED", "exit_code": result.returncode}))
        return
    value = json.loads(result.stdout)
    (HERE / "host_probe.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value))

if __name__ == "__main__":
    main()
