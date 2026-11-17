"""S10-04 offline acceptance; no card or real transfer helper processes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_card_run_project


class CardStateTest(unittest.TestCase):
    setUp = test_card_run_project.CardProjectTest.setUp

    def test_per_tool_paths_and_cleanup_namespace(self):
        runner = self.runner
        local = runner.main_root(Path(runner.__file__).resolve().parents[1])
        self.assertEqual(runner.RECEIPT_DIR, local / '.work/_state/card')
        self.assertEqual(runner.default_lock(runner.ROOT), local / '.work/_state/card.lock')
        self.assertEqual(runner.main_root(local / '.work/another-ticket'), local)
        own = '/tmp/knc-boinc/claude-' + 'a' * 32
        foreign = '/tmp/claude/claude-' + 'a' * 32
        self.assertTrue(runner.RUN_DIR.fullmatch(own))
        self.assertFalse(runner.RUN_DIR.fullmatch(foreign))
        script = runner.remote_helpers()
        self.assertNotIn('/tmp/claude', script)
        self.assertNotIn('/claude/claude-', script)
        self.assertIn('/knc-boinc/claude-', script)
        # Exercise the shell's guard and reap entry point with the foreign path.
        probe = script + '\nrun_dir=' + foreign + '\nresolve_run_dir && exit 99\nreap_one "$run_dir"\n'
        result = subprocess.run(['C:/Program Files/Git/bin/bash.exe', '-s'], input=probe,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('directory shape', result.stderr)
        with patch.object(runner, 'ROOT', self.directory):
            session = runner.SSHSession.__new__(runner.SSHSession)
            session.helper_free = False
            session.host_helper = self.directory / 'read-only-helpers/transfer.exe'
            seen = []
            def send(name, path, timeout):
                self.assertEqual(path.read_bytes(), b'control bytes')
                seen.append(path)
                self.assertEqual(path.parent, self.directory / '.work/_state/card-scratch')
            session.send_path = send
            session.send_file('control', b'control bytes', 1)
            self.assertFalse(seen[0].exists())
        config = self.directory / 'config.json'
        config.write_text(json.dumps(dict(host='fake', identity='fake', knownHosts='fake', ledger='fake',
                                         transportTimeout=10)))
        with patch.object(sys, 'argv', ['card_run', '--config', str(config), 'fake']), \
             patch.object(runner, 'SSHTransport') as transport, \
             patch.object(runner, 'run', return_value={'exit_code': 0}) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 0)
        state = local / '.work/_state'
        self.assertEqual(run.call_args.kwargs['receipt_path'], state / 'card-result.json')
        self.assertEqual(transport.call_args.args[6], state / 'collected')
        self.assertEqual(transport.call_args.args[1], 120)
        self.assertEqual(transport.call_args.args[3:5], ('auto', 1024 * 1024))

    def test_shared_latch_write_and_card_lock(self):
        runner = self.runner
        shared = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_state')
        self.assertEqual(runner.SSHTransport({}, 1).dma_latch, shared / 'card-dma-active.lock')
        self.assertEqual(runner.SSHTransport({}, 1).card_lock, shared / 'card.lock')
        helper = self.directory / 'fake-helper'
        helper.write_bytes(b'fake')
        config = dict(transferHost=str(helper), transferHelper=str(helper))
        with patch.object(runner, 'ROOT', self.directory / 'local'), \
             patch.object(runner, 'UPSTREAM_ROOT', self.directory / 'upstream'):
            transport = runner.SSHTransport(config, 1, transfer='dma')
            expected = self.directory / 'upstream/.work/_state/card-dma-active.lock'
            self.assertEqual(transport.dma_latch, expected)
            def rpc(command, timeout, *, step):
                if step == 'dma-probe':
                    return b'available\n'
                if step == 'dma-protect':
                    raise OSError('fake transport stopped after latch write')
                self.fail('unexpected RPC: ' + step)
            session = SimpleNamespace(dma_enabled=True, host_helper=helper,
                                      cygwin_bin=self.directory, dma_latch=transport.dma_latch,
                                      run_dir='/tmp/knc-boinc/claude-' + 'a' * 32,
                                      boot_id='fake-boot', rpc=rpc)
            health = SimpleNamespace(event_log=lambda: {'fake': True})
            with patch.dict(sys.modules, {'host_card_transfer': health}), \
                 patch.object(runner.card_dma.subprocess, 'run',
                              return_value=SimpleNamespace(returncode=0)), \
                 patch.object(runner.card_dma.subprocess, 'Popen',
                              side_effect=AssertionError('real helper forbidden')):
                with self.assertRaisesRegex(OSError, 'fake transport stopped'):
                    runner.card_dma.HelperPair(session, 1).run(helper, 'private', 4, 'up', 'dma')
            self.assertEqual(json.loads(expected.read_text())['boot_id'], 'fake-boot')
            self.assertFalse((self.directory / 'local').exists())
        # The common job lock is mandatory even when --lock selects a local file.
        # An existing latch blocks SSH too; neither refusal connects to the card.
        program = self.directory / 'program'
        program.write_bytes(b'fake')
        shared_lock = self.directory / 'shared-card.lock'
        latch = self.directory / 'shared-latch'
        for blocked in ('lock', 'latch', None):
            class Transport(test_card_run_project.FakeTransport):
                dma_latch = latch
                card_lock = shared_lock
                def connect(this, *args, **kwargs):
                    self.assertTrue(shared_lock.exists())
                    return super().connect(*args, **kwargs)
            if blocked == 'lock':
                shared_lock.write_text('upstream owns it')
            if blocked == 'latch':
                latch.write_text('uncertain cleanup')
            with patch.object(runner, 'ROOT', self.directory), \
                 patch.object(runner, 'RECEIPT_DIR', self.directory / 'receipts'), \
                 patch.dict(runner.os.environ, {'USERNAME': 'offline', 'PM_ROLE': 'offline'}):
                result = runner.run(program, [], lock_path=self.directory / 'local.lock',
                                    external_locks=[], baseline_names=[], timeout=1, transport_timeout=1,
                                    receipt_path=None, transport=Transport(), ledger_path=self.ledger,
                                    benchmark=True, monotonic=lambda: 0)
            self.assertEqual(result['exit_code'], 125 if blocked else 0, result)
            if blocked == 'lock':
                self.assertEqual(shared_lock.read_text(), 'upstream owns it')
                shared_lock.unlink()
            if blocked == 'latch':
                self.assertTrue(latch.exists())
                latch.unlink()
            self.assertFalse(shared_lock.exists())

    def test_threshold_routing_and_uncertain_cleanup(self):
        runner = self.runner
        transport = runner.SSHTransport({}, 1)
        self.assertEqual(transport.transfer, 'auto')
        self.assertEqual(transport.threshold_bytes, 1024 * 1024)
        selected = []
        class Backend:
            def __init__(self, method):
                self.method = method
            def stage(self, source, private, *, size, direction):
                selected.append(self.method)
                return dict(bytes=size, file_complete=True, seconds=1)
            def publish(self, private, destination):
                pass
        backends = {name: Backend(name) for name in ('ssh', 'dma', 'tcp')}
        for size, expected in [(4096, 'ssh'), (1024 * 1024 - 1, 'ssh'),
                               (1024 * 1024, 'dma')]:
            row = runner.transfer_file('source', 'destination', size=size, direction='up',
                                               backends=backends, method=transport.transfer,
                                               threshold_bytes=transport.threshold_bytes)
            self.assertEqual(row['method'], expected)
        failure = runner.card_dma.TransferFailure('uncertain cleanup', kind='uncertain_cleanup',
                                                  data_started=True, cleanup_confirmed=False)
        with patch.object(backends['dma'], 'stage', side_effect=failure):
            before = list(selected)
            with self.assertRaises(runner.card_dma.TransferFailure):
                runner.transfer_file('s', 'd', size=transport.threshold_bytes, direction='up',
                                             backends=backends, method='auto',
                                             threshold_bytes=transport.threshold_bytes)
            self.assertEqual(selected, before)

        for kind, started, cleaned, falls_back in [('unavailable', False, False, True),
                                                   ('io', True, True, False)]:
            failure = runner.card_dma.TransferFailure('fake failure', kind=kind,
                                                      data_started=started, cleanup_confirmed=cleaned)
            with patch.object(backends['dma'], 'stage', side_effect=failure):
                if falls_back:
                    row = runner.transfer_file('s', 'd', size=transport.threshold_bytes, direction='up',
                                               backends=backends, method='auto',
                                               threshold_bytes=transport.threshold_bytes)
                    self.assertEqual(row['method'], 'tcp')
                    self.assertEqual(row['fallback']['method'], 'dma')
                else:
                    before = list(selected)
                    with self.assertRaises(runner.card_dma.TransferFailure):
                        runner.transfer_file('s', 'd', size=transport.threshold_bytes, direction='up',
                                             backends=backends, method='auto',
                                             threshold_bytes=transport.threshold_bytes)
                    self.assertEqual(selected, before)

    def test_recovery_dry_run_confirm_and_refusals(self):
        path = Path(__file__).resolve().parents[1] / 'tools/card_dma_recover.py'
        self.assertTrue(path.is_file(), 'recovery script missing')
        spec = importlib.util.spec_from_file_location('recover', path)
        recover = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recover)
        latch = self.directory / 'latch'
        row = dict(run_dir='/tmp/knc-boinc/claude-' + 'b' * 32,
                   boot_id='card-boot', host_state={'boot': 'host-boot', 'bugcheckRecord': 0})
        class Fake:
            def __init__(self):
                self.health = row['host_state']
                self.host = []
                self.card = dict(boot_id='card-boot', helpers=[])
                self.removed = []
            def host_state(self):
                return self.health
            def host_helpers(self):
                return self.host
            def card_state(self):
                return self.card
            def remove_run_dir(self, run_dir, boot_id):
                self.removed.append((run_dir, boot_id))
        for bad in (None, 'host-boot', 'bugcheck', 'host-process', 'card-boot', 'card-process', 'foreign-dir'):
            for confirm in (False, True):
                with self.subTest(bad=bad, confirm=confirm):
                    data = dict(row)
                    fake = Fake()
                    if bad == 'host-boot': fake.health = dict(boot='changed', bugcheckRecord=0)
                    if bad == 'bugcheck': fake.health = dict(boot='host-boot', bugcheckRecord=1)
                    if bad == 'host-process': fake.host = [42]
                    if bad == 'card-boot': fake.card['boot_id'] = 'changed'
                    if bad == 'card-process': fake.card['helpers'] = [43]
                    if bad == 'foreign-dir': data['run_dir'] = '/tmp/claude/claude-' + 'b' * 32
                    latch.write_text(json.dumps(data))
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        code = recover.recover(latch, fake, confirm=confirm,
                                               archive_dir=self.directory / 'archives')
                    self.assertEqual(code, 125 if bad else 0, output.getvalue())
                    changed = not bad and confirm
                    self.assertEqual(bool(fake.removed), changed)
                    self.assertEqual(latch.exists(), not changed)
                    if changed:
                        archives = list((self.directory / 'archives').glob('*.json'))
                        self.assertEqual(len(archives), 1)
                        self.assertEqual(json.loads(archives[0].read_text()), row)
                        archives[0].unlink()
                    if bad:
                        self.assertIn('REFUSE', output.getvalue())
