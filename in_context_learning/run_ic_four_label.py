"""Four-label, within-user IC-only baseline based on Wu et al. (IEEE S&P 2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import KFold

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = EXPERIMENT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))
from run_four_label_benchmark import ID_TO_LABEL, LABEL_ORDER, compute_metrics  # noqa: E402

LABEL_TO_ID = {text: number for number, text in ID_TO_LABEL.items()}
AGE_RANGES = {"1": "18-24", "2": "25-34", "3": "35-44", "4": "45-54", "5": "55 or older"}
REQUIRED_COLUMNS = (
    "participant_id", "query_id", "query", "tool", "raw_data_type", "label_text", "label_id"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def load_inputs(data_path: Path, raw_path: Path) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    df = pd.read_csv(data_path, keep_default_na=False)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing dataset columns: {sorted(missing)}")
    if df.duplicated(["participant_id", "query_id", "tool", "raw_data_type"]).any():
        raise ValueError("Duplicate participant/query/tool/data-type rows")
    if set(df["label_id"]) != set(LABEL_ORDER):
        raise ValueError("Dataset must contain all four labels")
    if any(LABEL_TO_ID.get(row.label_text) != row.label_id for row in df.itertuples()):
        raise ValueError("label_text and label_id disagree")
    users = json.loads(raw_path.read_text(encoding="utf-8"))
    profiles = {str(user["uuid"]): user for user in users if user.get("Valid") is True}
    if set(df["participant_id"]) != set(profiles):
        raise ValueError("Participant IDs differ between the CSV and raw survey")
    return df, profiles


def make_jobs(df: pd.DataFrame, seed: int) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for participant_id, user_rows in df.groupby("participant_id", sort=True):
        query_ids = np.array(sorted(int(qid) for qid in user_rows["query_id"].unique()))
        if len(query_ids) < 5:
            raise ValueError(f"{participant_id} has fewer than 5 queries")
        splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
        all_test: list[int] = []
        for fold, (train_pos, test_pos) in enumerate(splitter.split(query_ids)):
            train_qids = [int(value) for value in query_ids[train_pos]]
            test_qids = [int(value) for value in query_ids[test_pos]]
            if set(train_qids) & set(test_qids):
                raise AssertionError("History/test query overlap")
            all_test.extend(test_qids)
            jobs.append({
                "job_id": f"{participant_id}_fold{fold}",
                "participant_id": participant_id,
                "fold": fold,
                "train_query_ids": train_qids,
                "test_query_ids": test_qids,
                "train_rows": int(user_rows["query_id"].isin(train_qids).sum()),
                "test_rows": int(user_rows["query_id"].isin(test_qids).sum()),
            })
        if sorted(all_test) != query_ids.tolist():
            raise AssertionError(f"{participant_id} has missing/repeated test queries")
    return jobs


def permission_key(row: Any) -> str:
    return f"{row.tool},{row.raw_data_type}"


def make_bundles(rows: pd.DataFrame, include_answers: bool) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for query_id, query_rows in rows.groupby("query_id", sort=True):
        permissions: dict[str, Any] = {}
        for row in query_rows.itertuples():
            key = permission_key(row)
            if key in permissions:
                raise ValueError(f"Duplicate permission key for query {query_id}: {key}")
            permissions[key] = row.label_text if include_answers else None
        bundles.append({
            "query": str(query_rows.iloc[0]["query"]),
            "id": int(query_id),
            "answer" if include_answers else "permission": permissions,
        })
    return bundles


def profile_text(user: dict[str, Any]) -> tuple[str, str]:
    age = AGE_RANGES.get(str(user.get("age", "")), "unspecified")
    bio = f"Age group: {age}; gender: {user.get('gender') or 'unspecified'}; education: {user.get('education') or 'unspecified'}."
    experience = {
        "AI familiarity (survey 1-5)": user.get("aiFamiliarity", ""),
        "AI usage frequency (survey 1-5)": user.get("aiFrequency", ""),
        "AI use purposes": user.get("aiPurposes", ""),
        "Trust in AI privacy (survey 1-5)": user.get("aiTrust", ""),
        "Privacy importance (survey 1-5)": user.get("privacyImportance", ""),
        "Privacy concerns": user.get("privacyDetails", ""),
        "Privacy-sensitive domains": user.get("concern_domain") or [],
    }
    return bio, json.dumps(experience, ensure_ascii=False, indent=2)


def build_prompt(
    user: dict[str, Any], history: list[dict[str, Any]], requests: list[dict[str, Any]]
) -> str:
    bio, experience = profile_text(user)
    labels = [ID_TO_LABEL[index] for index in LABEL_ORDER]
    return (
        "You are a personalized permission assistant predicting this user's data-access decisions.\n"
        "Consider demographics, AI usage, privacy attitudes, the user's own permission history, "
        "and the meaning of each new request. The four responses differ both in immediate sharing "
        "and whether the assistant should ask again next time.\n"
        "For each new query and every listed permission key, return exactly one of these labels: "
        + json.dumps(labels, ensure_ascii=False) + ".\n"
        "Return a JSON array with one object per new query. Each object must have id, query, "
        "and permission. Under permission, keep every input key exactly and return "
        "{\"label\": one allowed label, \"score\": a number from 0 to 1} for each key. "
        "The score is confidence in that exact four-class label. Return JSON only.\n\n"
        "User demographic and bio information:\n" + bio + "\n\n"
        "User AI tool usage and privacy information:\n" + experience + "\n\n"
        "User permission decision history:\n"
        + json.dumps(history, ensure_ascii=False, indent=2) + "\n\n"
        "New permission requests (null values are to be predicted):\n"
        + json.dumps(requests, ensure_ascii=False, indent=2)
    )


def job_rows(df: pd.DataFrame, job: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    user_rows = df.loc[df["participant_id"] == job["participant_id"]]
    train_rows = user_rows.loc[user_rows["query_id"].isin(job["train_query_ids"])]
    test_rows = user_rows.loc[user_rows["query_id"].isin(job["test_query_ids"])]
    if len(train_rows) != job["train_rows"] or len(test_rows) != job["test_rows"]:
        raise ValueError(f"Job row counts changed: {job['job_id']}")
    if set(train_rows["query_id"]) & set(test_rows["query_id"]):
        raise AssertionError("A test query is present in the history")
    return train_rows, test_rows


def parse_response(response: str, test_rows: pd.DataFrame) -> list[dict[str, Any]]:
    payload = response.strip()
    if payload.startswith("```"):
        lines = payload.splitlines()
        if lines[0].strip().lower() not in ("```", "```json") or lines[-1].strip() != "```":
            raise ValueError("Malformed fenced JSON response")
        payload = "\n".join(lines[1:-1])
    value = json.loads(payload)
    if not isinstance(value, list):
        raise ValueError("Expected a JSON array")
    expected_bundles = make_bundles(test_rows, include_answers=False)
    expected = {bundle["id"]: set(bundle["permission"]) for bundle in expected_bundles}
    if len(value) != len(expected):
        raise ValueError("Missing or extra query predictions")
    by_query: dict[int, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            raise ValueError("Each prediction needs an integer query id")
        query_id = item["id"]
        if query_id not in expected or query_id in by_query:
            raise ValueError("Unknown or duplicate query id")
        permission = item.get("permission")
        if not isinstance(permission, dict) or set(permission) != expected[query_id]:
            raise ValueError(f"Missing or extra permission predictions for query {query_id}")
        by_query[query_id] = permission
    result: list[dict[str, Any]] = []
    for row in test_rows.itertuples():
        prediction = by_query[int(row.query_id)][permission_key(row)]
        if not isinstance(prediction, dict):
            raise ValueError("Permission prediction must be an object")
        label = prediction.get("label")
        score = prediction.get("score")
        if label not in LABEL_TO_ID or type(score) not in (int, float) or not 0 <= score <= 1:
            raise ValueError("Invalid four-class label or confidence score")
        result.append({
            "row_index": int(row.Index),
            "participant_id": row.participant_id,
            "query_id": int(row.query_id),
            "tool": row.tool,
            "raw_data_type": row.raw_data_type,
            "fold": None,
            "true_label_id": int(row.label_id),
            "pred_label_id": LABEL_TO_ID[label],
            "pred_label_text": label,
            "confidence": float(score),
        })
    return result


PRICE_PER_MILLION = {
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
    "gpt-4o-mini": (0.15, 0.60),
}


def max_call_cost_usd(prompt: str, model: str, max_completion_tokens: int) -> float:
    """Conservative pre-call bound: UTF-8 bytes upper-bound text tokens."""
    input_rate, output_rate = PRICE_PER_MILLION[model]
    input_upper_bound = len(prompt.encode("utf-8")) + 128
    return (input_upper_bound * input_rate + max_completion_tokens * output_rate) / 1_000_000


def usage_and_cost(completion: Any, model: str) -> dict[str, Any]:
    usage = completion.usage
    if usage is None:
        raise ValueError("API response has no token usage")
    prompt_tokens = int(usage.prompt_tokens)
    completion_tokens = int(usage.completion_tokens)
    input_rate, output_rate = PRICE_PER_MILLION[model]
    # Charge all prompt tokens at the full input rate; cached-token discounts only reduce the real bill.
    cost_usd = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "charged_or_reserved_cost_usd": cost_usd,
    }


def tracked_spend_usd(checkpoint_dir: Path) -> float:
    total = 0.0
    for path in checkpoint_dir.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "charged_or_reserved_cost_usd" not in record:
            raise ValueError(f"Checkpoint lacks a budget record: {path}")
        total += float(record["charged_or_reserved_cost_usd"])
    return total


def call_model(client: Any, model: str, prompt: str, max_completion_tokens: int) -> Any:
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_completion_tokens,
    )


def participant_bootstrap_ci(predictions: pd.DataFrame, samples: int = 2000) -> dict[str, Any]:
    """Percentile intervals with participant, rather than row, as the sampling unit."""
    rng = np.random.default_rng(20260809)
    participants = sorted(predictions["participant_id"].unique())
    positions = {
        participant: np.flatnonzero(predictions["participant_id"].to_numpy() == participant)
        for participant in participants
    }
    truth = predictions["true_label_id"].to_numpy(dtype=int)
    predicted = predictions["pred_label_id"].to_numpy(dtype=int)
    metric_names = (
        "accuracy", "macro_f1", "quadratic_weighted_kappa",
        "over_sharing_rate", "persistent_over_allow_rate",
    )
    values: dict[str, list[float]] = {name: [] for name in metric_names}
    for _ in range(samples):
        drawn = rng.choice(participants, size=len(participants), replace=True)
        sample_rows = np.concatenate([positions[participant] for participant in drawn])
        metrics = compute_metrics(truth[sample_rows], predicted[sample_rows])
        for name in metric_names:
            values[name].append(float(metrics[name]))
    return {
        "unit": "participant",
        "samples": samples,
        "seed": 20260809,
        "percentile_95_ci": {
            name: [float(np.nanpercentile(values[name], 2.5)),
                   float(np.nanpercentile(values[name], 97.5))]
            for name in metric_names
        },
    }


def write_results(out_dir: Path, df: pd.DataFrame, jobs: list[dict[str, Any]]) -> None:
    prediction_rows: list[dict[str, Any]] = []
    for job in jobs:
        checkpoint = json.loads((out_dir / "checkpoints" / f"{job['job_id']}.json").read_text(encoding="utf-8"))
        rows = checkpoint["predictions"]
        if len(rows) != job["test_rows"]:
            raise ValueError(f"Incomplete checkpoint: {job['job_id']}")
        prediction_rows.extend(rows)
    predictions = pd.DataFrame(prediction_rows).sort_values("row_index").reset_index(drop=True)
    if predictions["row_index"].tolist() != list(range(len(df))):
        raise ValueError("Prediction coverage is not exactly one per dataset row")
    true_labels = predictions["true_label_id"].to_numpy(dtype=int)
    pred_labels = predictions["pred_label_id"].to_numpy(dtype=int)
    metrics = compute_metrics(true_labels, pred_labels)
    metrics.update({
        "model": "ic_only_four_label",
        "n_rows": len(predictions),
        "n_participants": int(predictions["participant_id"].nunique()),
        "n_jobs": len(jobs),
        "coverage": 1.0,
    })
    predictions.to_csv(out_dir / "predictions.csv", index=False, encoding="utf-8")
    save_json(out_dir / "metrics.json", metrics)
    save_json(out_dir / "participant_bootstrap_ci.json", participant_bootstrap_ci(predictions))
    save_json(out_dir / "classification_report.json", classification_report(
        true_labels, pred_labels, labels=LABEL_ORDER,
        target_names=[ID_TO_LABEL[label] for label in LABEL_ORDER],
        output_dict=True, zero_division=0,
    ))
    matrix = confusion_matrix(true_labels, pred_labels, labels=LABEL_ORDER)
    pd.DataFrame(matrix, index=[f"true_{i}" for i in LABEL_ORDER],
                 columns=[f"pred_{i}" for i in LABEL_ORDER]).to_csv(
        out_dir / "confusion_matrix.csv", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_DIR / "data/processed/four_label_dataset.csv")
    parser.add_argument("--raw", type=Path, default=PROJECT_DIR / "external/ai-agent-permissions/data/user_study.json")
    parser.add_argument("--out", type=Path, required=True, help="New output directory, or the same directory to resume")
    parser.add_argument("--model", default="o3-mini", help="Paper model; released code instead defaults to o4-mini")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--execute", action="store_true", help="Actually call the OpenAI API")
    parser.add_argument("--max-jobs", type=int, default=None, help="Stop after this many new API calls for a pilot")
    parser.add_argument("--env-file", type=Path, default=None, help="Optional dotenv file containing OPENAI_API_KEY")
    parser.add_argument("--max-cost-usd", type=float, default=4.0, help="Hard cap on tracked API spend (maximum 4 USD)")
    parser.add_argument("--max-completion-tokens", type=int, default=3000)
    args = parser.parse_args()
    if args.max_jobs is not None and args.max_jobs < 1:
        parser.error("--max-jobs must be positive")
    if not 0 < args.max_cost_usd <= 4.0:
        parser.error("--max-cost-usd must be in (0, 4]")
    if args.max_completion_tokens < 1:
        parser.error("--max-completion-tokens must be positive")
    if args.model not in PRICE_PER_MILLION:
        parser.error(f"Unknown model price for budget accounting: {args.model}")
    if args.max_jobs is not None and not args.execute:
        parser.error("--max-jobs requires --execute")
    data_path, raw_path = args.data.resolve(), args.raw.resolve()
    df, profiles = load_inputs(data_path, raw_path)
    jobs = make_jobs(df, args.seed)
    config = {
        "protocol": "within_participant_5fold_query_heldout",
        "seed": args.seed,
        "model": args.model,
        "max_completion_tokens": args.max_completion_tokens,
        "data_path": str(data_path),
        "data_sha256": file_sha256(data_path),
        "raw_path": str(raw_path),
        "raw_sha256": file_sha256(raw_path),
        "script_sha256_at_prepare": file_sha256(Path(__file__)),
        "n_rows": len(df),
        "n_participants": len(profiles),
        "n_jobs": len(jobs),
        "label_mapping": {str(key): value for key, value in ID_TO_LABEL.items()},
        "feature_regime": "raw_profile_and_same_user_history_no_oracle_query_metadata",
    }
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    config_path = out_dir / "run_config.json"
    if config_path.exists():
        old = json.loads(config_path.read_text(encoding="utf-8"))
        for key, value in config.items():
            if key != "script_sha256_at_prepare" and old.get(key) != value:
                raise ValueError(f"Cannot resume: run configuration changed at {key}")
    elif any(out_dir.iterdir()):
        raise ValueError("Refusing to write into a nonempty unrelated output directory")
    else:
        save_json(config_path, config)
        save_json(out_dir / "fold_manifest.json", jobs)
        first = jobs[0]
        train_rows, test_rows = job_rows(df, first)
        preview = build_prompt(
            profiles[first["participant_id"]],
            make_bundles(train_rows, True),
            make_bundles(test_rows, False),
        )
        (out_dir / "preview_prompt.txt").write_text(preview, encoding="utf-8")
    checkpoint_dir = out_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    new_calls = 0
    budget_stop = False
    if args.execute:
        from dotenv import load_dotenv
        from openai import OpenAI
        if args.env_file is not None:
            if not args.env_file.is_file():
                raise FileNotFoundError(f"Dotenv file not found: {args.env_file}")
            load_dotenv(args.env_file, override=False)
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY or provide --env-file before --execute")
        client = OpenAI(max_retries=0, timeout=300)
        for job in jobs:
            checkpoint_path = checkpoint_dir / f"{job['job_id']}.json"
            if checkpoint_path.exists():
                continue
            if args.max_jobs is not None and new_calls >= args.max_jobs:
                break
            train_rows, test_rows = job_rows(df, job)
            prompt = build_prompt(
                profiles[job["participant_id"]],
                make_bundles(train_rows, True),
                make_bundles(test_rows, False),
            )
            reserve = max_call_cost_usd(prompt, args.model, args.max_completion_tokens)
            current_spend = tracked_spend_usd(checkpoint_dir)
            if current_spend + reserve > args.max_cost_usd:
                budget_stop = True
                print(f"Budget stop before {job['job_id']}: tracked USD {current_spend:.4f}; "
                      f"next-call reserve USD {reserve:.4f}; cap USD {args.max_cost_usd:.2f}")
                break
            raw_response = None
            charge = reserve
            usage_record: dict[str, Any] = {}
            try:
                completion = call_model(client, args.model, prompt, args.max_completion_tokens)
                usage_record = usage_and_cost(completion, args.model)
                charge = float(usage_record["charged_or_reserved_cost_usd"])
                raw_response = completion.choices[0].message.content
                if not raw_response:
                    raise ValueError("The model returned empty content")
                parsed = parse_response(raw_response, test_rows)
                for row in parsed:
                    row["fold"] = job["fold"]
                save_json(checkpoint_path, {
                    "job_id": job["job_id"], "predictions": parsed,
                    **usage_record,
                })
            except Exception as exc:
                save_json(checkpoint_dir / f"{job['job_id']}.error.json", {
                    "job_id": job["job_id"], "error": str(exc),
                    "raw_response": raw_response,
                    "charged_or_reserved_cost_usd": charge,
                    **usage_record,
                })
                raise RuntimeError(f"Stopped at {job['job_id']}: {exc}") from exc
            new_calls += 1
            print(f"Completed {job['job_id']} ({new_calls} new calls); "
                  f"tracked USD {tracked_spend_usd(checkpoint_dir):.4f}", flush=True)
    completed = sum((checkpoint_dir / f"{job['job_id']}.json").exists() for job in jobs)
    save_json(out_dir / "status.json", {
        "completed_jobs": completed, "total_jobs": len(jobs),
        "complete": completed == len(jobs), "api_calls_this_invocation": new_calls,
        "tracked_spend_usd": tracked_spend_usd(checkpoint_dir),
        "max_cost_usd": args.max_cost_usd,
        "budget_stop": budget_stop,
    })
    if completed == len(jobs):
        write_results(out_dir, df, jobs)
        print(f"Complete: {len(df)} predictions; metrics in {out_dir / 'metrics.json'}")
    else:
        print(f"Prepared/resumable: {completed}/{len(jobs)} jobs; preview in {out_dir / 'preview_prompt.txt'}")


if __name__ == "__main__":
    main()


