"""One-factor raw versus bounded-count DDQN comparison with matched warm-up."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.cause_diagnosis import (DiagnosisLog, clone_user_context, context_snapshot, describe_arm,
                                       render_comparison)
from rl_testing.online_check import QUERIES, annotate_counts, validate_protocol, wall_deadline, _user_digest
from rl_testing.records import json_write, new_output, protected_state, learner_counters
from rl_testing.runner import RuleSelection, run_sequence

MODES = ('raw_v1', 'bounded_ratio_v1')
TRAIN_TASKS = 15
EVALUATION_GROUPS = tuple((mode, model, context) for mode in MODES
                          for model in ('trained', 'frozen') for context in ('fresh', 'retained'))


class CountLog(DiagnosisLog):
    def report(self, summary=None):
        report = super().report(summary)
        report.update(mode='online-check', experiment_kind='bounded_count_single_factor')
        return report


def prefix_matches(rows, reference):
    if len(rows) != TRAIN_TASKS or len(reference) != TRAIN_TASKS:
        return False
    return all(all(row[k] == expected[k] for k in ('query_id', 'status', 'return', 'epsilon', 'metrics'))
               for row, expected in zip(rows, reference))


def fixed_q_probe(policy, boundaries):
    """Score predeclared common boundaries; no rewards fed back, no new actions."""
    from rl_testing.control_trace import _score_candidates
    from rl_testing.torch_checks import _checkpoint_signature
    before = _checkpoint_signature(policy)
    rows = []
    for boundary in boundaries:
        encoded = policy.encoder.encode(boundary)
        scores = _score_candidates(policy, encoded)
        mask = encoded.mask.tolist()
        valid = [q for q, allowed in zip(scores, mask) if allowed]
        best = max(valid)
        rows.append({'token': boundary.token, 'decision': boundary.view.logical_step,
                     'candidate_ids': list(encoded.candidate_ids), 'mask': mask, 'q': scores,
                     'greedy_actions': sorted({candidate.action.value for candidate, q, allowed
                                              in zip(boundary.view.candidates, scores, mask) if allowed and q == best}),
                     'max_valid_q': best})
    values = [q for row in rows for q, valid in zip(row['q'], row['mask']) if valid]
    if before != _checkpoint_signature(policy):
        raise RuntimeError('fixed Q probe changed policy')
    return {'boundary_count': len(rows), 'valid_candidate_count': len(values),
            'above_one_count': sum(q > 1 for q in values),
            'above_one_fraction': sum(q > 1 for q in values) / len(values),
            'max_valid_q': max(values), 'mean_valid_q': sum(values) / len(values),
            'policy_unchanged': True, 'rows': rows}


def run_check(config, reference, output, *, deadline, completed_groups):
    from rl_testing.audit_cache_check import audit_cache_check
    from rl_testing.control_trace import TracedPolicy
    from rl_testing.torch_checks import (_policy, _frozen_copy, _network_digest, _checkpoint_signature,
                                         _parameters, _update_evidence)
    from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
    from personal_assistant.learning.count_representation import (STATE_COUNT_FEATURE_NAMES, CANDIDATE_COUNT_FEATURE_NAMES)
    validate_protocol(config)
    if config.seed != 3:
        raise ValueError('this first fixed comparison uses the approved seed 3')
    audit = audit_cache_check(config, output / 'audit_equivalence', deadline=deadline)
    print(json.dumps({'phase': 'audit_equivalence', 'passed': True,
                      'speedup': audit['fixed_ledger_speedup']}), flush=True)
    warm_dir = output / 'common_warmup'
    warm_dir.mkdir()
    warm_log = CountLog(config, warm_dir)
    warm = run_sequence(config, RuleSelection(), warm_log, queries=QUERIES, training=False,
                        case_id='update-fixture', phase='common_observed_warmup', deadline=deadline)
    annotate_counts(warm_log)
    warm_log.save({'task_count': 3, 'transition_count': len(warm.transitions),
                   'purpose': 'shared observed warm-up; also fresh rule reference'})
    policies = {mode: _policy(config, None, count_representation=mode) for mode in MODES}
    init_digests = {m: _network_digest(p.learner.online_network) for m, p in policies.items()}
    if len(set(init_digests.values())) != 1:
        raise RuntimeError('initial network weights differ')
    initial, warm_details = {}, {}
    for mode, policy in policies.items():
        directory = output / mode
        directory.mkdir()
        for transition in warm.transitions:
            if time.monotonic() >= deadline:
                raise TimeoutError('shared count comparison deadline')
            policy.observe(transition)
        if learner_counters(policy)['optimizer_steps'] != 32:
            raise RuntimeError('warm-up update count changed')
        initial[mode] = _frozen_copy(config, policy)
        warm_details[mode] = {'updates': 32, 'signature': _checkpoint_signature(policy)}
        save_checkpoint(policy, directory / 'warm_policy.pt')
    json_write(output / 'matched_initialization.json', {'same_initial_network': True,
        'network_digests': init_digests, 'warmup': warm_details,
        'transformed_state_counts': STATE_COUNT_FEATURE_NAMES, 'transformed_candidate_counts': CANDIDATE_COUNT_FEATURE_NAMES})

    training, training_summaries = {}, {}
    for mode, policy in policies.items():
        directory = output / mode
        log = CountLog(config, directory)
        trace = TracedPolicy(policy, log)
        before_parameters = _parameters(policy)
        prior = learner_counters(policy)
        def save_completed(count, user):
            if count % 3 == 0:
                save_checkpoint(policy, directory / f'policy_after_{count:03d}.pt')
                if count == TRAIN_TASKS:
                    json_write(directory / 'context_after_015.json', context_snapshot(user))
                print(json.dumps({'phase': 'training', 'representation': mode, 'completed': count}), flush=True)
        status, result = 'completed', None
        try:
            result = run_sequence(config, trace, log, queries=QUERIES * 5, training=True,
                                  case_id='cause-training', phase='count_representation_training',
                                  on_completed=save_completed, deadline=deadline)
        except Exception:
            status = 'incomplete'
            raise
        finally:
            annotate_counts(log)
            summary = {'status': status, 'count_representation': mode,
                       'observed': describe_arm(log, trace.rows),
                       'online_optimizer_steps': learner_counters(policy)['optimizer_steps'] - prior['optimizer_steps']}
            if status == 'completed':
                summary.update(_update_evidence(policy, before_parameters))
                saved = restore_checkpoint(directory / 'policy_after_015.pt', user_id=config.user_id,
                                           device=config.device, count_representation=mode)
                summary['checkpoint_roundtrip'] = _checkpoint_signature(policy) == _checkpoint_signature(saved)
                if not summary['checkpoint_roundtrip']:
                    raise RuntimeError('representation checkpoint round-trip failed')
            log.save(summary)
            training_summaries[mode] = summary
            from rl_testing.plots import render_plots
            render_plots(log.report(summary), directory / 'plots')
        if mode == 'raw_v1':
            matched = prefix_matches(log.tasks, reference)
            json_write(output / 'raw_prefix_equivalence.json', {'matched': matched, 'tasks': len(log.tasks)})
            if not matched:
                raise RuntimeError('raw prefix changed; stop before attributing any effect to bounded inputs')
        training[mode] = result

    common_user = training['raw_v1'].user
    contexts_before = {m: _user_digest(r.user) for m, r in training.items()}
    policy_before = {m: _checkpoint_signature(p) for m, p in policies.items()}
    frozen_before = {m: _checkpoint_signature(p) for m, p in initial.items()}
    boundaries = tuple(t.pre_decision for t in warm.transitions) + tuple(t.pre_decision for t in training['raw_v1'].transitions[-32:])
    probes = {f'{mode}_{name}': fixed_q_probe(p, boundaries)
              for mode in MODES for name, p in (('frozen', initial[mode]), ('trained', policies[mode]))}
    json_write(output / 'fixed_q_probes.json', probes)

    for mode, model, context in EVALUATION_GROUPS:
        if time.monotonic() >= deadline:
            raise TimeoutError('shared count comparison deadline')
        arm = f'{mode}_{model}_{context}'
        directory = output / 'evaluations' / arm
        directory.mkdir(parents=True)
        log = CountLog(config, directory)
        source = policies[mode] if model == 'trained' else initial[mode]
        base = _frozen_copy(config, source)
        before = _checkpoint_signature(base)
        trace = TracedPolicy(base, log)
        branch = clone_user_context(common_user) if context == 'retained' else None
        status = 'completed'
        try:
            run_sequence(config, trace, log, queries=QUERIES, training=False,
                         case_id='cause-eval', phase='count_greedy_evaluation',
                         user_context=branch, deadline=deadline)
        except Exception:
            status = 'incomplete'
            raise
        finally:
            annotate_counts(log)
            integrity = (before == _checkpoint_signature(base)
                and all(contexts_before[m] == _user_digest(r.user) for m, r in training.items())
                and all(policy_before[m] == _checkpoint_signature(p) for m, p in policies.items())
                and all(frozen_before[m] == _checkpoint_signature(p) for m, p in initial.items()))
            summary = {'arm': arm, 'status': status, 'representation': mode,
                       'model': model, 'context': context, 'evaluation_epsilon': 0.,
                       'integrity_passed': integrity, 'observed': describe_arm(log, trace.rows)}
            log.save(summary)
            completed_groups.append(summary)
            print(json.dumps({'phase': 'evaluation', 'arm': arm, 'successes': summary['observed']['successes'],
                              'tasks': len(log.tasks)}), flush=True)
        if not integrity:
            raise RuntimeError('evaluation modified training or frozen state')
    rule_dir = output / 'rule_retained'
    rule_dir.mkdir()
    rule_log = CountLog(config, rule_dir)
    run_sequence(config, RuleSelection(), rule_log, queries=QUERIES, training=False,
                 user_context=clone_user_context(common_user), case_id='cause-eval',
                 phase='rule_retained_reference', deadline=deadline)
    annotate_counts(rule_log)
    rule_summary = {'arm': 'rule_retained', 'observed': describe_arm(rule_log, [])}
    rule_log.save(rule_summary)
    rules = [{'arm': 'rule_fresh', 'observed': describe_arm(warm_log, [])}, rule_summary]
    json_write(output / 'rule_references.json', rules)
    render_comparison(completed_groups + rules, output / 'bounded_count_comparison.svg')
    return {'same_initial_weights': True, 'common_warmup_transitions': len(warm.transitions),
            'raw_prefix_equivalent': True, 'training': training_summaries,
            'evaluations': completed_groups, 'rule_references': rules, 'audit_equivalence': audit,
            'fixed_probe_summaries': {k: {a: b for a, b in v.items() if a != 'rows'} for k, v in probes.items()},
            'learning_protocol_tasks_completed': 60, 'independent_audit_tasks_completed': 6}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--reference-prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-training', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_training:
        parser.error('--allow-training required; no Torch import or update attempted')
    config = RunConfig.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
    validate_protocol(config)
    reference = json.loads(args.reference_prefix.read_text(encoding='utf-8'))
    output = new_output(args.output)
    json_write(output / 'config.json', config.to_dict())
    json_write(output / 'reference_prefix.json', reference)
    before = protected_state()
    json_write(output / 'protected_sources.json', before)
    from personal_assistant.integration.readonly import NetworkBlock
    guard = NetworkBlock()
    status, error, details, completed = 'completed', None, {}, []
    start = time.monotonic()
    try:
        with guard, wall_deadline(config.max_seconds):
            details = run_check(config, reference, output, deadline=start+config.max_seconds, completed_groups=completed)
    except Exception as exc:
        status = 'incomplete'
        error = {'type': type(exc).__name__, 'message': str(exc),
                 'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                            for f in traceback.extract_tb(exc.__traceback__)]}
    source_ok = before == protected_state()
    if not source_ok or guard.attempts:
        status = 'integrity_failed'
    summary = {'status': status, 'error': error, 'elapsed_seconds': time.monotonic()-start,
        'network_attempts': guard.attempts, 'protected_sources_unchanged': source_ok,
        'scheduled_learning_protocol_tasks': 60, 'scheduled_audit_tasks': 6,
        'completed_evaluation_groups': len(completed), 'converged': None,
        'limits': ['Single seed, seen-query, constant Allow Reuse diagnostic; no preference or generalization claim.',
                   'Only count representation varies between learning arms; no Q clipping or reward changes.',
                   'Shared retained context was generated by raw training; not independent deployment history.'], **details}
    json_write(output / 'summary.json', summary)
    print(json.dumps({'status': status, 'groups': len(completed), 'seconds': summary['elapsed_seconds']}), flush=True)
    return 0 if status == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
