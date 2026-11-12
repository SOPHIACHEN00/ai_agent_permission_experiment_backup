"""The supported Wu entry point must run when every retired package is absent."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[2]


class IndependentWuTests(unittest.TestCase):
    def test_all_queries_run_in_a_clean_copy_without_old_code_or_network(self):
        # Break caught: a direct, delayed or transitive import of a retired
        # package makes the public runner unusable after the approved archive.
        with tempfile.TemporaryDirectory(prefix='wu_independent_') as temporary:
            root = Path(temporary)
            shutil.copytree(PROJECT / 'mock_tools', root / 'mock_tools')
            shutil.copytree(PROJECT / 'rl_agent_structure/src/personal_assistant',
                            root / 'rl_agent_structure/src/personal_assistant')
            source = root / 'external/ai-agent-permissions'
            source.mkdir(parents=True)
            shutil.copy2(PROJECT / 'external/ai-agent-permissions/queries.json', source)
            checks = root / 'tests/mock_tools'
            checks.mkdir(parents=True)
            shutil.copy2(PROJECT / 'tests/mock_tools/test_read_write.py', checks)
            script = '''
import importlib.abc, pathlib, runpy, socket, sys
root = pathlib.Path(sys.argv[1]).resolve()
retired = {'pa_rl', 'agent_permission_harness_v1', 'agent_mock_harness_v0'}
class RejectOldCode(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in retired:
            raise AssertionError('retired dependency: ' + fullname)
def offline(*args, **kwargs):
    raise AssertionError('local functionality test must not use the network')
socket.socket.connect = offline
socket.create_connection = offline
sys.meta_path.insert(0, RejectOldCode())
# The public entry point itself must locate the new package. Do not inject its
# src path here, which would hide a broken or retired bootstrap in run.py.
sys.path.insert(0, str(root))
from mock_tools.run import run
summary = run(root / 'output', tuple(range(65)))
assert summary['passed'] == 65, summary
assert summary['api_calls'] == summary['training_steps'] == 0
import unittest
suite = unittest.defaultTestLoader.discover(str(root / 'tests/mock_tools'), pattern='test_read_write.py')
result = unittest.TextTestRunner(verbosity=0).run(suite)
assert result.wasSuccessful(), 'isolated permission-boundary regression failed'
for name, module in list(sys.modules.items()):
    if name.split('.')[0] in {'mock_tools', 'personal_assistant'}:
        assert pathlib.Path(module.__file__).resolve().is_relative_to(root), name
    assert name.split('.')[0] not in retired, name
print('65 independent Wu queries passed; no old packages, API or training')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(root)],
                                    cwd=root, text=True, capture_output=True, timeout=55)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('65 independent Wu queries passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
