"""GPU UUID formatting check; only external hardware queries are replaced."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class IdentityTests(unittest.TestCase):
    def test_same_uuid_without_vendor_prefix_matches_but_other_gpu_fails(self):
        import run_learner_pilot as r
        props = SimpleNamespace(uuid='fd2b38fa-d72c-dfda-3db7-f0a3acbe6940')
        with patch.object(r.sys, 'platform', 'linux'), \
             patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES':'1','PA_RL_DEVICE':'cuda:0'}), \
             patch.object(r, 'family3_v2_execution_device', return_value=SimpleNamespace(type='cuda')), \
             patch.object(r, 'family3_v2_device_metadata', return_value={}), \
             patch.object(r.subprocess, 'run', return_value=SimpleNamespace(stdout='1, GPU-fd2b38fa-d72c-dfda-3db7-f0a3acbe6940, fixture')), \
             patch.object(r.torch.cuda, 'get_device_properties', return_value=props):
            self.assertEqual(r.gpu_metadata()['physical_gpu_index'], 1)
            props.uuid = '00000000-0000-0000-0000-000000000000'
            with self.assertRaises(r.IntegrityError):
                r.gpu_metadata()


if __name__ == '__main__':
    unittest.main()
