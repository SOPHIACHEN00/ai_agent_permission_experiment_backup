"""Preview a S-QSTN prompt offline, or explicitly send one paid request."""
import argparse
import json
from pathlib import Path

from sqstn import RetrievalSimulator
from sqstn.retrieval.calibration import PROFILES

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-items', action='store_true', help='List all supported Wu situations; no API call')
    parser.add_argument('--query-id', type=int)
    parser.add_argument('--tool')
    parser.add_argument('--data-item')
    parser.add_argument('--profile', choices=PROFILES, help='Otherwise assign a persona with the frozen mixture')
    parser.add_argument('--sample-id', default='0', help='Stable synthetic-user/sampling identifier')
    parser.add_argument('--output', type=Path, help='Prompt JSON path; default outputs/prompt.json')
    parser.add_argument('--send', action='store_true', help='Make ONE PAID OpenRouter call, using the existing cumulative ledger')
    args = parser.parse_args()
    sim = RetrievalSimulator(ROOT)
    if args.list_items:
        if args.send:
            parser.error('--list-items and --send cannot be combined')
        print(json.dumps(sim.items(), ensure_ascii=False, indent=2))
        return 0
    fields = (args.query_id is not None, args.tool is not None, args.data_item is not None)
    if any(fields) and not all(fields):
        parser.error('Supply --query-id, --tool and --data-item together')
    item = (dict(query_id=args.query_id, tool=args.tool, data_item=args.data_item)
            if all(fields) else sim.items()[0])
    profile = args.profile or sim.profile_for(args.sample_id)
    compiled = sim.compile(profile, **item, sample_id=args.sample_id)
    output = args.output or ROOT / 'outputs/prompt.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = dict(item=item, profile=profile, prompt_file=str(output.resolve()), paid_call=args.send)
    if args.send:
        from sqstn.client import respond
        result = respond(compiled, ROOT)
        summary.update(status=result['status'], answer=result['answer'],
                       failed_calls=int(result['status'] != 'ok'), job_id=result['job_id'])
        if result.get('error'):
            summary['error'] = result['error']
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return int(args.send and summary.get('status') != 'ok')


if __name__ == '__main__':
    raise SystemExit(main())
