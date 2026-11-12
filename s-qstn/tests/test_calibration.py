import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from sqstn.retrieval.calibration import conditioned_distributions, recommend, fit_weights, PROFILES, apply_calibration_contract
from sqstn.retrieval.population import PROFILE_WEIGHTS
from sqstn.provider import CostLedger, request_payload
from sqstn.retrieval.prompt import render_population_cases
from sqstn.core.runtime import LABELS


def evidence():
    return {'version':'case_retrieval_v2','population':'all_reference_respondents','profile_filter':None,
            'cases':[dict(query='test',tool='Tool',raw_data_type='Data',exact=True,similarity=1.,
                          tool_match=True,data_match=True,counts=[1,2,3,4],support=10,shares=[.1,.2,.3,.4],
                          source_response_ids=['NEVER_TRANSMIT_THIS_ID'])]}


class CalibrationTests(unittest.TestCase):
    def test_population_marginals_and_zero_support_are_preserved(self):
        for p in ([.1,.2,.3,.4],[0,.2,.8,0],[1,0,0,0]):
            for power in (0,.5,1,4):
                q=conditioned_distributions(p,power)
                np.testing.assert_allclose(q.sum(axis=1),1,atol=1e-10)
                np.testing.assert_allclose(np.array(list(PROFILE_WEIGHTS.values()))@q,p,atol=1e-10)
                self.assertTrue((q>=0).all())
                self.assertTrue((q[:,np.array(p)==0]==0).all())

    def test_reference_conditioning_is_soft_and_has_expected_direction(self):
        q=conditioned_distributions([.25]*4)
        self.assertGreater(q[0,3],q[1,3])
        self.assertGreater(q[1,2],q[2,2])
        self.assertGreater(q[2,:2].sum(),q[0,:2].sum())

    def test_zero_power_leaves_persona_conditioning_to_original_core(self):
        q=conditioned_distributions([.1,.2,.3,.4],0)
        for row in q:
            np.testing.assert_allclose(row,[.1,.2,.3,.4])
        e=recommend(evidence(),PROFILES[1],'case',power=0,policy='empirical')
        prompt=render_population_cases(e)
        self.assertIn('human survey behavior',prompt)
        self.assertIn('verified memory',prompt)

    def test_outer_contract_preserves_original_prompt_and_is_audited(self):
        base={'messages':[{'role':'system','content':'original persona instruction'},
                          {'role':'user','content':'original rules and memory'}], 'prompt_sha256':'base'}
        e=recommend(evidence(),PROFILES[0],'case',policy='empirical_system',power=0)
        out=apply_calibration_contract(base,e)
        self.assertEqual(base['messages'][0]['content'],'original persona instruction')
        self.assertTrue(out['messages'][0]['content'].startswith(base['messages'][0]['content']))
        self.assertEqual(out['messages'][1],base['messages'][1])
        self.assertEqual(out['calibration_contract_audit']['base_prompt_sha256'],'base')
        self.assertNotEqual(out['prompt_sha256'],'base')

    def test_choice_calibration_does_not_rewrite_human_evidence(self):
        a=recommend(evidence(),PROFILES[0],'case',power=0)
        b=recommend(evidence(),PROFILES[0],'case',power=0,choice_multipliers=[1,.6,1,1])
        self.assertEqual(a['cases'],b['cases'])
        self.assertEqual(a['calibration']['population_shares'],b['calibration']['population_shares'])
        self.assertEqual(a['calibration']['profile_conditioned_shares'],b['calibration']['profile_conditioned_shares'])
        self.assertLess(b['calibration']['sampling_shares'][1],a['calibration']['sampling_shares'][1])
        with self.assertRaises(ValueError):
            recommend(evidence(),PROFILES[0],'case',choice_multipliers=[1,-1,1,1])

    def test_recommendation_ignores_evaluator_fields_and_has_no_identity_in_prompt(self):
        e=evidence()
        a=recommend(e,PROFILES[0],'case')
        e.update(gt='secret-target',counts=[900,0,0,0],participant_id='PRIVATE')
        b=recommend(e,PROFILES[0],'case')
        self.assertEqual(a['calibration'],b['calibration'])
        text=render_population_cases(b)
        for secret in ('NEVER_TRANSMIT_THIS_ID','secret-target','PRIVATE'):
            self.assertNotIn(secret,text)
        self.assertIn(a['calibration']['recommended_answer'],text)
        self.assertEqual(a['calibration'],recommend(evidence(),PROFILES[0],'case')['calibration'])

    def test_minimax_weights_respect_all_cells_and_keep_every_persona(self):
        A=np.array([[.1,.4,.7],[.2,.3,.1],[.3,.2,.1],[.4,.1,.1]]*2)
        target=A@np.array([.4,.4,.2])
        w=fit_weights(A,target)
        values=np.array([w[p] for p in PROFILES])
        self.assertAlmostEqual(values.sum(),1)
        self.assertGreaterEqual(values.min(),.05-1e-10)
        np.testing.assert_allclose(A@values,target,atol=1e-9)

    def test_separate_budget_does_not_mutate_old_ledger_and_stops_at_limit(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            root=Path(temp)
            old=root/'old.json'
            old.write_text('{"historical":"unchanged"}',encoding='utf-8')
            before=old.read_bytes()
            ledger=CostLedger(root/'new.json',limit='.02')
            payload=request_payload([{'role':'user','content':'permission test'}])
            ledger.reserve('one',payload)
            with self.assertRaises(ValueError):
                ledger.reserve('two',payload)
            self.assertEqual(old.read_bytes(),before)


if __name__=='__main__':
    unittest.main()
