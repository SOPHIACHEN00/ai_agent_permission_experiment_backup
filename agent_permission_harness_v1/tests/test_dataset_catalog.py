"""Source inventory checks; catalogued tasks are not executable-task claims."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from agent_permission_harness_v1.dataset_catalog import load_dataset_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class OriginalCorpusCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_dataset_catalog(PROJECT_ROOT)

    def test_original_queries_domains_and_external_labels_are_complete(self):
        self.assertEqual(self.catalog.counts["query_count"], 65)
        self.assertEqual(self.catalog.query_ids, tuple(range(65)))
        self.assertEqual(len(self.catalog.external_tool_labels), 28)
        self.assertEqual(len(self.catalog.domains), 8)
        self.assertEqual(self.catalog.internal_channels, ("mira",))
        self.assertEqual(self.catalog.counts["permission_context_count"], 373)
        self.assertEqual(self.catalog.tools_without_questionnaire_contexts,
                         ("Energy Management", "Health Records", "Investment", "Security Camera", "Smart Lock"))

    def test_source_text_and_data_fields_are_preserved_exactly(self):
        rows = json.loads((PROJECT_ROOT / "external/ai-agent-permissions/queries.json").read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in rows}
        for query in self.catalog.queries:
            self.assertEqual(query.query, by_id[query.query_id]["query"])
            self.assertEqual(query.original_fields, by_id[query.query_id])
        self.assertTrue(self.catalog.queries[0].query.endswith(" "))

    def test_mira_contexts_are_internal_and_never_dropped(self):
        contexts = [context for query in self.catalog.queries for context in query.permission_contexts]
        self.assertTrue(any(context.tool == "mira" for context in contexts))
        self.assertNotIn("mira", self.catalog.external_tool_labels)
        self.assertEqual(self.catalog.counts["permission_context_count"], len(contexts))
        self.assertTrue(all(context.questionnaire_item_id for context in contexts))

    def test_catalogue_does_not_claim_all_original_task_oracles_exist(self):
        self.assertEqual(self.catalog.counts["authored_task_oracle_count"], 1)
        self.assertEqual(self.catalog.counts["catalogued_without_task_oracle_count"], 64)
        query = next(q for q in self.catalog.queries if q.query_id == 22)
        self.assertEqual(query.coverage_status, "authored_task_oracle")
        self.assertIn("agent_mock_harness_v0", query.authored_task_oracle)
        self.assertTrue(all(c.synthetic_field is None for q in self.catalog.queries for c in q.permission_contexts))

    def test_json_export_has_context_metadata_without_participant_answers(self):
        exported = self.catalog.to_dict()
        encoded = json.dumps(exported, ensure_ascii=False)
        self.assertEqual(exported["counts"]["query_count"], 65)
        self.assertNotIn('"participant_id"', encoded)
        self.assertNotIn('"label_id"', encoded)
        self.assertNotIn('"label_text"', encoded)
        exported["queries"][0]["original_fields"]["query"] = "modified"
        self.assertNotEqual(self.catalog.queries[0].query, "modified")


class CatalogValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.query = {"id": 0, "query": "  Read my document. ", "domain": "Work", "tool1": "Cloud Drive", "tool2": "",
                      "datatype": ["Document"], "data_tool1": "Document", "data_tool2": "", "data_MIRA": "",
                      "data_incorrect": "", "data_tool1_incorrect": "", "data_tool2_incorrect": "", "data_MIRA_incorrect": ""}
        self.context = {"query_id": "0", "query": "Read  my document.", "domain": "Work", "tool": "cloud drive",
                        "raw_data_type": " Document ", "generic_data_type": "Document", "necessity_status": "necessary"}
        self.item = {"query_id": "0", "questionnaire_item_id": "permission_0_doc", "domain": "Work", "tool": "Cloud Drive",
                     "raw_data_type": "Document", "generic_data_type": "Document", "necessity_status": "necessary",
                     "question_content": "User request: Read my document.\nTool: Cloud Drive\nData item requested: Document"}

    def tearDown(self):
        self.directory.cleanup()

    def write_sources(self, queries=None, contexts=None, items=None):
        query_path = self.root / "external/ai-agent-permissions/queries.json"
        query_path.parent.mkdir(parents=True, exist_ok=True)
        query_path.write_text(json.dumps(queries if queries is not None else [self.query]), encoding="utf-8")
        for relative, rows in (("data/processed/four_label_dataset.csv", contexts if contexts is not None else [self.context]),
                               ("qstn_simulator/outputs/questionnaire_items.csv", items if items is not None else [self.item])):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

    def test_whitespace_case_aliases_match_but_original_values_are_retained(self):
        self.write_sources(contexts=[self.context, dict(self.context)])
        catalog = load_dataset_catalog(self.root)
        context = catalog.queries[0].permission_contexts[0]
        self.assertEqual(catalog.counts["permission_context_count"], 1)
        self.assertEqual(context.tool, "Cloud Drive")
        self.assertIn("cloud drive", context.tool_aliases)
        self.assertIn(" Document ", context.raw_data_type_aliases)
        self.assertEqual(catalog.queries[0].query, "  Read my document. ")
        self.assertIn("Read  my document.", catalog.queries[0].query_aliases)

    def test_duplicate_original_query_id_fails(self):
        self.write_sources(queries=[self.query, dict(self.query)])
        with self.assertRaisesRegex(ValueError, "duplicate query ID"):
            load_dataset_catalog(self.root)

    def test_unknown_query_and_conflicting_context_metadata_fail(self):
        self.write_sources(contexts=[dict(self.context, query_id="3")])
        with self.assertRaisesRegex(ValueError, "unknown query ID"):
            load_dataset_catalog(self.root)
        self.write_sources(contexts=[self.context, dict(self.context, necessity_status="incorrect_explicit")])
        with self.assertRaisesRegex(ValueError, "conflicting context metadata"):
            load_dataset_catalog(self.root)

    def test_query_text_mismatch_and_undeclared_tool_fail(self):
        self.write_sources(contexts=[dict(self.context, query="Invented task")])
        with self.assertRaisesRegex(ValueError, "query text mismatch"):
            load_dataset_catalog(self.root)
        self.write_sources(contexts=[dict(self.context, tool="Banking")])
        with self.assertRaisesRegex(ValueError, "undeclared tool"):
            load_dataset_catalog(self.root)

    def test_duplicate_questionnaire_context_and_wrong_item_fail(self):
        self.write_sources(items=[self.item, dict(self.item, questionnaire_item_id="duplicate")])
        with self.assertRaisesRegex(ValueError, "duplicate questionnaire context"):
            load_dataset_catalog(self.root)
        self.write_sources(items=[dict(self.item, raw_data_type="Different item")])
        with self.assertRaisesRegex(ValueError, "questionnaire context mismatch"):
            load_dataset_catalog(self.root)

    def test_invalid_query_id_is_not_silently_coerced(self):
        self.write_sources(queries=[dict(self.query, id=True)])
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            load_dataset_catalog(self.root)


if __name__ == "__main__":
    unittest.main()
