"""Portable factual user context reconstructed from the fixed training report.

Replays actual consent commands and copies observed answers. It never issues
new consent, renews lifetimes, copies active task gates, or restores a policy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from personal_assistant.config import PermissionConfig, RuntimeLimits
from personal_assistant.contracts.permission import (
    AuthorizationStatus, PermissionChoice, canonical_hash, contract_json_round_trip, freeze_value,
)
from personal_assistant.execution.user_session import UserSession
from personal_assistant.interaction.history import ObservedAnswer
from personal_assistant.permissions.ledger_events import LedgerEvent, key_data, key_from
from personal_assistant.permissions.persistent_ledger import UserAuthorizationLedger

SCHEMA = "rl_testing.fixed_history_snapshot.v1"
QUERIES = (40, 41, 55) * 20
FIELDS = {"schema", "user_id", "run_id", "persist_rounds", "runtime_limits", "source",
          "source_report_sha256", "ledger_events", "observed_answers", "position", "digest",
          "snapshot_hash"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(user: UserSession) -> str:
    """Same factual context definition as online_check._user_digest."""
    return canonical_hash(contract_json_round_trip({
        "position": user.position, "history": user.history.view(),
        "consent_records": user.ledger.records(), "consent_events": user.ledger.events(),
    }))


def _answers(events: tuple[LedgerEvent, ...], user_id: str) -> list[ObservedAnswer]:
    answers, seen = [], set()
    query_id = None
    for event in events:
        if event.kind == "begin_task":
            query_id = event.payload["query_id"]
        elif event.kind == "answer":
            payload = event.payload
            _require(query_id is not None and payload["response_id"] not in seen,
                     "duplicate or unbound observed answer")
            answer = ObservedAnswer(user_id, query_id, key_from(payload["key"]),
                                    PermissionChoice(payload["choice"]), payload["response_id"],
                                    len(answers) + 1, source="explicit_fixture")
            answers.append(answer)
            seen.add(answer.response_id)
    return answers


def _answer_json(answer: ObservedAnswer) -> dict:
    return {"user_id": answer.user_id, "query_id": answer.query_id,
            "key": key_data(answer.key), "choice": answer.choice.value,
            "response_id": answer.response_id, "event_index": answer.event_index,
            "source": answer.source}


def _restore(events_data: list[dict], user_id: str, persist_rounds: int,
             runtime_limits: dict, run_id: str) -> UserSession:
    _require(isinstance(events_data, list) and bool(events_data), "missing ledger events")
    events = tuple(LedgerEvent(sequence=e["sequence"], kind=e["kind"],
                               payload=freeze_value(e["payload"]),
                               previous_hash=e["previous_hash"], event_hash=e["event_hash"])
                   for e in events_data)
    _require(events[0].kind == "init" and events[-1].kind == "finish_task", "unclosed ledger")
    _require(sum(e.kind == "init" for e in events) == 1, "multiple ledger initializations")
    _require(events[0].payload["user_id"] == user_id
             and events[0].payload["persist_rounds"] == persist_rounds,
             "snapshot consent configuration mismatch")
    begins = [e.payload for e in events if e.kind == "begin_task"]
    _require(tuple(e["query_id"] for e in begins) == QUERIES, "wrong task sequence")
    _require(len({e["task_id"] for e in begins}) == 60
             and sum(e.kind == "finish_task" for e in events) == 60,
             "incomplete or duplicate task stream")
    # This invokes the original hash-chain checks and authority transitions.
    ledger = UserAuthorizationLedger.replay(events)
    user = UserSession(user_id, PermissionConfig(persist_rounds), run_id=run_id,
                       runtime_limits=RuntimeLimits(**runtime_limits))
    user.ledger = ledger
    for answer in _answers(events, user_id):
        user.history.append(answer)
    _require(user.position is not None and user.position.round_index == 60,
             "wrong final task position")
    return user


def snapshot_from_report(path: Path | str) -> dict:
    """Extract the predeclared seed-3 candidate state after exactly 60 tasks."""
    raw = Path(path).read_bytes()
    report = json.loads(raw)
    config, tasks = report["config"], report["tasks"]
    _require(config["seed"] == 3 and config["exploration"] == "candidate"
             and config["fixture_answer"] == "allow_reuse", "wrong fixed source report")
    _require(tuple(t["query_id"] for t in tasks) == QUERIES, "wrong source task sequence")
    user_id, persist = config["user_id"], config["persist_rounds"]
    run_id = f"{user_id}:3:training"
    events, decisions = [], 0
    for index, task in enumerate(tasks, 1):
        _require(task["user_id"] == user_id and task["seed"] == 3
                 and task["round"] == index and task["task_index"] == index,
                 "foreign or reordered task")
        _require(task["answer_source"] == "explicit_fixture"
                 and not task.get("integrity_failures"), "unverified human answer source")
        metrics = task["metrics"]
        _require(metrics["task_success"] + metrics["task_failure"] == 1
                 and metrics["authorization_evidence_complete"] is True
                 and metrics["ledger_replay_verified"] is True
                 and metrics["monitor_audit_verified"] is True,
                 "unfinished or unverified task")
        segment = task["consent_events"]
        _require(segment and segment[-1]["kind"] == "finish_task", "unfinished task segment")
        begin = [e for e in segment if e["kind"] == "begin_task"]
        _require(len(begin) == 1 and begin[0]["payload"] == {
            "query_id": task["query_id"], "task_id": task["task_id"]},
            "task metadata differs from ledger")
        events.extend(segment)
        decisions += metrics["decisions"]
    user = _restore(events, user_id, persist, config["runtime_limits"], run_id)
    _require(user.position.task_id == tasks[-1]["task_id"]
             and user.position.decision_index == decisions, "source final position mismatch")
    active = sum(r.status == AuthorizationStatus.ACTIVE and r.allows
                 and r.expires_at_round > user.position.round_index for r in user.ledger.records())
    _require(active == tasks[-1]["metrics"]["active_consent_items_after_task"],
             "source final consent count mismatch")
    snapshot = {"schema": SCHEMA, "user_id": user_id, "run_id": run_id,
                "persist_rounds": persist, "runtime_limits": config["runtime_limits"],
                "source": {"seed": 3, "arm": "candidate", "completed_tasks": 60,
                           "query_sequence": list(QUERIES)},
                "source_report_sha256": hashlib.sha256(raw).hexdigest(),
                "ledger_events": contract_json_round_trip(user.ledger.events()),
                "observed_answers": [_answer_json(a) for a in user.history.view()],
                "position": contract_json_round_trip(user.position), "digest": _digest(user)}
    snapshot["snapshot_hash"] = canonical_hash(snapshot)
    return snapshot


def user_from_snapshot(snapshot: dict) -> UserSession:
    """Return an independent user at the original clock, with no active gates."""
    _require(isinstance(snapshot, dict) and set(snapshot) == FIELDS, "invalid snapshot fields")
    copied = contract_json_round_trip(snapshot)
    claimed_hash = copied.pop("snapshot_hash")
    _require(canonical_hash(copied) == claimed_hash, "snapshot hash mismatch")
    _require(copied["schema"] == SCHEMA, "unsupported history snapshot")
    _require(copied["source"] == {"seed": 3, "arm": "candidate", "completed_tasks": 60,
                                 "query_sequence": list(QUERIES)}, "wrong fixed source metadata")
    _require(isinstance(copied["source_report_sha256"], str)
             and re.fullmatch(r"[0-9a-f]{64}", copied["source_report_sha256"]) is not None,
             "invalid source report digest")
    _require(copied["run_id"] == f"{copied['user_id']}:3:training", "wrong source run identity")
    user = _restore(copied["ledger_events"], copied["user_id"], copied["persist_rounds"],
                    copied["runtime_limits"], copied["run_id"])
    _require([_answer_json(a) for a in user.history.view()] == copied["observed_answers"],
             "history differs from actual ledger answers")
    _require(contract_json_round_trip(user.position) == copied["position"],
             "snapshot position mismatch")
    _require(_digest(user) == copied["digest"], "snapshot factual state mismatch")
    return user
