"""Frozen 20-person S-QSTN/o4-mini answers with paired Gemini 0/4-shot prediction.

Default invocation prepares local artifacts only. --execute permits API calls.
Every request is reserved in a durable cost ledger before dispatch; successful
answers are reused on resume, and failed attempts require --retry-errors.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from dotenv import dotenv_values
from openai import OpenAI

HERE = Path(__file__).resolve().parent
IC_DIR = HERE.parent
PROJECT = IC_DIR.parent
sys.path.insert(0, str(IC_DIR))
sys.path.insert(0, str(IC_DIR / "multi_model_screening"))
from run_ic_four_label import (  # noqa: E402
    ID_TO_LABEL, build_prompt, file_sha256, load_inputs, make_bundles,
    parse_response, save_json,
)
from screen_models import MODEL_SPECS, completion_for_job, usage_record  # noqa: E402
from sqstn_backend import SQSTNBackend, parse_answer  # noqa: E402

SOURCE_RUN = IC_DIR / "multi_model_screening/artifacts/screen_40_seed20260925_4shot_8k_low"
PUBLIC_PROVENANCE = IC_DIR / "multi_model_screening/artifacts/full_201_gemini_4shot_fold0_seed20260925_8k_low/public_data_provenance.json"
DATA = PROJECT / "data/processed/four_label_dataset.csv"
RAW = PROJECT / "external/ai-agent-permissions/data/user_study.json"
ENV_FILE = PROJECT / "qstn_simulator/.env"
PERSONAS = PROJECT / "qstn_simulator/outputs/empirical_personas_v2/personas_with_empirical_profiles.csv"
DEFAULT_OUT = HERE / "artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1"
QUOTAS = {"broad_restrictors": 3, "persistent_granters": 7, "reconsent_seekers": 10}
GENERATOR_MODEL = "o4-mini"
GENERATOR_MAX_TOKENS = 4096
PREDICTOR_MAX_TOKENS = 8000
PRICES = {"input": 1.10, "cached_input": 0.275, "output": 4.40}
# Exact JSONSingleResponseGenerationMethod schema from installed QSTN 0.5.1.
# Keep the API format separate from the questionnaire text, as QSTN does.
GENERATOR_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "json_schema",
        "schema": {
            "$defs": {"Answer": {"enum": list(ID_TO_LABEL.values()), "title": "Answer", "type": "string"}},
            "additionalProperties": False,
            "properties": {"answer": {"$ref": "#/$defs/Answer"}},
            "required": ["answer"], "title": "StructuredOutput", "type": "object",
        },
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def frozen_json(path: Path, value: Any) -> None:
    if path.exists():
        if read_json(path) != value:
            raise ValueError(f"Frozen artifact differs: {path.name}")
    else:
        save_json(path, value)


def frozen_csv(path: Path, frame: pd.DataFrame) -> None:
    text = frame.to_csv(index=False, lineterminator="\n")
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Frozen table differs: {path.name}")
    else:
        path.write_text(text, encoding="utf-8")


def reserve(messages: list[dict[str, str]], stage: str) -> float:
    # UTF-8 bytes bound token count conservatively; allow message/JSON overhead.
    input_bound = sum(len(m["content"].encode("utf-8")) for m in messages) + 1024
    if stage == "generator":
        return (input_bound * PRICES["input"] + GENERATOR_MAX_TOKENS * PRICES["output"]) / 1e6
    spec = MODEL_SPECS["gemini"]
    return (input_bound * spec.max_input_usd_per_million + PREDICTOR_MAX_TOKENS * spec.max_output_usd_per_million) / 1e6


def select_participants() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    jobs = read_json(SOURCE_RUN / "job_manifest.json")
    personas = pd.read_csv(PERSONAS, keep_default_na=False)
    if personas["participant_id"].duplicated().any():
        raise ValueError("Persona participant IDs are not unique")
    lookup = personas.set_index("participant_id")
    source_ids = {job["participant_id"] for job in jobs}
    rng = np.random.default_rng(20260926)
    chosen: list[str] = []
    for profile_id in sorted(QUOTAS):
        candidates = sorted(pid for pid in source_ids if lookup.loc[pid, "profile_id"] == profile_id)
        chosen.extend(str(pid) for pid in rng.choice(candidates, QUOTAS[profile_id], replace=False))
    chosen = sorted(chosen)
    selected = sorted([job for job in jobs if job["participant_id"] in chosen], key=lambda j: j["participant_id"])
    participants = lookup.loc[chosen, ["persona_id", "profile_id"]].reset_index()
    assert len(selected) == len(participants) == 20
    for job in selected:
        assert job["fold"] == 0
        assert len(set(job["prompt_history_query_ids"])) == 4
        assert len(set(job["test_query_ids"])) == 4
        assert set(job["prompt_history_query_ids"]).issubset(job["train_query_ids"])
        assert not set(job["train_query_ids"]) & set(job["test_query_ids"])
    return participants, selected


def prepare(out: Path, cap: float) -> tuple[pd.DataFrame, dict, list[dict], list[dict]]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "calls").mkdir(exist_ok=True)
    (out / "prompts").mkdir(exist_ok=True)
    settings = dotenv_values(ENV_FILE)
    if settings.get("OPENAI_MODEL") != GENERATOR_MODEL:
        raise ValueError("Configured S-QSTN model changed; expected o4-mini")
    df, public_profiles = load_inputs(DATA, RAW)
    participants, jobs = select_participants()
    backend = SQSTNBackend(PROJECT)
    config = {
        "schema_version": 1, "purpose": "synthetic_permission_predictability_pilot",
        "generator_model": GENERATOR_MODEL, "generator_endpoint": "https://api.openai.com/v1",
        "predictor_model": MODEL_SPECS["gemini"].model_id,
        "predictor_endpoint": "https://openrouter.ai/api/v1",
        "selection_seed": 20260926, "profile_quotas": QUOTAS,
        "fold": 0, "fold_seed": 42, "source_shot_seed": 20260925,
        "conditions": [0, 4], "generator_reasoning_effort": "low",
        "generator_max_completion_tokens": GENERATOR_MAX_TOKENS,
        "generator_response_format": GENERATOR_RESPONSE_FORMAT, "generator_seed": 42,
        "predictor_reasoning_effort": "low", "predictor_max_tokens": PREDICTOR_MAX_TOKENS,
        "generator_prices_per_million_usd": PRICES,
        "generator_pricing_source": "https://developers.openai.com/api/docs/models/o4-mini",
        "max_run_cost_usd": cap, "source_run": str(SOURCE_RUN),
        "state_mode": "fresh_empty_state_per_item_no_events",
        "predictor_information": "original public profile fields; zero or four synthetic answered queries; unanswered test requests",
        "human_calibration_claimed": False,
        "hashes": {
            "dataset": file_sha256(DATA), "raw_public_profiles": file_sha256(RAW),
            "source_manifest": file_sha256(SOURCE_RUN / "job_manifest.json"),
            "public_provenance": file_sha256(PUBLIC_PROVENANCE),
            "runner": file_sha256(Path(__file__)),
            "backend": file_sha256(HERE / "sqstn_backend.py"),
            "analysis": file_sha256(HERE / "analyze_pilot.py"),
            "original_icl": file_sha256(IC_DIR / "run_ic_four_label.py"),
            "original_screen_runner": file_sha256(IC_DIR / "multi_model_screening/screen_models.py"),
        },
        "backend_assets": backend.metadata(),
        "packages": {name: importlib.metadata.version(name) for name in ("openai", "pandas", "numpy", "scikit-learn", "qstn")},
    }
    frozen_json(out / "run_config.json", config)
    frozen_json(out / "job_manifest.json", jobs)
    frozen_csv(out / "participants.csv", participants)
    frozen_json(out / "public_data_provenance.json", read_json(PUBLIC_PROVENANCE))
    generator_jobs: list[dict] = []
    for job in jobs:
        pid = job["participant_id"]
        history = set(job["prompt_history_query_ids"])
        tests = set(job["test_query_ids"])
        rows = df.loc[df["participant_id"].eq(pid) & df["query_id"].isin(history | tests)]
        assert int(rows["query_id"].isin(tests).sum()) == job["test_rows"]
        for row_index, row in rows.sort_index().iterrows():
            safe_row = row.drop(labels=["label_id", "label_text"]).to_dict()
            rendered = backend.messages_for(pid, safe_row)
            record = {
                "call_id": f"generator_{pid}_row{row_index}", "stage": "generator",
                "row_index": int(row_index), "participant_id": pid,
                "query_id": int(row["query_id"]), "tool": str(row["tool"]),
                "raw_data_type": str(row["raw_data_type"]),
                "role": "history" if int(row["query_id"]) in history else "test",
                **rendered,
            }
            record["prompt_sha256"] = digest(record["messages"])
            record["reserved_cost_usd"] = reserve(record["messages"], "generator")
            generator_jobs.append(record)
    frozen_json(out / "generator_preflight.json", generator_jobs)
    # Bound possible Gemini history labels without consulting any human answers.
    longest = max(ID_TO_LABEL.values(), key=len)
    predictor_bound = 0.0
    for job in jobs:
        user_rows = df.loc[df["participant_id"].eq(job["participant_id"])].copy()
        user_rows["label_text"] = longest
        history = user_rows.loc[user_rows["query_id"].isin(job["prompt_history_query_ids"])]
        tests = user_rows.loc[user_rows["query_id"].isin(job["test_query_ids"])]
        for shots in (0, 4):
            prompt = build_prompt(public_profiles[job["participant_id"]], make_bundles(history, True) if shots else [], make_bundles(tests, False))
            predictor_bound += reserve([{"role": "user", "content": prompt}], "predictor")
    summary = {
        "n_participants": 20, "generator_calls": len(generator_jobs),
        "history_permission_rows": sum(j["role"] == "history" for j in generator_jobs),
        "test_permission_rows": sum(j["role"] == "test" for j in generator_jobs),
        "predictor_calls": 40, "generator_worst_case_usd": sum(j["reserved_cost_usd"] for j in generator_jobs),
        "predictor_worst_case_usd": predictor_bound, "run_cap_usd": cap,
        "reservation_note": "Worst-case totals assume every response reaches its token cap; each dispatch is gated by the run budget including in-flight reservations.",
    }
    frozen_json(out / "preflight_summary.json", summary)
    print(json.dumps(summary), flush=True)
    return df, public_profiles, jobs, generator_jobs


def ledger(out: Path) -> list[dict]:
    return [read_json(path) for path in sorted((out / "calls").glob("*.json"))]


def success_map(out: Path) -> dict[str, dict]:
    records = [r for r in ledger(out) if r["status"] == "success"]
    result = {r["call_id"]: r for r in records}
    if len(result) != len(records):
        raise ValueError("More than one successful completion for a call")
    return result


def spend(out: Path) -> float:
    return sum(float(r["charged_or_reserved_cost_usd"]) for r in ledger(out))


def write_status(out: Path, generator_total: int, phase: str, cap: float) -> None:
    records = ledger(out)
    successful = [r for r in records if r["status"] == "success"]
    generation = sum(r["stage"] == "generator" for r in successful)
    prediction = sum(r["stage"] == "predictor" for r in successful)
    save_json(out / "status.json", {
        "updated_at_utc": utc_now(), "phase": phase,
        "generator_completed": generation, "generator_total": generator_total,
        "predictor_completed": prediction, "predictor_total": 40,
        "failed_attempts": sum(r["status"] == "error" for r in records),
        "inflight_attempts": sum(r["status"] == "inflight" for r in records),
        "tracked_run_cost_usd": spend(out), "max_run_cost_usd": cap,
        "complete": phase == "complete" and generation == generator_total and prediction == 40,
    })


def generator_usage(completion: Any) -> dict:
    usage = completion.usage
    if usage is None:
        raise ValueError("OpenAI response lacks token usage")
    input_tokens, output_tokens = int(usage.prompt_tokens), int(usage.completion_tokens)
    cached = int(getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0)
    if not 0 <= cached <= input_tokens or output_tokens < 0:
        raise ValueError("Invalid OpenAI token usage")
    estimate = ((input_tokens - cached) * PRICES["input"] + cached * PRICES["cached_input"] + output_tokens * PRICES["output"]) / 1e6
    return {
        "prompt_tokens": input_tokens, "completion_tokens": output_tokens,
        "cached_prompt_tokens": cached,
        "reasoning_tokens": getattr(usage.completion_tokens_details, "reasoning_tokens", None),
        "provider_reported_cost_usd": None, "estimated_cost_usd": estimate,
        "charged_or_reserved_cost_usd": estimate, "cost_basis": "OpenAI public token pricing, including cached-input discount",
    }


def perform(job: dict, path: Path, clients: dict, secrets: list[str]) -> dict:
    record = read_json(path)
    try:
        if job["stage"] == "generator":
            completion = clients["openai"].chat.completions.create(
                model=GENERATOR_MODEL, messages=job["messages"],
                reasoning_effort="low", max_completion_tokens=GENERATOR_MAX_TOKENS,
                response_format=GENERATOR_RESPONSE_FORMAT, seed=42,
            )
            record.update(generator_usage(completion))
        else:
            completion = completion_for_job(clients, MODEL_SPECS["gemini"], job["messages"][0]["content"], PREDICTOR_MAX_TOKENS)
            record.update(usage_record(completion, MODEL_SPECS["gemini"]))
            record["cost_basis"] = "OpenRouter reported cost, or configured price ceiling if unavailable"
        record.update({"response_id": completion.id, "returned_model": completion.model,
                       "finish_reason": completion.choices[0].finish_reason,
                       "raw_response": completion.choices[0].message.content or ""})
        if completion.choices[0].finish_reason != "stop":
            raise ValueError(f"Unexpected finish_reason: {completion.choices[0].finish_reason}")
        if job["stage"] == "generator":
            if not completion.model.startswith(GENERATOR_MODEL):
                raise ValueError("Generator returned a different model")
            label, label_id = parse_answer(record["raw_response"])
            record["answer"] = {"label_text": label, "label_id": label_id}
        else:
            if completion.model != MODEL_SPECS["gemini"].model_id:
                raise ValueError("Predictor returned a different model")
            rows = parse_response(record["raw_response"], job["test_rows"])
            for row in rows:
                row.update({"fold": 0, "history_shots": job["shots"], "model_id": completion.model})
            record["predictions"] = rows
        record["status"] = "success"
    except Exception as exc:
        message = str(exc)
        for secret in secrets:
            if secret:
                message = message.replace(secret, "[REDACTED]")
        record.update({"status": "error", "error_type": type(exc).__name__, "error": message[:1000]})
    record["finished_at_utc"] = utc_now()
    save_json(path, record)
    return record


def dispatch(pending_jobs: list[dict], out: Path, args: argparse.Namespace, clients: dict, secrets: list[str], total_generator: int, remaining: int) -> tuple[int, bool]:
    completed = success_map(out)
    pending = []
    for job in pending_jobs:
        previous = completed.get(job["call_id"])
        if previous:
            if previous["prompt_sha256"] != job["prompt_sha256"]:
                raise ValueError("Resume prompt differs from completed call")
            continue
        pending.append(job)
    existing = ledger(out)
    bad = {r["call_id"] for r in existing if r["status"] != "success"}
    if any(j["call_id"] in bad for j in pending) and not args.retry_errors:
        raise RuntimeError("Previous failed/in-flight attempt found; inspect ledger before explicit --retry-errors")
    consumed = 0
    for start in range(0, len(pending), args.concurrency):
        if consumed >= remaining:
            return consumed, False
        batch = pending[start:start + min(args.concurrency, remaining - consumed)]
        scheduled: list[tuple[dict, Path]] = []
        for job in batch:
            reserved = reserve(job["messages"], job["stage"])
            if spend(out) + reserved > args.max_cost_usd:
                if scheduled:
                    break
                raise RuntimeError("Budget admission stopped the next request")
            attempts = list((out / "calls").glob(job["call_id"] + ".attempt*.json"))
            path = out / "calls" / f"{job['call_id']}.attempt{len(attempts) + 1}.json"
            save_json(path, {
                "call_id": job["call_id"], "stage": job["stage"], "status": "inflight",
                "participant_id": job["participant_id"], "row_index": job.get("row_index"),
                "shots": job.get("shots"), "prompt_sha256": job["prompt_sha256"],
                "requested_model": GENERATOR_MODEL if job["stage"] == "generator" else MODEL_SPECS["gemini"].model_id,
                "reserved_cost_usd": reserved, "charged_or_reserved_cost_usd": reserved,
                "started_at_utc": utc_now(),
            })
            scheduled.append((job, path))
        failures = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(perform, job, path, clients, secrets) for job, path in scheduled]
            for future in as_completed(futures):
                result = future.result()
                consumed += 1
                if result["status"] != "success":
                    failures.append(result["call_id"])
                print(f"{result['status']} {result['call_id']}; run tracked ${spend(out):.4f}", flush=True)
        write_status(out, total_generator, pending[0]["stage"], args.max_cost_usd)
        if failures:
            raise RuntimeError(f"API/parse failure saved; automatic retry disabled: {failures}")
        if len(scheduled) != len(batch):
            raise RuntimeError("Budget admission stopped the remainder of the batch")
    return consumed, True


def freeze_answers(out: Path, generator_jobs: list[dict], source_df: pd.DataFrame) -> pd.DataFrame:
    completed = success_map(out)
    rows = []
    for job in generator_jobs:
        record = completed[job["call_id"]]
        if record["prompt_sha256"] != job["prompt_sha256"]:
            raise ValueError("Generator checkpoint prompt mismatch")
        rows.append({key: job[key] for key in ("row_index", "participant_id", "query_id", "tool", "raw_data_type", "role", "profile_id", "questionnaire_item_id")} | record["answer"])
    answers = pd.DataFrame(rows).sort_values("row_index")
    if answers["row_index"].duplicated().any():
        raise ValueError("Duplicate synthetic answer index")
    frozen_csv(out / "synthetic_answers.csv", answers)
    frozen_json(out / "synthetic_freeze.json", {
        "n_answers": len(answers), "sha256": file_sha256(out / "synthetic_answers.csv"),
        "generator_prompt_hashes_sha256": digest([j["prompt_sha256"] for j in generator_jobs]),
        "generator_answers_sha256": digest(rows), "state": "frozen_before_predictor_inference",
    })
    synthetic = source_df.loc[answers["row_index"].astype(int)].copy()
    lookup = answers.set_index("row_index")
    synthetic["label_id"] = lookup.loc[synthetic.index, "label_id"].to_numpy()
    synthetic["label_text"] = lookup.loc[synthetic.index, "label_text"].to_numpy()
    return synthetic


def predictor_jobs(out: Path, jobs: list[dict], synthetic: pd.DataFrame, profiles: dict) -> list[dict]:
    calls = []
    prompt_manifest = []
    for job in jobs:
        user_rows = synthetic.loc[synthetic["participant_id"].eq(job["participant_id"])]
        history = user_rows.loc[user_rows["query_id"].isin(job["prompt_history_query_ids"])]
        tests = user_rows.loc[user_rows["query_id"].isin(job["test_query_ids"])]
        for shots in (0, 4):
            prompt = build_prompt(profiles[job["participant_id"]], make_bundles(history, True) if shots else [], make_bundles(tests, False))
            messages = [{"role": "user", "content": prompt}]
            record = {"call_id": f"gemini_{shots}shot_{job['job_id']}", "stage": "predictor",
                      "participant_id": job["participant_id"], "shots": shots,
                      "messages": messages, "prompt_sha256": digest(messages),
                      "test_row_indices": [int(x) for x in tests.index]}
            prompt_manifest.append(record)
            calls.append({**record, "test_rows": tests})
    frozen_json(out / "predictor_preflight.json", prompt_manifest)
    return calls


def write_predictions(out: Path, calls: list[dict]) -> None:
    completed = success_map(out)
    for shots in (0, 4):
        predictions = [p for job in calls if job["shots"] == shots for p in completed[job["call_id"]]["predictions"]]
        frame = pd.DataFrame(predictions).sort_values("row_index").reset_index(drop=True)
        if frame["row_index"].duplicated().any():
            raise ValueError("Duplicate predictor row index")
        frozen_csv(out / f"predictions_{shots}shot.csv", frame)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--phase", choices=("all", "generate", "predict"), default="all")
    parser.add_argument("--max-cost-usd", type=float, default=8.0)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-new-calls", type=int, default=10000)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    if not 0 < args.max_cost_usd <= 8 or not 1 <= args.concurrency <= 4 or args.max_new_calls < 1:
        raise ValueError("Invalid budget/concurrency/call limit")
    out = args.out.resolve()
    df, profiles, jobs, generation = prepare(out, args.max_cost_usd)
    if not args.execute:
        write_status(out, len(generation), "prepared", args.max_cost_usd)
        print("Prepared locally; no API calls.", flush=True)
        return
    settings = dotenv_values(ENV_FILE)
    openai_key = str(settings.get("OPENAI_API_KEY") or "").strip()
    router_key = str(settings.get("OPENROUTER_API_KEY") or "").strip()
    if not openai_key or not router_key:
        raise RuntimeError("Required API key is missing")
    clients = {
        "openai": OpenAI(api_key=openai_key, base_url="https://api.openai.com/v1", max_retries=0, timeout=300),
        "openrouter": OpenAI(api_key=router_key, base_url="https://openrouter.ai/api/v1", max_retries=0, timeout=300),
    }
    secrets = [openai_key, router_key]
    remaining = args.max_new_calls
    try:
        if args.phase in ("all", "generate"):
            used, complete = dispatch(generation, out, args, clients, secrets, len(generation), remaining)
            remaining -= used
            if not complete:
                write_status(out, len(generation), "generation_paused_at_call_limit", args.max_cost_usd)
                return
        generated = success_map(out)
        if not all(j["call_id"] in generated for j in generation):
            raise RuntimeError("Generation is incomplete")
        synthetic = freeze_answers(out, generation, df)
        calls = predictor_jobs(out, jobs, synthetic, profiles)
        if args.phase == "generate" or remaining == 0:
            write_status(out, len(generation), "answers_frozen", args.max_cost_usd)
            return
        _, complete = dispatch(calls, out, args, clients, secrets, len(generation), remaining)
        if not complete:
            write_status(out, len(generation), "prediction_paused_at_call_limit", args.max_cost_usd)
            return
        write_predictions(out, calls)
        from analyze_pilot import summarize
        summarize(out)
        write_status(out, len(generation), "complete", args.max_cost_usd)
        print(f"Experiment complete: {out}", flush=True)
    except Exception:
        write_status(out, len(generation), "stopped_for_review", args.max_cost_usd)
        raise
    finally:
        for client in clients.values():
            client.close()


if __name__ == "__main__":
    main()
