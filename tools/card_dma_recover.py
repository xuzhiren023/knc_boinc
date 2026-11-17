#!/usr/bin/env python3
"""Lead/owner DMA recovery. Inspect by default; --confirm is explicit sign-off."""
import argparse
from datetime import datetime, timezone
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

RUN_DIR = re.compile(r'/tmp/knc-boinc/claude-[0-9a-f]{32}\Z')


def load_runner():
    loader = importlib.machinery.SourceFileLoader('recovery_card_run', str(Path(__file__).with_name('card_run')))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    runner = importlib.util.module_from_spec(spec)
    loader.exec_module(runner)
    return runner


def recover(latch, transport, *, confirm=False, archive_dir=None, card_lock=None):
    """Inspect every health check; mutate only after all checks and sign-off."""
    latch = Path(latch)
    held = False
    try:
        if confirm and card_lock is not None:
            fd = os.open(str(card_lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            held = True
            os.close(fd)
        if latch.is_symlink() or not latch.is_file():
            raise ValueError('latch must be an existing regular file')
        original = latch.read_bytes()
        row = json.loads(original)
        run_dir, boot_id, host_state = row['run_dir'], row['boot_id'], row['host_state']
        if not isinstance(run_dir, str) or not RUN_DIR.fullmatch(run_dir):
            raise ValueError('foreign or unsafe run dir; GCC-KNC owner must recover their own directory')
        if not isinstance(boot_id, str) or not boot_id.strip() or not isinstance(host_state, dict):
            raise ValueError('missing boot or host health baseline')
        if not host_state.get('boot') or 'bugcheckRecord' not in host_state:
            raise ValueError('incomplete host health baseline')
        passed = True
        def check(label, operation):
            nonlocal passed
            try:
                ok, detail = operation()
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
                ok, detail = False, str(error)
            print('%s: %s %s' % (label, 'PASS' if ok else 'REFUSE', detail))
            passed = passed and ok
        check('(a) host boot/bugcheck', lambda: (transport.host_state() == host_state, 'must equal latch host_state'))
        check('(b) host helper processes', lambda: (transport.host_helpers() == [], 'must have no claude-transfer.exe'))
        def card_check():
            state = transport.card_state()
            return (state['boot_id'] == boot_id and state['helpers'] == [],
                    'boot_id must equal latch; no claude-transfer processes')
        check('(c) card boot/helper processes', card_check)
        if not passed:
            print('REFUSE: clear nothing; lead/owner investigation required. Never reboot automatically.')
            return 125
        if not confirm:
            print('(d) DRY RUN: would remove exact owned run dir including claude-dma-active: ' + run_dir)
            print('(e) DRY RUN: would archive then delete latch: ' + str(latch))
            return 0
        if latch.read_bytes() != original:
            raise ValueError('latch changed during checks; clear nothing')
        # The transport rechecks boot and helper absence immediately before rm.
        transport.remove_run_dir(run_dir, boot_id)
        print('(d) PASS: removed ' + run_dir)
        if latch.read_bytes() != original:
            raise ValueError('latch changed after remote removal; retain latch for owner')
        directory = Path(archive_dir) if archive_dir is not None else latch.parent / 'dma-recovery'
        directory.mkdir(parents=True, exist_ok=True)
        archive = directory / ('card-dma-active-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                               + '-' + uuid.uuid4().hex + '.json')
        with archive.open('xb') as output:
            output.write(original)
            output.flush()
            os.fsync(output.fileno())
        if archive.read_bytes() != original or latch.read_bytes() != original:
            raise ValueError('archive verification or latch comparison failed; retain latch')
        latch.unlink()
        print('(e) PASS: archived to %s; deleted %s' % (archive, latch))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('REFUSE: ' + str(error))
        return 125
    finally:
        if held:
            Path(card_lock).unlink()


# No pkill/kill, reboot, DMA probe, or transfer is part of recovery.
CARD_STATE = r'''
set -eu
printf 'BOOT\t'
cat /proc/sys/kernel/random/boot_id
for proc in /proc/[0-9]*; do
    if name=$(cat "$proc/comm" 2>/dev/null); then
        case "$name" in claude-transfer*) printf 'HELPER\t%s\n' "${proc##*/}" ;; esac
    elif [ -d "$proc" ]; then
        echo 'cannot inspect a live card process' >&2; exit 92
    fi
done
'''


class RecoveryTransport:
    def __init__(self, runner, config, timeout):
        self.runner, self.config, self.timeout = runner, config, timeout

    def host_state(self):
        saved = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            from host_card_transfer import event_log
        finally:
            sys.dont_write_bytecode = saved
        return event_log()

    def host_helpers(self):
        command = ("$ErrorActionPreference='Stop'; ConvertTo-Json -Compress -InputObject "
                   "@(Get-CimInstance Win32_Process -Filter \"Name='claude-transfer.exe'\" "
                   "| ForEach-Object { [int]$_.ProcessId })")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, check=True, timeout=self.timeout)
        value = json.loads(result.stdout)
        if not isinstance(value, list) or any(not isinstance(pid, int) or pid <= 0 for pid in value):
            raise ValueError('invalid host process inventory')
        return value

    def ssh(self, script):
        c = self.config
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', c['host']):
            raise ValueError('invalid card host')
        command = ['C:/Windows/System32/OpenSSH/ssh.exe', '-T', '-F', 'NUL', '-i', c['identity'],
                   '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                   '-o', 'GlobalKnownHostsFile=NUL', '-o', 'UserKnownHostsFile=' + c['knownHosts'],
                   '-o', 'HostKeyAlgorithms=ssh-ed25519', '-o', 'ConnectTimeout=5',
                   'root@' + c['host'], 'exec sh']
        # Binary stdin preserves LF: Windows text pipes send CRLF, which BusyBox sh rejects.
        return subprocess.run(command, input=script.encode("utf8"), capture_output=True,
                              check=True, timeout=self.timeout).stdout.decode("utf8")

    def card_state(self):
        lines = self.ssh(CARD_STATE).splitlines()
        if not lines or not lines[0].startswith('BOOT\t') or not lines[0][5:].strip():
            raise ValueError('invalid card boot inventory')
        helpers = []
        for line in lines[1:]:
            if not line.startswith('HELPER\t') or not line[7:].isdigit():
                raise ValueError('invalid card process inventory')
            helpers.append(int(line[7:]))
        return dict(boot_id=lines[0][5:], helpers=helpers)

    def remove_run_dir(self, run_dir, boot_id):
        if not RUN_DIR.fullmatch(run_dir) or not isinstance(boot_id, str) or not boot_id.strip():
            raise ValueError('unsafe run dir or boot ID')
        # Check card health again in the same SSH invocation as guarded removal.
        script = ('state=$(\n' + CARD_STATE + '\n) || exit 92\n'
                  'case "$state" in *HELPER*) echo "card helper present" >&2; exit 92 ;; esac\n'
                  + self.runner.remote_helpers() + '\nrun_dir=' + shlex.quote(run_dir)
                  + '\nboot_id=' + shlex.quote(boot_id) + '\n'
                  'check_boot || exit 92\n'
                  'if [ -e "$run_dir" ] || [ -L "$run_dir" ]; then\n'
                  '  cd -- "$run_dir" && guard_boot || exit 92\n'
                  '  rm -rf -- "$run_dir" || exit 92\n'
                  'fi\n')
        self.ssh(script)


def main():
    runner = load_runner()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=runner.main_root(runner.UPSTREAM_ROOT) / 'config/card.local.json')
    parser.add_argument('--latch', type=Path, default=runner.main_root(runner.UPSTREAM_ROOT) / '.work/_state/card-dma-active.lock')
    parser.add_argument('--archive-dir', type=Path, default=runner.main_root(runner.ROOT) / '.work/_state/dma-recovery')
    parser.add_argument('--transport-timeout', type=float, default=120.0)
    parser.add_argument('--confirm', action='store_true', help='lead/owner sign-off to remove owned run dir, archive and delete latch')
    args = parser.parse_args()
    try:
        if args.confirm and (os.environ.get('PM_ROLE') == 'engineer' or os.environ.get('USERNAME', '').startswith('CodexSandbox')):
            raise ValueError('recovery changes are lead/owner-only')
        if not math.isfinite(args.transport_timeout) or args.transport_timeout <= 0:
            raise ValueError('transport timeout must be finite and positive')
        config = json.loads(args.config.read_text(encoding='utf8'))
        return recover(args.latch, RecoveryTransport(runner, config, args.transport_timeout),
                       confirm=args.confirm, archive_dir=args.archive_dir,
                       card_lock=runner.main_root(runner.UPSTREAM_ROOT) / '.work/_state/card.lock')
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('REFUSE: ' + str(error))
        return 125


if __name__ == '__main__':
    sys.exit(main())
