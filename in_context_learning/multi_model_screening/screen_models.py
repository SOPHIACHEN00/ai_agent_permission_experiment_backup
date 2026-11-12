"""Paired, budget-capped screening of three recent four-label ICL models.

Preparation is offline. API requests require --execute and the relevant keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report

SCREEN_DIR = Path(__file__).resolve().parent
IC_DIR = SCREEN_DIR.parent
PROJECT_DIR = IC_DIR.parent
sys.path.insert(0, str(IC_DIR))
from run_ic_four_label import (  # noqa: E402
    ID_TO_LABEL,
    LABEL_ORDER,
    build_prompt,
    file_sha256,
    job_rows,
    load_inputs,
    make_bundles,
    make_jobs,
    parse_response,
    participant_bootstrap_ci,
    save_json,
)

sys.path.insert(0, str(PROJECT_DIR))
from classification.run_four_label_benchmark import compute_metrics  # noqa: E402


@dataclass(frozen=True)
class ModelSpec:
    name: str
    route: str
    model_id: str
    max_input_usd_per_million: float
    max_output_usd_per_million: float


# OpenRouter ceilings are enforced again at the gateway via provider.max_price.
# They are intentionally above today's cheapest DeepSeek endpoint to permit
# fallback to another inexpensive provider while bounding every request.
MODEL_SPECS: dict[str, ModelSpec] = {
    "luna": ModelSpec("luna", "openrouter", "openai/gpt-6-luna", 0.10, 0.50),
    "deepseek": ModelSpec(
        "deepseek", "openrouter", "deepseek/deepseek-v4-flash-0731", 0.20, 0.60
    ),
    "gemini": ModelSpec(
        "gemini", "openrouter", "google/gemini-3.8-flash", 0.75, 3.75
    ),
}
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_AUTHORIZED_USD = 24.0
WARN_AT_USD = 10.0


def select_jobs(
    df: pd.DataFrame, *, fold_seed: int, sample_seed: int,
    n_participants: int, fold: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    all_jobs = make_jobs(df, fold_seed)
    participants = sorted(str(value) for value in df["participant_id"].unique())
    if not 1 <= n_participants <= len(participants):
        raise ValueError(f"n_participants must be between 1 and {len(participants)}")
    chosen = sorted(
        str(value) for value in np.random.default_rng(sample_seed).choice(
            participants, size=n_participants, replace=False
        )
    )
    selected = [
        job for job in all_jobs
        if job["participant_id"] in chosen and (fold == "all" or job["fold"] == int(fold))
    ]
    expected = n_participants * (5 if fold == "all" else 1)
    if len(selected) != expected:
        raise AssertionError("Screening manifest does not cover the selected participants")
    return chosen, selected


def select_history_shots(
    jobs: list[dict[str, Any]], shots: int, seed: int,
) -> list[dict[str, Any]]:
    """Choose complete training queries deterministically for each held-out fold."""
    selected_jobs = []
    for job in jobs:
        train_query_ids = [int(value) for value in job["train_query_ids"]]
        if shots > len(train_query_ids):
            raise ValueError(f"{job['job_id']} has only {len(train_query_ids)} history queries")
        digest = hashlib.sha256(f"{seed}:{job['job_id']}".encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
        sampled = set(rng.choice(train_query_ids, size=shots, replace=False).tolist())
        chosen = [query_id for query_id in train_query_ids if query_id in sampled]
        selected_jobs.append({**job, "prompt_history_query_ids": chosen})
    return selected_jobs


def prompt_for_job(
    df: pd.DataFrame, profiles: dict[str, dict[str, Any]], job: dict[str, Any]
) -> tuple[str, pd.DataFrame]:
    history, test = job_rows(df, job)
    if "prompt_history_query_ids" in job:
        chosen = set(job["prompt_history_query_ids"])
        if not chosen.issubset(set(job["train_query_ids"])):
            raise AssertionError("Prompt history includes a held-out query")
        history = history.loc[history["query_id"].isin(chosen)]
        if history["query_id"].nunique() != len(chosen):
            raise AssertionError("A selected history query is missing")
    prompt = build_prompt(
        profiles[job["participant_id"]],
        make_bundles(history, include_answers=True),
        make_bundles(test, include_answers=False),
    )
    return prompt, test


def reserve_cost_usd(prompt: str, spec: ModelSpec, max_output_tokens: int) -> float:
    # For UTF-8 text, byte length bounds ordinary token count. The margin
    # covers message framing; output is explicitly capped in the API call.
    input_token_bound = len(prompt.encode("utf-8")) + 128
    return (
        input_token_bound * spec.max_input_usd_per_million
        + max_output_tokens * spec.max_output_usd_per_million
    ) / 1_000_000


def usage_record(completion: Any, spec: ModelSpec) -> dict[str, Any]:
    usage = completion.usage
    if usage is None:
        raise ValueError("API response has no token usage; cannot account for spend")
    input_tokens = int(usage.prompt_tokens)
    output_tokens = int(usage.completion_tokens)
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Negative usage token count")
    ceiling_cost = (
        input_tokens * spec.max_input_usd_per_million
        + output_tokens * spec.max_output_usd_per_million
    ) / 1_000_000
    reported_cost = getattr(usage, "cost", None)
    if reported_cost is None:
        reported_cost = (getattr(usage, "model_extra", None) or {}).get("cost")
    if reported_cost is not None:
        reported_cost = float(reported_cost)
        if not math.isfinite(reported_cost) or reported_cost < 0:
            raise ValueError("Invalid provider-reported cost")
    # A missing OpenRouter cost is accounted for at the enforced gateway cap.
    charged = float(reported_cost) if reported_cost is not None else ceiling_cost
    details = getattr(usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None)
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "reasoning_tokens": None if reasoning_tokens is None else int(reasoning_tokens),
        "provider_reported_cost_usd": reported_cost,
        "charged_or_reserved_cost_usd": charged,
    }


def tracked_spend_usd(checkpoint_dir: Path) -> float:
    total = 0.0
    for path in checkpoint_dir.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "charged_or_reserved_cost_usd" not in record:
            raise ValueError(f"Checkpoint lacks a budget entry: {path}")
        total += float(record["charged_or_reserved_cost_usd"])
    return total


def safe_error_text(exc: Exception) -> str:
    """Keep API keys out of saved provider error messages."""
    message = str(exc)
    for name in ("OPENROUTER_API_KEY",):
        secret = os.getenv(name)
        if secret:
            message = message.replace(secret, "[REDACTED_API_KEY]")
    return message[:500]

def completion_for_job(clients: dict[str, Any], spec: ModelSpec, prompt: str, max_output_tokens: int) -> Any:
    request = {
        "model": spec.model_id,
        "messages": [{"role": "user", "content": prompt}],
    }
    if spec.route != "openrouter":
        raise ValueError(f"Unsupported route: {spec.route}")
    provider = {
        "sort": "price",
        "max_price": {
            "prompt": spec.max_input_usd_per_million,
            "completion": spec.max_output_usd_per_million,
        },
        "data_collection": "deny",
    }
    return clients["openrouter"].chat.completions.create(
        **request,
        max_tokens=max_output_tokens,
        extra_body={"provider": provider, "usage": {"include": True}, "reasoning": {"effort": "low"}},
    )


def build_clients(models: list[ModelSpec], env_file: Path | None) -> dict[str, Any]:
    from dotenv import dotenv_values
    from openai import OpenAI

    if env_file is not None and not env_file.is_file():
        raise FileNotFoundError(f"Environment file not found: {env_file}")
    if any(spec.route != "openrouter" for spec in models):
        raise ValueError("All screening models must use OpenRouter")
    settings = dotenv_values(env_file) if env_file is not None else os.environ
    api_key = (settings.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Provide OPENROUTER_API_KEY through the environment or explicit --env-file before --execute")
    if api_key == "TODO_REPLACE_WITH_YOUR_OPENROUTER_API_KEY":
        raise RuntimeError("Replace the OPENROUTER_API_KEY TODO before --execute")
    os.environ["OPENROUTER_API_KEY"] = api_key
    return {"openrouter": OpenAI(
        api_key=api_key, base_url=OPENROUTER_BASE_URL,
        max_retries=0, timeout=300,
    )}


def result_rows(
    out_dir: Path, selected_jobs: list[dict[str, Any]], spec: ModelSpec,
) -> pd.DataFrame:
    rows = []
    for job in selected_jobs:
        path = out_dir / "checkpoints" / f"{spec.name}_{job['job_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        if len(record["predictions"]) != job["test_rows"]:
            raise ValueError(f"Incomplete checkpoint: {path}")
        rows.extend(record["predictions"])
    predictions = pd.DataFrame(rows).sort_values("row_index").reset_index(drop=True)
    if predictions["row_index"].duplicated().any():
        raise ValueError(f"Duplicate test rows for {spec.name}")
    return predictions


def write_comparison(
    out_dir: Path, selected_jobs: list[dict[str, Any]], models: list[ModelSpec],
) -> None:
    summary = []
    expected_indices: list[int] | None = None
    for spec in models:
        predictions = result_rows(out_dir, selected_jobs, spec)
        indices = predictions["row_index"].astype(int).tolist()
        if expected_indices is None:
            expected_indices = indices
        elif indices != expected_indices:
            raise AssertionError("Models did not predict the same test rows")
        y_true = predictions["true_label_id"].to_numpy(dtype=int)
        y_pred = predictions["pred_label_id"].to_numpy(dtype=int)
        metrics = compute_metrics(y_true, y_pred)
        metrics.update({
            "model_name": spec.name,
            "model_id": spec.model_id,
            "route": spec.route,
            "n_rows": len(predictions),
            "n_participants": int(predictions["participant_id"].nunique()),
            "n_jobs": len(selected_jobs),
            "coverage": 1.0,
        })
        model_dir = out_dir / spec.name
        model_dir.mkdir(exist_ok=True)
        predictions.to_csv(model_dir / "predictions.csv", index=False, encoding="utf-8")
        save_json(model_dir / "metrics.json", metrics)
        save_json(model_dir / "classification_report.json", classification_report(
            y_true, y_pred, labels=LABEL_ORDER,
            target_names=[ID_TO_LABEL[i] for i in LABEL_ORDER],
            output_dict=True, zero_division=0,
        ))
        save_json(model_dir / "participant_bootstrap_ci.json", participant_bootstrap_ci(predictions, samples=1000))
        cost = sum(
            float(json.loads((out_dir / "checkpoints" / f"{spec.name}_{job['job_id']}.json").read_text(
                encoding="utf-8"
            ))["charged_or_reserved_cost_usd"])
            for job in selected_jobs
        )
        summary.append({
            "model_name": spec.name,
            "model_id": spec.model_id,
            "n_rows": len(predictions),
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
            "quadratic_weighted_kappa": metrics["quadratic_weighted_kappa"],
            "over_sharing_rate": metrics["over_sharing_rate"],
            "persistent_over_allow_rate": metrics["persistent_over_allow_rate"],
            "tracked_cost_usd": cost,
        })
    pd.DataFrame(summary).to_csv(out_dir / "screening_summary.csv", index=False, encoding="utf-8")


def write_status(
    out_dir: Path, jobs: list[dict[str, Any]], models: list[ModelSpec],
    planned_bound: float, cap: float, prior_spend: float, new_calls: int, budget_stop: bool,
) -> int:
    checkpoint_dir = out_dir / "checkpoints"
    completed = sum(
        (checkpoint_dir / f"{spec.name}_{job['job_id']}.json").exists()
        for job in jobs for spec in models
    )
    total = len(jobs) * len(models)
    run_spend = tracked_spend_usd(checkpoint_dir)
    cumulative_spend = prior_spend + run_spend
    save_json(out_dir / "status.json", {
        "completed_calls": completed,
        "total_calls": total,
        "complete": completed == total,
        "api_calls_this_invocation": new_calls,
        "tracked_spend_usd": cumulative_spend,
        "run_spend_usd": run_spend,
        "prior_spend_usd": prior_spend,
        "warning_threshold_usd": WARN_AT_USD,
        "warning_reached": cumulative_spend >= WARN_AT_USD,
        "max_cost_usd": cap,
        "planned_worst_case_cost_usd": prior_spend + planned_bound,
        "budget_stop": budget_stop,
    })
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_DIR / "data/processed/four_label_dataset.csv")
    parser.add_argument("--raw", type=Path, default=PROJECT_DIR / "external/ai-agent-permissions/data/user_study.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=MODEL_SPECS, default=list(MODEL_SPECS))
    parser.add_argument("--participants", type=int, default=40)
    parser.add_argument("--sample-seed", type=int, default=20260925)
    parser.add_argument("--fold-seed", type=int, default=42)
    parser.add_argument("--fold", choices=["0", "1", "2", "3", "4", "all"], default="0")
    parser.add_argument("--history-shots", type=int, default=None,
                        help="Number of complete same-user history queries; default uses all")
    parser.add_argument("--shot-seed", type=int, default=20260925,
                        help="Fixed seed for selecting history queries")
    parser.add_argument("--max-output-tokens", type=int, default=8000)
    parser.add_argument("--max-cost-usd", type=float, default=24.0)
    parser.add_argument("--prior-spend-usd", type=float, default=0.0)
    parser.add_argument("--env-file", type=Path, default=None,
                        help="Optional explicit credential file; never loaded during preparation")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-new-calls", type=int, default=None)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    if not 0 < args.max_cost_usd <= MAX_AUTHORIZED_USD:
        parser.error(f"--max-cost-usd must be in (0, {MAX_AUTHORIZED_USD}]")
    if args.max_output_tokens < 1:
        parser.error("--max-output-tokens must be positive")
    if args.history_shots is not None and args.history_shots < 1:
        parser.error("--history-shots must be positive")
    if not 0 <= args.prior_spend_usd < args.max_cost_usd:
        parser.error("--prior-spend-usd must be nonnegative and below --max-cost-usd")
    if args.max_new_calls is not None and (args.max_new_calls < 1 or not args.execute):
        parser.error("--max-new-calls requires --execute and a positive integer")
    if len(set(args.models)) != len(args.models):
        parser.error("--models cannot contain duplicates")
    models = [MODEL_SPECS[name] for name in args.models]

    data_path, raw_path = args.data.resolve(), args.raw.resolve()
    df, profiles = load_inputs(data_path, raw_path)
    participants, jobs = select_jobs(
        df, fold_seed=args.fold_seed, sample_seed=args.sample_seed,
        n_participants=args.participants, fold=args.fold,
    )
    if args.history_shots is not None:
        jobs = select_history_shots(jobs, args.history_shots, args.shot_seed)
    first_prompt, _ = prompt_for_job(df, profiles, jobs[0])
    planned_bound = sum(
        reserve_cost_usd(prompt_for_job(df, profiles, job)[0], spec, args.max_output_tokens)
        for job in jobs for spec in models
    )
    config = {
        "protocol": "within_participant_query_holdout_paired_model_screen",
        "fold_seed": args.fold_seed,
        "sample_seed": args.sample_seed,
        "fold": args.fold,
        "history_shots": args.history_shots,
        "shot_seed": args.shot_seed if args.history_shots is not None else None,
        "participants": participants,
        "models": [asdict(spec) for spec in models],
        "max_output_tokens": args.max_output_tokens,
        "prior_spend_usd": args.prior_spend_usd,
        "data_path": str(data_path),
        "data_sha256": file_sha256(data_path),
        "raw_path": str(raw_path),
        "raw_sha256": file_sha256(raw_path),
        "icl_script_sha256": file_sha256(IC_DIR / "run_ic_four_label.py"),
        "script_sha256": file_sha256(Path(__file__)),
        "n_test_rows": sum(job["test_rows"] for job in jobs),
        "label_mapping": {str(key): value for key, value in ID_TO_LABEL.items()},
        "feature_regime": "raw_profile_and_same_user_history_no_oracle_query_metadata",
        "generation_settings": "OpenRouter reasoning.effort=low for all; one user message; output capped; no tools",
    }
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    config_path = out_dir / "run_config.json"
    if config_path.exists():
        old = json.loads(config_path.read_text(encoding="utf-8"))
        if old != config:
            raise ValueError("Cannot resume: run configuration, data, or source code changed")
        saved_jobs = json.loads((out_dir / "job_manifest.json").read_text(encoding="utf-8"))
        if saved_jobs != jobs:
            raise ValueError("Cannot resume: job manifest changed")
    elif any(out_dir.iterdir()):
        raise ValueError("Refusing to write into a nonempty unrelated output directory")
    else:
        save_json(config_path, config)
        save_json(out_dir / "job_manifest.json", jobs)
        (out_dir / "preview_prompt.txt").write_text(first_prompt, encoding="utf-8")
    checkpoint_dir = out_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    new_calls = 0
    budget_stop = False
    if args.execute:
        clients = build_clients(models, args.env_file.resolve() if args.env_file is not None else None)
        for job in jobs:
            prompt, test_rows = prompt_for_job(df, profiles, job)
            for spec in models:
                stem = f"{spec.name}_{job['job_id']}"
                checkpoint = checkpoint_dir / f"{stem}.json"
                if checkpoint.exists():
                    continue
                if args.max_new_calls is not None and new_calls >= args.max_new_calls:
                    break
                prior_errors = sorted(checkpoint_dir.glob(f"{stem}.error*.json"))
                if prior_errors and not args.retry_errors:
                    raise RuntimeError(f"Prior failed call for {stem}; inspect it, then use --retry-errors")
                reserve = reserve_cost_usd(prompt, spec, args.max_output_tokens)
                spent = args.prior_spend_usd + tracked_spend_usd(checkpoint_dir)
                if spent + reserve > args.max_cost_usd:
                    budget_stop = True
                    print(f"Budget stop before {stem}: spent ${spent:.4f}, reserve ${reserve:.4f}, "
                          f"cap ${args.max_cost_usd:.2f}")
                    break
                raw_response: str | None = None
                cost_record: dict[str, Any] = {"charged_or_reserved_cost_usd": reserve}
                try:
                    completion = completion_for_job(clients, spec, prompt, args.max_output_tokens)
                    cost_record = usage_record(completion, spec)
                    if float(cost_record["charged_or_reserved_cost_usd"] ) > reserve:
                        raise ValueError("Reported charge exceeds pre-call reserve; inspect provider pricing")
                    raw_response = completion.choices[0].message.content
                    if not isinstance(raw_response, str) or not raw_response.strip():
                        raise ValueError("Empty model response")
                    predictions = parse_response(raw_response, test_rows)
                    for row in predictions:
                        row["fold"] = job["fold"]
                    save_json(checkpoint, {
                        "job_id": job["job_id"], "model_name": spec.name,
                        "requested_model_id": spec.model_id,
                        "returned_model_id": getattr(completion, "model", None),
                        "predictions": predictions, **cost_record,
                    })
                except Exception as exc:
                    error_path = checkpoint_dir / f"{stem}.error{len(prior_errors) + 1}.json"
                    save_json(error_path, {
                        "job_id": job["job_id"], "model_name": spec.name,
                        "error_type": type(exc).__name__,
                        "error": safe_error_text(exc), "raw_response": raw_response,
                        **cost_record,
                    })
                    current = args.prior_spend_usd + tracked_spend_usd(checkpoint_dir)
                    if spent < WARN_AT_USD <= current:
                        print(f"ALERT: cumulative tracked spend ${current:.4f} reached ${WARN_AT_USD:.2f}; continuing toward ${args.max_cost_usd:.2f} cap", flush=True)
                    write_status(out_dir, jobs, models, planned_bound, args.max_cost_usd, args.prior_spend_usd, new_calls, budget_stop)
                    raise RuntimeError(f"Stopped at {stem}: {type(exc).__name__}; inspect the error checkpoint") from None
                new_calls += 1
                current = args.prior_spend_usd + tracked_spend_usd(checkpoint_dir)
                if spent < WARN_AT_USD <= current:
                    print(f"ALERT: cumulative tracked spend ${current:.4f} reached ${WARN_AT_USD:.2f}; continuing toward ${args.max_cost_usd:.2f} cap", flush=True)
                print(f"Completed {stem}; cumulative tracked ${current:.4f}", flush=True)
            if budget_stop or (args.max_new_calls is not None and new_calls >= args.max_new_calls):
                break
    completed = write_status(out_dir, jobs, models, planned_bound, args.max_cost_usd, args.prior_spend_usd, new_calls, budget_stop)
    if completed == len(jobs) * len(models):
        write_comparison(out_dir, jobs, models)
        print(f"Screening complete: {out_dir / 'screening_summary.csv'}")
    else:
        print(f"Prepared/resumable: {completed}/{len(jobs) * len(models)} calls; "
              f"planned worst-case bound ${args.prior_spend_usd + planned_bound:.4f}; cap ${args.max_cost_usd:.2f}")


if __name__ == "__main__":
    main()
