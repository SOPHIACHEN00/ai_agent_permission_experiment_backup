"""Local, no-network contract tests for the isolated S-QSTN wrapper."""
import csv
from copy import deepcopy
import json
from pathlib import Path
import unittest

from sqstn.core.runtime import SQSTNWrapper, LABELS, parse_answer
from sqstn.core.context import build_context
from sqstn.core.memory import PublicMemory

ROOT = Path(__file__).resolve().parents[1] / 'sqstn'


class WrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = SQSTNWrapper(ROOT)
        cls.pid = next(iter(cls.wrapper.personas))
        cls.item = next(iter(cls.wrapper.questions.values()))
        content = cls.item['question_content'].splitlines()
        cls.row = dict(query_id=cls.item['query_id'], query=content[0][14:],
                       tool=cls.item['tool'], raw_data_type=cls.item['raw_data_type'])

    def render(self, **kwargs):
        return self.wrapper.messages_for(self.pid, self.row, **kwargs)

    def test_real_empirical_card_is_connected(self):
        result = self.render()
        text = json.dumps(result['messages'])
        self.assertIn(self.wrapper.personas[self.pid]['profile_card_text'],
                      result['messages'][1]['content'])
        self.assertEqual(result['profile_audit']['source'], 'discovery_only_empirical_cluster')
        self.assertNotIn(self.pid, text)

    def test_target_and_oracle_mutations_cannot_change_prompt(self):
        original = self.render()
        for field in ('label_text', 'label_id', 'task3', 'oracle', 'reward',
                      'necessity_status', 'generic_data_type', 'expected_answer'):
            poisoned = {**self.row, field: 'CANARY_HIDDEN_ANSWER_DO_NOT_RENDER'}
            actual = self.wrapper.messages_for(self.pid, poisoned)
            self.assertEqual(original['messages'], actual['messages'], field)
            self.assertNotIn('CANARY_HIDDEN', json.dumps(actual))

    def test_all_questionnaires_match_wu_source(self):
        report = self.wrapper.verify_question_inventory()
        self.assertEqual(report['questionnaire_items'], 373)
        self.assertEqual(report['unique_queries'], 65)
        self.assertEqual(report['mismatches'], [])

    def test_static_state_is_empty_and_four_options_preserved(self):
        result = self.render()
        self.assertEqual(result['memory_audit']['transition_audit'], [])
        self.assertEqual(result['memory_audit']['view']['visible_events'], [])
        for label in LABELS:
            self.assertIn(label, result['messages'][1]['content'])

    def test_unknown_fields_do_not_activate_specific_rules(self):
        result = self.render()
        audit = {x['rule_id']: x for x in result['rule_audit']['directional']}
        self.assertEqual(len(audit), 6)
        for prefix in ('P4.', 'P5.', 'P6.'):
            entry = next(v for k, v in audit.items() if k.startswith(prefix))
            self.assertEqual(entry['status'], 'unknown')
            self.assertEqual(entry['effects'], [])
        self.assertEqual(result['context_audit']['values']['necessity_status'], 'unknown')
        self.assertEqual(result['context_audit']['provenance']['necessity_status']['source'],
                         'withheld_evaluator_only')

    def test_explicit_public_annotations_activate_rules_with_trace(self):
        annotations = {k: {'value': v, 'source': 'explicit_annotation',
                           'reference': 'unit-test-public-fixture', 'respondent_visible': True}
                       for k, v in {'expectedness': 'unexpected', 'revocable': True,
                                    'explanation_present': True}.items()}
        result = self.render(annotations=annotations)
        audit = result['rule_audit']['directional']
        for prefix in ('P4.', 'P5.', 'P6.'):
            entry = next(x for x in audit if x['rule_id'].startswith(prefix))
            self.assertEqual(entry['status'], 'active')
            self.assertTrue(entry['source_rule_ids'])
            self.assertTrue(entry['condition_inputs'])

    def test_timing_alone_does_not_prove_explanation_or_comprehension(self):
        result = self.render(annotations={'explanation_timing': {
            'value': 'just_in_time', 'source': 'explicit_annotation',
            'reference': 'fixture', 'respondent_visible': True}})
        p6 = next(x for x in result['rule_audit']['directional'] if x['rule_id'].startswith('P6.'))
        self.assertNotEqual(p6['status'], 'active')

    def test_controllability_is_not_a_temporary_allow_command(self):
        rule = next(x for x in self.wrapper.pack['rules'] if x['rule_id'].startswith('P5.'))
        self.assertNotIn('controlled_temporary_permission', json.dumps(rule['effects']))
        self.assertIn('defer', rule['prompt_instruction'])

    def test_presence_is_not_comprehension(self):
        rule = next(x for x in self.wrapper.pack['rules'] if x['rule_id'].startswith('P6.'))
        self.assertFalse(any(x['target'] in {'request_understanding', 'informed_choice'}
                             and x['direction'] == 'increase' for x in rule['effects']))

    def test_profile_only_is_a_real_ablation(self):
        result = self.render(rules_enabled=False)
        text = result['messages'][1]['content']
        self.assertNotIn('Active RulePack context:', text)
        self.assertNotIn('P9.necessity', text)
        self.assertIn(self.wrapper.personas[self.pid]['profile_card_text'], text)
        self.assertFalse(result['rule_audit']['injected'])

    def test_wrong_task_text_or_participant_is_rejected(self):
        with self.assertRaises(ValueError):
            self.wrapper.messages_for(self.pid, {**self.row, 'query': 'invented task'})
        with self.assertRaises(ValueError):
            self.wrapper.messages_for('nonexistent', self.row)
        with self.assertRaises(ValueError):
            self.wrapper.messages_for(self.pid, {**self.row, 'participant_id': 'different'})

    def test_output_schema_is_exact_and_duplicate_keys_rejected(self):
        for i, label in enumerate(LABELS):
            self.assertEqual(parse_answer(json.dumps({'answer': label})), (label, i))
        for raw in ('{"answer":"Yes, always share","extra":1}',
                    '{"answer":"No, never share","answer":"Yes, always share"}',
                    '{"answer":"allow"}', 'not json'):
            with self.assertRaises(ValueError):
                parse_answer(raw)

    def test_annotations_require_typed_visible_documented_sources(self):
        bad = [
            {'revocable': {'value': 'true', 'source': 'explicit_annotation', 'reference': 'x', 'respondent_visible': True}},
            {'revocable': {'value': True, 'source': 'model_inference', 'reference': 'x', 'respondent_visible': True}},
            {'revocable': {'value': True, 'source': 'explicit_annotation', 'reference': '', 'respondent_visible': True}},
            {'revocable': {'value': True, 'source': 'explicit_annotation', 'reference': 'x', 'respondent_visible': False}},
            {'expectedness': {'value': 'safe', 'source': 'explicit_annotation', 'reference': 'x', 'respondent_visible': True}},
            {'oracle': {'value': 'safe', 'source': 'explicit_annotation', 'reference': 'x', 'respondent_visible': True}},
            {'necessity_status': {'value': 'necessary', 'source': 'explicit_annotation', 'reference': 'x', 'respondent_visible': True}},
        ]
        for annotations in bad:
            with self.subTest(annotations=annotations), self.assertRaises(ValueError):
                self.render(annotations=annotations)

    def test_inconsistent_explicit_fields_rejected(self):
        values = {'scope': 'persistent', 'scope_explicit': False}
        annotations = {k: dict(value=v, source='explicit_annotation', reference='x', respondent_visible=True)
                       for k, v in values.items()}
        with self.assertRaises(ValueError):
            self.render(annotations=annotations)


class MemoryTests(unittest.TestCase):
    def memory(self):
        return PublicMemory(ROOT, subject_id='test-user', horizon_turns=3)

    def event(self, **updates):
        value = dict(event_id='evt1', subject_id='test-user', event_type='verified_agent_error',
                     turn_index=1, event_time='fixture-not-real', source='external_verified',
                     verification_status='verified', respondent_visible=True,
                     evidence_ref='public-fixture:failure-1', scope='task1/tool1',
                     metadata={'trust_dimension': 'competence'})
        value.update(updates)
        return value

    def test_hidden_oracle_and_cross_user_events_rejected(self):
        for updates in ({'source': 'synthetic_oracle'}, {'respondent_visible': False},
                        {'subject_id': 'another'}, {'evidence_ref': ''},
                        {'metadata': {'oracle_answer': 'CANARY'}}, {'turn_index': True}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.memory().append(self.event(**updates))

    def test_verified_visible_event_changes_only_relevant_dimension(self):
        memory = self.memory()
        memory.append(self.event())
        view, audit = memory.view(2)
        self.assertEqual(view['state_snapshot']['trust_competence'], 'caution')
        self.assertEqual(view['state_snapshot']['trust_integrity'], 'unknown')
        self.assertEqual(len(audit), 1)

    def test_future_event_does_not_affect_past_state(self):
        memory = self.memory()
        memory.append(self.event(turn_index=9))
        view, audit = memory.view(2)
        self.assertEqual(view['state_snapshot']['memory_caution'], 'unknown')
        self.assertEqual(audit, [])

    def test_ordinary_denial_is_not_agent_violation(self):
        memory = self.memory()
        memory.append(self.event(event_type='permission_response_recorded',
                                 metadata={'answer': 'No, never share'}))
        view, audit = memory.view(2)
        self.assertEqual(view['state_snapshot']['memory_caution'], 'unknown')
        self.assertIn('ORDINARY_DENIAL_NOT_VIOLATION', audit[0]['reason_codes'])

    def test_events_bounded_and_subject_isolation(self):
        memory = self.memory()
        memory.append(self.event(event_type='permission_request_presented', metadata={}))
        view, _ = memory.view(5)
        self.assertEqual(view['visible_events'], [])
        with self.assertRaises(ValueError):
            memory.append(self.event())


if __name__ == '__main__':
    unittest.main()
