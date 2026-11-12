"""Deterministic local functionality run; no LLM, S-QSTN, torch or API calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

# Local entry point uses only the independent package; no RL installation needed.
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'rl_agent_structure/src'))

from personal_assistant.contracts.permission import PermissionChoice, contract_json_round_trip
from personal_assistant.interaction.human_channel import HumanReply, LocalHumanChannel
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from personal_assistant.execution.runner import AgentSession
from .sources import SOURCE_FILE, query_ids
from .tasks import build_wu_task
from .runtime import ReadWriteRuntime


def run(output: Path, ids: tuple[int, ...]) -> dict:
    output = output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError('keep results outside the mock_tools source directory')
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('query selection must be nonempty and unique')
    tasks = [build_wu_task(query_id) for query_id in ids]
    output.mkdir(parents=True, exist_ok=False)
    summaries, coverage = [], []
    for task in tasks:
        channel = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', PermissionChoice.ALLOW_REUSE))
        result = AgentSession(task, ScriptedPlanner(fixture_decisions(task)), channel=channel,
                              tools=ReadWriteRuntime(), max_planner_turns=24, max_control_steps=80).run()
        (output / f'{task.scenario_id}.json').write_text(
            json.dumps(contract_json_round_trip(result), ensure_ascii=False, indent=2), encoding='utf-8')
        summaries.append({'query_id': task.oracle.query_id, 'status': result.status,
                          'dataflow_complete': result.oracle_result['dataflow_complete'],
                          'human_prompts': result.prompts_used, 'escalations': result.escalations_used,
                          'error': result.error, 'privacy_proxy': result.oracle_result['privacy_proxy'],
                          'ledger_verified': result.ledger_replay_verified,
                          'monitor_verified': result.monitor_audit_verified})
        coverage.append({'query_id': task.oracle.query_id,
                         'original_source': contract_json_round_trip(task.oracle.source),
                         'authored_extensions': list(task.oracle.extensions),
                         'omitted_source_data': list(task.oracle.omitted_source_data),
                         'steps': [{'step_id': step.step_id, 'tool': step.operation_scopes[0].tool,
                                    'operation_alias': step.operation_scopes[0].operation,
                                    'direction': task.tool_models[step.step_id]['direction'],
                                    'required_fields': list(step.operation_scopes[0].data_attributes),
                                    'broad_fields': list(step.operation_scopes[-1].data_attributes)}
                                   for step in task.steps]})
    summary = {'evaluation': 'wu_minimal_dataflow_functionality', 'queries': summaries,
               'query_count': len(tasks), 'passed': sum(row['dataflow_complete'] for row in summaries),
               'third_party_tools': sorted({s.operation_scopes[0].tool for t in tasks for s in t.steps} - {'mira'}),
               'api_calls': 0, 'training_steps': 0,
               'planner': 'ScriptedPlanner', 'policy': 'LeastScopeRulePolicy',
               'human': 'fixed ALLOW_REUSE fixture; S-QSTN not invoked',
               'source_sha256': hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest(),
               'business_answer_quality_evaluated': False,
               'boundary': 'Only minimal read/write flow completion, not real task-answer quality or learned-policy performance.'}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--all', action='store_true')
    selection.add_argument('--query-id', type=int, choices=range(65))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    summary = run(args.output, query_ids() if args.all else (args.query_id,))
    print(json.dumps({k: summary[k] for k in ('query_count', 'passed', 'api_calls', 'training_steps')}))
    return 0 if summary['passed'] == summary['query_count'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
