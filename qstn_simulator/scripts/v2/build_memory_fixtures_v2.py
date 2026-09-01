"""Build deterministic, label-free memory fixtures for S-QSTN v2.0.

These fixtures are engineering diagnostics for event boundaries and retention.
They are not human behavior data, calibration labels, or claims about human
forgetting durations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "s_qstn_v2" / "memory_fixtures_v2.json"


def _event(
    event_id: str,
    subject_id: str,
    event_type: str,
    turn_index: int,
    *,
    verification_status: str = "verified",
    source: str = "synthetic_oracle",
    retention_class: str | None = None,
    scope: str = "fixture_scope",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "subject_id": subject_id,
        "event_type": event_type,
        "turn_index": turn_index,
        "event_time": f"fixture-turn-{turn_index}",
        "source": source,
        "verification_status": verification_status,
        "scope": scope,
        "metadata": metadata or {},
    }
    if retention_class is not None:
        payload["retention_class"] = retention_class
    return payload


def build_fixtures() -> dict[str, Any]:
    return {
        "fixture_set_id": "s_qstn_rulepack_v2_memory_diagnostic_v1",
        "version": "2.0.0",
        "purpose": "Label-free deterministic diagnostics for bounded memory and categorical state transitions.",
        "human_calibration": "not_claimed",
        "fixtures": [
            {
                "fixture_id": "verified_scope_violation_visible",
                "subject_id": "fixture_scope_violation",
                "current_turn": 2,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_scope_violation_1",
                        "fixture_scope_violation",
                        "verified_scope_violation",
                        1,
                        scope="calendar_scope",
                        metadata={"trust_dimension": "integrity"},
                    )
                ],
            },
            {
                "fixture_id": "verified_repair_recovery",
                "subject_id": "fixture_repair_recovery",
                "current_turn": 3,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_verified_error_1",
                        "fixture_repair_recovery",
                        "verified_agent_error",
                        1,
                        scope="assistant_scope",
                        metadata={"trust_dimension": "integrity"},
                    ),
                    _event(
                        "event_repair_completed_1",
                        "fixture_repair_recovery",
                        "repair_completed",
                        2,
                        scope="assistant_scope",
                        metadata={"trust_dimension": "integrity"},
                    ),
                ],
            },
            {
                "fixture_id": "explicit_prompt_burden",
                "subject_id": "fixture_prompt_burden",
                "current_turn": 2,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_prompt_interruption_1",
                        "fixture_prompt_burden",
                        "prompt_interruption",
                        1,
                        metadata={"burden_bucket": "high_explicit"},
                    )
                ],
            },
            {
                "fixture_id": "recent_event_expired_from_view",
                "subject_id": "fixture_expired_event",
                "current_turn": 5,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_recent_request_1",
                        "fixture_expired_event",
                        "permission_request_presented",
                        1,
                        metadata={"burden_bucket": "low_explicit"},
                    )
                ],
            },
            {
                "fixture_id": "ordinary_denial_is_not_violation",
                "subject_id": "fixture_ordinary_denial",
                "current_turn": 1,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_permission_denial_1",
                        "fixture_ordinary_denial",
                        "permission_response_recorded",
                        1,
                        metadata={"answer": "No, never share"},
                    )
                ],
            },
            {
                "fixture_id": "unverified_event_remains_unknown",
                "subject_id": "fixture_unverified_event",
                "current_turn": 1,
                "memory_horizon_turns": 3,
                "memory_horizon_source": "synthetic_fixture_only",
                "events": [
                    _event(
                        "event_unverified_error_1",
                        "fixture_unverified_event",
                        "verified_agent_error",
                        1,
                        verification_status="unverified",
                        source="unknown",
                        scope="assistant_scope",
                        metadata={"trust_dimension": "integrity"},
                    )
                ],
            },
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_fixtures()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "compiled", "fixture_count": len(payload["fixtures"]), "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
