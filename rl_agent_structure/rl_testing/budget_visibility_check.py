"""Matched 22-dimensional DDQN comparison: hidden versus visible remaining budgets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.bounded_counts_check import fixed_q_probe
from rl_testing.cause_diagnosis import (DiagnosisLog, clone_user_context, context_snapshot,
                                       describe_arm, render_comparison)
from rl_testing.online_check import QUERIES, annotate_counts, validate_protocol, wall_deadline, _user_digest
from rl_testing.records import json_write, new_output, protected_state, learner_counters
from rl_testing.runner import RuleSelection, run_sequence

MODES = ('masked_v1', 'remaining_ratio_v1')
COUNT_MODE = 'bounded_ratio_v1'
TRAIN_TASKS = 15
EVALUATION_GROUPS = tuple((mode, model, context) for mode in MODES
                          for model in ('trained', 'frozen') for context in ('fresh', 'retained'))


class BudgetLog(DiagnosisLog):
    def report(self, summary=None):
        result = super().report(summary)
        result.update(mode='online-check', experiment_kind='budget_visibility_single_factor')
        return result


def execution_budget_diagnostics(log, traces):
    """Actual selected EXECUTEs, not just task success after guards force progress."""
    rows = []
    for task in log.tasks:
        selected = [row for row in traces if row['task_id'] == task['task_id']]
        executes = [row for row in selected if row['selected_action'] == 'EXECUTE']
        execution_rows = []
        for row in executes:
            budget = row['runtime_budgets']
            used, limit = budget['release_steps_used'], budget['release_step_limit']
            if type(used) is not int or type(limit) is not int or limit < 1:
                raise ValueError('execution diagnostics require actual runtime budgets')
            execution_rows.append({'global_decision': row['global_decision'],
                'control_steps_used': budget['control_steps_used'],
                'release_steps_used': used, 'release_step_limit': limit,
                'release_budget_exhausted': used >= limit,
                'legal_release_candidates': sum(c['valid'] and c['action'] == 'RELEASE'
                                                for c in row['candidates'])})
        rows.append({'query_id': task['query_id'], 'status': task['status'],
                     'execution_kind': 'selected_control_action_check_receipts_for_actual_effect',
                     'task_success': task['metrics']['task_success'],
                     'selected_release_count': sum(row['selected_action'] == 'RELEASE' for row in selected),
                     'executions': execution_rows,
                     'first_execute_before_release_limit': None if not execution_rows else
                         not execution_rows[0]['release_budget_exhausted'],
                     'active_gates_before_cleanup': task['metrics']['active_gate_items_before_cleanup']})
    return rows


def run_check(config, output, *, deadline, completed_groups):
    from rl_testing.control_trace import TracedPolicy
    from rl_testing.torch_checks import (_policy, _frozen_copy, _network_digest, _checkpoint_signature,
                                         _parameters, _update_evidence)
    from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
    validate_protocol(config)
    if config.seed != 3:
        raise ValueError('this fixed first budget comparison uses seed 3')

    warm_dir = output / 'common_warmup'
    warm_dir.mkdir()
    warm_log = BudgetLog(config, warm_dir)
    warm = run_sequence(config, RuleSelection(), warm_log, queries=QUERIES, training=False,
                        case_id='update-fixture', phase='common_observed_warmup', deadline=deadline)
    annotate_counts(warm_log)
    warm_log.save({'task_count': len(warm.tasks), 'transition_count': len(warm.transitions),
                   'purpose': 'same observed warm-up as previous diagnostic; not a new rule arm'})
    policies = {mode: _policy(config, None, count_representation=COUNT_MODE,
                              budget_representation=mode) for mode in MODES}
    digests = {mode: _network_digest(p.learner.online_network) for mode, p in policies.items()}
    if len(set(digests.values())) != 1 or any(p.learner.model_spec.state_dim != 22 for p in policies.values()):
        raise RuntimeError('initial network weights or architecture differ')
    # Matched observations, with only the two appended inputs different.
    left, right = (policies[mode] for mode in MODES)
    for transition in warm.transitions:
        a, b = left.encoder.encode(transition.pre_decision), right.encoder.encode(transition.pre_decision)
        import torch
        if (not torch.equal(a.state[:-2], b.state[:-2]) or bool(a.state[-2:].any())
                or not torch.equal(a.candidate_features, b.candidate_features)
                or not torch.equal(a.mask, b.mask) or a.candidate_ids != b.candidate_ids):
            raise RuntimeError('non-budget features differ')
    initial, warmup = {}, {}
    for mode, policy in policies.items():
        directory = output / mode
        directory.mkdir()
        for transition in warm.transitions:
            if time.monotonic() >= deadline: raise TimeoutError('budget comparison deadline')
            policy.observe(transition)
        if learner_counters(policy)['optimizer_steps'] != 32:
            raise RuntimeError('warm-up update count changed')
        initial[mode] = _frozen_copy(config, policy)
        warmup[mode] = _checkpoint_signature(policy)
        save_checkpoint(policy, directory / 'warm_policy.pt')
    json_write(output / 'matched_initialization.json', {'same_initial_network': True,
        'initial_network_digests': digests, 'state_dimensions': 22,
        'warmup_transitions': len(warm.transitions), 'warmup_updates_per_arm': 32,
        'non_budget_inputs_identical': True, 'warmup_model_signatures': warmup})

    training, training_summaries = {}, {}
    for mode, policy in policies.items():
        directory = output / mode
        log = BudgetLog(config, directory)
        trace = TracedPolicy(policy, log)
        before_parameters, prior = _parameters(policy), learner_counters(policy)
        def save_completed(count, user):
            if count % 3 == 0:
                save_checkpoint(policy, directory / f'policy_after_{count:03d}.pt')
                if count == TRAIN_TASKS:
                    json_write(directory / 'context_after_015.json', context_snapshot(user))
                print(json.dumps({'phase': 'training', 'budget': mode, 'completed': count}), flush=True)
        status = 'completed'
        try:
            result = run_sequence(config, trace, log, queries=QUERIES * 5, training=True,
                                  case_id='cause-training', phase='budget_visibility_training',
                                  on_completed=save_completed, deadline=deadline)
        except Exception:
            status = 'incomplete'
            raise
        finally:
            annotate_counts(log)
            summary = {'status': status, 'budget_representation': mode,
                       'observed': describe_arm(log, trace.rows),
                       'execution_budgets': execution_budget_diagnostics(log, trace.rows),
                       'online_optimizer_steps': learner_counters(policy)['optimizer_steps'] - prior['optimizer_steps']}
            if status == 'completed':
                summary.update(_update_evidence(policy, before_parameters))
                restored = restore_checkpoint(directory / 'policy_after_015.pt', user_id=config.user_id,
                    device=config.device, count_representation=COUNT_MODE, budget_representation=mode)
                summary['checkpoint_roundtrip'] = _checkpoint_signature(policy) == _checkpoint_signature(restored)
                if not summary['checkpoint_roundtrip']: raise RuntimeError('budget checkpoint round-trip failed')
            log.save(summary)
            training_summaries[mode] = summary
            from rl_testing.plots import render_plots
            render_plots(log.report(summary), directory / 'plots')
        training[mode] = result

    common_user = training[MODES[0]].user
    context_signatures = {m: _user_digest(r.user) for m, r in training.items()}
    policy_signatures = {m: _checkpoint_signature(p) for m, p in policies.items()}
    frozen_signatures = {m: _checkpoint_signature(p) for m, p in initial.items()}
    boundaries = tuple(t.pre_decision for t in warm.transitions) + tuple(
        t.pre_decision for t in training[MODES[0]].transitions[-32:])
    probes = {f'{mode}_{name}': fixed_q_probe(p, boundaries)
              for mode in MODES for name, p in (('frozen', initial[mode]), ('trained', policies[mode]))}
    json_write(output / 'fixed_q_probes.json', probes)
    for mode, model, context in EVALUATION_GROUPS:
        if time.monotonic() >= deadline: raise TimeoutError('budget comparison deadline')
        arm = f'{mode}_{model}_{context}'
        directory = output / 'evaluations' / arm
        directory.mkdir(parents=True)
        log = BudgetLog(config, directory)
        base = _frozen_copy(config, policies[mode] if model == 'trained' else initial[mode])
        before = _checkpoint_signature(base)
        trace = TracedPolicy(base, log)
        branch = clone_user_context(common_user) if context == 'retained' else None
        status = 'completed'
        try:
            run_sequence(config, trace, log, queries=QUERIES, training=False, case_id='cause-eval',
                         phase='budget_greedy_evaluation', user_context=branch, deadline=deadline)
        except Exception:
            status = 'incomplete'
            raise
        finally:
            annotate_counts(log)
            integrity = (before == _checkpoint_signature(base)
                and all(context_signatures[m] == _user_digest(r.user) for m, r in training.items())
                and all(policy_signatures[m] == _checkpoint_signature(p) for m, p in policies.items())
                and all(frozen_signatures[m] == _checkpoint_signature(p) for m, p in initial.items()))
            summary = {'arm': arm, 'status': status, 'budget_representation': mode,
                'model': model, 'context': context, 'evaluation_epsilon': 0., 'integrity_passed': integrity,
                'observed': describe_arm(log, trace.rows),
                'execution_budgets': execution_budget_diagnostics(log, trace.rows)}
            log.save(summary)
            completed_groups.append(summary)
            print(json.dumps({'phase': 'evaluation', 'arm': arm, 'successes': summary['observed']['successes'],
                              'tasks': len(log.tasks)}), flush=True)
        if not integrity: raise RuntimeError('evaluation modified source context or weights')
    render_comparison(completed_groups, output / 'budget_visibility_comparison.svg')
    return {'same_initial_weights': True, 'non_budget_inputs_identical': True,
        'common_warmup_transitions': len(warm.transitions), 'training': training_summaries,
        'evaluations': completed_groups, 'tasks_completed': 57,
        'fixed_probe_summaries': {k: {a: b for a, b in v.items() if a != 'rows'} for k, v in probes.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-training', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_training: parser.error('--allow-training required; no Torch update attempted')
    config = RunConfig.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
    validate_protocol(config)
    output = new_output(args.output)
    json_write(output / 'config.json', config.to_dict())
    before = protected_state()
    json_write(output / 'protected_sources.json', before)
    from personal_assistant.integration.readonly import NetworkBlock
    guard = NetworkBlock()
    status, error, details, completed = 'completed', None, {}, []
    start = time.monotonic()
    try:
        with guard, wall_deadline(config.max_seconds):
            details = run_check(config, output, deadline=start+config.max_seconds, completed_groups=completed)
    except Exception as exc:
        status = 'incomplete'
        error = {'type': type(exc).__name__, 'message': str(exc),
                 'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                            for f in traceback.extract_tb(exc.__traceback__)]}
    source_ok = before == protected_state()
    if not source_ok or guard.attempts: status = 'integrity_failed'
    summary = {'status': status, 'error': error, 'elapsed_seconds': time.monotonic()-start,
        'network_attempts': guard.attempts, 'protected_sources_unchanged': source_ok,
        'scheduled_tasks': 57, 'recorded_evaluation_groups': len(completed),
        'completed_evaluation_groups': sum(g['status'] == 'completed' for g in completed), 'converged': None,
        'limitations': ['Single seed, repeated seen queries, constant Allow Reuse; no preference learning claim.',
            'Matched 22D architectures; previous 20D results are historical, not a matched control.',
            'Same task budget, potentially unequal optimizer updates.',
            'Common retained context and late Q probes come from masked training.'], **details}
    json_write(output / 'summary.json', summary)
    print(json.dumps({'status': status, 'groups': len(completed), 'seconds': summary['elapsed_seconds']}), flush=True)
    return 0 if status == 'completed' else 1


if __name__ == '__main__': raise SystemExit(main())
