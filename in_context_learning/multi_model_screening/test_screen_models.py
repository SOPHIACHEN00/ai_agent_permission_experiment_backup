"""Offline checks for paired screening, routing, and shared budget accounting."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pandas as pd

from screen_models import (
    MODEL_SPECS,
    build_clients,
    completion_for_job,
    reserve_cost_usd,
    safe_error_text,
    select_history_shots,
    select_jobs,
    tracked_spend_usd,
    usage_record,
)


class FakeCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))


class ScreeningTests(unittest.TestCase):
    def test_provider_error_redacts_keys(self) -> None:
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-secret"}):
            message = safe_error_text(RuntimeError("request failed with sk-test-secret"))
        self.assertNotIn("sk-test-secret", message)
        self.assertIn("[REDACTED_API_KEY]", message)
    def test_all_models_receive_identical_query_holdouts(self) -> None:
        rows = []
        for participant in ("P001", "P002", "P003"):
            for query_id in range(10):
                for item in ("A", "B"):
                    rows.append({"participant_id": participant, "query_id": query_id,
                                 "raw_data_type": item})
        df = pd.DataFrame(rows)
        participants, jobs = select_jobs(
            df, fold_seed=42, sample_seed=7, n_participants=2, fold="0"
        )
        self.assertEqual(len(participants), 2)
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job["fold"], 0)
            self.assertEqual(job["test_rows"], 4)
            self.assertFalse(set(job["train_query_ids"]) & set(job["test_query_ids"]))
        self.assertEqual(
            jobs,
            select_jobs(df, fold_seed=42, sample_seed=7, n_participants=2, fold="0")[1],
        )

    def test_all_three_models_use_openrouter_and_price_ceilings(self) -> None:
        router_calls = FakeCompletions()
        clients = {
            "openrouter": SimpleNamespace(chat=SimpleNamespace(completions=router_calls)),
        }
        expected_ids = {
            "luna": "openai/gpt-6-luna",
            "deepseek": "deepseek/deepseek-v4-flash-0731",
            "gemini": "google/gemini-3.8-flash",
        }
        for name, model_id in expected_ids.items():
            spec = MODEL_SPECS[name]
            self.assertEqual(spec.route, "openrouter")
            completion_for_job(clients, spec, "Prompt", 4000)
            request = router_calls.kwargs
            self.assertEqual(request["model"], model_id)
            self.assertEqual(request["max_tokens"], 4000)
            provider = request["extra_body"]["provider"]
            self.assertEqual(provider["max_price"], {
                "prompt": spec.max_input_usd_per_million,
                "completion": spec.max_output_usd_per_million,
            })
            self.assertEqual(provider["data_collection"], "deny")
            self.assertEqual(request["extra_body"]["usage"], {"include": True})
            self.assertEqual(request["extra_body"]["reasoning"], {"effort": "low"})

    def test_four_shot_selection_is_reproducible_and_stays_in_training_fold(self) -> None:
        jobs = [{
            "job_id": "P001_fold0",
            "train_query_ids": list(range(16)),
            "test_query_ids": [16, 17, 18, 19],
        }]
        first = select_history_shots(jobs, shots=4, seed=20260925)
        second = select_history_shots(jobs, shots=4, seed=20260925)
        chosen = first[0]["prompt_history_query_ids"]
        self.assertEqual(first, second)
        self.assertEqual(len(chosen), 4)
        self.assertTrue(set(chosen).issubset(set(jobs[0]["train_query_ids"])))
        self.assertFalse(set(chosen) & set(jobs[0]["test_query_ids"]))
        self.assertNotIn("prompt_history_query_ids", jobs[0])

    def test_one_openrouter_key_is_sufficient(self) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("OPENROUTER_API_KEY=sk-test\n", encoding="utf-8")
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test", "OPENAI_API_KEY": ""}):
                clients = build_clients(list(MODEL_SPECS.values()), env_file)
        self.assertEqual(set(clients), {"openrouter"})

    def test_todo_key_in_env_is_rejected_before_network(self) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "OPENROUTER_API_KEY=TODO_REPLACE_WITH_YOUR_OPENROUTER_API_KEY\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-unrelated-shell-key"}):
                with self.assertRaisesRegex(RuntimeError, "Replace the OPENROUTER_API_KEY TODO"):
                    build_clients(list(MODEL_SPECS.values()), env_file)

    def test_cost_uses_provider_report_and_keeps_old_failed_spend(self) -> None:
        spec = MODEL_SPECS["deepseek"]
        reserve = reserve_cost_usd("example" * 100, spec, 4000)
        completion = SimpleNamespace(usage=SimpleNamespace(
            prompt_tokens=100, completion_tokens=200, cost=0.00005,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=50),
        ))
        record = usage_record(completion, spec)
        self.assertEqual(record["provider_reported_cost_usd"], 0.00005)
        self.assertEqual(record["reasoning_tokens"], 50)
        self.assertGreater(reserve, record["charged_or_reserved_cost_usd"])
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "luna_P001_fold0.json").write_text(json.dumps(record), encoding="utf-8")
            (folder / "luna_P002_fold0.error1.json").write_text(
                json.dumps({"charged_or_reserved_cost_usd": reserve}), encoding="utf-8"
            )
            self.assertAlmostEqual(
                tracked_spend_usd(folder), reserve + record["charged_or_reserved_cost_usd"]
            )


if __name__ == "__main__":
    unittest.main()
