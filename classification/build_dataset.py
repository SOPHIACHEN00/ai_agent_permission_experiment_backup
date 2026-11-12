import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


LABEL_TO_ID = {
    "No, never share": 0,
    "No, but ask me next time": 1,
    "Yes, but ask me next time": 2,
    "Yes, always share": 3,
}

ID_TO_LABEL = {value: key for key, value in LABEL_TO_ID.items()}


def normalize_text(value):
    value = "" if value is None else str(value)
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def split_data_list(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def loose_contains(left, right):
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return False
    return left_norm == right_norm or left_norm.startswith(right_norm) or right_norm.startswith(left_norm)


def load_generic_data_type_map(data_types_path):
    mapping = {}
    raw_catalog = []
    with data_types_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            generic = row["Generic Data Type"].strip()
            raw_field = row["Raw Data Type"].strip()
            raw_catalog.append((generic, raw_field))
            for raw_item in split_data_list(raw_field):
                mapping[normalize_text(raw_item)] = generic
    return mapping, raw_catalog


def map_generic_data_type(raw_data_type, exact_mapping, raw_catalog):
    norm = normalize_text(raw_data_type)
    if norm in exact_mapping:
        return exact_mapping[norm]
    for generic, raw_field in raw_catalog:
        if norm and norm in normalize_text(raw_field):
            return generic
    return "Unknown"


def build_query_lookup(queries):
    return {int(query["id"]): query for query in queries}


def query_data_sets(query):
    necessary = set()
    incorrect = set()
    for field in ["datatype", "data_tool1", "data_tool2", "data_MIRA"]:
        value = query.get(field, "")
        if isinstance(value, list):
            necessary.update(item.strip() for item in value if str(item).strip())
        else:
            necessary.update(split_data_list(value))
    for field in ["data_incorrect", "data_tool1_incorrect", "data_tool2_incorrect", "data_MIRA_incorrect"]:
        incorrect.update(split_data_list(query.get(field, "")))
    return necessary, incorrect


def necessity_status(raw_data_type, query):
    necessary, incorrect = query_data_sets(query)
    if any(loose_contains(raw_data_type, item) for item in incorrect):
        return "incorrect_explicit"
    if any(loose_contains(raw_data_type, item) for item in necessary):
        return "necessary"
    return "unknown"


def parse_permission_key(permission_key):
    if "," not in permission_key:
        return permission_key.strip(), ""
    tool, raw_data_type = permission_key.split(",", 1)
    return tool.strip(), raw_data_type.strip()


def build_rows(repo_path):
    data_dir = repo_path / "data"
    user_study_path = data_dir / "user_study.json"
    queries_path = repo_path / "queries.json"
    data_types_path = data_dir / "data_types.csv"

    with user_study_path.open("r", encoding="utf-8") as handle:
        users = json.load(handle)
    with queries_path.open("r", encoding="utf-8") as handle:
        queries = json.load(handle)

    query_lookup = build_query_lookup(queries)
    exact_mapping, raw_catalog = load_generic_data_type_map(data_types_path)

    rows = []
    skipped_labels = Counter()
    skipped_missing_query = 0

    for user in users:
        if user.get("Valid") is not True:
            continue

        participant_id = user.get("uuid", "")
        concern_domain = "|".join(user.get("concern_domain") or [])
        profile = {
            "participant_id": participant_id,
            "age": user.get("age", ""),
            "gender": user.get("gender", ""),
            "education": user.get("education", ""),
            "ai_familiarity": user.get("aiFamiliarity", ""),
            "ai_frequency": user.get("aiFrequency", ""),
            "ai_trust": user.get("aiTrust", ""),
            "privacy_importance": user.get("privacyImportance", ""),
            "concern_domain": concern_domain,
        }

        for response in user.get("task3", []):
            query_id = int(response["id"])
            query = query_lookup.get(query_id)
            if query is None:
                skipped_missing_query += 1
                continue

            for permission_key, label_text in response.get("answer", {}).items():
                if label_text not in LABEL_TO_ID:
                    skipped_labels[label_text] += 1
                    continue

                tool, raw_data_type = parse_permission_key(permission_key)
                generic_data_type = map_generic_data_type(raw_data_type, exact_mapping, raw_catalog)
                status = necessity_status(raw_data_type, query)

                row = {
                    **profile,
                    "query_id": query_id,
                    "query": query.get("query", ""),
                    "domain": query.get("domain", ""),
                    "tool": tool,
                    "raw_data_type": raw_data_type,
                    "generic_data_type": generic_data_type,
                    "necessity_status": status,
                    "label_text": label_text,
                    "label_id": LABEL_TO_ID[label_text],
                }
                rows.append(row)

    return pd.DataFrame(rows), {
        "skipped_labels": dict(skipped_labels),
        "skipped_missing_query": skipped_missing_query,
    }


def write_outputs(df, out_path, build_info):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    summary = {
        "n_rows": int(len(df)),
        "n_participants": int(df["participant_id"].nunique()),
        "n_queries": int(df["query_id"].nunique()),
        "label_counts": {ID_TO_LABEL[int(k)]: int(v) for k, v in df["label_id"].value_counts().sort_index().items()},
        "necessity_counts": {str(k): int(v) for k, v in df["necessity_status"].value_counts().items()},
        "domain_counts": {str(k): int(v) for k, v in df["domain"].value_counts().items()},
        "label_mapping": {str(k): int(v) for k, v in LABEL_TO_ID.items()},
        "build_info": build_info,
    }
    summary_path = out_path.with_name("dataset_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    label_path = out_path.with_name("label_mapping.json")
    label_path.write_text(json.dumps(LABEL_TO_ID, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_dataset(df):
    required = ["participant_id", "query_id", "tool", "raw_data_type", "label_id"]
    missing_columns = [column for column in required if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    if df[required].isna().any().any():
        raise ValueError("Required columns contain null values")
    labels = set(df["label_id"].unique())
    if labels != {0, 1, 2, 3}:
        raise ValueError(f"Expected all four labels 0..3, got {sorted(labels)}")


def main():
    parser = argparse.ArgumentParser(description="Build four-label permission benchmark dataset.")
    parser.add_argument("--repo", required=True, type=Path, help="Path to cloned ai-agent-permissions repo.")
    parser.add_argument("--out", required=True, type=Path, help="Output CSV path.")
    args = parser.parse_args()

    df, build_info = build_rows(args.repo)
    validate_dataset(df)
    write_outputs(df, args.out, build_info)
    print(f"Wrote {len(df)} rows to {args.out}")


if __name__ == "__main__":
    main()
