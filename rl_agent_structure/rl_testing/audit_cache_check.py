"""Independent no-learning equivalence and timing check for replay memoization."""
from __future__ import annotations

import time

from personal_assistant.config import PermissionConfig, RuntimeLimits
from personal_assistant.execution.user_session import UserSession
from rl_testing.online_check import QUERIES, annotate_counts, _user_digest
from rl_testing.records import RunLog, json_write
from rl_testing.runner import RuleSelection, run_sequence


def audit_cache_check(config, output, *, deadline):
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for mode in ('full', 'cache'):
        branch = output / mode
        branch.mkdir()
        log = RunLog(config, branch)
        user = UserSession(config.user_id, PermissionConfig(config.persist_rounds),
                           run_id='audit-equivalence', runtime_limits=RuntimeLimits(**config.runtime_limits))
        user.ledger.set_replay_cache_enabled(mode == 'cache')
        start = time.perf_counter()
        result = run_sequence(config, RuleSelection(), log, queries=QUERIES, training=False,
                              case_id='audit-equivalence', user_context=user, deadline=deadline)
        elapsed = time.perf_counter() - start
        annotate_counts(log)
        summary = {'mode': mode, 'task_count': len(log.tasks), 'elapsed_seconds': elapsed,
                   'ledger_digest': _user_digest(user), 'verification_stats': dict(user.ledger.replay_verification_stats)}
        log.save(summary)
        results[mode] = (result, log, summary)
    full, cached = results['full'], results['cache']
    equality = {'task_rows': full[1].tasks == cached[1].tasks,
                'decisions': full[1].decisions == cached[1].decisions,
                'ledger_and_history': _user_digest(full[0].user) == _user_digest(cached[0].user)}
    if not all(equality.values()):
        raise RuntimeError('cached and full audit execution differ; no learning comparison allowed')
    ledger = cached[0].user.ledger
    # Same completed ledger, repeated ABBA order, with both paths warmed first.
    assert ledger.verify_replay(cache=False) and ledger.verify_replay(cache=True)
    timings = []
    for mode in ('full', 'cache', 'cache', 'full'):
        start = time.perf_counter()
        for _ in range(10):
            if time.monotonic() >= deadline:
                raise TimeoutError('audit timing deadline')
            if not ledger.verify_replay(cache=mode == 'cache'):
                raise RuntimeError('fixed-ledger audit failed')
        timings.append({'mode': mode, 'calls': 10, 'seconds': time.perf_counter() - start})
    total = {mode: sum(row['seconds'] for row in timings if row['mode'] == mode) for mode in ('full', 'cache')}
    summary = {'status': 'passed', 'task_count': 6, 'equivalence': equality,
               'execution_timings': {m: r[2]['elapsed_seconds'] for m, r in results.items()},
               'fixed_ledger_event_count': len(ledger.events()), 'timing_batches': timings,
               'fixed_ledger_seconds': total, 'fixed_ledger_speedup': total['full'] / total['cache'],
               'verification_stats': {m: r[2]['verification_stats'] for m, r in results.items()},
               'limits': 'Single fixed synthetic history; timing is not a universal speedup claim.'}
    json_write(output / 'summary.json', summary)
    return summary
