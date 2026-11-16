"""Card-free acceptance for the lead's end-to-end launcher."""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock
import contextlib
import io

ROOT = pathlib.Path(__file__).resolve().parents[1]


class EndToEnd(unittest.TestCase):
    def test_dry_run(self):
        config = json.loads(pathlib.Path(
            'C:/Users/xuzhi/Documents/gcc_knc/config/card.local.json').read_text())
        for case, threads, timing in (('medium', '4', '60 s -> suspend 30 s'),
                                      ('large', '240', '5 s -> suspend 5 s')):
            with self.subTest(case=case):
                result = subprocess.run(['bash', 'scripts/e2e_card.sh', '--dry-run',
                                         '--case', case, '--threads', threads], cwd=ROOT,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.assertEqual(result.returncode, 0, result.stdout)
                for token in ('ssh.exe', 'scp.exe', '192.168.1.100', 'xeon_phi_rsa',
                              '/tmp/claude/claude-knc-boinc', 'STOP', 'CONT', 'KILL',
                              'ps -o stat=', 'checkpoint.request', 'knc_checkpoint',
                              'snapshot', 'stdout.txt', 'stderr.txt', 'rm -rf',
                              timing, 'restart', 'compare.py', 'live-card.png'):
                    self.assertIn(token, result.stdout)
                for line in result.stdout.splitlines():
                    if 'ssh.exe' in line or 'scp.exe' in line:
                        self.assertIn('-o UserKnownHostsFile=' + config['knownHosts'], line)
                        self.assertIn('-o StrictHostKeyChecking=yes', line)
                self.assertNotIn('--fake-card', result.stdout)

    def test_known_hosts_validation(self):
        spec = importlib.util.spec_from_file_location('e2e', ROOT / 'scripts/e2e_card.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            config = pathlib.Path(tmp) / 'card.local.json'
            with self.assertRaisesRegex(RuntimeError, 'card.local.json'):
                module.transport_options(config)
            for value in ({}, {'knownHosts': 'missing-host-key-file'}, {'knownHosts': ''}):
                config.write_text(json.dumps(value))
                with self.assertRaisesRegex(RuntimeError, 'knownHosts'):
                    module.transport_options(config)
            hosts = pathlib.Path(tmp) / 'known hosts'
            hosts.write_text('test host key')
            config.write_text(json.dumps({'knownHosts': str(hosts)}))
            options = module.transport_options(config)
            self.assertIn('UserKnownHostsFile=' + str(hosts), options)
            self.assertIn('StrictHostKeyChecking=yes', options)

    def test_wrapper_host_options(self):
        # Exercise the real transport argv builder using local failing stubs.
        # No SSH/SCP executable or private key is accessed.
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            slot = pathlib.Path(tmp)
            for name in ('known_hosts', 'params.lua', 'input.hist', 'app.mic'):
                (slot / name).write_text('fixture')
            for name, code in (('ssh', 0), ('scp', 1)):
                stub = slot / (name + '.sh')
                stub.write_bytes(chr(10).join(['#!/bin/bash',
                    'printf "%s' + chr(92) + 'n" "$@" >> ' + name + '-args',
                    'exit ' + str(code), '']).encode())
                stub.chmod(0o755)
            cfg = dict(host='card.invalid', user='root', ssh_key=str(slot / 'unused-key'),
                       known_hosts=(slot / 'known_hosts').as_posix(),
                       ssh_path=(slot / 'ssh.sh').as_posix(), scp_path=(slot / 'scp.sh').as_posix(),
                       package_dir=slot.as_posix(), app='app.mic', retry_limit=0)
            (slot / 'knc_wrapper.cfg').write_text(''.join(k + '=' + str(v) + chr(10) for k, v in cfg.items()))
            env = dict(os.environ)
            env['PATH'] = 'C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin' + os.pathsep + env['PATH']
            env.pop('KNC_FAKE_CARD', None)
            result = subprocess.run([str(ROOT / 'build/wrapper/knc_wrapper.exe')], cwd=slot,
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ('ssh', 'scp'):
                self.assertTrue((slot / (name + '-args')).is_file(), result.stderr)
                argv = (slot / (name + '-args')).read_text().splitlines()
                self.assertIn('UserKnownHostsFile=' + cfg['known_hosts'], argv)
                self.assertIn('StrictHostKeyChecking=yes', argv)

    def test_large_slot(self):
        spec = importlib.util.spec_from_file_location('e2e', ROOT / 'scripts/e2e_card.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            root = pathlib.Path(tmp)
            for name in ('dist/milkyway_package/knc_wrapper.exe',
                         'dist/milkyway_package/knc_nbody_graphics.exe',
                         'dist/milkyway_package/milkyway_nbody.mic',
                         'build/boinc/boinc_fake_client.exe', 'build/x86/milkyway_nbody.exe',
                         'workunits/large/params.lua', 'workunits/large/input.hist'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('fixture')
            options = module.transport_options()
            args = argparse.Namespace(case='large', threads=240, in_granted_turn=True,
                                      ssh_options=options)
            def stop_at_launch(*argv, **kwargs):
                slot = kwargs['cwd']
                cfg = dict(line.split('=', 1) for line in
                           (slot / 'knc_wrapper.cfg').read_text().splitlines())
                self.assertEqual(cfg['known_hosts'], options[-1].split('=', 1)[1])
                self.assertEqual(cfg['ssh_path'], module.SSH)
                self.assertEqual(cfg['scp_path'], module.SCP)
                self.assertEqual(cfg['bodies'], '20000')
                self.assertEqual(cfg['OMP_NUM_THREADS'], '240')
                self.assertEqual(kwargs['env']['KNC_E2E_LARGE'], '1')
                self.assertTrue(kwargs['env']['KNC_TASK_ARGS'].endswith(' 20000'))
                self.assertEqual((slot / 'params.data').read_text(), 'fixture')
                raise RuntimeError('stopped before launch')
            with mock.patch.object(module, 'ROOT', root),                  mock.patch.object(module.subprocess, 'Popen', side_effect=stop_at_launch),                  contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'stopped before launch'):
                    module.live(args)

    def test_ledger(self):
        spec = importlib.util.spec_from_file_location('e2e', ROOT / 'scripts/e2e_card.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Exercise argument routing with every process launch forbidden.
        with mock.patch.object(module.subprocess, 'Popen', side_effect=AssertionError('process launched')), \
             mock.patch.object(module.subprocess, 'run', side_effect=AssertionError('process launched')), \
             mock.patch('sys.argv', ['e2e_card.py', '--dry-run']), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as tmp:
            ledger = pathlib.Path(tmp) / 'jobs.jsonl'
            def check(rows, blocked):
                ledger.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                if blocked:
                    with self.assertRaises(RuntimeError):
                        module.check_ledger(ledger)
                else:
                    module.check_ledger(ledger)
            foreign = dict(jobId='other', project='gcc-knc', event='queued')
            check([foreign], True)
            check([dict(foreign, event='start')], True)
            for close in ('finish', 'superseded', 'cancelled', 'close'):
                check([foreign, dict(foreign, event=close)], False)
            check([dict(foreign, project='knc-boinc')], False)
            check([dict(foreign, project=None)], True)
            ledger.write_text('{broken\n')
            with self.assertRaises(RuntimeError):
                module.check_ledger(ledger)


if __name__ == '__main__':
    unittest.main()
