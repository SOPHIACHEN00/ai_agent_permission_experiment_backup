"""Tiny local receipt regression; synthetic credentials, no network or model."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ai_agent_permission_experiment'))
from rl_sqstn_integration_v0 import secure_control


class ReceiptCheck(unittest.TestCase):
    def test_machine_fields_preserved_and_credentials_rejected(self):
        auth = ('example.invalid', '22', 'synthetic_account', 'synthetic_secret')
        receipt = {'bytes': 12234, 'sha256': 'aa22bb', 'gpu_uuid': 'GPU-aa22-bb'}
        raw = json.dumps(receipt)
        # Root-cause witness for the reviewed old string replacement.
        with self.assertRaises(json.JSONDecodeError):
            json.loads(raw.replace(auth[1], '[REDACTED]'))
        self.assertTrue(hasattr(secure_control, 'decode_receipt'), 'Expected missing safe receipt decoder')
        self.assertEqual(secure_control.decode_receipt(raw, auth), receipt)
        for unsafe in ({'message': 'example.invalid'}, {'message': 'synthetic_secret'},
                       {'port': 22}, {'nested': {'password': 'anything'}}):
            with self.assertRaises(ValueError):
                secure_control.decode_receipt(json.dumps(unsafe), auth)


if __name__ == '__main__':
    unittest.main(verbosity=2)
