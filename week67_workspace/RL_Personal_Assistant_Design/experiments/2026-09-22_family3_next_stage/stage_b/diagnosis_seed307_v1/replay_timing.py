"""Reconstruct only logged reward sampling times; no model or optimizer execution."""
import json
from pathlib import Path
import random
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from learner_bridge import EXPERIMENT_ID
from pa_rl.family3_v2_learning import Family3V2LearnerRngDeriver

rewards={s:[] for s in (101,211,307)}
with (HERE.parent/'formal_gpu01_v1/server_evidence/unpacked/run_v1/train_steps.jsonl').open(encoding='utf-8') as f:
    for line in f:
        r=json.loads(line)['payload']
        if r['gamma']==1:
            rewards[r['seed']].append(r['event']['after']['status']=='success')
result=[]
for seed,rs in rewards.items():
    deriver=Family3V2LearnerRngDeriver(EXPERIMENT_ID,'masked_ddqn',seed)
    positive_updates=[]
    for update,step in enumerate(range(256,12001,4)):
        n=sum(rs[j] for j in random.Random(deriver.replay_sampling_seed(update)).sample(range(step),64))
        if n:
            positive_updates.append(dict(environment_step=step,optimizer_update=update+1,positive_draws=n))
    first=positive_updates[0]
    result.append(dict(seed=seed,first_positive_sample=first,
        remaining_optimizer_updates_including_first=2937-first['optimizer_update']+1,
        target_syncs_after_first_positive_sample=[dict(optimizer_update=u,environment_step=252+4*u)
              for u in range(250,2938,250) if u>=first['optimizer_update']]))
with (HERE/'replay_timing.json').open('x',encoding='utf-8') as f:
    json.dump(dict(mode='index_reconstruction_only',training_updates_performed=0,models=result),f,indent=2)
print(json.dumps(result))
