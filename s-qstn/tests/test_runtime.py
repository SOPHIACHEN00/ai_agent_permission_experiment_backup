"""Offline migration regression checks against the frozen final model inputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sqstn import RetrievalSimulator
from sqstn.retrieval.calibration import PROFILES

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = RetrievalSimulator()

    def test_default_paths_are_inside_this_distribution(self):
        self.assertEqual(self.sim.root, ROOT)
        self.assertEqual(self.sim.wrapper.root, ROOT / 'sqstn')
        self.assertEqual(len(self.sim.corpus.records), 13089)
        self.assertEqual(len(self.sim.items()), 373)
        self.assertEqual(self.sim.wrapper.verify_question_inventory()['mismatches'], [])

    def test_all_final_prompts_match_the_saved_experiment(self):
        fixtures = json.loads((ROOT / 'tests/fixtures/prompts.json').read_text(encoding='utf-8'))
        self.assertEqual(len(fixtures), 216)
        for item in fixtures:
            with self.subTest(query_id=item['query_id'], tool=item['tool'],
                              data_item=item['data_item'], profile=item['profile_id']):
                actual = self.sim.compile(item['profile_id'], item['query_id'], item['tool'], item['data_item'])
                self.assertEqual(actual['prompt_sha256'], item['prompt_sha256'])
                self.assertEqual(actual['memory_audit']['view']['visible_events'], [])

    def test_profile_assignment_is_stable_and_uses_frozen_weights(self):
        self.assertAlmostEqual(sum(self.sim.profile_weights.values()), 1)
        self.assertAlmostEqual(self.sim.profile_weights['reconsent_seekers'], .05)
        first = [self.sim.profile_for(str(i)) for i in range(100)]
        self.assertEqual(first, [self.sim.profile_for(str(i)) for i in range(100)])
        self.assertEqual(set(first), set(PROFILES))

    def test_unknown_question_does_not_silently_change_the_task(self):
        with self.assertRaises(ValueError):
            self.sim.compile(PROFILES[0], -1, 'missing tool', 'missing data')

    def test_isolated_process_works_without_reading_source_project(self):
        code = '''
import json, pathlib, sys
root=pathlib.Path(sys.argv[1]).resolve()
blocked=[root.parent/'qstn_simulator',root.parent/'external']
def audit(event,args):
    if event=='open' and isinstance(args[0],str):
        path=pathlib.Path(args[0]).resolve()
        if any(path.is_relative_to(p) for p in blocked):
            raise RuntimeError('Read from old project is forbidden: '+str(path))
sys.addaudithook(audit)
sys.path.insert(0,str(root))
from sqstn import RetrievalSimulator
sim=RetrievalSimulator()
fixtures=json.loads((root/'tests/fixtures/prompts.json').read_text(encoding='utf-8'))
item=fixtures[0]
result=sim.compile(item['profile_id'],item['query_id'],item['tool'],item['data_item'])
assert result['prompt_sha256']==item['prompt_sha256']
assert sim.wrapper.verify_question_inventory()['mismatches']==[]
for name,module in list(sys.modules.items()):
    if name=='sqstn' or name.startswith('sqstn.'):
        assert pathlib.Path(module.__file__).resolve().is_relative_to(root)
print('independent_runtime_ok')
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tests') as cwd:
            result=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT)],cwd=cwd,
                                  capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('independent_runtime_ok',result.stdout)


if __name__ == '__main__':
    unittest.main()
