"""Fast non-training checks for the DistilBERT four-label runner."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import run_distilbert_four_label as runner  # noqa: E402


class DistilBertRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data_path = PROJECT_ROOT / "data" / "processed" / "four_label_dataset.csv"
        cls.frame, cls.data_hash = runner.validate_input_dataset(data_path, False)
        cls.outer_train, cls.inner_train, cls.validation, cls.outer_test_ids = runner.make_splits(
            cls.frame, 20260809
        )

    def test_audited_splits(self) -> None:
        self.assertEqual(self.data_hash, runner.EXPECTED_DATASET_SHA256)
        self.assertEqual((len(self.outer_train), self.outer_train["participant_id"].nunique()), (13038, 160))
        self.assertEqual((len(self.inner_train), self.inner_train["participant_id"].nunique()), (10417, 128))
        self.assertEqual((len(self.validation), self.validation["participant_id"].nunique()), (2621, 32))
        self.assertEqual(len(self.outer_test_ids), 41)
        self.assertFalse(set(self.outer_train["participant_id"]) & self.outer_test_ids)

    def test_balanced_class_weights(self) -> None:
        observed = runner.compute_class_weights(self.inner_train["label_id"], "balanced")
        expected = np.asarray([1.880325, 2.239252, 0.586411, 0.759700])
        np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-6)

    def test_metrics_match_frozen_flat_lr_artifact(self) -> None:
        predictions = pd.read_csv(
            WORKSPACE_ROOT
            / "classification_experiments"
            / "artifacts"
            / "nested_tuning_20260809"
            / "participant_heldout"
            / "test_predictions.csv"
        )
        selected = predictions.loc[
            (predictions["model"] == "flat_four_class_lr")
            & (predictions["variant"] == "tuned")
        ]
        metrics = runner.compute_metrics(selected["label_id"], selected["pred_label_id"])
        self.assertAlmostEqual(metrics["accuracy"], 0.4092687330725248, places=15)
        self.assertAlmostEqual(metrics["macro_f1"], 0.3706549458606443, places=15)
        self.assertAlmostEqual(metrics["quadratic_weighted_kappa"], 0.3154949229526881, places=14)
        self.assertAlmostEqual(metrics["over_sharing_rate"], 0.4257075471698113, places=15)
        self.assertAlmostEqual(metrics["persistent_over_allow_rate"], 0.2104332449160035, places=15)

    def test_serializer_maps_codes_and_excludes_targets(self) -> None:
        row = self.inner_train.iloc[0].copy()
        row["age"] = 3
        row["gender"] = np.nan
        row["concern_domain"] = "Finance|Health & Fitness"
        text = runner.serialize_permission_row(row)
        self.assertIn("age group 35-44", text)
        self.assertIn("gender unspecified", text)
        self.assertIn("Finance, Health & Fitness", text)
        self.assertNotIn(str(row["participant_id"]), text)
        self.assertNotIn(str(row["label_text"]), text)

    def test_preselection_manifest_hides_test_label_counts(self) -> None:
        manifest = runner.split_manifest(
            self.frame,
            self.outer_train,
            self.inner_train,
            self.validation,
            self.outer_test_ids,
            20260809,
        )
        self.assertIsNone(manifest["outer_test"]["label_counts"])
        self.assertIn("not inspected", manifest["outer_test"]["label_counts_status"])

    def test_output_guard_rejects_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            output = Path(temp_root) / "run"
            output.mkdir()
            (output / "sentinel.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                runner.ensure_new_output_directory(output)

    def test_mixed_precision_cpu_resolution(self) -> None:
        cpu = runner.torch.device("cpu")
        self.assertEqual(runner.resolve_mixed_precision("auto", cpu), "none")
        self.assertEqual(runner.resolve_mixed_precision("none", cpu), "none")
        with self.assertRaises(RuntimeError):
            runner.resolve_mixed_precision("fp16", cpu)


if __name__ == "__main__":
    unittest.main()
