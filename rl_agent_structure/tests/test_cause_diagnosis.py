"""Context isolation and accounting checks for diagnosis A; no local training."""
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT.parent), str(ROOT / 'tests')]

from rl_testing.cause_diagnosis import (ARMS, TRAIN_TASKS, DiagnosisLog, ReplayProfiler,
                                      clone_user_context, context_snapshot, describe_arm, render_comparison)
from rl_testing.online_check import _user_digest, annotate_counts
from rl_testing.runner import RuleSelection, run_sequence
from test_online_check import config


class CauseDiagnosisTests(unittest.TestCase):
    def test_fixed_design_and_no_torch_cli_gate(self):
        self.assertEqual(TRAIN_TASKS, 15)
        self.assertEqual(len(ARMS) * 3, 30)
        self.assertEqual(len(set(ARMS)), 10)
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'rl_testing/cause_diagnosis.py'),
                                 '--config', 'missing', '--initial-checkpoint', 'missing', '--output', 'missing'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--allow-training required', result.stderr)
        self.assertNotIn('No module named', result.stderr)

    def test_retained_context_clones_preserve_authority_without_sharing_mutation(self):
        cfg = config()
        source = run_sequence(cfg, RuleSelection(), DiagnosisLog(cfg), queries=(40,), training=False,
                              deadline=time.monotonic()+60).user
        before = _user_digest(source)
        clone1, clone2 = clone_user_context(source), clone_user_context(source)
        self.assertIsNot(clone1.ledger, clone2.ledger)
        self.assertIsNot(clone1.history, clone2.history)
        self.assertEqual(_user_digest(clone1), before)
        self.assertEqual(context_snapshot(source)['digest'], before)
        log = DiagnosisLog(cfg)
        result = run_sequence(cfg, RuleSelection(), log, queries=(41,), training=False,
                              case_id='branch', user_context=clone1, deadline=time.monotonic()+60)
        self.assertEqual(result.tasks[0]['round'], 2)
        self.assertEqual(result.tasks[0]['metrics']['task_success'], 1)
        self.assertEqual(_user_digest(source), before)
        self.assertEqual(_user_digest(clone2), before)
        with self.assertRaisesRegex(ValueError, 'isolated'):
            run_sequence(cfg, RuleSelection(), DiagnosisLog(cfg), queries=(41,), training=True, user_context=clone2)
        with self.assertRaisesRegex(ValueError, 'isolated'):
            run_sequence(replace(cfg, user_id='foreign'), RuleSelection(), DiagnosisLog(cfg),
                         queries=(41,), training=False, user_context=clone2)

    def test_profiler_preserves_successful_and_failed_audits(self):
        from personal_assistant.permissions.persistent_ledger import UserAuthorizationLedger as Ledger
        from personal_assistant.config import PermissionConfig
        from dataclasses import replace
        ledger = Ledger('fixture', PermissionConfig(3))
        descriptor = Ledger.__dict__['replay']
        with ReplayProfiler() as profile:
            for _ in range(2):
                self.assertEqual(Ledger.replay(ledger.events()).records(), ledger.records())
            bad = (replace(ledger.events()[0], event_hash='corrupt'),)
            with self.assertRaises(ValueError): Ledger.replay(bad)
        self.assertIs(Ledger.__dict__['replay'], descriptor)
        self.assertEqual(profile.calls, 3)
        self.assertEqual(profile.repeated_inputs, 1)
        self.assertGreater(profile.seconds, 0)

    def test_action_reward_join_and_partial_plot(self):
        cfg = config()
        log = DiagnosisLog(cfg)
        run_sequence(cfg, RuleSelection(), log, queries=(40,), training=False, deadline=time.monotonic()+60)
        annotate_counts(log)
        summary = describe_arm(log, [])
        self.assertEqual(summary['successes'], 1)
        self.assertEqual(summary['actions']['EXECUTE'], 2)
        self.assertEqual(summary['cost_totals']['unauthorized_executed_field_instances'], 0)
        self.assertTrue(summary['complete_authorization_evidence'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'chart.svg'
            render_comparison([{'arm': 'rule_fresh_greedy', 'observed': summary}], path)
            ET.parse(path)
            self.assertIn('1/3; finished 1/3', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
