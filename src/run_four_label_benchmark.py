import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ID_TO_LABEL = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}

LABEL_ORDER = [0, 1, 2, 3]

TEXT_COLUMNS = ["query", "tool", "raw_data_type", "generic_data_type", "domain"]
CATEGORICAL_COLUMNS = [
    "domain",
    "tool",
    "generic_data_type",
    "necessity_status",
    "gender",
    "education",
    "concern_domain",
]
NUMERIC_COLUMNS = ["age", "ai_familiarity", "ai_frequency", "ai_trust", "privacy_importance"]


def add_feature_columns(df):
    df = df.copy()
    for column in TEXT_COLUMNS + CATEGORICAL_COLUMNS:
        df[column] = df[column].fillna("").astype(str)
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(-1)
    df["text_features"] = df[TEXT_COLUMNS].agg(" ".join, axis=1)
    return df


def make_one_hot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore")


def make_preprocessor():
    return ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000), "text_features"),
            ("categorical", make_one_hot_encoder(), CATEGORICAL_COLUMNS),
            ("numeric", "passthrough", NUMERIC_COLUMNS),
        ],
        remainder="drop",
    )


def make_lr(multiclass=False):
    kwargs = {
        "class_weight": "balanced",
        "max_iter": 2000,
        "solver": "lbfgs",
        "random_state": 42,
    }
    return LogisticRegression(**kwargs)


def make_pipeline(multiclass=False):
    return Pipeline(
        steps=[
            ("features", make_preprocessor()),
            ("clf", make_lr(multiclass=multiclass)),
        ]
    )


class FlatFourClassModel:
    name = "flat_four_class_lr"

    def __init__(self):
        self.pipeline = make_pipeline(multiclass=True)

    def fit(self, train_df):
        self.pipeline.fit(train_df, train_df["label_id"])
        return self

    def predict(self, test_df):
        return self.pipeline.predict(test_df).astype(int)


class OrdinalLogisticModel:
    name = "ordinal_lr"

    def __init__(self):
        self.thresholds = [0, 1, 2]
        self.models = []

    def fit(self, train_df):
        self.models = []
        y = train_df["label_id"].to_numpy()
        for threshold in self.thresholds:
            binary_y = (y > threshold).astype(int)
            model = make_pipeline(multiclass=False)
            model.fit(train_df, binary_y)
            self.models.append(model)
        return self

    @staticmethod
    def positive_probability(model, test_df):
        classes = list(model.named_steps["clf"].classes_)
        if 1 not in classes:
            return np.zeros(len(test_df))
        positive_index = classes.index(1)
        return model.predict_proba(test_df)[:, positive_index]

    def predict(self, test_df):
        probabilities = [self.positive_probability(model, test_df) for model in self.models]
        threshold_predictions = [(proba >= 0.5).astype(int) for proba in probabilities]
        return np.sum(threshold_predictions, axis=0).astype(int)


class FactoredLogisticModel:
    name = "factored_lr"

    def __init__(self):
        self.access_model = make_pipeline(multiclass=False)
        self.persistence_model = make_pipeline(multiclass=False)

    def fit(self, train_df):
        y = train_df["label_id"].to_numpy()
        access_y = np.isin(y, [2, 3]).astype(int)  # 1 = allow, 0 = deny
        persistence_y = np.isin(y, [0, 3]).astype(int)  # 1 = persist, 0 = ask_again
        self.access_model.fit(train_df, access_y)
        self.persistence_model.fit(train_df, persistence_y)
        return self

    def predict(self, test_df):
        access = self.access_model.predict(test_df).astype(int)
        persistence = self.persistence_model.predict(test_df).astype(int)
        preds = np.zeros(len(test_df), dtype=int)
        preds[(access == 1) & (persistence == 1)] = 3
        preds[(access == 1) & (persistence == 0)] = 2
        preds[(access == 0) & (persistence == 0)] = 1
        preds[(access == 0) & (persistence == 1)] = 0
        return preds


def split_data(df, split_name):
    if split_name == "row_stratified":
        train_df, test_df = train_test_split(
            df,
            test_size=0.2,
            random_state=42,
            stratify=df["label_id"],
        )
    elif split_name == "participant_heldout":
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(df, groups=df["participant_id"]))
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
    else:
        raise ValueError(f"Unknown split: {split_name}")
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def over_sharing_rate(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    deny_mask = np.isin(y_true, [0, 1])
    if deny_mask.sum() == 0:
        return 0.0, 0, 0
    errors = deny_mask & np.isin(y_pred, [2, 3])
    return float(errors.sum() / deny_mask.sum()), int(errors.sum()), int(deny_mask.sum())


def persistent_over_allow_rate(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    non_persistent_allow_mask = y_true != 3
    if non_persistent_allow_mask.sum() == 0:
        return 0.0, 0, 0
    errors = non_persistent_allow_mask & (y_pred == 3)
    return float(errors.sum() / non_persistent_allow_mask.sum()), int(errors.sum()), int(non_persistent_allow_mask.sum())


def compute_metrics(y_true, y_pred):
    over_rate, over_count, over_denom = over_sharing_rate(y_true, y_pred)
    persist_rate, persist_count, persist_denom = persistent_over_allow_rate(y_true, y_pred)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true, y_pred, weights="quadratic", labels=LABEL_ORDER)),
        "over_sharing_rate": over_rate,
        "over_sharing_count": over_count,
        "over_sharing_denominator": over_denom,
        "persistent_over_allow_rate": persist_rate,
        "persistent_over_allow_count": persist_count,
        "persistent_over_allow_denominator": persist_denom,
    }


def save_confusion_matrix(y_true, y_pred, out_path):
    matrix = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
    df = pd.DataFrame(
        matrix,
        index=[f"true_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
        columns=[f"pred_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
    )
    df.to_csv(out_path, encoding="utf-8")


def run_benchmark(data_path, split_name, output_root):
    df = pd.read_csv(data_path)
    df = add_feature_columns(df)
    train_df, test_df = split_data(df, split_name)

    output_dir = output_root / split_name
    output_dir.mkdir(parents=True, exist_ok=True)

    models = [FlatFourClassModel(), OrdinalLogisticModel(), FactoredLogisticModel()]
    metrics_rows = []
    prediction_frames = []

    y_true = test_df["label_id"].to_numpy().astype(int)

    for model in models:
        print(f"Training {model.name} on {len(train_df)} rows; testing on {len(test_df)} rows")
        model.fit(train_df)
        y_pred = model.predict(test_df)
        if not set(np.unique(y_pred)).issubset(set(LABEL_ORDER)):
            raise ValueError(f"{model.name} produced invalid labels: {sorted(set(np.unique(y_pred)))}")

        metrics = compute_metrics(y_true, y_pred)
        metrics_rows.append({"model": model.name, **metrics})

        pred_df = test_df[
            [
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
        ].copy()
        pred_df["model"] = model.name
        pred_df["pred_label_id"] = y_pred
        pred_df["pred_label_text"] = [ID_TO_LABEL[int(label)] for label in y_pred]
        prediction_frames.append(pred_df)

        save_confusion_matrix(y_true, y_pred, output_dir / f"confusion_matrix_{model.name}.csv")
        report = classification_report(
            y_true,
            y_pred,
            labels=LABEL_ORDER,
            target_names=[ID_TO_LABEL[label] for label in LABEL_ORDER],
            output_dict=True,
            zero_division=0,
        )
        (output_dir / f"classification_report_{model.name}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(output_dir / "metrics.csv", index=False, encoding="utf-8")
    pd.concat(prediction_frames, ignore_index=True).to_csv(output_dir / "predictions.csv", index=False, encoding="utf-8")

    run_config = {
        "data_path": str(data_path),
        "split": split_name,
        "n_rows": int(len(df)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "train_label_counts": {ID_TO_LABEL[int(k)]: int(v) for k, v in train_df["label_id"].value_counts().sort_index().items()},
        "test_label_counts": {ID_TO_LABEL[int(k)]: int(v) for k, v in test_df["label_id"].value_counts().sort_index().items()},
        "train_participants": int(train_df["participant_id"].nunique()),
        "test_participants": int(test_df["participant_id"].nunique()),
        "models": [model.name for model in models],
        "metrics": [
            "accuracy",
            "macro_f1",
            "quadratic_weighted_kappa",
            "over_sharing_rate",
            "persistent_over_allow_rate",
        ],
    }
    (output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(metrics_df.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Run four-label permission prediction benchmarks.")
    parser.add_argument("--data", required=True, type=Path, help="Path to four_label_dataset.csv")
    parser.add_argument(
        "--split",
        required=True,
        choices=["row_stratified", "participant_heldout"],
        help="Evaluation split.",
    )
    parser.add_argument("--out", default=Path("results"), type=Path, help="Output root directory.")
    args = parser.parse_args()
    run_benchmark(args.data, args.split, args.out)


if __name__ == "__main__":
    main()
