"""One non-model syntax/configuration and unchanged-training-loop check."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'hyperparam_tuning_gpu0_v1'


def main() -> None:
    parsed = {}
    for name in ('tune_gpu0.py','secure_control.py','postflight.py','static_check.py'):
        parsed[name] = ast.parse((HERE/name).read_text(encoding='utf-8'), filename=name)
    previous = ast.parse((OLD/'tune_gpu0.py').read_text(encoding='utf-8'))
    def function(tree: ast.AST, name: str) -> ast.FunctionDef:
        return next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    def training_loop(tree: ast.AST) -> ast.For:
        return next(n for n in ast.walk(function(tree,'worker')) if isinstance(n,ast.For)
                    and isinstance(n.target,ast.Name) and n.target.id=='graph')
    assert ast.dump(training_loop(previous)) == ast.dump(training_loop(parsed['tune_gpu0.py']))
    for name in ('cuda_adapter','gpu_idle','guard_memory','resources','coordinates'):
        assert ast.dump(function(previous,name)) == ast.dump(function(parsed['tune_gpu0.py'],name))
    prior_class = next(n for n in ast.walk(previous) if isinstance(n,ast.ClassDef) and n.name=='TunedDDQN')
    new_class = next(n for n in ast.walk(parsed['tune_gpu0.py']) if isinstance(n,ast.ClassDef) and n.name=='TunedDDQN')
    assert ast.dump(prior_class) == ast.dump(new_class)
    config = json.loads((HERE/'config.json').read_text())
    old_config = json.loads((OLD/'config.json').read_text())
    for key in ('fixed','gamma','transitions_per_graph','transitions_per_group','validation_graphs','conditions','near_optimal_mean_regret','torch_threads'):
        assert config[key] == old_config[key]
    assert config['configs'] == old_config['configs'][:2]
    assert set(config['seeds']).isdisjoint(old_config['seeds']) and len(set(config['seeds']))==3
    groups = len(config['configs'])*len(config['seeds'])
    assert groups==config['expected_checkpoints']==6
    assert groups*config['transitions_per_group']==config['expected_transitions']==72000
    assert groups*len(range(256,12001,4))==config['expected_optimizer_updates']==17622
    assert groups*4==config['expected_exact_rows']==24
    assert hashlib.sha256((OLD/'server_evidence/unpacked/resume_completion.json').read_bytes()).hexdigest()==config['prior_selection_sha256']
    result={'status':'PASS','parsed_files':list(parsed),'training_loop_ast_unchanged':True,
            'learner_class_ast_unchanged':True,'resource_device_rng_coordinate_functions_unchanged':True,
            'seeds':config['seeds'],'groups':groups,'transitions':72000,'optimizer_updates':17622,'exact_rows':24,
            'local_model_execution':False,'test_opened':False,
            'files':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('tune_gpu0.py','secure_control.py','postflight.py','config.json')}}
    (HERE/'static_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
