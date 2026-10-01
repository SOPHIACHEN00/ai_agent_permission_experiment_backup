"""Fine-tune DistilBERT for the four-label permission prediction task.

The script deliberately keeps hyperparameter selection inside the outer training
participants.  The participant-held-out test set is evaluated only after a
candidate and an epoch count have been selected on an inner participant split.

This runner is self-contained apart from pandas, NumPy, PyTorch and
Transformers.  In particular, it does not require scikit-learn, which lets the
locally cached DistilBERT checkpoint run in the existing system Python runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ID_TO_LABEL = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}
LABEL_ORDER = [0, 1, 2, 3]
EXPECTED_DATASET_SHA256 = "4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463"
SERIALIZER_VERSION = "distilbert_permission_prompt_v1"

INPUT_COLUMNS = [
    "query",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "domain",
    "necessity_status",
    "age",
    "gender",
    "education",
    "ai_familiarity",
    "ai_frequency",
    "ai_trust",
    "privacy_importance",
    "concern_domain",
]
REQUIRED_COLUMNS = ["participant_id", "query_id", "label_id", "label_text", *INPUT_COLUMNS]
EXCLUDED_FROM_TEXT = ["participant_id", "query_id", "_row_id", "label_id", "label_text"]

AGE_GROUPS = {
    1: "18-24",
    2: "25-34",
    3: "35-44",
    4: "45-54",
    5: "55 or older",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        return None if not math.isfinite(value) else value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def ensure_new_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise FileExistsError(f"Output path exists and is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)


def normalize_scalar(value: Any) -> str:
    if pd.isna(value):
        return "unspecified"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return "unspecified"
    return text


def integer_code(value: Any) -> int | None:
    if pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not number.is_integer():
        return None
    return int(number)


def age_group_text(value: Any) -> str:
    code = integer_code(value)
    if code is None:
        return "unspecified"
    return AGE_GROUPS.get(code, f"survey age-group code {code}")


def rating_text(value: Any, dimension: str) -> str:
    code = integer_code(value)
    if code is None:
        return "unspecified"
    return f"{dimension} rating {code} out of 5"


def serialize_permission_row(row: Mapping[str, Any]) -> str:
    concern_domains = normalize_scalar(row["concern_domain"])
    if concern_domains != "unspecified":
        concern_domains = concern_domains.replace("|", ", ")

    text = (
        f"User request: {normalize_scalar(row['query'])}\n"
        f"Agent tool: {normalize_scalar(row['tool'])}\n"
        f"Requested data: {normalize_scalar(row['raw_data_type'])}\n"
        f"Generic data category: {normalize_scalar(row['generic_data_type'])}\n"
        f"Application domain: {normalize_scalar(row['domain'])}\n"
        f"Data necessity: {normalize_scalar(row['necessity_status'])}\n"
        "User profile: "
        f"age group {age_group_text(row['age'])}; "
        f"gender {normalize_scalar(row['gender'])}; "
        f"education {normalize_scalar(row['education'])}; "
        f"{rating_text(row['ai_familiarity'], 'AI familiarity')}; "
        f"{rating_text(row['ai_frequency'], 'AI usage frequency')}; "
        f"{rating_text(row['ai_trust'], 'AI trust')}; "
        f"{rating_text(row['privacy_importance'], 'privacy importance')}; "
        f"privacy concern domains {concern_domains}."
    )
    lowered = text.lower()
    if any(forbidden in lowered for forbidden in [" nan", ":nan", "=nan"]):
        raise ValueError("Serializer emitted a NaN token.")
    return text


def serialize_dataframe(df: pd.DataFrame) -> list[str]:
    return [serialize_permission_row(row) for row in df.to_dict(orient="records")]


def validate_input_dataset(data_path: Path, allow_hash_mismatch: bool) -> tuple[pd.DataFrame, str]:
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset does not exist: {data_path}")
    data_hash = sha256_file(data_path)
    if data_hash != EXPECTED_DATASET_SHA256 and not allow_hash_mismatch:
        raise ValueError(
            "Dataset SHA-256 does not match the audited four-label dataset. "
            f"Expected {EXPECTED_DATASET_SHA256}, got {data_hash}. "
            "Pass --allow-dataset-hash-mismatch only for an intentional new dataset."
        )

    df = pd.read_csv(data_path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    if "_row_id" in df.columns:
        raise ValueError("Dataset already contains reserved column '_row_id'.")
    df = df.copy()
    df["label_id"] = pd.to_numeric(df["label_id"], errors="raise").astype(int)
    labels = sorted(df["label_id"].unique().tolist())
    if labels != LABEL_ORDER:
        raise ValueError(f"Expected all four labels {LABEL_ORDER}; got {labels}")
    if df["participant_id"].isna().any():
        raise ValueError("participant_id contains missing values.")
    df["participant_id"] = df["participant_id"].astype(str)
    df["_row_id"] = np.arange(len(df), dtype=np.int64)
    return df, data_hash


def group_shuffle_split(
    df: pd.DataFrame,
    *,
    group_column: str,
    test_size: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match sklearn GroupShuffleSplit for one split without importing sklearn."""
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be strictly between 0 and 1.")
    groups = np.unique(df[group_column].astype(str).to_numpy())
    if len(groups) < 2:
        raise ValueError("At least two groups are required.")
    n_test = int(math.ceil(test_size * len(groups)))
    permutation = np.random.RandomState(seed).permutation(len(groups))
    test_groups = set(groups[permutation[:n_test]].tolist())
    is_test = df[group_column].astype(str).isin(test_groups)
    train_df = df.loc[~is_test].copy().reset_index(drop=True)
    test_df = df.loc[is_test].copy().reset_index(drop=True)
    return train_df, test_df


def label_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = df["label_id"].value_counts().reindex(LABEL_ORDER, fill_value=0)
    return {str(label): int(counts.loc[label]) for label in LABEL_ORDER}


def participant_ids(df: pd.DataFrame) -> list[str]:
    return sorted(df["participant_id"].astype(str).unique().tolist())


def validate_split(name: str, train_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    overlap = set(participant_ids(train_df)) & set(participant_ids(test_df))
    if overlap:
        raise ValueError(f"{name} has participant overlap: {sorted(overlap)[:5]}")
    for part_name, part_df in [("train", train_df), ("test", test_df)]:
        labels = sorted(part_df["label_id"].unique().tolist())
        if labels != LABEL_ORDER:
            raise ValueError(f"{name}/{part_name} does not contain all four labels: {labels}")


def make_splits(df: pd.DataFrame, validation_seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    outer_train, outer_test = group_shuffle_split(
        df,
        group_column="participant_id",
        test_size=0.2,
        seed=42,
    )
    validate_split("outer", outer_train, outer_test)
    inner_train, validation = group_shuffle_split(
        outer_train,
        group_column="participant_id",
        test_size=0.2,
        seed=validation_seed,
    )
    validate_split("inner", inner_train, validation)

    if len(df) == 16361 and df["participant_id"].nunique() == 201:
        expected = {
            "outer_train": (13038, 160),
            "outer_test": (3323, 41),
            "inner_train": (10417, 128),
            "validation": (2621, 32),
        }
        observed = {
            "outer_train": (len(outer_train), outer_train["participant_id"].nunique()),
            "outer_test": (len(outer_test), outer_test["participant_id"].nunique()),
            "inner_train": (len(inner_train), inner_train["participant_id"].nunique()),
            "validation": (len(validation), validation["participant_id"].nunique()),
        }
        if observed != expected:
            raise ValueError(f"Audited split counts changed. Expected {expected}, got {observed}")
    return inner_train, validation, outer_test


def split_manifest(
    df: pd.DataFrame,
    inner_train: pd.DataFrame,
    validation: pd.DataFrame,
    outer_test: pd.DataFrame,
    validation_seed: int,
) -> dict[str, Any]:
    outer_train_ids = sorted(set(participant_ids(inner_train)) | set(participant_ids(validation)))
    pieces = {
        "inner_train": inner_train,
        "validation": validation,
        "outer_test": outer_test,
    }
    manifest: dict[str, Any] = {
        "protocol": "participant_heldout_with_inner_participant_validation",
        "outer_seed": 42,
        "validation_seed": validation_seed,
        "outer_test_was_not_used_for_candidate_selection": True,
        "all_rows": int(len(df)),
        "all_participants": int(df["participant_id"].nunique()),
        "outer_train": {
            "rows": int(len(inner_train) + len(validation)),
            "participants": len(outer_train_ids),
            "participant_ids": outer_train_ids,
            "label_counts": {
                str(label): int(
                    (pd.concat([inner_train, validation], ignore_index=True)["label_id"] == label).sum()
                )
                for label in LABEL_ORDER
            },
        },
    }
    for name, part_df in pieces.items():
        manifest[name] = {
            "rows": int(len(part_df)),
            "participants": int(part_df["participant_id"].nunique()),
            "participant_ids": participant_ids(part_df),
            "label_counts": label_counts(part_df),
        }
    manifest["participant_overlap_checks"] = {
        "inner_train_vs_validation": len(set(participant_ids(inner_train)) & set(participant_ids(validation))),
        "outer_train_vs_test": len(set(outer_train_ids) & set(participant_ids(outer_test))),
    }
    return manifest


def confusion_matrix_four(y_true: Sequence[int], y_pred: Sequence[int]) -> np.ndarray:
    matrix = np.zeros((4, 4), dtype=np.int64)
    for truth, prediction in zip(y_true, y_pred, strict=True):
        matrix[int(truth), int(prediction)] += 1
    return matrix


def quadratic_weighted_kappa(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    observed = confusion_matrix_four(y_true, y_pred).astype(np.float64)
    n = observed.sum()
    if n == 0:
        return float("nan")
    true_hist = observed.sum(axis=1)
    pred_hist = observed.sum(axis=0)
    expected = np.outer(true_hist, pred_hist) / n
    indices = np.arange(4, dtype=np.float64)
    weights = ((indices[:, None] - indices[None, :]) ** 2) / 9.0
    denominator = float((weights * expected).sum())
    numerator = float((weights * observed).sum())
    if denominator == 0.0:
        return 1.0 if numerator == 0.0 else float("nan")
    return 1.0 - numerator / denominator


def classwise_statistics(y_true: np.ndarray, y_pred: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in LABEL_ORDER:
        true_positive = int(((y_true == label) & (y_pred == label)).sum())
        predicted_positive = int((y_pred == label).sum())
        actual_positive = int((y_true == label).sum())
        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "label_id": label,
                "label_text": ID_TO_LABEL[label],
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "support": actual_positive,
            }
        )
    return rows


def compute_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, Any]:
    truth = np.asarray(y_true, dtype=np.int64)
    prediction = np.asarray(y_pred, dtype=np.int64)
    if truth.shape != prediction.shape:
        raise ValueError(f"Shape mismatch: y_true={truth.shape}, y_pred={prediction.shape}")
    if len(truth) == 0:
        raise ValueError("Cannot compute metrics on zero rows.")
    class_rows = classwise_statistics(truth, prediction)
    deny_mask = np.isin(truth, [0, 1])
    over_mask = deny_mask & np.isin(prediction, [2, 3])
    non_persistent_allow = truth != 3
    persistent_over_mask = non_persistent_allow & (prediction == 3)
    return {
        "accuracy": float((truth == prediction).mean()),
        "macro_f1": float(np.mean([row["f1"] for row in class_rows])),
        "quadratic_weighted_kappa": float(quadratic_weighted_kappa(truth, prediction)),
        "over_sharing_rate": float(over_mask.sum() / deny_mask.sum()) if deny_mask.any() else 0.0,
        "over_sharing_count": int(over_mask.sum()),
        "over_sharing_denominator": int(deny_mask.sum()),
        "persistent_over_allow_rate": (
            float(persistent_over_mask.sum() / non_persistent_allow.sum())
            if non_persistent_allow.any()
            else 0.0
        ),
        "persistent_over_allow_count": int(persistent_over_mask.sum()),
        "persistent_over_allow_denominator": int(non_persistent_allow.sum()),
    }


def classification_report_dict(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, Any]:
    truth = np.asarray(y_true, dtype=np.int64)
    prediction = np.asarray(y_pred, dtype=np.int64)
    class_rows = classwise_statistics(truth, prediction)
    support_total = int(len(truth))
    result: dict[str, Any] = {
        ID_TO_LABEL[row["label_id"]]: {
            "precision": row["precision"],
            "recall": row["recall"],
            "f1-score": row["f1"],
            "support": row["support"],
        }
        for row in class_rows
    }
    result["accuracy"] = float((truth == prediction).mean())
    result["macro avg"] = {
        "precision": float(np.mean([row["precision"] for row in class_rows])),
        "recall": float(np.mean([row["recall"] for row in class_rows])),
        "f1-score": float(np.mean([row["f1"] for row in class_rows])),
        "support": support_total,
    }
    result["weighted avg"] = {
        "precision": float(sum(row["precision"] * row["support"] for row in class_rows) / support_total),
        "recall": float(sum(row["recall"] * row["support"] for row in class_rows) / support_total),
        "f1-score": float(sum(row["f1"] * row["support"] for row in class_rows) / support_total),
        "support": support_total,
    }
    return result


def save_confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], path: Path) -> None:
    matrix = confusion_matrix_four(y_true, y_pred)
    frame = pd.DataFrame(
        matrix,
        index=[f"true_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
        columns=[f"pred_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
    )
    frame.to_csv(path, encoding="utf-8")


def compute_class_weights(labels: Sequence[int], weighting: str) -> np.ndarray:
    labels_array = np.asarray(labels, dtype=np.int64)
    if weighting == "none":
        return np.ones(4, dtype=np.float32)
    if weighting != "balanced":
        raise ValueError(f"Unknown loss weighting: {weighting}")
    counts = np.bincount(labels_array, minlength=4).astype(np.float64)
    if np.any(counts == 0):
        raise ValueError(f"Cannot compute balanced weights with zero-count classes: {counts.tolist()}")
    return (len(labels_array) / (4.0 * counts)).astype(np.float32)


def set_all_seeds(seed: int) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except TypeError:
        torch.use_deterministic_algorithms(True)


class EncodedDataset(Dataset):
    def __init__(self, encodings: Mapping[str, torch.Tensor], labels: Sequence[int], row_ids: Sequence[int]):
        self.encodings = {key: value.to(dtype=torch.long) for key, value in encodings.items()}
        self.labels = torch.as_tensor(np.asarray(labels, dtype=np.int64), dtype=torch.long)
        self.row_ids = torch.as_tensor(np.asarray(row_ids, dtype=np.int64), dtype=torch.long)
        if len(self.labels) != len(self.row_ids):
            raise ValueError("labels and row_ids have different lengths")
        if any(len(value) != len(self.labels) for value in self.encodings.values()):
            raise ValueError("An encoded tensor has a different row count from labels")

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = {key: value[index] for key, value in self.encodings.items()}
        item["labels"] = self.labels[index]
        item["row_id"] = self.row_ids[index]
        return item


def tokenize_dataframe(tokenizer: Any, df: pd.DataFrame, max_length: int) -> tuple[EncodedDataset, list[str]]:
    texts = serialize_dataframe(df)
    encodings = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    tensors = {key: value for key, value in encodings.items() if key in {"input_ids", "attention_mask"}}
    dataset = EncodedDataset(tensors, df["label_id"].to_numpy(), df["_row_id"].to_numpy())
    return dataset, texts


def token_length_summary(tokenizer: Any, texts: Sequence[str], max_length: int, chunk_size: int = 512) -> dict[str, Any]:
    lengths: list[int] = []
    for start in range(0, len(texts), chunk_size):
        batch = list(texts[start : start + chunk_size])
        encoded = tokenizer(batch, padding=False, truncation=False, return_length=True)
        if "length" in encoded:
            lengths.extend(int(value) for value in encoded["length"])
        else:
            lengths.extend(len(value) for value in encoded["input_ids"])
    values = np.asarray(lengths, dtype=np.int64)
    return {
        "rows": int(len(values)),
        "minimum": int(values.min()),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "maximum": int(values.max()),
        "max_length": max_length,
        "rows_exceeding_max_length": int((values > max_length).sum()),
        "fraction_exceeding_max_length": float((values > max_length).mean()),
    }


def make_loader(dataset: Dataset, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
        pin_memory=False,
    )


def build_model(model_name: str, seed: int, local_files_only: bool) -> Any:
    set_all_seeds(seed)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=4,
        id2label=ID_TO_LABEL,
        label2id={text: label for label, text in ID_TO_LABEL.items()},
        local_files_only=local_files_only,
    )
    return model


def make_linear_schedule(optimizer: torch.optim.Optimizer, total_steps: int, warmup_ratio: float) -> Any:
    warmup_steps = int(round(total_steps * warmup_ratio))

    def scale(step: int) -> float:
        if warmup_steps > 0 and step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        remaining = total_steps - (step + 1)
        decay_steps = max(1, total_steps - warmup_steps)
        return max(0.0, float(remaining) / float(decay_steps))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=scale)


def train_one_epoch(
    model: Any,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    class_weights: torch.Tensor,
    device: torch.device,
    max_grad_norm: float,
    max_batches: int | None = None,
) -> tuple[float, int]:
    model.train()
    loss_sum = 0.0
    row_count = 0
    steps = 0
    for batch_index, batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        labels = batch["labels"].to(device)
        inputs = {
            key: value.to(device)
            for key, value in batch.items()
            if key not in {"labels", "row_id"}
        }
        optimizer.zero_grad(set_to_none=True)
        logits = model(**inputs).logits
        loss = F.cross_entropy(logits, labels, weight=class_weights)
        if not torch.isfinite(loss):
            raise FloatingPointError(f"Non-finite training loss: {loss.item()}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        scheduler.step()
        batch_rows = int(labels.shape[0])
        loss_sum += float(loss.detach().cpu()) * batch_rows
        row_count += batch_rows
        steps += 1
    if row_count == 0:
        raise RuntimeError("Training loader produced zero rows.")
    return loss_sum / row_count, steps


@dataclass
class EvaluationOutput:
    metrics: dict[str, Any]
    loss: float
    row_ids: np.ndarray
    labels: np.ndarray
    predictions: np.ndarray
    probabilities: np.ndarray


def evaluate_model(
    model: Any,
    loader: DataLoader,
    class_weights: torch.Tensor,
    device: torch.device,
    max_batches: int | None = None,
) -> EvaluationOutput:
    model.eval()
    loss_sum = 0.0
    row_count = 0
    row_ids: list[np.ndarray] = []
    labels_all: list[np.ndarray] = []
    probabilities_all: list[np.ndarray] = []
    with torch.no_grad():
        for batch_index, batch in enumerate(loader):
            if max_batches is not None and batch_index >= max_batches:
                break
            labels = batch["labels"].to(device)
            inputs = {
                key: value.to(device)
                for key, value in batch.items()
                if key not in {"labels", "row_id"}
            }
            logits = model(**inputs).logits
            loss = F.cross_entropy(logits, labels, weight=class_weights)
            probabilities = torch.softmax(logits, dim=-1)
            batch_rows = int(labels.shape[0])
            loss_sum += float(loss.detach().cpu()) * batch_rows
            row_count += batch_rows
            row_ids.append(batch["row_id"].cpu().numpy())
            labels_all.append(labels.cpu().numpy())
            probabilities_all.append(probabilities.cpu().numpy())
    if row_count == 0:
        raise RuntimeError("Evaluation loader produced zero rows.")
    row_id_array = np.concatenate(row_ids).astype(np.int64)
    label_array = np.concatenate(labels_all).astype(np.int64)
    probability_array = np.concatenate(probabilities_all).astype(np.float64)
    prediction_array = probability_array.argmax(axis=1).astype(np.int64)
    return EvaluationOutput(
        metrics=compute_metrics(label_array, prediction_array),
        loss=loss_sum / row_count,
        row_ids=row_id_array,
        labels=label_array,
        predictions=prediction_array,
        probabilities=probability_array,
    )


def metric_rank(metrics: Mapping[str, Any]) -> tuple[float, float, float, float, float]:
    def finite_or_negative_infinity(value: Any) -> float:
        numeric = float(value)
        return numeric if math.isfinite(numeric) else -math.inf

    return (
        finite_or_negative_infinity(metrics["macro_f1"]),
        finite_or_negative_infinity(metrics["quadratic_weighted_kappa"]),
        finite_or_negative_infinity(metrics["accuracy"]),
        -finite_or_negative_infinity(metrics["over_sharing_rate"]),
        -finite_or_negative_infinity(metrics["persistent_over_allow_rate"]),
    )


@dataclass
class CandidateOutput:
    candidate_id: str
    learning_rate: float
    loss_weighting: str
    best_epoch: int
    best_evaluation: EvaluationOutput
    history: list[dict[str, Any]]
    stopped_early: bool


def train_candidate(
    *,
    candidate_id: str,
    model_name: str,
    train_dataset: EncodedDataset,
    validation_dataset: EncodedDataset,
    learning_rate: float,
    loss_weighting: str,
    train_batch_size: int,
    eval_batch_size: int,
    max_epochs: int,
    patience: int,
    weight_decay: float,
    warmup_ratio: float,
    max_grad_norm: float,
    seed: int,
    device: torch.device,
    local_files_only: bool,
    max_train_batches: int | None = None,
    max_eval_batches: int | None = None,
) -> CandidateOutput:
    model = build_model(model_name, seed, local_files_only).to(device)
    weights_array = compute_class_weights(train_dataset.labels.numpy(), loss_weighting)
    class_weights = torch.as_tensor(weights_array, dtype=torch.float32, device=device)
    train_loader = make_loader(train_dataset, train_batch_size, True, seed)
    validation_loader = make_loader(validation_dataset, eval_batch_size, False, seed)
    effective_steps_per_epoch = len(train_loader)
    if max_train_batches is not None:
        effective_steps_per_epoch = min(effective_steps_per_epoch, max_train_batches)
    total_steps = max(1, effective_steps_per_epoch * max_epochs)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = make_linear_schedule(optimizer, total_steps, warmup_ratio)

    history: list[dict[str, Any]] = []
    best_epoch = 0
    best_evaluation: EvaluationOutput | None = None
    epochs_without_improvement = 0
    stopped_early = False

    for epoch in range(1, max_epochs + 1):
        epoch_start = time.perf_counter()
        train_loss, steps = train_one_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            class_weights,
            device,
            max_grad_norm,
            max_batches=max_train_batches,
        )
        evaluation = evaluate_model(
            model,
            validation_loader,
            class_weights,
            device,
            max_batches=max_eval_batches,
        )
        elapsed = time.perf_counter() - epoch_start
        history_row = {
            "phase": "candidate",
            "candidate_id": candidate_id,
            "learning_rate": learning_rate,
            "loss_weighting": loss_weighting,
            "epoch": epoch,
            "optimizer_steps": steps,
            "train_loss": train_loss,
            "validation_loss": evaluation.loss,
            **evaluation.metrics,
            "elapsed_seconds": elapsed,
        }
        history.append(history_row)
        print(
            f"[{candidate_id}] epoch {epoch}/{max_epochs}: "
            f"train_loss={train_loss:.4f}, val_macro_f1={evaluation.metrics['macro_f1']:.4f}, "
            f"val_accuracy={evaluation.metrics['accuracy']:.4f}, seconds={elapsed:.1f}",
            flush=True,
        )

        if best_evaluation is None or metric_rank(evaluation.metrics) > metric_rank(best_evaluation.metrics):
            best_epoch = epoch
            best_evaluation = evaluation
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= patience:
            stopped_early = True
            break

    if best_evaluation is None:
        raise RuntimeError(f"Candidate {candidate_id} produced no validation evaluation.")
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return CandidateOutput(
        candidate_id=candidate_id,
        learning_rate=learning_rate,
        loss_weighting=loss_weighting,
        best_epoch=best_epoch,
        best_evaluation=best_evaluation,
        history=history,
        stopped_early=stopped_early,
    )


def select_candidate(candidates: Sequence[CandidateOutput]) -> CandidateOutput:
    if not candidates:
        raise ValueError("No candidate outputs were provided.")
    return max(candidates, key=lambda candidate: metric_rank(candidate.best_evaluation.metrics))


def prediction_frame(source_df: pd.DataFrame, evaluation: EvaluationOutput) -> pd.DataFrame:
    metadata_columns = [
        "_row_id",
        "participant_id",
        "query_id",
        "query",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
        "label_id",
        "label_text",
    ]
    indexed = source_df.set_index("_row_id", drop=False)
    rows = indexed.loc[evaluation.row_ids, metadata_columns].reset_index(drop=True).copy()
    observed_labels = rows["label_id"].to_numpy(dtype=np.int64)
    if not np.array_equal(observed_labels, evaluation.labels):
        raise ValueError("Evaluation labels do not align with source rows.")
    rows.insert(0, "model", "distilbert_flat_four_class")
    rows.insert(1, "variant", "tuned")
    rows["pred_label_id"] = evaluation.predictions
    rows["pred_label_text"] = [ID_TO_LABEL[int(label)] for label in evaluation.predictions]
    for label in LABEL_ORDER:
        rows[f"prob_label_{label}"] = evaluation.probabilities[:, label]
    return rows


def candidate_summary(candidate: CandidateOutput) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "learning_rate": candidate.learning_rate,
        "loss_weighting": candidate.loss_weighting,
        "best_epoch": candidate.best_epoch,
        "epochs_completed": len(candidate.history),
        "stopped_early": candidate.stopped_early,
        "validation_loss": candidate.best_evaluation.loss,
        **candidate.best_evaluation.metrics,
    }


def configure_runtime(torch_threads: int) -> None:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if torch_threads > 0:
        torch.set_num_threads(torch_threads)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass


def choose_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable.")
    return device


def runtime_manifest(device: torch.device) -> dict[str, Any]:
    import tokenizers
    import transformers

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "tokenizers": tokenizers.__version__,
        "device": str(device),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_version": torch.version.cuda,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torch_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(),
    }


def save_serialization_manifest(
    path: Path,
    tokenizer: Any,
    train_texts: Sequence[str],
    max_length: int,
) -> dict[str, Any]:
    summary = token_length_summary(tokenizer, train_texts, max_length)
    payload = {
        "serializer_version": SERIALIZER_VERSION,
        "input_columns": INPUT_COLUMNS,
        "excluded_columns": EXCLUDED_FROM_TEXT,
        "missing_value_text": "unspecified",
        "age_group_mapping": {str(key): value for key, value in AGE_GROUPS.items()},
        "likert_representation": "<dimension> rating <integer> out of 5",
        "concern_domain_separator": "'|' is serialized as ', '",
        "outer_train_token_lengths": summary,
        "example_without_label_or_ids": train_texts[0],
    }
    write_json(path, payload)
    return payload


def refit_on_outer_train(
    *,
    model_name: str,
    train_dataset: EncodedDataset,
    learning_rate: float,
    loss_weighting: str,
    epochs: int,
    train_batch_size: int,
    weight_decay: float,
    warmup_ratio: float,
    max_grad_norm: float,
    seed: int,
    device: torch.device,
    local_files_only: bool,
) -> tuple[Any, list[dict[str, Any]], np.ndarray]:
    model = build_model(model_name, seed, local_files_only).to(device)
    weights_array = compute_class_weights(train_dataset.labels.numpy(), loss_weighting)
    class_weights = torch.as_tensor(weights_array, dtype=torch.float32, device=device)
    loader = make_loader(train_dataset, train_batch_size, True, seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    scheduler = make_linear_schedule(optimizer, max(1, len(loader) * epochs), warmup_ratio)
    history: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        start = time.perf_counter()
        train_loss, steps = train_one_epoch(
            model,
            loader,
            optimizer,
            scheduler,
            class_weights,
            device,
            max_grad_norm,
        )
        elapsed = time.perf_counter() - start
        history.append(
            {
                "phase": "final_refit",
                "candidate_id": "selected",
                "learning_rate": learning_rate,
                "loss_weighting": loss_weighting,
                "epoch": epoch,
                "optimizer_steps": steps,
                "train_loss": train_loss,
                "elapsed_seconds": elapsed,
            }
        )
        print(
            f"[final refit] epoch {epoch}/{epochs}: train_loss={train_loss:.4f}, seconds={elapsed:.1f}",
            flush=True,
        )
    return model, history, weights_array


def run_smoke(
    *,
    args: argparse.Namespace,
    tokenizer: Any,
    inner_train: pd.DataFrame,
    validation: pd.DataFrame,
    device: torch.device,
    output_dir: Path,
) -> None:
    train_dataset, train_texts = tokenize_dataframe(tokenizer, inner_train, args.max_length)
    validation_dataset, _ = tokenize_dataframe(tokenizer, validation, args.max_length)
    start = time.perf_counter()
    candidate = train_candidate(
        candidate_id="smoke_lr_" + format(args.learning_rates[0], ".0e"),
        model_name=args.model_name,
        train_dataset=train_dataset,
        validation_dataset=validation_dataset,
        learning_rate=args.learning_rates[0],
        loss_weighting=args.loss_weightings[0],
        train_batch_size=args.train_batch_size,
        eval_batch_size=args.eval_batch_size,
        max_epochs=1,
        patience=1,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        max_grad_norm=args.max_grad_norm,
        seed=args.seed,
        device=device,
        local_files_only=args.local_files_only,
        max_train_batches=args.smoke_train_batches,
        max_eval_batches=args.smoke_eval_batches,
    )
    elapsed = time.perf_counter() - start
    payload = {
        "status": "smoke_completed",
        "official_result": False,
        "frozen_test_accessed": False,
        "train_batches": args.smoke_train_batches,
        "validation_batches": args.smoke_eval_batches,
        "elapsed_seconds": elapsed,
        "candidate": candidate_summary(candidate),
        "serializer_example": train_texts[0],
        "note": "Smoke metrics cover only a few batches and must not be reported as experiment results.",
    }
    write_json(output_dir / "smoke_summary.json", json_safe(payload))
    print("Smoke test completed. The frozen test set was not tokenized or evaluated.", flush=True)


def run_experiment(args: argparse.Namespace) -> None:
    output_dir = args.out.resolve()
    ensure_new_output_directory(output_dir)
    start_time = time.perf_counter()
    configure_runtime(args.torch_threads)
    device = choose_device(args.device)
    data_path = args.data.resolve()
    script_path = Path(__file__).resolve()

    df, dataset_hash = validate_input_dataset(data_path, args.allow_dataset_hash_mismatch)
    inner_train, validation, outer_test = make_splits(df, args.validation_seed)
    outer_train = (
        pd.concat([inner_train, validation], ignore_index=True)
        .sort_values("_row_id")
        .reset_index(drop=True)
    )
    if len(outer_train) + len(outer_test) != len(df):
        raise ValueError("Outer split does not cover the full dataset.")

    source_dir = output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(script_path, source_dir / script_path.name)
    write_json(
        output_dir / "split_manifest.json",
        split_manifest(df, inner_train, validation, outer_test, args.validation_seed),
    )
    write_json(output_dir / "environment.json", json_safe(runtime_manifest(device)))

    print(
        f"Loading tokenizer {args.model_name!r} (local_files_only={args.local_files_only}) on {device}.",
        flush=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        local_files_only=args.local_files_only,
        use_fast=True,
    )

    if args.smoke:
        run_smoke(
            args=args,
            tokenizer=tokenizer,
            inner_train=inner_train,
            validation=validation,
            device=device,
            output_dir=output_dir,
        )
        write_json(
            output_dir / "run_config.json",
            json_safe(
                {
                    "status": "smoke_completed",
                    "official_result": False,
                    "data_path": str(data_path),
                    "dataset_sha256": dataset_hash,
                    "script_sha256": sha256_file(script_path),
                    "arguments": vars(args),
                }
            ),
        )
        return

    inner_train_dataset, inner_train_texts = tokenize_dataframe(tokenizer, inner_train, args.max_length)
    validation_dataset, _ = tokenize_dataframe(tokenizer, validation, args.max_length)
    serialization_payload = save_serialization_manifest(
        output_dir / "serialization_manifest.json",
        tokenizer,
        inner_train_texts,
        args.max_length,
    )

    candidate_outputs: list[CandidateOutput] = []
    for learning_rate in args.learning_rates:
        for loss_weighting in args.loss_weightings:
            candidate_id = f"lr_{learning_rate:.0e}_{loss_weighting}".replace("+", "")
            print(f"Starting candidate {candidate_id}.", flush=True)
            candidate_outputs.append(
                train_candidate(
                    candidate_id=candidate_id,
                    model_name=args.model_name,
                    train_dataset=inner_train_dataset,
                    validation_dataset=validation_dataset,
                    learning_rate=learning_rate,
                    loss_weighting=loss_weighting,
                    train_batch_size=args.train_batch_size,
                    eval_batch_size=args.eval_batch_size,
                    max_epochs=args.max_epochs,
                    patience=args.early_stopping_patience,
                    weight_decay=args.weight_decay,
                    warmup_ratio=args.warmup_ratio,
                    max_grad_norm=args.max_grad_norm,
                    seed=args.seed,
                    device=device,
                    local_files_only=args.local_files_only,
                )
            )

    selected = select_candidate(candidate_outputs)
    print(
        f"Selected {selected.candidate_id}, epoch {selected.best_epoch}, "
        f"validation macro-F1={selected.best_evaluation.metrics['macro_f1']:.4f}.",
        flush=True,
    )
    candidate_rows = [candidate_summary(candidate) for candidate in candidate_outputs]
    pd.DataFrame(candidate_rows).to_csv(output_dir / "candidate_results.csv", index=False, encoding="utf-8")
    all_history = [row for candidate in candidate_outputs for row in candidate.history]
    pd.DataFrame(all_history).to_csv(output_dir / "training_curves.csv", index=False, encoding="utf-8")
    validation_predictions = prediction_frame(validation, selected.best_evaluation)
    validation_predictions.to_csv(output_dir / "validation_predictions.csv", index=False, encoding="utf-8")
    selected_payload = {
        "selection_source": "inner participant-held-out validation only",
        "selection_order": [
            "macro_f1 descending",
            "quadratic_weighted_kappa descending",
            "accuracy descending",
            "over_sharing_rate ascending",
            "persistent_over_allow_rate ascending",
        ],
        **candidate_summary(selected),
    }
    write_json(output_dir / "selected_hyperparameters.json", json_safe(selected_payload))

    del inner_train_dataset, validation_dataset
    outer_train_dataset, outer_train_texts = tokenize_dataframe(tokenizer, outer_train, args.max_length)
    final_model, final_history, outer_train_weights = refit_on_outer_train(
        model_name=args.model_name,
        train_dataset=outer_train_dataset,
        learning_rate=selected.learning_rate,
        loss_weighting=selected.loss_weighting,
        epochs=selected.best_epoch,
        train_batch_size=args.train_batch_size,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        max_grad_norm=args.max_grad_norm,
        seed=args.seed,
        device=device,
        local_files_only=args.local_files_only,
    )
    pd.DataFrame([*all_history, *final_history]).to_csv(
        output_dir / "training_history.csv", index=False, encoding="utf-8"
    )

    # The frozen test is tokenized and evaluated only after hyperparameters and
    # the final model are fixed.
    test_dataset, test_texts = tokenize_dataframe(tokenizer, outer_test, args.max_length)
    test_loader = make_loader(test_dataset, args.eval_batch_size, False, args.seed)
    test_weights = torch.as_tensor(outer_train_weights, dtype=torch.float32, device=device)
    test_evaluation = evaluate_model(final_model, test_loader, test_weights, device)
    if len(test_evaluation.labels) != len(outer_test):
        raise ValueError("Frozen test evaluation did not return all rows.")
    test_rows = prediction_frame(outer_test, test_evaluation)
    if len(test_rows) != 3323 or test_rows["_row_id"].duplicated().any():
        raise ValueError("Frozen test predictions failed the audited row-count/uniqueness check.")

    metrics_row = {
        "model": "distilbert_flat_four_class",
        "variant": "tuned",
        "test_loss": test_evaluation.loss,
        **test_evaluation.metrics,
    }
    pd.DataFrame([metrics_row]).to_csv(output_dir / "test_metrics.csv", index=False, encoding="utf-8")
    test_rows.to_csv(output_dir / "test_predictions.csv", index=False, encoding="utf-8")
    save_confusion_matrix(
        test_evaluation.labels,
        test_evaluation.predictions,
        output_dir / "confusion_matrix_distilbert_flat_tuned.csv",
    )
    write_json(
        output_dir / "classification_report_distilbert_flat_tuned.json",
        json_safe(classification_report_dict(test_evaluation.labels, test_evaluation.predictions)),
    )

    if args.save_final_model:
        final_model_dir = output_dir / "final_model"
        final_model.save_pretrained(final_model_dir)
        tokenizer.save_pretrained(final_model_dir)

    serialization_payload["outer_train_token_lengths"] = token_length_summary(
        tokenizer, outer_train_texts, args.max_length
    )
    serialization_payload["outer_test_token_lengths"] = token_length_summary(
        tokenizer, test_texts, args.max_length
    )
    write_json(output_dir / "serialization_manifest.json", json_safe(serialization_payload))

    elapsed_total = time.perf_counter() - start_time
    diagnostics = {
        "run_completed": True,
        "smoke": False,
        "losses_all_finite": bool(
            all(math.isfinite(float(row["train_loss"])) for row in [*all_history, *final_history])
            and math.isfinite(test_evaluation.loss)
        ),
        "candidate_epochs_completed": {
            candidate.candidate_id: len(candidate.history) for candidate in candidate_outputs
        },
        "early_stopping_triggered": {
            candidate.candidate_id: candidate.stopped_early for candidate in candidate_outputs
        },
        "selected_candidate": selected.candidate_id,
        "selected_epoch": selected.best_epoch,
        "final_refit_completed": True,
        "frozen_test_evaluations": 1,
        "elapsed_seconds": elapsed_total,
    }
    write_json(output_dir / "training_diagnostics.json", json_safe(diagnostics))

    model_config = getattr(final_model, "config", None)
    commit_hash = getattr(model_config, "_commit_hash", None) if model_config is not None else None
    run_config = {
        "status": "completed",
        "official_result": True,
        "model": "distilbert_flat_four_class",
        "model_name": args.model_name,
        "resolved_model_commit": commit_hash,
        "local_files_only": args.local_files_only,
        "data_path": str(data_path),
        "dataset_sha256": dataset_hash,
        "script_path": str(script_path),
        "script_sha256": sha256_file(script_path),
        "source_snapshot_sha256": sha256_file(source_dir / script_path.name),
        "serializer_version": SERIALIZER_VERSION,
        "input_columns": INPUT_COLUMNS,
        "outer_split": {"kind": "participant_heldout", "test_size": 0.2, "seed": 42},
        "inner_split": {
            "kind": "participant_heldout",
            "validation_size": 0.2,
            "seed": args.validation_seed,
        },
        "learning_rates": args.learning_rates,
        "loss_weightings": args.loss_weightings,
        "train_batch_size": args.train_batch_size,
        "eval_batch_size": args.eval_batch_size,
        "max_epochs": args.max_epochs,
        "early_stopping_patience": args.early_stopping_patience,
        "weight_decay": args.weight_decay,
        "warmup_ratio": args.warmup_ratio,
        "max_grad_norm": args.max_grad_norm,
        "max_length": args.max_length,
        "seed": args.seed,
        "selected": selected_payload,
        "outer_train_class_weights": outer_train_weights.tolist(),
        "test_metrics": metrics_row,
        "elapsed_seconds": elapsed_total,
        "runtime": runtime_manifest(device),
    }
    write_json(output_dir / "run_config.json", json_safe(run_config))
    print(pd.DataFrame([metrics_row]).to_string(index=False), flush=True)
    print(f"Completed in {elapsed_total / 60.0:.1f} minutes. Artifacts: {output_dir}", flush=True)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return parsed


def probability(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("Value must be between 0 and 1.")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune a flat four-class DistilBERT permission classifier."
    )
    parser.add_argument("--data", required=True, type=Path, help="Path to four_label_dataset.csv")
    parser.add_argument("--out", required=True, type=Path, help="New, empty output directory")
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--learning-rates", nargs="+", type=float, default=[2e-5, 5e-5])
    parser.add_argument(
        "--loss-weightings",
        nargs="+",
        choices=["balanced", "none"],
        default=["balanced"],
    )
    parser.add_argument("--train-batch-size", type=positive_int, default=32)
    parser.add_argument("--eval-batch-size", type=positive_int, default=64)
    parser.add_argument("--max-epochs", type=positive_int, default=2)
    parser.add_argument("--early-stopping-patience", type=positive_int, default=2)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=probability, default=0.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--max-length", type=positive_int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-seed", type=int, default=20260809)
    parser.add_argument("--torch-threads", type=positive_int, default=14)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or another torch device")
    parser.add_argument(
        "--local-files-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Forbid model/tokenizer network access (default: true).",
    )
    parser.add_argument(
        "--save-final-model",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save the selected final checkpoint (default: true).",
    )
    parser.add_argument(
        "--allow-dataset-hash-mismatch",
        action="store_true",
        help="Allow an intentional dataset other than the audited canonical CSV.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a few inner-train/validation batches; never evaluate the frozen test.",
    )
    parser.add_argument("--smoke-train-batches", type=positive_int, default=2)
    parser.add_argument("--smoke-eval-batches", type=positive_int, default=2)
    args = parser.parse_args(argv)
    if any(rate <= 0.0 for rate in args.learning_rates):
        parser.error("All learning rates must be positive.")
    if args.weight_decay < 0.0:
        parser.error("--weight-decay must be non-negative.")
    if args.max_grad_norm <= 0.0:
        parser.error("--max-grad-norm must be positive.")
    return args


def main() -> None:
    args = parse_args()
    run_experiment(args)


if __name__ == "__main__":
    main()
