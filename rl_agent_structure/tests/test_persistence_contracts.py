import unittest
from dataclasses import replace
from helpers import binding, key_for


class PersistenceContracts(unittest.TestCase):
    def test_key_matches_q40_q41_weather_only(self):
        a = key_for(40)
        self.assertEqual(a, key_for(41))
        self.assertNotEqual(a, key_for(41, tool='Local Search'))
        self.assertNotEqual(a, replace(a, recipient='mira', direction='read'))
        self.assertNotEqual(a, replace(a, user_id='bob'))
        self.assertNotEqual(replace(a, data_item='Address'), replace(a, data_item='Delivery address'))

    def test_invalid_n_never_constructs_config(self):
        from personal_assistant.config import PermissionConfig
        for n in (True, False, 0, -1, 1.2, '3', None):
            with self.subTest(n=n), self.assertRaises(ValueError):
                PermissionConfig(n)
        self.assertEqual(PermissionConfig(3).persist_rounds, 3)

    def test_all_65_bindings_preserve_source_and_explicit_extensions(self):
        from mock_tools.sources import source_queries
        from personal_assistant.contracts.persistence import SetupPermissionKey
        rows = source_queries()
        for q in range(65):
            b = binding(q)
            self.assertEqual(b.task.goal, rows[q]['query'])
            self.assertTrue(b.keys_for('alice', f'q{q}'))
            if q in (63, 64):
                self.assertTrue(all(isinstance(k, SetupPermissionKey) for k in b.keys_for('alice', f'q{q}')))
        ext = binding(54)
        k = next(k for k in ext.keys_for('alice', 'q54') if k.tool == 'Instagram' and k.data_item == 'Instagram post content')
        self.assertIsNone(ext.questionnaire_key(k))

    def test_setup_is_task_and_parameter_bound_and_cap_does_not_truncate(self):
        from personal_assistant.integration.wu import catalog_limits
        b = binding(64)
        self.assertNotEqual(b.keys_for('alice', 'one'), b.keys_for('alice', 'two'))
        u, s, cap = catalog_limits()
        self.assertGreater(u, 0)
        self.assertGreaterEqual(cap, u + 3 * s + 2)


if __name__ == '__main__':
    unittest.main()
