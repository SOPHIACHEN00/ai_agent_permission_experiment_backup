"""Local functional acceptance only. No provider, no keys, no training."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT/'src'), str(ROOT.parent)]

from personal_assistant.config import PermissionConfig, PERMISSION_SCHEMA
from personal_assistant.contracts.permission import PermissionChoice as C, contract_json_round_trip
from personal_assistant.integration.wu import load_wu_binding
from personal_assistant.integration.readonly import dependency_inventory, NetworkBlock
from personal_assistant.execution.user_session import UserSession
from personal_assistant.interaction.human_channel import LocalHumanChannel, HumanReply
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from personal_assistant.learning.outcomes import task_metrics, METRICS_SCHEMA
from mock_tools.runtime import ReadWriteRuntime


def task(user, q, *, choice=C.ALLOW_REUSE):
    b = load_wu_binding(q)
    channel = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', choice), session_id=f'{user.user_id}-q{q}')
    s = user.start_task(f'q{q}', b, ScriptedPlanner(fixture_decisions(b.task)), channel, ReadWriteRuntime())
    s.answer_source = 'explicit_fixture'
    r = s.run()
    row = {'user_id': user.user_id, 'query_id': q, 'round': user.position.round_index, 'status': r.status,
           'error': r.error, **task_metrics(s), 'ledger_replay_verified': r.ledger_replay_verified,
           'monitor_audit_verified': r.monitor_audit_verified}
    return s, r, row


def lifecycle_checks():
    checks, rows = [], []
    for n in (1, 2, 3):
        u = UserSession(f'lifecycle_n{n}', PermissionConfig(n), run_id=f'lifecycle_n{n}')
        _, _, a = task(u, 40); s, r, b = task(u, 41); rows.extend((a, b))
        weather = [m for m in r.human_snapshot['messages'] if m['message']['requested_scope']['tool'] == 'Weather']
        checks.append({'name': f'n{n}_expiry_or_reuse', 'passed': bool(weather) if n == 1 else not weather})
    u = UserSession('lifecycle_never', PermissionConfig(3), run_id='lifecycle_never')
    _, _, a = task(u, 40, choice=C.DENY_PERSIST); _, _, b = task(u, 41); rows.extend((a, b))
    checks.append({'name': 'never_suppresses_reask_and_keeps_failed_task', 'passed': b['permission_items'] == 0 and not b['task_success']})
    # Explicit revocation at the current task-end boundary, followed by real Q41.
    u = UserSession('lifecycle_revoke', PermissionConfig(3), run_id='lifecycle_revoke')
    bind = load_wu_binding(40)
    ch = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.ALLOW_REUSE), session_id='revoke')
    s = u.start_task('q40', bind, ScriptedPlanner(fixture_decisions(bind.task)), ch, ReadWriteRuntime())
    s.answer_source = 'explicit_fixture'
    while True:
        view = s.advance()
        if view.phase == 'task_end': break
        s.dispatch_control(s.policy.choose(view))
    for record in tuple(u.ledger.records()):
        if record.allows and record.status.value == 'active': u.ledger.disable(record.record_id, u.position)
    s.run(); _, r, row = task(u, 41); rows.append(row)
    checks.append({'name': 'revoked_permission_requires_new_answer', 'passed': any(m['message']['requested_scope']['tool'] == 'Weather' for m in r.human_snapshot['messages'])})
    return checks, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--persist-rounds', type=int, required=True)
    parser.add_argument('--all-wu', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    config = PermissionConfig(args.persist_rounds)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output == ROOT: raise ValueError('output must be a new subdirectory of rl_agent_structure')
    if output.exists(): raise FileExistsError('output already exists; refusing to overwrite')
    before = dependency_inventory(ROOT.parent)
    coverage, rows, event_rows = [], [], []
    with NetworkBlock() as guard:
        for q in range(65):
            u = UserSession(f'coverage_{q:02d}', config, run_id=f'coverage_{q:02d}')
            s, r, row = task(u, q); rows.append(row)
            b = load_wu_binding(q)
            coverage.append({'query_id': q, 'success': bool(row['task_success']),
                'original_questionnaire_items': len(b.questionnaire_keys),
                'mock_authority_items': len(b.permission_keys),
                'manual_extension_items': len(b.extensions)})
            event_rows.append({'query_id': q, 'answer_source': 'explicit_fixture', 'ledger': r.ledger_events,
                               'monitor': r.monitor_events, 'controller': r.controller_trace,
                               'message_costs': s.message_cost_events, 'checkpoints': s.checkpoint_events,
                               'gate_events': s.gate.events, 'terminal_gates': s.terminal_active_gate_keys})
        checks, lifecycle_rows = lifecycle_checks()
    after = dependency_inventory(ROOT.parent)
    summary = {'protocol': PERMISSION_SCHEMA, 'metrics_schema': METRICS_SCHEMA, 'persist_rounds': config.persist_rounds,
        'coverage_tasks': len(rows), 'coverage_successes': sum(r['task_success'] for r in rows),
        'answer_source': 'explicit_fixture', 'planner': 'scripted', 'policy': 'history_scope_rule_four_actions',
        'training': False, 'optimizer_steps': 0, 'network_attempts': guard.attempts,
        'dependencies_unchanged': before == after, 'lifecycle_checks': checks,
        'metrics': rows, 'lifecycle_metrics': lifecycle_rows,
        'evidence_boundary': 'Functional dataflow only; no learning benefit, business quality or human validity conclusion.'}
    passed = (summary['coverage_successes'] == 65 and before == after and guard.attempts == 0
              and all(c['passed'] for c in checks) and all(r['ledger_replay_verified'] and r['monitor_audit_verified'] for r in rows))
    output.mkdir(parents=True)
    for name, data in (('summary.json', summary), ('query_coverage.json', coverage),
        ('test_status.json', {'functional_acceptance': 'passed' if passed else 'failed',
          'torch': 'not_executed', 'api': 'not_executed', 'manual_extensions': sum(x['manual_extension_items'] for x in coverage)})):
        with (output/name).open('x', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    with (output/'events.jsonl').open('x', encoding='utf-8') as f:
        for row in event_rows: f.write(json.dumps(contract_json_round_trip(row), ensure_ascii=False)+'\n')
    print(json.dumps({k: summary[k] for k in ('coverage_tasks', 'coverage_successes', 'network_attempts', 'optimizer_steps', 'dependencies_unchanged', 'lifecycle_checks')}))
    return 0 if passed else 1


if __name__ == '__main__': raise SystemExit(main())
