"""Offline checks for the four-label IC-only protocol and strict response parser."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pandas as pd

from run_ic_four_label import (
    build_prompt, make_bundles, make_jobs, max_call_cost_usd,
    parse_response, tracked_spend_usd, usage_and_cost,
)


class ICFourLabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame(
            [
                {
                    "participant_id": participant,
                    "query_id": query_id,
                    "query": f"Question {query_id}?",
                    "tool": "Tool",
                    "raw_data_type": f"Data {query_id}",
                    "label_text": [
                        "No, never share",
                        "No, but ask me next time",
                        "Yes, but ask me next time",
                        "Yes, always share",
                    ][query_id % 4],
                    "label_id": query_id % 4,
                }
                for participant in ("P001", "P002")
                for query_id in range(10)
            ]
        )

    def test_each_query_is_tested_once_without_history_overlap(self) -> None:
        jobs = make_jobs(self.df, seed=42)
        self.assertEqual(len(jobs), 10)
        for participant in ("P001", "P002"):
            user_jobs = [job for job in jobs if job["participant_id"] == participant]
            self.assertEqual(sorted(query for job in user_jobs for query in job["test_query_ids"]), list(range(10)))
            for job in user_jobs:
                self.assertFalse(set(job["train_query_ids"]) & set(job["test_query_ids"]))
                self.assertEqual(job["train_rows"], 8)
                self.assertEqual(job["test_rows"], 2)

    def test_budget_reservation_and_persistent_spend(self) -> None:
        reserve = max_call_cost_usd("example" * 100, "o3-mini", 3000)
        usage = SimpleNamespace(prompt_tokens=200, completion_tokens=100)
        cost = usage_and_cost(SimpleNamespace(usage=usage), "o3-mini")
        self.assertGreaterEqual(reserve, cost["charged_or_reserved_cost_usd"])
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "P001_fold0.json").write_text(
                json.dumps(cost), encoding="utf-8"
            )
            (folder / "P001_fold1.error.json").write_text(
                json.dumps({"charged_or_reserved_cost_usd": reserve}), encoding="utf-8"
            )
            self.assertAlmostEqual(
                tracked_spend_usd(folder),
                cost["charged_or_reserved_cost_usd"] + reserve,
            )

    def test_test_bundles_hide_answers_and_parser_requires_complete_output(self) -> None:
        user_rows = self.df.loc[(self.df["participant_id"] == "P001") & self.df["query_id"].isin([0, 1])]
        requests = make_bundles(user_rows, include_answers=False)
        self.assertTrue(all(value is None for bundle in requests for value in bundle["permission"].values()))
        history = make_bundles(self.df.loc[(self.df["participant_id"] == "P001") & (self.df["query_id"] == 2)], True)
        prompt = build_prompt({"age": 2, "gender": "Female", "education": "Master's"}, history, requests)
        self.assertIn("Yes, but ask me next time", prompt)
        self.assertIn("No, but ask me next time", prompt)
        response = [
            {
                "id": bundle["id"],
                "query": bundle["query"],
                "permission": {
                    key: {"label": "No, never share", "score": 0.7}
                    for key in bundle["permission"]
                },
            }
            for bundle in requests
        ]
        self.assertEqual(len(parse_response(json.dumps(response), user_rows)), len(user_rows))
        self.assertEqual(len(parse_response("```json\n" + json.dumps(response) + "\n```", user_rows)), len(user_rows))
        with self.assertRaises(ValueError):
            parse_response(json.dumps(response[:1]), user_rows)
        response[0]["permission"].clear()
        with self.assertRaises(ValueError):
            parse_response(json.dumps(response), user_rows)


if __name__ == "__main__":
    unittest.main()

