"""S8-06 acceptance: regenerate the ledger from a tiny, isolated source tree."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PilotMetricsTest(unittest.TestCase):
    def test_fixture_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)

            def put(path, data):
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(data if isinstance(data, str) else json.dumps(data), encoding='utf-8')

            put('work/tickets/S8-01.md', '# S8-01 Example\n\nSprint 8. Depth: light.\n'
                '## Engineer report\nUsed knc-twin simulate; used a model table.\n'
                'Built GCC-KNC variants V0 and V1; card run passed.\n')
            put('.codex-logs/S8-01-0.jsonl', '\n'.join(json.dumps(d) for d in [
                {'timestamp': '2026-11-16T00:00:00Z', 'type': 'turn.started'},
                {'timestamp': '2026-11-16T01:00:00Z', 'type': 'turn.completed',
                 'usage': {'input_tokens': 100, 'output_tokens': 20}}]))
            twin = {'status': 'ok', 'result_class': 'unvalidated_scenario_estimate',
                    'timestamp_utc': '2026-11-16T00:05:00Z',
                    'invocation': {'command': 'simulate', 'cwd': str(root / '.work/S8-01')},
                    'python_execution_seconds': 2.5,
                    'prediction': {'predicted_cycles': 1000, 'dynamic_instructions': 200}}
            put('.work/S8-01/twin/simulate/result.json', twin)
            put('twin/copied/result.json', twin)  # A copy is not a second invocation.
            put('.work/S8-01/runs/card/run.json', {'job_id': 'fixture-job', 'card_minutes': 3,
                                                 'window': 12})
            put('runs/copy.json', {'job_id': 'fixture-job', 'card_minutes': 3, 'window': 12})
            put('jobs.jsonl', '\n'.join(json.dumps(d) for d in [
                {'jobId': 'fixture-job', 'purpose': 'knc-boinc S8-01', 'event': 'finish',
                 'card_minutes': 3},
                {'jobId': 'unrelated', 'purpose': 'other project', 'card_minutes': 99}]))
            predictions = [
                {'id': 'win', 'tickets': ['S8-01'], 'method': 'model',
                 'predicted': 2, 'measured': 4, 'baseline': 8, 'unit': 's',
                 'ranked_variants': ['V0', 'V1'], 'sent_variants': ['V0']},
                {'id': 'loss', 'tickets': ['S8-01'], 'method': 'twin',
                 'predicted_range': [1, 2], 'measured': 10, 'baseline': 8, 'unit': 's',
                 'predicted_winner': 'parallel', 'measured_winner': 'serial'},
                {'id': 'blocked', 'tickets': ['S8-01'], 'method': 'twin', 'status': 'unsupported'},
                {'id': 'pending', 'tickets': ['S8-01'], 'method': 'twin', 'predicted': 2}]
            put('docs/pilot-study/predictions.json', predictions)
            script = ROOT / 'tools/pilot_metrics.py'
            self.assertTrue(script.is_file(), 'missing pilot metrics generator')
            subprocess.run([sys.executable, str(script), '--repo', str(root),
                            '--ledger', str(root / 'jobs.jsonl'),
                            '--predictions', str(root / 'docs/pilot-study/predictions.json'),
                            '--output', str(root / 'output')],
                           check=True, capture_output=True, text=True)
            metrics = json.loads((root / 'output/metrics.json').read_text())
            t = metrics['tickets'][0]
            self.assertEqual((t['sprint'], t['depth'], t['sessions'], t['engineer_seconds']),
                             (8, 'light', 1, 3600))
            self.assertEqual(t['tokens'], {'input_tokens': 100, 'output_tokens': 20})
            self.assertEqual(t['twin_status'], {'ok': 1, 'unsupported': 0,
                                               'missing_parameter': 0, 'other': 0})
            self.assertEqual((t['twin_host_seconds'], t['model_table'], t['gcc_knc_variants'],
                              t['card_jobs'], t['card_minutes']), (2.5, True, True, 1, 3))
            self.assertEqual(metrics['twin_runs'][0]['simulated_cycles'], 1000)
            self.assertEqual(metrics['twin_runs'][0]['simulated_instructions'], 200)
            self.assertEqual(metrics['sprints'][0]['card_minutes'], 3)
            scores = metrics['predictions']
            self.assertEqual([s['usefulness'] for s in scores],
                             ['decided', 'missed', 'unsupported', 'not-attempted'])
            self.assertEqual(scores[0]['ratio'], 2)
            self.assertEqual(scores[1]['ratio_range'], [5, 10])
            self.assertIsNone(scores[1]['ratio'])
            self.assertEqual([s['direction_right'] for s in scores], [True, False, None, None])
            self.assertEqual(metrics['totals']['direction_hit_rate'], 0.5)
            self.assertEqual(metrics['totals']['card_runs_avoided'], 1)
            readme = (root / 'output/README.md').read_text()
            self.assertIn('| 8 | S8-01 | 1 | 1.000 | 1/0 | 2.500 | yes | 1 | 3.000 |', readme)
            self.assertIn('| win |', readme)
            self.assertIn('| 8 | 1 | 1 | 1.000 |', readme)


if __name__ == '__main__':
    unittest.main()
