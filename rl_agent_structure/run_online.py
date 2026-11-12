"""Preview by default; --execute enables paid Planner and S-QSTN API requests."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent)]

from personal_assistant.integration.online import OpenRouterTransport, load_client, load_policy, run_queries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queries', type=int, nargs='+', required=True, choices=range(65))
    parser.add_argument('--user-id', required=True, help='Must match the user in a DDQN checkpoint')
    parser.add_argument('--profile', choices=('persistent_granters', 'reconsent_seekers', 'broad_restrictors'),
                        default='persistent_granters')
    parser.add_argument('--persist-rounds', type=int, required=True)
    parser.add_argument('--policy', choices=('ddqn', 'rule'), default='ddqn',
                        help='DDQN by default; rule is an explicitly selected baseline')
    parser.add_argument('--checkpoint', type=Path,
                        help='Existing compatible user-local DDQN checkpoint; required for DDQN execution')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--max-model-calls', type=int, default=32, help='Combined Planner + S-QSTN request-attempt cap')
    parser.add_argument('--output', type=Path, help='New directory under rl_agent_structure/outputs')
    parser.add_argument('--execute', action='store_true', help='Enable paid API requests; no DDQN updates')
    args = parser.parse_args(argv)
    if args.persist_rounds < 1 or args.max_model_calls < 1 or not args.user_id.strip():
        parser.error('persist-rounds and max-model-calls must be positive; user-id must be nonempty')
    if args.policy == 'rule' and args.checkpoint is not None:
        parser.error('--policy rule does not use a checkpoint')
    if args.execute and args.policy == 'ddqn' and args.checkpoint is None:
        parser.error('DDQN is the default controller: --execute requires --checkpoint and its matching --user-id; '
                     'use --policy rule only to explicitly run the rule baseline')
    if args.checkpoint is not None and not args.checkpoint.is_file():
        parser.error('Checkpoint file does not exist')
    sqstn_root = ROOT.parent / 's-qstn'
    preview = {'mode': 'api_inference' if args.execute else 'preview', 'queries': args.queries,
               'user_id': args.user_id, 'profile': args.profile, 'policy': args.policy,
               'persist_rounds': args.persist_rounds, 'max_model_calls': args.max_model_calls,
               'checkpoint': None if args.checkpoint is None else str(args.checkpoint),
               'checkpoint_required_for_execution': args.policy == 'ddqn',
               'env_file': str(args.env_file), 'budget_file': str(sqstn_root / 'state/budget.json'),
               'training': False, 'paid_requests_enabled': args.execute}
    if not args.execute:
        print(json.dumps(preview, indent=2))
        return 0
    if args.output is None:
        parser.error('--execute requires --output to preserve call and task evidence')
    output = args.output.resolve()
    output_root = (ROOT / 'outputs').resolve()
    if not output.is_relative_to(output_root) or output == output_root or output.exists():
        parser.error('--output must be a new subdirectory of rl_agent_structure/outputs')
    # All local validation precedes the first possible paid call.
    client = load_client(sqstn_root)
    key = client.load_api_key(sqstn_root, args.env_file)
    if not (sqstn_root / 'state/budget.json').is_file():
        parser.error('Missing budget ledger. For a new campaign only: python s-qstn/run.py --init-budget')
    policy = load_policy(args.policy, user_id=args.user_id, checkpoint=args.checkpoint)
    transport = OpenRouterTransport(sqstn_root, key, max_model_calls=args.max_model_calls)
    output.mkdir(parents=True)
    (output / 'config.json').write_text(json.dumps(preview, indent=2) + '\n', encoding='utf-8')
    report = run_queries(args.queries, user_id=args.user_id, profile=args.profile,
                         persist_rounds=args.persist_rounds, sqstn_root=sqstn_root,
                         transport=transport, policy=policy)
    (output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'summary': str(output / 'summary.json'),
                      'statuses': [task['status'] for task in report['tasks']],
                      'model_request_attempts': transport.attempts, 'optimizer_updates': 0}, indent=2))
    return int(len(report['tasks']) != len(args.queries) or any(
        task['status'] != 'completed' or task['integrity_failures']
        or not task['result']['ledger_replay_verified'] or not task['result']['monitor_audit_verified']
        for task in report['tasks']))


if __name__ == '__main__':
    raise SystemExit(main())
