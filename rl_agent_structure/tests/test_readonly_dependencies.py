import unittest
import socket
from helpers import ROOT
from test_user_session import start, user_session


class ReadonlyTests(unittest.TestCase):
    def test_noapi_run_preserves_dependency_tree(self):
        from personal_assistant.integration.readonly import dependency_inventory, NetworkBlock
        before = dependency_inventory(ROOT.parent)
        with NetworkBlock() as guard:
            result = start(user_session()).run()
            self.assertTrue(result.oracle_result['success'])
            self.assertEqual(guard.attempts, 0)
        self.assertEqual(dependency_inventory(ROOT.parent), before)
        self.assertFalse(list((ROOT/'src').rglob('*.md')) + list((ROOT/'tests').rglob('*.md')))

    def test_network_guard_rejects_even_accidental_dns(self):
        from personal_assistant.integration.readonly import NetworkBlock
        with NetworkBlock() as guard:
            with self.assertRaises(RuntimeError): socket.getaddrinfo('should-not-resolve.invalid', 443)
            self.assertEqual(guard.attempts, 1)


if __name__ == '__main__': unittest.main()
