"""Offline migration regressions. Run with s-qstn's scientific Python environment."""
from pathlib import Path
import importlib
import json
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

HERE = Path(__file__).absolute().parent
PROJECT = HERE.parent
sys.path.insert(0, str(HERE / 'sqstn_pilot'))
sys.path.insert(0, str(HERE / 'multi_model_screening'))
sys.path.insert(0, str(HERE))


class CurrentSQSTNTests(unittest.TestCase):
    def test_missing_credentials_fail_before_client_creation(self):
        from screen_models import build_clients, MODEL_SPECS
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                build_clients([MODEL_SPECS['gemini']], None)

    def test_four_label_parser_remains_strict(self):
        from sqstn_backend import parse_answer
        labels = ['No, never share', 'No, but ask me next time', 'Yes, but ask me next time', 'Yes, always share']
        for number, label in enumerate(labels):
            self.assertEqual(parse_answer(json.dumps({'answer': label})), (label, number))
        for raw in ('{}', '[]', '{"answer": "yes"}', '{"answer": "No, never share", "answer": "Yes, always share"}'):
            with self.assertRaises(ValueError):
                parse_answer(raw)

    def test_icl_and_screening_metrics_work_without_legacy_src(self):
        icl = importlib.import_module('run_ic_four_label')
        screen = importlib.import_module('screen_models')
        compare = importlib.import_module('compare_shots')
        for compute in (icl.compute_metrics, screen.compute_metrics, compare.compute_metrics):
            score = compute([0, 1, 2, 3], [0, 1, 2, 3])
            self.assertEqual(score['accuracy'], 1.)
            self.assertEqual(score['macro_f1'], 1.)
            self.assertEqual(score['over_sharing_rate'], 0.)

    def test_backend_uses_current_default_and_ignores_evaluator_labels(self):
        from sqstn_backend import SQSTNBackend
        backend = SQSTNBackend(PROJECT)
        from sqstn import RetrievalSimulator
        sim = RetrievalSimulator()
        item = sim.items()[0]
        question = sim.wrapper.questions[(str(item['query_id']), item['tool'], item['data_item'])]
        user = 'sim-P001'
        row = {'participant_id': user, 'query_id': item['query_id'],
               'query': question['question_content'].splitlines()[0][14:],
               'tool': item['tool'], 'raw_data_type': item['data_item']}
        actual = backend.messages_for(user, row)
        expected = sim.compile(sim.profile_for(user), **item, sample_id=user)
        self.assertEqual(actual['messages'], expected['messages'])
        self.assertEqual(actual['profile_id'], sim.profile_for(user))
        poisoned = {**row, 'label_id': 1234, 'label_text': 'EVALUATOR_ONLY_CANARY',
                    'necessity_status': 'EVALUATOR_ONLY_CANARY'}
        self.assertEqual(backend.messages_for(user, poisoned)['messages'], actual['messages'])
        with self.assertRaises(ValueError):
            backend.messages_for('sim-P002', row)
        with self.assertRaises(ValueError):
            backend.messages_for(user, {**row, 'query': 'changed query'})
        with self.assertRaises(ValueError):
            backend.messages_for(user, {**row, 'tool': 'unknown tool'})

    def test_preparation_preserves_queries_not_human_identities_or_answers(self):
        from run_pilot import prepare, predictor_jobs, freeze_answers, write_predictions, save_json
        from run_ic_four_label import parse_response, make_bundles, ID_TO_LABEL
        with TemporaryDirectory(dir=os.environ.get('ICL_TEST_TMP')) as temporary:
            out = Path(temporary) / 'new'
            df, profiles, jobs, generation = prepare(out, 8.)
            self.assertEqual(len(jobs), 20)
            self.assertEqual(len(generation), 624)
            self.assertEqual(sum(g['role'] == 'history' for g in generation), 350)
            self.assertEqual(sum(g['role'] == 'test' for g in generation), 274)
            self.assertTrue(all(j['participant_id'].startswith('sim-') for j in jobs))
            self.assertTrue(all(not set(j['prompt_history_query_ids']) & set(j['test_query_ids']) for j in jobs))
            self.assertTrue(all(len(j['prompt_history_query_ids']) == 4 for j in jobs))
            self.assertTrue(all(profile == {} for profile in profiles.values()))
            self.assertTrue(df['label_text'].eq('').all())
            self.assertTrue(df['label_id'].eq(-1).all())
            config = json.loads((out / 'run_config.json').read_text(encoding='utf-8'))
            self.assertEqual(config['simulator_protocol'], 'current_retrieval_calibrated')
            self.assertFalse(config['human_demographics_used'])
            self.assertTrue(config['generator_uses_reference_human_answers'])
            # Fixture answers are test inputs, never experiment/model results.
            fixture = df.copy()
            fixture['label_id'] = 2
            fixture['label_text'] = 'Yes, but ask me next time'
            calls = predictor_jobs(out, jobs, fixture, profiles)
            self.assertEqual(len(calls), 40)
            for call in calls:
                prompt = call['messages'][0]['content']
                self.assertIn('Age group: unspecified', prompt)
                self.assertNotIn('recommended_answer', prompt)
                self.assertNotIn('profile_conditioned_shares', prompt)
                self.assertNotIn('persistent_granters', prompt)
                tail = prompt.split('New permission requests (null values are to be predicted):\n')[1]
                queries = json.loads(tail)
                self.assertTrue(all(value is None for q in queries for value in q['permission'].values()))
                history = prompt.split('User permission decision history:\n')[1].split('\n\nNew permission requests')[0]
                self.assertEqual(len(json.loads(history)), call['shots'])
            before = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
            prepare(out, 8.)
            after = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            # Complete the disk/parse/freeze/analysis path using labelled fixtures.
            # These are deliberately fabricated unit-test responses, NOT LLM results.
            for job in generation:
                label_id = job['row_index'] % 4
                save_json(out / 'calls' / (job['call_id'] + '.attempt1.json'), {
                    'call_id': job['call_id'], 'status': 'success',
                    'prompt_sha256': job['prompt_sha256'],
                    'answer': {'label_id': label_id, 'label_text': ID_TO_LABEL[label_id]},
                })
            frozen = freeze_answers(out, generation, df)
            self.assertEqual(len(frozen), 624)
            self.assertTrue(frozen['label_id'].isin([0, 1, 2, 3]).all())
            # Predictor messages change when fixture labels change: use a new test-only folder.
            predictions_out = out / 'fixture_predictions'
            predictions_out.mkdir()
            (predictions_out / 'calls').mkdir()
            (predictions_out / 'participants.csv').write_bytes((out / 'participants.csv').read_bytes())
            calls = predictor_jobs(predictions_out, jobs, frozen, profiles)
            for call in calls:
                payload = []
                for bundle in make_bundles(call['test_rows'], True):
                    payload.append({'id': bundle['id'], 'query': bundle['query'],
                                    'permission': {k: {'label': v, 'score': 1.} for k, v in bundle['answer'].items()}})
                parsed = parse_response(json.dumps(payload), call['test_rows'])
                save_json(predictions_out / 'calls' / (call['call_id'] + '.attempt1.json'),
                          {'call_id': call['call_id'], 'status': 'success', 'predictions': parsed})
            write_predictions(predictions_out, calls)
            from analyze_pilot import summarize
            summary = summarize(predictions_out)
            self.assertEqual(summary['n_rows'], 274)
            self.assertEqual(summary['metrics']['0shot']['accuracy'], 1.)
            self.assertEqual(summary['metrics']['4shot']['accuracy'], 1.)

    def test_prepare_refuses_old_or_unrelated_outputs_without_writing(self):
        from run_pilot import prepare
        with TemporaryDirectory(dir=os.environ.get('ICL_TEST_TMP')) as temporary:
            out = Path(temporary)
            marker = out / 'run_config.json'
            old = b'{"schema_version": 1, "purpose": "synthetic_permission_predictability_pilot"}'
            marker.write_bytes(old)
            with self.assertRaises(ValueError):
                prepare(out, 8.)
            self.assertEqual(marker.read_bytes(), old)
            self.assertEqual([p.name for p in out.iterdir()], ['run_config.json'])
        with TemporaryDirectory(dir=os.environ.get('ICL_TEST_TMP')) as temporary:
            out = Path(temporary)
            (out / 'keep.txt').write_text('keep', encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(out, 8.)
            self.assertEqual([p.name for p in out.iterdir()], ['keep.txt'])


if __name__ == '__main__':
    unittest.main()
