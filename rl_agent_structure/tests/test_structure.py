"""Check independent imports and the absence of runtime links to retired packages."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "personal_assistant"


class IndependentPackageTests(unittest.TestCase):
    def test_package_imports_from_a_copy_without_any_old_repository(self):
        self.assertTrue(PACKAGE.is_dir(), "the independent personal_assistant package is missing")
        with tempfile.TemporaryDirectory(prefix="assistant_import_check_") as temporary:
            isolated = Path(temporary)
            shutil.copytree(PACKAGE, isolated / "personal_assistant")
            script = '''
import importlib, importlib.abc, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
class RejectRetiredImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pa_rl', 'agent_permission_harness_v1', 'agent_mock_harness_v0'}:
            raise AssertionError('runtime depended on a retired package: ' + fullname)
sys.meta_path.insert(0, RejectRetiredImports())
sys.path.insert(0, str(root))
for name in (
    'contracts.permission', 'contracts.task', 'contracts.tool_call',
    'permissions.ledger', 'permissions.monitor', 'permissions.candidates',
    'permissions.scope', 'interaction.human_channel', 'planning.planner', 'safety.checker',
    'execution.runner', 'execution.adapter', 'execution.store', 'planning.compiler',
    'planning.scripted', 'permissions.dispatch', 'permissions.rule_policy',
):
    module = importlib.import_module('personal_assistant.' + name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root)
print('independent core imports: OK')
'''
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(isolated)],
                cwd=isolated, text=True, capture_output=True, timeout=40,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("independent core imports: OK", result.stdout)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "optional torch dependency is not installed")
    def test_learning_imports_and_tensor_contracts_without_training(self):
        with tempfile.TemporaryDirectory(prefix="assistant_learning_import_") as temporary:
            isolated = Path(temporary)
            shutil.copytree(PACKAGE, isolated / "personal_assistant")
            script = '''
import importlib, importlib.abc, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
class RejectRetiredImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pa_rl', 'agent_permission_harness_v1', 'agent_mock_harness_v0'}:
            raise AssertionError('retired dependency: ' + fullname)
sys.meta_path.insert(0, RejectRetiredImports())
sys.path.insert(0, str(root))
for name in ('ddqn', 'device', 'features', 'policy', 'public_state', 'transitions', 'exposure'):
    module = importlib.import_module('personal_assistant.learning.' + name)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root)
import torch
from personal_assistant.learning.ddqn import CandidateQNetwork, double_dqn_targets
from personal_assistant.learning.features import MODEL_SPEC
from personal_assistant.learning.device import resolve_device
assert str(resolve_device('cpu')) == 'cpu'
network = CandidateQNetwork(MODEL_SPEC)
with torch.no_grad():
    output = network(torch.zeros((1, MODEL_SPEC.state_dim)), torch.zeros((1, 2, MODEL_SPEC.candidate_dim)))
assert output.shape == (1, 2)
targets = double_dqn_targets(
    rewards=torch.tensor([1., 2.]), dones=torch.tensor([False, True]),
    online_next_q=torch.tensor([[1., 50., 3.], [0., 0., 0.]]),
    target_next_q=torch.tensor([[10., 90., 4.], [float('nan')] * 3]),
    next_mask=torch.tensor([[True, False, True], [False, False, False]]), gamma=.5)
assert targets.tolist() == [3., 2.]
print('independent learning imports and tensor checks: OK; no optimization performed')
'''
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(isolated)],
                cwd=isolated, text=True, capture_output=True, timeout=55,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("no optimization performed", result.stdout)

    def test_static_imports_do_not_hide_a_dependency_in_optional_learning_code(self):
        self.assertTrue(PACKAGE.is_dir(), "the independent personal_assistant package is missing")
        forbidden = {"pa_rl", "agent_permission_harness_v1", "agent_mock_harness_v0"}
        violations = []
        for path in PACKAGE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module or ""]
                if any(name.split(".")[0] in forbidden for name in modules):
                    violations.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
