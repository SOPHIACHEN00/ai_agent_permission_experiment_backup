"""Charts must show measured rows, missing data and provenance faithfully."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]
NS = {"s": "http://www.w3.org/2000/svg"}


def setUpModule():
    (ROOT / "outputs").mkdir(exist_ok=True)


class PlotTests(unittest.TestCase):
    def renderer(self):
        self.assertIsNotNone(importlib.util.find_spec("rl_testing.plots"),
                             "plotting module has not been implemented")
        from rl_testing.plots import render_plots
        return render_plots

    def report(self):
        return {
            "schema": "rl_testing.four_actions.v2", "action_schema": "four_actions_v1",
            "evidence": "functional_only",
            "config": {"user_id": "fixture<&>", "seed": 3},
            "tasks": [
                {"task_index": 1, "return": None, "metrics": {
                    "task_success": 1, "permission_messages": 4, "extra_read_instances": 0,
                    "extra_write_instances": 0, "idle_gate_key_checkpoints": 1,
                    "extra_permission_messages": 0, "active_gate_items_before_cleanup": 0,
                    "active_consent_items_after_task": 4}},
                {"task_index": 2, "return": None, "metrics": {
                    "task_success": 0, "permission_messages": 1, "extra_read_instances": 0,
                    "extra_write_instances": 0, "idle_gate_key_checkpoints": 0,
                    "extra_permission_messages": 0, "active_gate_items_before_cleanup": 0,
                    "active_consent_items_after_task": 0}},
            ], "updates": [], "evaluations": [],
        }

    def test_functional_chart_keeps_failed_row_and_has_no_fake_loss(self):
        render = self.renderer()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "charts"
            render(self.report(), output)
            svg = ET.parse(output / "task_metrics.svg")
            self.assertIn("FUNCTIONAL ONLY", "".join(svg.getroot().itertext()))
            self.assertIn("fixture<&>", "".join(svg.getroot().itertext()))
            successes = svg.findall('.//s:g[@data-metric="task_success"]/s:circle', NS)
            self.assertEqual([float(e.attrib["data-value"]) for e in successes], [1., 0.])
            for metric, expected in (("permission_messages", [4., 1.]),
                                     ("extra_permission_messages", [0., 0.]),
                                     ("active_gate_items_before_cleanup", [0., 0.]),
                                     ("active_consent_items_after_task", [4., 0.])):
                points = svg.findall(f'.//s:g[@data-metric="{metric}"]/s:circle', NS)
                self.assertEqual([float(p.attrib["data-value"]) for p in points], expected)
            loss = ET.parse(output / "loss.svg")
            self.assertEqual(loss.findall(".//s:circle", NS), [])
            self.assertIn("No optimizer updates", "".join(loss.getroot().itertext()))
            self.assertTrue((output / "tasks.csv").is_file())
            with self.assertRaises(FileExistsError):
                render(self.report(), output)

    def test_invalid_values_and_unsorted_time_are_rejected_before_creating_output(self):
        render = self.renderer()
        for kind in ("nonfinite", "nonmonotonic"):
            report = self.report()
            if kind == "nonfinite":
                report["tasks"][0]["metrics"]["permission_items"] = float("nan")
            else:
                report["tasks"][1]["task_index"] = 1
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
                dest = Path(temp) / "invalid"
                with self.assertRaises(ValueError): render(report, dest)
                self.assertFalse(dest.exists())

    def test_functional_report_cannot_present_optimizer_losses_as_learning_evidence(self):
        render = self.renderer()
        report = self.report()
        report["updates"] = [{"optimizer_steps": 1, "total_loss": .2,
                              "td_loss_derived": .2, "auxiliary_loss": None}]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            dest = Path(temp) / "mislabelled"
            with self.assertRaises(ValueError):
                render(report, dest)
            self.assertFalse(dest.exists())

    def test_different_users_cannot_be_silently_joined_into_one_learning_curve(self):
        render = self.renderer()
        report = self.report()
        report["tasks"][0]["user_id"] = "somebody_else"
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            dest = Path(temp) / "mixed-users"
            with self.assertRaises(ValueError):
                render(report, dest)
            self.assertFalse(dest.exists())

    def test_six_action_reports_are_rejected_before_output_creation(self):
        render = self.renderer()
        report = self.report()
        report["schema"] = "rl_testing.v1"
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            dest = Path(temp) / "legacy"
            with self.assertRaisesRegex(ValueError, "six-action reports"):
                render(report, dest)
            self.assertFalse(dest.exists())

    def test_parameter_diagnostic_uses_measured_summary_endpoints_only(self):
        report = self.report()
        report["evidence"] = "real_ddqn_fixture_diagnostic"
        report["config"]["mode"] = "update-check"
        report["summary"] = {"parameter_l2_change": .125, "optimizer_steps": 5}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "charts"
            self.renderer()(report, output)
            svg = ET.parse(output / "parameter_change.svg")
            points = svg.findall('.//s:g[@data-metric="parameter_l2_change"]/s:circle', NS)
            self.assertEqual([float(p.attrib["data-x"]) for p in points], [0., 1.])
            self.assertEqual([float(p.attrib["data-value"]) for p in points], [0., .125])
            self.assertIn("NOT A LEARNING CURVE", "".join(svg.getroot().itertext()))
            self.assertTrue((output / "parameter_change.csv").is_file())

    def test_missing_parameter_summary_does_not_invent_change(self):
        report = self.report()
        report["evidence"] = "real_ddqn_fixture_diagnostic"
        report["config"]["mode"] = "update-check"
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "charts"
            self.renderer()(report, output)
            svg = ET.parse(output / "parameter_change.svg")
            self.assertEqual(svg.findall(".//s:circle", NS), [])
            self.assertIn("No measured parameter-change", "".join(svg.getroot().itertext()))

    def test_parameter_change_rejects_negative_nonfinite_and_functional_evidence(self):
        for change, evidence in ((-.1, "real_ddqn_fixture_diagnostic"),
                                 (float("nan"), "real_ddqn_fixture_diagnostic"),
                                 (.1, "functional_only")):
            report = self.report()
            report["evidence"] = evidence
            report["summary"] = {"parameter_l2_change": change}
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
                output = Path(temp) / "charts"
                with self.assertRaises(ValueError): self.renderer()(report, output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
