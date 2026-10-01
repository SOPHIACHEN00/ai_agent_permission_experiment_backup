"""Summarize frozen real/synthetic runs locally; makes no model/API calls."""
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ICL = PROJECT / "in_context_learning"
REAL = ICL / "multi_model_screening/artifacts/full_201_gemini_4shot_fold0_seed20260925_8k_low"
OLD = ICL / "multi_model_screening/artifacts/screen_40_seed20260925_4shot_8k_low"
SYNTH = ICL / "sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def metrics(frame):
    truth, pred = frame.true_label_id, frame.pred_label_id
    denied = truth.isin([0, 1])
    nonpersistent = truth.ne(3)
    return {
        "n_users": int(frame.participant_id.nunique()),
        "n_rows": len(frame),
        "n_correct": int(truth.eq(pred).sum()),
        "accuracy": float(accuracy_score(truth, pred)),
        "macro_f1_fixed_four_labels": float(f1_score(truth, pred, labels=[0, 1, 2, 3], average="macro", zero_division=0)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(truth, pred, labels=[0, 1, 2, 3], weights="quadratic")),
        "false_allow_count": int((denied & pred.isin([2, 3])).sum()),
        "false_allow_denominator": int(denied.sum()),
        "false_allow_rate": float((denied & pred.isin([2, 3])).sum() / denied.sum()),
        "persistent_over_allow_count": int((nonpersistent & pred.eq(3)).sum()),
        "persistent_over_allow_denominator": int(nonpersistent.sum()),
        "persistent_over_allow_rate": float((nonpersistent & pred.eq(3)).sum() / nonpersistent.sum()),
        "truth_counts": {str(label): int(truth.eq(label).sum()) for label in range(4)},
    }


def volumes(source, manifest):
    participants = [job["participant_id"] for job in manifest]
    result = {"n_users": len(participants), "available_human_rows": len(source[source.participant_id.isin(participants)])}
    selections = []
    for role, key in [("history", "prompt_history_query_ids"), ("test", "test_query_ids")]:
        rows = pd.concat([source[(source.participant_id == job["participant_id"]) & source.query_id.isin(job[key])] for job in manifest])
        selections.append(rows)
        result[role] = {
            "permission_rows": len(rows),
            "user_query_pairs": len(rows[["participant_id", "query_id"]].drop_duplicates()),
            "distinct_query_ids": int(rows.query_id.nunique()),
            "distinct_permission_items": len(rows[["query_id", "tool", "raw_data_type"]].drop_duplicates()),
        }
    combined = pd.concat(selections)
    result["selected_permission_rows"] = len(combined)
    result["selected_distinct_query_ids"] = int(combined.query_id.nunique())
    result["selected_distinct_permission_items"] = len(combined[["query_id", "tool", "raw_data_type"]].drop_duplicates())
    return result


def main():
    source = pd.read_csv(PROJECT / "data/processed/four_label_dataset.csv")
    personas = pd.read_csv(SYNTH / "participants.csv")
    ids = set(personas.participant_id)
    real = pd.read_csv(REAL / "gemini/predictions.csv")
    matched = real[real.participant_id.isin(ids)].sort_values("row_index").reset_index(drop=True)
    old = pd.read_csv(OLD / "gemini/predictions.csv")
    old = old[old.participant_id.isin(ids)].sort_values("row_index").reset_index(drop=True)
    synth0 = pd.read_csv(SYNTH / "predictions_0shot.csv").sort_values("row_index").reset_index(drop=True)
    synth4 = pd.read_csv(SYNTH / "predictions_4shot.csv").sort_values("row_index").reset_index(drop=True)
    keys = ["row_index", "participant_id", "query_id", "tool", "raw_data_type"]
    real_manifest, synth_manifest = read_json(REAL / "job_manifest.json"), read_json(SYNTH / "job_manifest.json")
    by_id = {job["participant_id"]: job for job in real_manifest}
    out = {
        "description": "Local descriptive comparison of frozen runs, 2026-09-26. No new model calls. Different target labels across real and synthetic data.",
        "sources": {"human_data": str(PROJECT / "data/processed/four_label_dataset.csv"), "real_run": str(REAL), "synthetic_run": str(SYNTH)},
        "pairing": {
            "same_test_contexts": bool(matched[keys].equals(synth4[keys])),
            "same_0shot_4shot_test_truth": bool(synth0[keys + ["true_label_id"]].equals(synth4[keys + ["true_label_id"]])),
            "same_history_and_test_query_lists": all(all(job[key] == by_id[job["participant_id"]][key] for key in ["prompt_history_query_ids", "test_query_ids"]) for job in synth_manifest),
            "real20_predictions_identical_to_old40_subset": bool(matched.equals(old)),
        },
        "volumes": {"real201": volumes(source, real_manifest), "matched20": volumes(source, synth_manifest)},
        "metrics": {"real201_4shot": metrics(real), "real20_4shot": metrics(matched), "synthetic20_0shot": metrics(synth0), "synthetic20_4shot": metrics(synth4)},
        "costs_usd": {
            "real201": read_json(REAL / "cost_accounting.json"),
            "real20_4shot_reported": sum(read_json(REAL / f"checkpoints/gemini_{pid}_fold0.json")["provider_reported_cost_usd"] for pid in sorted(ids)),
            "synthetic20": read_json(SYNTH / "cost_accounting.json"),
        },
    }
    (HERE / "comparison_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    matched.to_csv(HERE / "real20_4shot_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"condition": name, **{k: v for k, v in values.items() if k != "truth_counts"}} for name, values in out["metrics"].items()]).to_csv(HERE / "comparison_metrics.csv", index=False, encoding="utf-8-sig")
    print(json.dumps({"pairing": out["pairing"], "volumes": out["volumes"], "metrics": out["metrics"], "real20_cost_usd": out["costs_usd"]["real20_4shot_reported"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
