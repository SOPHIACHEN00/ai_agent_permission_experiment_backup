"""CLI for mechanical offline probes or one bounded synthetic OpenAI session."""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from pa_rl.contracts import ControllerAction as A, PermissionChoice, contract_json_round_trip
from agent_mock_harness_v0.agent_openai import _write_json
from .dataset_catalog import load_dataset_catalog
from .human_channel import HumanReply, LocalHumanChannel
from .llm import StructuredChatTransport
from .planner import ScriptedPlanner, StructuredOpenAIPlanner, fixture_decisions
from .runner import AgentSession
from .scenarios import adaptive_read_task, q22_report_share


def fixture_responder(message):
    if message.kind == 'escalation':
        return HumanReply(message.message_id, 'clarification', text='Continue the synthetic task with the next declared scope.')
    return HumanReply(message.message_id, 'permission', PermissionChoice.ALLOW_REUSE)


class LifecycleFixturePolicy:
    """Hand-authored six-action wiring probe; absolutely not learned behavior."""
    def __init__(self):
        self._specs = iter([(A.REQUEST_AUTHORIZATION, ('private_notes', 'title')),
            (A.REQUEST_REFRESH, ('title',)), (A.EXECUTE_WITH_AUTHORIZATION, ('title',)),
            (A.DISABLE_LOCAL_AUTHORIZATION, None), (A.ESCALATE, None), (A.DENY_WITH_REASON, None),
            (A.REQUEST_AUTHORIZATION, ('private_notes', 'title')),
            (A.EXECUTE_WITH_AUTHORIZATION, ('private_notes', 'title'))])

    def choose(self, view):
        action, fields = next(self._specs)
        return next(c.candidate_id for c in view.candidates if c.valid and c.action == action and
                    (fields is None or (c.operation_scope or c.request_scope).data_attributes == fields))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['q22', 'adaptive'], default='q22')
    parser.add_argument('--planner', choices=['offline', 'openai'], default='offline')
    parser.add_argument('--policy', choices=['rule', 'lifecycle-fixture', 'ddqn'], default='rule')
    parser.add_argument('--checkpoint', type=Path, help='New Agent DDQN inference checkpoint; never Family3 weights')
    parser.add_argument('--device', default='auto')
    parser.add_argument('--interruption-budget', type=int, default=3)
    parser.add_argument('--exposure-budget', type=int, default=20)
    parser.add_argument('--output', type=Path, required=True, help='New local directory; never overwrites an existing run')
    parser.add_argument('--export-catalog', action='store_true')
    args = parser.parse_args(argv)
    if args.policy == 'lifecycle-fixture' and (args.scenario != 'adaptive' or args.planner != 'offline'):
        parser.error('lifecycle fixture uses adaptive scenario + offline planner only')
    if args.policy == 'ddqn' and args.checkpoint is None:
        parser.error('--policy ddqn requires --checkpoint')
    if args.policy != 'ddqn' and args.checkpoint is not None:
        parser.error('--checkpoint is only valid with --policy ddqn')
    args.output.mkdir(parents=True, exist_ok=False)
    task = q22_report_share() if args.scenario == 'q22' else adaptive_read_task()
    transport = None
    if args.planner == 'openai':
        transport = StructuredChatTransport(args.output)
        planner = StructuredOpenAIPlanner(transport)
    else:
        decisions = fixture_decisions(task)
        if args.policy == 'lifecycle-fixture':
            decisions = [decisions[0], decisions[1], decisions[1], decisions[1], decisions[2]]
        planner = ScriptedPlanner(decisions)
        if args.policy == 'ddqn' and args.scenario == 'adaptive':
            from .learning_scenarios import ReactiveReadPlanner
            planner = ReactiveReadPlanner()
    policy = LifecycleFixturePolicy() if args.policy == 'lifecycle-fixture' else None
    learning_end = None
    if args.policy == 'ddqn':
        from .learning_checkpoints import load_checkpoint
        from .learning_contracts import EpisodeConfig, EpisodeEnd
        from .learning_environment import AgentLearningEnvironment
        from .learning_rollout import drive_episode, episode_metrics
        policy = load_checkpoint(args.checkpoint, device=args.device)
        policy.evaluation_context = task.scenario_id
        # Keep the existing live API-call cap (8); offline staged reads allow 32.
        session = AgentSession(task, planner, channel=LocalHumanChannel(fixture_responder),
                               max_planner_turns=8 if args.planner == 'openai' else 32)
        environment = AgentLearningEnvironment(session, EpisodeConfig(args.interruption_budget, args.exposure_budget))
        learning_end = drive_episode(environment, policy)
        result = learning_end.result
        if isinstance(learning_end, EpisodeEnd):
            _write_json(args.output / 'learning_metrics.json', episode_metrics(learning_end))
        _write_json(args.output / 'exposure_events.json', environment.exposure.snapshot())
    else:
        result = AgentSession(task, planner, policy, LocalHumanChannel(fixture_responder)).run()
    _write_json(args.output / 'result.json', contract_json_round_trip(result))
    summary = {'scenario_id': task.scenario_id, 'planner': args.planner, 'policy': args.policy,
        'status': result.status, 'oracle': result.oracle_result,
        'planner_turns': result.planner_turns, 'controller_steps': result.controller_steps,
        'permission_prompts': result.prompts_used, 'escalations': result.escalations_used,
        'actions_seen': sorted({x['selected']['action'] for x in result.controller_trace}),
        'ledger_replay_verified': result.ledger_replay_verified, 'monitor_audit_verified': result.monitor_audit_verified,
        'all_tools_are_local_mocks': True, 'human_answers': 'fixed synthetic fixture; not Wu/S-QSTN preference predictions',
        'trained_rl_policy': False, 'error_type': result.error}
    if args.policy == 'ddqn':
        summary.update(ddqn_checkpoint=str(args.checkpoint), ddqn_feature_schema=policy.schema_version,
            device=str(policy.learner.device), trained_rl_policy=policy.checkpoint_metadata['optimizer_steps'] > 0,
            frozen_evaluation=True, constrained_reward=getattr(learning_end, 'reward', None))
    if transport is not None:
        summary['api_budget'] = transport.summary()
    _write_json(args.output / 'summary.json', summary)
    if args.export_catalog:
        _write_json(args.output / 'dataset_catalog.json', load_dataset_catalog().to_dict())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.status == 'completed' else 1


if __name__ == '__main__':
    sys.exit(main())
