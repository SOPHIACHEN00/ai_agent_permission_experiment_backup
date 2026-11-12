import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from helpers import ROOT


class NoAPIAcceptance(unittest.TestCase):
    def test_65_wu_queries_and_lifecycle_noapi_entry(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix='test_run_') as temp:
            output = Path(temp) / 'results'
            cmd = [sys.executable, '-I', '-B', str(ROOT / 'run_noapi.py'), '--persist-rounds', '3', '--all-wu', '--output', str(output)]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((output / 'summary.json').read_text())
            self.assertEqual(summary['coverage_tasks'], 65)
            self.assertEqual(summary['coverage_successes'], 65)
            self.assertEqual(summary['network_attempts'], 0)
            self.assertEqual(summary['optimizer_steps'], 0)
            self.assertEqual(summary['answer_source'], 'explicit_fixture')
            self.assertTrue(summary['dependencies_unchanged'])
            self.assertTrue(all(c['passed'] for c in summary['lifecycle_checks']))
            self.assertEqual(len(json.loads((output / 'query_coverage.json').read_text())), 65)
            again = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn('already exists', again.stderr)


if __name__ == '__main__': unittest.main()
