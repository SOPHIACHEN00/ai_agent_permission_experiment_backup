"""Continue unstarted groups after the inter-worker GPU0 idle-check stop."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from fractions import Fraction as F
import tune_gpu0 as base
ROOT = base.ROOT

def wait_idle(group: str) -> None:
    started = time.monotonic()
    consecutive = 0
    while time.monotonic()-started < 60:
        memory = base.guard_memory(4)
        try:
            sample = base.gpu_idle()
            consecutive += 1
            state = {'status': 'IDLE', 'sample': sample, 'consecutive': consecutive}
        except RuntimeError as error:
            if str(error) != 'GPU0 occupied; no fallback':
                raise
            consecutive = 0
            state = {'status': 'WAITING_FOR_RELEASE', 'gpu0': subprocess.run(['nvidia-smi', '--id=0', '--query-gpu=index,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True, timeout=15).stdout.strip()}
        with (ROOT/'inter_group_resource_checks.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps({'group': group, 'checked_at_utc': base.stamp(), 'headroom_bytes': memory['effective_headroom_bytes'], **state})+'\n')
            output.flush()
            os.fsync(output.fileno())
        if consecutive >= 2:
            return
        time.sleep(2)
    raise RuntimeError('GPU0 did not remain idle in60seconds')

def main() -> int:
    config=base.verify_inputs()
    upload=json.loads((ROOT/'resume_upload_receipt.json').read_text())
    assert base.sha(Path(__file__)) == upload['sha256']
    prior=json.loads((ROOT/'failure.json').read_text())
    assert prior['error']=='GPU0 occupied; no fallback' and prior['groups_completed']==1
    assert json.loads((ROOT/'exit_receipt.json').read_text())['exit_code']==1
    assert not (ROOT/'resume_master_status.json').exists()
    completed=[]
    code=1
    try:
        for index,(setting,seed) in enumerate(base.coordinates(config)):
            group=f"{setting['id']}_seed{seed}"
            directory=ROOT/'run_v1'/group
            if index==0:
                result=json.loads((directory/'completion.json').read_text())
                meta=json.loads((directory/'checkpoint.json').read_text())
                assert result==prior['completed'][0]
                assert result['status']=='COMPLETE' and result['transitions']==12000 and not any(result['hard_counts'].values())
                assert base.sha(directory/meta['file'])==meta['sha256']==result['checkpoint_sha256']
                completed.append(result)
                base.write_json(ROOT/'resume_adoption_receipt.json',{'group':group,'checkpoint_sha256':meta['sha256'],'checkpoint_preserved':True,'training_repeated':False,'prior_failure_sha256':base.sha(ROOT/'failure.json'),'supervisor_sha256':base.sha(Path(__file__))})
                continue
            if directory.exists():
                raise RuntimeError('unstarted group already has output; stop for review')
            base.verify_inputs()
            base.write_json(ROOT/'resume_master_status.json',{'status':'WAITING_FOR_GPU_RELEASE','current_group':group,'group_index':index,'groups_completed':len(completed),'completed':completed,'test_opened':False,'updated_at_utc':base.stamp()})
            wait_idle(group)
            with (ROOT/(group+'.log')).open('xb') as log:
                child=subprocess.Popen([sys.executable,'-B',str(ROOT/'tune_gpu0.py'),'--group',str(index)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy())
                base.write_json(ROOT/'resume_master_status.json',{'status':'RUNNING','worker_pid':child.pid,'worker_start_ticks':Path(f'/proc/{child.pid}/stat').read_text().split()[21],'current_group':group,'group_index':index,'groups_completed':len(completed),'completed':completed,'test_opened':False,'updated_at_utc':base.stamp()})
                returned=child.wait()
            if returned:
                raise RuntimeError(f'worker {group} exited{returned}; no retry')
            result=json.loads((directory/'completion.json').read_text())
            if result['status']!='COMPLETE' or result['test_opened'] or any(result['hard_counts'].values()):
                raise RuntimeError('worker completion integrity failure')
            completed.append(result)
            print(json.dumps({'group':group,'mean_exact_value':result['mean_exact_value'],'groups_completed':len(completed)}),flush=True)
        assert len(completed)==config['expected_checkpoints']
        assert sum(r['transitions'] for r in completed)==config['expected_transitions']
        assert sum(r['optimizer_steps'] for r in completed)==config['expected_optimizer_updates']
        assert sum(r['exact_rows'] for r in completed)==config['expected_exact_rows']
        baseline={r['seed']:F(r['mean_exact_value']) for r in completed if r['config_id']==config['configs'][0]['id']}
        summaries=[]
        for setting in config['configs']:
            rows=[r for r in completed if r['config_id']==setting['id']]
            summaries.append({**setting,'seed_count':len(rows),'seed_values':{r['seed']:r['mean_exact_value'] for r in rows},'seed_regrets':{r['seed']:r['mean_exact_regret'] for r in rows},'mean_exact_value':str(sum((F(r['mean_exact_value']) for r in rows),F(0))/3),'mean_exact_regret':str(sum((F(r['mean_exact_regret']) for r in rows),F(0))/3),'paired_improvements_over_baseline':{r['seed']:str(F(r['mean_exact_value'])-baseline[r['seed']]) for r in rows},'near_optimal_seeds':sum(r['near_optimal'] for r in rows),'worst_seed_value':str(min(F(r['mean_exact_value']) for r in rows)),'total_optimizer_updates':sum(r['optimizer_steps'] for r in rows)})
        winner=min(summaries,key=lambda r:(F(r['mean_exact_regret']),r['total_optimizer_updates'],r['id']))['id']
        base.verify_inputs()
        result={'status':'COMPLETE','ended_at_utc':base.stamp(),'groups_completed':len(completed),'transitions':sum(r['transitions'] for r in completed),'optimizer_updates':sum(r['optimizer_steps'] for r in completed),'exact_rows':sum(r['exact_rows'] for r in completed),'summaries':summaries,'selected_config_by_validation':winner,'completed':completed,'physical_gpu_index':0,'test_opened':False,'automatic_retry':False,'supervisor_recovery':True,'retrained_completed_groups':0,'adopted_completed_groups':1,'resume_supervisor_sha256':base.sha(Path(__file__))}
        base.write_json(ROOT/'resume_completion.json',result)
        base.write_json(ROOT/'resume_master_status.json',result)
        code=0
    except BaseException as error:
        failure={'status':'STOPPED_ERROR','error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc(),'groups_completed':len(completed),'completed':completed,'ended_at_utc':base.stamp(),'test_opened':False,'automatic_retry':False}
        base.write_json(ROOT/'resume_failure.json',failure)
        base.write_json(ROOT/'resume_master_status.json',failure)
    finally:
        base.write_json(ROOT/'resume_exit_receipt.json',{'exit_code':code,'ended_at_utc':base.stamp(),'test_opened':False})
    return code

if __name__=='__main__':
    raise SystemExit(main())
