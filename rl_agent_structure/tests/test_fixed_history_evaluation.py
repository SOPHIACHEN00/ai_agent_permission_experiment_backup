"""Read-only comparison contracts; no torch, API or checkpoint evaluation locally."""
from contextlib import redirect_stderr
from copy import deepcopy
import io
import unittest
from helpers import ROOT
import sys
sys.path.insert(0,str(ROOT))
from rl_testing.fixed_history_evaluation import q_diagnostics, first_fingerprint, cold_matches, main


class FixedEvaluationTests(unittest.TestCase):
    def trace(self):
        return {'candidates':[{'candidate_id':'execute','action':'EXECUTE','valid':True,'q':.9},
                              {'candidate_id':'release','action':'RELEASE','valid':True,'q':1.2}],
                'runtime_budgets':{'release_step_limit':32,'release_steps_used':2},
                'pending_tool':'Weather','pending_step':'s1','selected_action':'RELEASE',
                'state_features':{'observed_answer_count':.8},'raw_observed_answers':4,
                'raw_active_allows':2,'round_index':61,'decision_index':1974}

    def test_q_summary_preserves_measured_values(self):
        result=q_diagnostics([self.trace()])
        self.assertEqual(result['max_valid_Q'],1.2)
        self.assertEqual(result['valid_Q_above_one'],1)
        self.assertAlmostEqual(result['first_execute_release_branch']['execute_minus_release'],-.3)
        self.assertEqual(result['first_execute_release_branch']['remaining_release_steps'],30)

    def test_context_match_excludes_network_scores_but_includes_user_state(self):
        a=self.trace();b=deepcopy(a);b['candidates'][0]['q']=-3.
        self.assertEqual(first_fingerprint(a),first_fingerprint(b))
        b['raw_observed_answers']=5
        self.assertNotEqual(first_fingerprint(a),first_fingerprint(b))

    def test_cold_comparison_checks_full_action_candidate_reward_sequence(self):
        task={'query_id':40,'task_id':'t','metrics':{'task_success':1},'return':.99}
        report={'tasks':[task],'decisions':[{'task_id':'t','action':'EXECUTE',
                                          'candidate_id':'c1','reward':.99}]}
        self.assertTrue(cold_matches(report,deepcopy(report),40))
        changed=deepcopy(report);changed['decisions'][0]['candidate_id']='c2'
        self.assertFalse(cold_matches(report,changed,40))

    def test_evaluation_opt_in_precedes_torch_import(self):
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:
            main(['--source-root','unused','--output','unused','--seed','3'])
        self.assertEqual(caught.exception.code,2)


if __name__=='__main__':unittest.main()
