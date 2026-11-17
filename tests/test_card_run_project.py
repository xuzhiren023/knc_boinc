"""S9-02 offline acceptance: fake transport and temporary ledgers only."""
import contextlib
from datetime import datetime, timedelta, timezone
import importlib.machinery
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    loader = importlib.machinery.SourceFileLoader('local_card_run', str(ROOT / 'tools/card_run'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FakeTransport:
    """No subprocesses, SSH, card binaries, or remote state."""
    def connect(self, *args, **kwargs):
        return self

    def snapshot(self, **kwargs):
        return dict(boot_id='fake-boot', processes=[],
                    meminfo='MemFree: 15000000 kB\n',
                    cpuinfo='\n\n'.join('processor: %d\ncore id: %d' % (cpu, cpu // 4)
                                         for cpu in range(240)))

    def reap_stale(self, *args, **kwargs):
        return dict(reaped=[], stale_kept=[])

    def stage(self, *args, **kwargs):
        pass

    def execute(self, *args, **kwargs):
        return 0

    def cleanup(self, *args, **kwargs):
        pass

    def close(self):
        pass


class CardProjectTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'build/tmp')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.ledger = self.directory / 'jobs.jsonl'
        self.ledger.write_text('', encoding='utf8')
        with patch.dict(os.environ, {}, clear=True):
            self.runner = load_runner()

    def rows(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def run_fake(self, rows=()):
        self.ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        program = self.directory / 'program'
        program.write_bytes(b'fake')
        # Redirect ALL runner writes, including retained receipts, into the temp tree.
        with patch.object(self.runner, 'ROOT', self.directory), \
             patch.object(self.runner, 'RECEIPT_DIR', self.directory / 'receipts'), \
             patch.dict(os.environ, {'USERNAME': 'offline-test', 'PM_ROLE': 'offline-test'}):
            return self.runner.run(program, [], lock_path=self.directory / 'card.lock',
                                   external_locks=[], baseline_names=[], timeout=1,
                                   transport_timeout=1, receipt_path=None,
                                   transport=FakeTransport(), ledger_path=self.ledger,
                                   benchmark=True, monotonic=lambda: 0)

    def test_tagging_and_project_selection(self):
        self.assertEqual(self.runner.PROJECT, 'knc-boinc')
        result = self.run_fake()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertRegex(result['job_id'], r'^claude-[0-9a-f]{32}$')
        self.assertEqual([row['project'] for row in self.rows()], ['knc-boinc', 'knc-boinc'])
        config = self.directory / 'config.json'
        config.write_text(json.dumps(dict(host='unused', identity='unused', knownHosts='unused',
                                         ledger=str(self.ledger))))
        for env, cli, expected in [('env-project', [], 'env-project'),
                                   ('env-project', ['--project', 'cli-project'], 'cli-project')]:
            with patch.dict(os.environ, {'CARD_PROJECT': env}):
                runner = load_runner()
            with patch.object(sys, 'argv', ['card_run', '--config', str(config)] + cli + ['unused']), \
                 patch.object(runner, 'SSHTransport'), \
                 patch.object(runner, 'run', return_value={'exit_code': 0}), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 0)
            self.assertEqual(runner.PROJECT, expected)
            self.runner.PROJECT = expected
            result = self.run_fake()
            self.assertEqual(result['exit_code'], 0, result)
            self.assertEqual({row['project'] for row in self.rows()}, {expected})

    def test_is_ours(self):
        for row, expected in [({'project': 'knc-boinc'}, True),
                              ({'project': 'gcc-knc', 'jobId': 'claude-' + 'a' * 32}, False),
                              ({'project': 'PhiWeather'}, False),
                              ({'jobId': 'claude-' + 'a' * 32}, True),
                              ({'job_id': 'claude-' + 'b' * 32}, True),
                              ({'jobId': 'foreign'}, False)]:
            self.assertEqual(self.runner.is_ours(row), expected, row)

    def test_own_turn_admission_with_foreign_queue(self):
        now = datetime.now(timezone.utc)
        def queued(project, job_id, minutes):
            return dict(agent='claude', project=project, jobId=job_id, event='queued', cores=[],
                        timingValid=True, queuedTime=(now - timedelta(minutes=minutes)).isoformat())
        foreign = queued('PhiWeather', 'foreign-queue', 5)
        prior = dict(event='finish', project='knc-boinc', jobId='claude-' + 'c' * 32, timingValid=True)
        cases = [('knc-boinc', 10, 0), ('gcc-knc', 10, 125), ('knc-boinc', 1, 125),
                 ('knc-boinc', 181, 125)]
        for project, age, expected in cases:
            with self.subTest(project=project, age=age):
                # A stepping clock ends refusal immediately without sleeping.
                ticks = itertools.chain([0], itertools.repeat(2))
                with patch.object(self.runner.time, 'sleep', side_effect=AssertionError('unexpected wait')):
                    original = self.runner.run
                    def timed(*args, **kwargs):
                        kwargs['monotonic'] = lambda: next(ticks)
                        return original(*args, **kwargs)
                    with patch.object(self.runner, 'run', side_effect=timed):
                        result = self.run_fake([prior, queued(project, 'claude-turn-test', age), foreign])
                self.assertEqual(result['exit_code'], expected, result)
                self.assertEqual(any(row['event'] == 'start' for row in self.rows()), expected == 0)
                if expected:
                    self.assertIn('their turn', result['detail'])

    def turn(self, *args):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/card_turn.py'),
                                 '--ledger', str(self.ledger)] + list(args),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_turn_lifecycle_and_dry_run(self):
        foreign = dict(event='queued', agent='claude', project='gcc-knc',
                       jobId='claude-turn-upstream', cores=[], timingValid=True,
                       purpose='existing foreign turn', queuedTime=datetime.now(timezone.utc).isoformat())
        self.ledger.write_text(json.dumps(foreign) + '\n')
        before = self.ledger.read_bytes()
        dry = self.turn('--dry-run', 'queue', '--purpose', 'offline test')[0]
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertEqual(set(dry), {'event', 'agent', 'project', 'jobId', 'cores', 'timingValid', 'purpose', 'queuedTime'})
        self.assertRegex(dry['jobId'], r'^claude-turn-knc-boinc-\d{8}T\d{12}Z$')
        first = self.turn('queue', '--purpose', 'offline test')[0]
        self.assertEqual(first['project'], 'knc-boinc')
        self.assertEqual(first['cores'], [])
        self.assertIs(first['timingValid'], True)
        self.assertIsNotNone(datetime.fromisoformat(first['queuedTime']).utcoffset())
        before = self.ledger.read_bytes()
        preview = self.turn('--dry-run', 'requeue', first['jobId'])
        self.assertEqual([row['event'] for row in preview], ['superseded', 'queued'])
        self.assertEqual(self.ledger.read_bytes(), before)
        closed, fresh = self.turn('requeue', first['jobId'])
        self.assertEqual(closed['jobId'], first['jobId'])
        self.assertNotEqual(fresh['jobId'], first['jobId'])
        self.assertGreater(fresh['queuedTime'], first['queuedTime'])
        self.assertEqual(fresh['purpose'], first['purpose'])
        self.assertEqual(set(self.runner.active_jobs(self.rows())), {foreign['jobId'], fresh['jobId']})
        finish = self.turn('finish', fresh['jobId'], '--outcome', 'success')[0]
        self.assertEqual(finish['event'], 'finish')
        self.assertEqual(finish['outcome'], 'success')
        self.assertEqual(set(self.runner.active_jobs(self.rows())), {foreign['jobId']})
        for job_id in (foreign['jobId'], fresh['jobId']):
            result = subprocess.run([sys.executable, str(ROOT / 'tools/card_turn.py'), '--ledger',
                                     str(self.ledger), 'finish', job_id, '--outcome', 'success'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_paths_and_local_call_sites(self):
        upstream = Path('C:/Users/xuzhi/Documents/gcc_knc')
        self.assertEqual(self.runner.ROOT, upstream)
        self.assertEqual(self.runner.default_lock(self.runner.ROOT), upstream / '.work/_state/card.lock')
        self.assertEqual(self.runner.RECEIPT_DIR, upstream / '.work/_state/card')
        self.assertTrue((ROOT / 'scripts/card-run-path.sh').is_file())
        for directory in ('scripts', 'packaging'):
            for path in (ROOT / directory).rglob('*'):
                if path.is_file() and path.suffix in ('.sh', '.py'):
                    code = chr(10).join(line for line in path.read_text().splitlines()
                                     if not line.lstrip().startswith('#'))
                    self.assertNotIn('C:/Users/xuzhi/Documents/gcc_knc/tools/card_run', code, str(path))


if __name__ == '__main__':
    unittest.main()
