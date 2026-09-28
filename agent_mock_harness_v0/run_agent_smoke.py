"""Run one synthetic query-22 task-agent smoke without any real tool effects."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Callable, Sequence

from pa_rl.contracts import PermissionChoice

from .agent_openai import BudgetedChatTransport, OpenAIPlanner
from .agent_runner import ExactAskPolicy, run_report_episode


def _save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main(
    argv: Sequence[str] | None = None, *,
    transport_factory: Callable[[Path], BudgetedChatTransport] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory for this one-shot run")
    arguments = parser.parse_args(argv)
    output = arguments.output.resolve()
    if output.exists():
        print("Output directory already exists; refusing to overwrite or resume.", file=sys.stderr)
        return 2
    if transport_factory is None and not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is missing; no online call was attempted.", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=False)
    transport = (
        BudgetedChatTransport(output) if transport_factory is None else transport_factory(output)
    )
    result = run_report_episode(
        OpenAIPlanner(transport), ExactAskPolicy(),
        lambda scope, step: PermissionChoice.ALLOW_ONCE, max_turns=8,
    )
    mode = "live_openai" if transport_factory is None else "offline_fake_transport"
    summary = {
        "mode": mode, "scenario_id": "wu_query_22_agent", "status": result.status,
        "oracle_success": result.oracle_success, "final_answer": result.final_answer,
        "prompt_count": result.prompt_count, "registry_version": result.registry_version,
        "outbox_count": len(result.outbox), "reads": result.reads,
        "audit_valid": result.audit_valid, "ledger_replay_valid": result.ledger_replay_valid,
        "transport": transport.summary(),
    }
    _save(output / "summary.json", summary)
    _save(output / "public_trace.json", result.public_trace)
    print(json.dumps({"output": str(output), "status": result.status,
                      "oracle_success": result.oracle_success,
                      "estimated_cost_usd": transport.summary()["estimated_cost_usd"]},
                     ensure_ascii=False))
    return 0 if result.oracle_success and result.audit_valid and result.ledger_replay_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
