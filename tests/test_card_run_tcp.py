"""S10-08 offline acceptance: fake endpoints, socket and SSH only."""
import importlib.util
import socket
import sys
import subprocess
import unittest
from unittest.mock import Mock, patch

import test_card_run_project


class TcpTest(unittest.TestCase):
    setUp = test_card_run_project.CardProjectTest.setUp

    def test_policy_and_preflight_boundary(self):
        r = self.runner
        calls = []
        class Backend:
            def __init__(self, name): self.name = name
            def stage(self, source, private, **kw):
                calls.append(self.name)
                return dict(bytes=kw['size'], seconds=1, file_complete=True)
            def publish(self, *args): pass
        backends = {n: Backend(n) for n in ('ssh', 'dma', 'tcp')}
        def transfer(method, size=10, direction='up'):
            return r.transfer_file('s', 'd', size=size, direction=direction,
                                   method=method, threshold_bytes=10, backends=backends)
        for method, small, large in [('auto', 'ssh', 'dma'), ('tcp-large', 'ssh', 'tcp'),
                                      ('tcp', 'tcp', 'tcp'), ('ssh', 'ssh', 'ssh')]:
            self.assertEqual(transfer(method, 9)['method'], small)
            self.assertEqual(transfer(method)['method'], large)
        self.assertEqual(transfer('tcp', direction='down')['method'], 'ssh')
        for kind, started, cleaned in [('unavailable', False, False), ('unavailable', True, True),
                                       ('io', True, True), ('uncertain_cleanup', True, False)]:
            error = r.card_dma.TransferFailure('fake DMA', kind=kind, data_started=started,
                                               cleanup_confirmed=cleaned)
            with patch.object(backends['dma'], 'stage', side_effect=error):
                calls.clear()
                if kind == 'unavailable' and not started:
                    self.assertEqual(transfer('auto')['method'], 'tcp')
                    self.assertEqual(calls, ['tcp'])
                else:
                    with self.assertRaises(r.card_dma.TransferFailure): transfer('auto')
                    self.assertEqual(calls, [])
        error = r.card_dma.TransferFailure('TCP accept timed out', kind='unavailable',
                                           data_started=False, cleanup_confirmed=True)
        with patch.object(backends['tcp'], 'stage', side_effect=error):
            self.assertEqual(transfer('tcp')['method'], 'ssh')

    def test_tcp_socket_guards_length_and_timeout(self):
        r = self.runner
        source = self.directory / 'payload'
        source.write_bytes(b'abc')
        for failure in (None, 'length', 'timeout', 'peer'):
            with self.subTest(failure=failure):
                session = r.SSHSession.__new__(r.SSHSession)
                session.file_command = Mock(return_value=['fake-ssh'])
                session.rpc = Mock(return_value=b'2\n' if failure == 'length' else b'3\n')
                listener, connection, child = Mock(), Mock(), Mock()
                listener.__enter__ = Mock(return_value=listener)
                listener.__exit__ = Mock(return_value=False)
                connection.__enter__ = Mock(return_value=connection)
                connection.__exit__ = Mock(return_value=False)
                listener.getsockname.return_value = ('192.168.1.99', 43210)
                listener.accept.return_value = (connection, ('192.168.1.101' if failure == 'peer'
                                                            else '192.168.1.100', 123))
                if failure == 'timeout': listener.accept.side_effect = socket.timeout('timed out')
                child.communicate.return_value = (b'', b'')
                child.returncode = 0
                child.poll.return_value = None if failure in ('timeout', 'peer') else 0
                with patch.object(r.socket, 'socket', return_value=listener), \
                     patch.object(r.subprocess, 'Popen', return_value=child):
                    endpoint = r.TCPEndpoint(session, 10)
                    if failure:
                        with self.assertRaises(r.card_dma.TransferFailure) as caught:
                            endpoint.stage(source, 'claude-part-test', size=3, direction='up')
                        self.assertEqual(caught.exception.kind, 'integrity' if failure == 'length' else 'unavailable')
                    else:
                        self.assertEqual(endpoint.stage(source, 'claude-part-test', size=3, direction='up')['bytes'], 3)
                        connection.sendall.assert_called_once_with(b'abc')
                    listener.bind.assert_called_once_with(('192.168.1.99', 0))
                    listener.listen.assert_called_once_with(1)
                    self.assertLessEqual(listener.settimeout.call_args[0][0], 5)
                    self.assertIn('nc ', session.file_command.call_args[0][0])
                    if failure in ('timeout', 'peer'): child.kill.assert_called_once()

    def test_helper_free_uploads_obey_policy_including_pack(self):
        r = self.runner
        session = r.SSHSession.__new__(r.SSHSession)
        session.helper_free = True
        session.transfer_method = 'tcp'
        session.transfers = []
        session.transfer_file = Mock()
        source = self.directory / 'payload'
        source.write_bytes(b'abc')
        session.send_path('claude-payload', source, 10)
        session.transfer_file.assert_called_once()
        # Packed staging must use send_file rather than bypassing policy with upload().
        session.transfer_file.reset_mock()
        session.run_dir = '/tmp/knc-boinc/claude-' + 'a' * 32
        session.boot_id = 'fake-boot'
        session.rpc = Mock()
        session.send_file = Mock()
        session.upload = Mock(side_effect=AssertionError('pack bypassed policy'))
        session.pin_helper = source
        session.unpack_helper = source
        session.stage(session.run_dir, source, timeout=10, packed=True)
        self.assertEqual([call.args[0] for call in session.send_file.call_args_list],
                         ['claude-unpack', 'claude-pack'])
        session.card_helper = source
        session.send_path = Mock()
        session.bootstrap_helper(10)
        session.send_path.assert_called_once_with('claude-transfer', source, 10)

    def test_recovery_binary_shell_protocol(self):
        path = self.runner.ROOT / 'tools/card_dma_recover.py'
        spec = importlib.util.spec_from_file_location('recovery_tcp_test', path)
        recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recovery)
        transport = recovery.RecoveryTransport(self.runner, dict(host='fake', identity='fake', knownHosts='fake'), 5)
        # Fake SSH emulates Windows text stdin conversion, then runs POSIX dash.
        proc = self.directory / 'fixture-proc'
        (proc / 'sys/kernel/random').mkdir(parents=True)
        (proc / 'sys/kernel/random/boot_id').write_bytes(b'card-boot' + bytes([10]))
        (proc / '42').mkdir()
        (proc / '42/comm').write_bytes(b'init' + bytes([10]))
        real_run = subprocess.run
        def ssh(command, **kw):
            data = kw['input']
            if kw.get('text'): data = data.replace('\n', '\r\n').encode()
            data = data.replace(b'/proc/', b'./fixture-proc/')
            return real_run(['C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin/dash.exe', '-s'],
                            input=data, capture_output=True, check=True, cwd=self.directory)
        fixture_script = recovery.CARD_STATE.replace('/proc/', './fixture-proc/')
        # The old text-pipe bytes reproduce exit 2 on a POSIX shell, without a card.
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            ssh([], input=fixture_script, text=True)
        self.assertEqual(caught.exception.returncode, 2)
        self.assertIn(b'Illegal option', caught.exception.stderr)
        recovery.CARD_STATE = fixture_script
        with patch.object(recovery.subprocess, 'run', side_effect=ssh):
            state = transport.card_state()
        self.assertEqual(state['boot_id'], 'card-boot')
        self.assertEqual(state['helpers'], [])

    def test_affinity_launcher(self):
        wrapper = self.runner.ROOT / 'tools/codex_affinity.py'
        probe = ('import ctypes; from ctypes import wintypes; k=ctypes.windll.kernel32; '
                 'k.GetCurrentProcess.restype=wintypes.HANDLE; '
                 'k.GetProcessAffinityMask.argtypes=[wintypes.HANDLE, '
                 'ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]; '
                 'p=ctypes.c_size_t(); s=ctypes.c_size_t(); '
                 'assert k.GetProcessAffinityMask(k.GetCurrentProcess(), ctypes.byref(p), ctypes.byref(s)); '
                 'print(hex(p.value))')
        result = subprocess.run([sys.executable, str(wrapper), sys.executable, '-c', probe],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '0x3ff')
