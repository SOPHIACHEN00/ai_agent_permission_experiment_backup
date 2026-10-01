"""Real journal and accounting tests; no API calls."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

class BudgetTests(unittest.TestCase):
    def make(self, path, **kw):
        from agent_permission_harness_v1.online_budget import OnlineBudget
        return OnlineBudget(path, caps_nusd={'human':100,'task':200},
                            call_caps={'human':10,'task':10}, **kw)

    def test_role_caps_and_settlement(self):
        with TemporaryDirectory() as d:
            b=self.make(Path(d))
            b.reserve('human','h1',80,'a'*64)
            b.settle('human','h1',20,{})
            b.reserve('human','h2',80,'a'*64)
            with self.assertRaises(RuntimeError): b.reserve('human','h3',1,'a'*64)
            b.reserve('task','t1',200,'b'*64)
            self.assertEqual(b.summary()['human']['settled_upper_nusd'],20)
            self.assertEqual(b.summary()['human']['reserved_unknown_nusd'],80)
            self.assertEqual(b.summary()['human']['attempts'],2)
            self.assertEqual(b.summary()['task']['attempts'],1)
            b.close()

    def test_unknown_call_blocks_resume(self):
        with TemporaryDirectory() as d:
            b=self.make(Path(d)); b.reserve('human','h1',80,'a'*64); b.close()
            with self.assertRaises(RuntimeError): self.make(Path(d),resume=True)

    def test_duplicate_settlement_and_corrupt_journal(self):
        with TemporaryDirectory() as d:
            b=self.make(Path(d)); b.reserve('human','h1',80,'a'*64)
            with self.assertRaises(ValueError): b.reserve('human','h1',80,'a'*64)
            b.settle('human','h1',20,{})
            with self.assertRaises(ValueError): b.settle('human','h1',20,{})
            for role,amount in [('other',1),('human',True),('human',-1)]:
                with self.assertRaises(ValueError): b.reserve(role,'invalid',amount,'a'*64)
            b.close()
            c=self.make(Path(d),resume=True)
            self.assertEqual(c.summary()['human']['settled_upper_nusd'],20); c.close()
            with (Path(d)/'attempts.jsonl').open('a') as f: f.write('{"broken":')
            with self.assertRaises(RuntimeError): self.make(Path(d),resume=True)

    def test_failure_locks_run_and_sanitizes_metadata(self):
        with TemporaryDirectory() as d:
            b=self.make(Path(d)); b.reserve('human','h1',80,'a'*64)
            b.fail('human','h1','request','TimeoutError')
            with self.assertRaises(RuntimeError): b.reserve('task','t1',10,'b'*64)
            with self.assertRaises(ValueError):
                b.settle('human','h1',1,{'api_key':'SENTINEL_SECRET'})
            self.assertNotIn('SENTINEL_SECRET',(Path(d)/'attempts.jsonl').read_text())
            b.close()

    def test_exclusive_writer_and_cap_binding(self):
        with TemporaryDirectory() as d:
            b=self.make(Path(d))
            with self.assertRaises((RuntimeError,FileExistsError)): self.make(Path(d))
            b.close()
            from agent_permission_harness_v1.online_budget import OnlineBudget
            with self.assertRaises(RuntimeError):
                OnlineBudget(Path(d),caps_nusd={'human':101,'task':200},
                             call_caps={'human':10,'task':10},resume=True)
