"""Three bounded repair checks, with no network or learner construction."""
import os
import unittest
from unittest.mock import patch


class RepairTests(unittest.TestCase):
    def test_packager_resolves_existing_frozen_evidence(self):
        import prepare_server_package as p
        relative = 'ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/server-formal/formal_evidence/formal_train_validate_v0_evidence.zip'
        self.assertTrue((p.WORKSPACE / relative).is_file(), 'package root must resolve the existing frozen archive')

    def test_memory_growth_is_bounded_above_current_not_historical_rss(self):
        import pilot_runtime as m
        mib = 1024 ** 2
        # Prior peak2GiB, current1GiB, new growth513MiB must trip512MiB cap.
        with patch.object(m, 'peak_rss_bytes', return_value=2048*mib, create=True), \
             patch.object(m, 'current_rss_bytes', side_effect=[1024*mib, 1537*mib], create=True):
            budget = m.EvaluationBudget()
            with self.assertRaises(m.ResourceLimit):
                budget.check()

    def test_only_selected_gpu1_reaches_cuda_constructor(self):
        import learner_bridge as m
        class ReachedCUDA(RuntimeError):
            pass
        # Parent constructor creates CUDA networks: replace that boundary only.
        with patch.object(m.Family3V2MaskedDoubleDQN, '__init__', side_effect=ReachedCUDA):
            with patch.dict(os.environ, {'PA_RL_DEVICE': 'cuda:0', 'CUDA_VISIBLE_DEVICES': '1'}):
                with self.assertRaises(ReachedCUDA):
                    m.BudgetRecourseDDQN(seed=101, gamma=1)
            for device, visible in (('cpu','1'), ('cuda:0','0'), ('cuda:0','2'), ('cuda:0','3'), ('cuda:0','0,1')):
                with patch.dict(os.environ, {'PA_RL_DEVICE': device, 'CUDA_VISIBLE_DEVICES': visible}):
                    with self.assertRaises(ValueError):
                        m.BudgetRecourseDDQN(seed=101, gamma=1)


if __name__ == '__main__':
    unittest.main()
