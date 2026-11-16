"""Implementation of e2e_card.sh; no network activity unless explicitly run live."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path('C:/Users/xuzhi/Documents/card-coordination/jobs.jsonl')
BASE = '/tmp/claude/claude-knc-boinc'
KEY = 'C:/Users/xuzhi/.ssh/xeon_phi_rsa'
SSH = 'C:/Windows/System32/OpenSSH/ssh.exe'
SCP = 'C:/Windows/System32/OpenSSH/scp.exe'
TARGET = 'root@192.168.1.100'
OPTIONS = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o',
           'ConnectionAttempts=1', '-o', 'ConnectTimeout=10', '-i', KEY]

CARD_CONFIG = Path('C:/Users/xuzhi/Documents/gcc_knc/config/card.local.json')
BODIES = dict(small=64, medium=1024, large=20000)


def transport_options(config=CARD_CONFIG):
    try:
        data = json.loads(config.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise RuntimeError('Cannot read card config {}: {}'.format(config, error))
    hosts = data.get('knownHosts') if isinstance(data, dict) else None
    if not isinstance(hosts, str) or not hosts.strip():
        raise RuntimeError('Card config {} needs a nonempty knownHosts path'.format(config))
    if not Path(hosts).is_file():
        raise RuntimeError('Card config knownHosts file missing: ' + hosts)
    return OPTIONS + ['-o', 'UserKnownHostsFile=' + hosts]


def cleanup_command(directory, pid):
    # Include the supervisor and descendants whose cwd is the deleted lease.
    # Allow the supervisor a bounded interval to reap the killed app and exit.
    return ('r=' + shlex.quote(directory) + '; p=' + shlex.quote(pid) +
            '; for n in 1 2 3 4 5 6 7 8 9 10; do '
            'busy=0; test ! -e "$r" || busy=1; '
            'kill -0 "$p" 2>/dev/null && busy=1; '
            'for c in /proc/[0-9]*/cwd; do d=$(readlink "$c" 2>/dev/null) || continue; '
            'case "$d" in "$r"|"$r (deleted)") busy=1;; esac; done; '
            'test "$busy" = 0 && exit 0; sleep 1; done; exit 1')


def check_ledger(path=LEDGER):
    """Replay by job ID: a new queue after a finish opens a reservation again."""
    try:
        active = {}
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            event, job = row['event'], row['jobId']
            if event in ('start', 'queued'):
                active[job] = row
            elif event in ('finish', 'close', 'closed', 'cancelled', 'canceled', 'superseded'):
                active.pop(job, None)
        foreign = [r for r in active.values() if r.get('project') != 'knc-boinc']
        if foreign:
            raise RuntimeError('Card ledger has open foreign/unknown reservations: ' +
                               ', '.join(r['jobId'] for r in foreign) +
                               '; lead may use --in-granted-turn after receiving the turn')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError('Cannot establish card ledger safety: ' + str(error))


def dry_plan(case, threads, options):
    # Runtime leases, PIDs, repeat counts and package inventory are symbolic.
    # Include each transport operation, including conditional/repeated ones.
    ssh = [SSH, '-T'] + options + ['--', TARGET]
    scp = [SCP, '-O'] + options + ['--']
    def remote(command):
        print(shlex.join(ssh + [command]))
    def copy(local, remote_name, upload=True):
        pair = [local, TARGET + ':' + shlex.quote(remote_name)]
        print(shlex.join(scp + (pair if upload else pair[::-1])))
    print('DRY RUN: no card commands executed; ledger enforced only for live runs.')
    run_seconds, suspend_seconds = (5, 5) if case == 'large' else (60, 30)
    print('case={} threads={} bodies={}; workunits/{}; run {} s -> suspend {} s -> resume 2 s -> checkpoint -> quit -> restart'.format(
        case, threads, BODIES[case], case, run_seconds, suspend_seconds))
    print('Screenshot at {} s after first live snapshot; suspend at {} s after that snapshot.'.format(
        2 if case == 'large' else 30, run_seconds))
    print('Templates: $R is a fresh ' + BASE + '/task-<pid>-<time> per launch;')
    print('$PID is read from its pid file; polling/retries repeat the listed commands.')
    for launch in ('initial', 'restart'):
        print('# ' + launch)
        remote('test -d "$R" || mkdir -p -- "$R"')
        remote('cd "$R" && if test -f exit; then printf "exit "; cat exit; fi; '
               'if test -f pid; then p=$(cat pid); case $p in \'\'|*[!0-9]*) exit 2;; esac; echo pid 1; '
               'if kill -0 "$p" 2>/dev/null; then echo live 1; fi; fi; '
               'if test -f progress; then printf "progress "; cat progress; fi; '
               'if test -f snapshot; then echo snapshot 1; fi; '
               'if test -f checkpoint.ready; then echo checkpoint 1; fi; true')
        print('# scp once for app and each packaged *.so*; stage input files in argv order')
        copy('dist/milkyway_package/milkyway_nbody.mic', '$R/milkyway_nbody.mic')
        runtimes = sorted((ROOT / 'dist/milkyway_package').glob('*.so*'))
        if runtimes:
            for runtime in runtimes:
                copy('dist/milkyway_package/' + runtime.name, '$R/' + runtime.name)
        else:
            copy('dist/milkyway_package/<each-runtime.so*>', '$R/<each-runtime.so*>')
        remote('cd "$R" && mkdir -p files')
        copy('slot/params.data', '$R/files/0')
        copy('slot/hist.data', '$R/files/1')
        if launch == 'restart':
            copy('slot/knc_checkpoint', '$R/checkpoint')
        copy('slot/knc_run.sh', '$R/run.sh')
        remote('cd "$R" && chmod u+x milkyway_nbody.mic && if mkdir started 2>/dev/null; then nohup sh ./run.sh >stdout.txt 2>stderr.txt </dev/null & fi')
        copy('slot/knc_snapshot.tmp', '$R/snapshot', False)
        if launch == 'initial':
            remote('cd "$R" && p=$(cat pid); kill -STOP "$p"')
            remote('cd "$R" && p=$(cat pid); printf "%s " "$p"; ps -o stat= -p "$p"')
            remote('cd "$R" && p=$(cat pid); kill -CONT "$p"')
            remote('cd "$R" && test -s checkpoint')
            remote('cd "$R" && rm -f checkpoint.ready; touch checkpoint.request')
            remote('cd "$R" && p=$(cat pid); kill -STOP "$p"')
            copy('slot/knc_checkpoint.tmp', '$R/checkpoint', False)
            remote('cd "$R" && p=$(cat pid); kill -KILL "$p"')
        else:
            remote('cd "$R" || exit 1; n=0; while ! test -s pid; do n=$((n+1)); test "$n" -lt 10 || exit 1; sleep 1; done; cat pid')
            copy('slot/nbody_stdout.txt', '$R/stdout.txt', False)
            copy('slot/nbody_stderr.txt', '$R/stderr.txt', False)
            copy('slot/result.data', '$R/files/2', False)
        remote('rm -rf -- "$R"')
        remote(cleanup_command('$R', '$PID'))
    print('Live graphics -> docs/img/live-card.png; wall times, wrapper log, cleanup and')
    print('scripts/compare.py (strict |diff| < 1e-10) -> runs/e2e/<timestamp>/summary.json')


def bmp_to_png(source, destination):
    """Convert the graphics consumer's uncompressed 24-bit bottom-up BMP."""
    data = source.read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height = struct.unpack_from('<ii', data, 18)
    if data[:2] != b'BM' or width <= 0 or height <= 0 or struct.unpack_from('<HI', data, 28) != (24, 0):
        raise RuntimeError('Unexpected graphics BMP format')
    stride = (width * 3 + 3) & ~3
    pixels = bytearray()
    for y in reversed(range(height)):
        row = data[offset + y * stride:offset + y * stride + width * 3]
        if len(row) != width * 3:
            raise RuntimeError('Truncated graphics capture')
        pixels.append(0)
        for x in range(0, len(row), 3):
            pixels.extend(row[x:x + 3][::-1])
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value) & 0xffffffff)
    destination.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
                            chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


def live(args):
    options = args.ssh_options
    if not args.in_granted_turn:
        check_ledger()
    package = ROOT / 'dist/milkyway_package'
    client = ROOT / 'build/boinc/boinc_fake_client.exe'
    reference = ROOT / 'build/x86/milkyway_nbody.exe'
    for file in (package / 'knc_wrapper.exe', package / 'knc_nbody_graphics.exe',
                 package / 'milkyway_nbody.mic', client, reference):
        if not file.is_file():
            raise RuntimeError('Missing {}; prepare package, boinc-api-test and x86 before card window'.format(file))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run = ROOT / 'runs/e2e' / stamp
    slot = run / 'slot'
    slot.mkdir(parents=True)
    summary = dict(case=args.case, threads=args.threads, granted_turn=args.in_granted_turn,
                   status='FAIL', cleanup=[], wall_seconds={})
    started = time.monotonic()
    child = None
    def ssh(command):
        argv = [SSH, '-T'] + options + ['--', TARGET, command]
        with (run / 'transport.log').open('a') as log:
            log.write(shlex.join(argv) + '\n')
            log.flush()
            result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=20)
            log.write(result.stdout)
        if result.returncode:
            raise RuntimeError('Card verification failed: ' + command + ': ' + result.stdout)
        return result.stdout.strip()
    try:
        for src, dst in (('params.lua', 'params.data'), ('input.hist', 'hist.data')):
            shutil.copyfile(ROOT / 'workunits' / args.case / src, slot / dst)
        for logical, physical in (('params.lua', 'params.data'), ('input.hist', 'hist.data'), ('histogram.txt', 'result.data')):
            (slot / logical).write_text('<soft_link>{}</soft_link>\n'.format(physical))
        bodies = BODIES[args.case]
        (slot / 'knc_wrapper.cfg').write_text(
            'host=192.168.1.100\nuser=root\nssh_key={}\nknown_hosts={}\nssh_path={}\nscp_path={}\nremote_base={}\n'
            'package_dir={}\napp=milkyway_nbody.mic\nOMP_NUM_THREADS={}\npoll_interval=1\n'
            'snapshot_interval=5\nconnect_timeout=10\nretry_limit=3\ncheckpoint_timeout=60\nbodies={}\n'.format(
                KEY, options[-1].split('=', 1)[1], SSH, SCP, BASE, package.as_posix(), args.threads, bodies))
        task = '-f params.lua -h input.hist -z histogram.txt --seed 670828913 --nthreads {} --print-histogram {}'.format(args.threads, bodies)
        env = dict(os.environ, KNC_TASK_ARGS=task, KNC_GRAPHICS_EXE=str(package / 'knc_nbody_graphics.exe'))
        env.pop('KNC_FAKE_CARD', None)
        env['KNC_E2E_LARGE'] = '1' if args.case == 'large' else '0'
        leases = {}
        phase_start = time.monotonic()
        with (run / 'client.log').open('w') as log:
            child = subprocess.Popen([str(client), str(package / 'knc_wrapper.exe'), 'local', 'e2e-card'],
                                     cwd=slot, env=env, stdout=log, stderr=subprocess.STDOUT)
            phases = ('suspended', 'checkpoint', 'quit-clean', 'restarted', 'final-clean')
            for phase in phases:
                marker = slot / ('e2e-' + phase)
                deadline = time.monotonic() + (43200 if phase == 'final-clean' else 300)
                while not marker.exists():
                    if child.poll() is not None:
                        raise RuntimeError('BOINC scenario exited before ' + phase + '; see client.log')
                    if time.monotonic() > deadline:
                        raise RuntimeError('Timed out waiting for ' + phase)
                    time.sleep(.1)
                if phase in ('suspended', 'restarted'):
                    directory = (slot / 'knc_remote').read_text().strip()
                    if not re.fullmatch(re.escape(BASE) + r'/task-\d+-\d+', directory):
                        raise RuntimeError('Unsafe remote lease: ' + directory)
                    if phase == 'suspended':
                        state = ssh('cd ' + shlex.quote(directory) + ' && p=$(cat pid); printf "%s " "$p"; ps -o stat= -p "$p"')
                        pid, stat = state.split()
                        if not stat.startswith('T'):
                            raise RuntimeError('Card process not stopped: ' + state)
                        (run / 'suspend-ps.txt').write_text(state + '\n')
                        image = run / 'live-card.png'
                        bmp_to_png(slot / 'live-card.bmp', image)
                        (ROOT / 'docs/img').mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(image, ROOT / 'docs/img/live-card.png')
                    else:
                        pid = ssh('cd ' + shlex.quote(directory) +
                                  ' || exit 1; n=0; while ! test -s pid; do n=$((n+1)); '
                                  'test "$n" -lt 10 || exit 1; sleep 1; done; cat pid')
                    if not pid.isdigit():
                        raise RuntimeError('Invalid card PID')
                    leases['initial' if phase == 'suspended' else 'restart'] = (directory, pid)
                elif phase == 'checkpoint':
                    ssh('cd ' + shlex.quote(leases['initial'][0]) + ' && test -s checkpoint')
                else:
                    which = 'initial' if phase == 'quit-clean' else 'restart'
                    directory, pid = leases[which]
                    ssh(cleanup_command(directory, pid))
                    summary['cleanup'].append(dict(launch=which, directory=directory, pid=pid, gone=True))
                summary['wall_seconds'][phase] = time.monotonic() - phase_start
                phase_start = time.monotonic()
                (slot / ('e2e-' + phase + '.ack')).touch()
            if child.wait(timeout=30):
                raise RuntimeError('BOINC scenario failed; see client.log')
        x86 = run / 'x86'
        x86.mkdir()
        command = [str(reference), '-f', str(slot / 'params.data'), '-h', str(slot / 'hist.data'),
                   '-z', str(x86 / 'histogram.txt'), '-c', str(x86 / 'checkpoint'), '--seed', '670828913',
                   '--nthreads', '1', '--print-histogram', '--ignore-checkpoint', '--checkpoint-interval=-1', str(bodies)]
        tick = time.monotonic()
        with (x86 / 'stdout.txt').open('w') as out, (x86 / 'stderr.txt').open('w') as err:
            subprocess.run(command, env=dict(os.environ, OMP_NUM_THREADS='1', OMP_DYNAMIC='FALSE'),
                           stdout=out, stderr=err, check=True, timeout=43200)
        summary['wall_seconds']['x86-reference'] = time.monotonic() - tick
        (x86 / 'command.txt').write_text(shlex.join(command) + '\n')
        with (run / 'compare.txt').open('w') as out:
            subprocess.run([sys.executable, str(ROOT / 'scripts/compare.py'), str(x86),
                            str(slot / 'nbody_stderr.txt')], stdout=out, stderr=subprocess.STDOUT, check=True)
        summary['comparison'] = (run / 'compare.txt').read_text()
        summary['status'] = 'PASS'
    except BaseException as error:
        summary['error'] = str(error)
        # Ask the IPC owner to abort and let the real wrapper clean its lease.
        if child is not None and child.poll() is None:
            (slot / 'e2e-abort').touch()
            try:
                child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                summary['error'] += '; client did not exit: remote lease may remain; inspect slot/knc_remote'
        raise
    finally:
        summary['wall_seconds']['total'] = time.monotonic() - started
        for name in ('knc_wrapper.log', 'e2e-times.tsv'):
            if (slot / name).exists():
                shutil.copyfile(slot / name, run / name)
        if (run / 'compare.txt').exists():
            summary['comparison'] = (run / 'compare.txt').read_text()
        if (run / 'e2e-times.tsv').exists():
            summary['phase_wall_seconds'] = {
                label: float(seconds) for label, seconds in
                (line.split('\t') for line in (run / 'e2e-times.tsv').read_text().splitlines()[1:])}
        summary['wrapper_log'] = 'knc_wrapper.log'
        summary['cleanup_complete'] = len(summary['cleanup']) == 2
        (run / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('Report: ' + str(run / 'summary.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('small', 'medium', 'large'), default='medium')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--in-granted-turn', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.threads <= 240:
        parser.error('--threads must be in 1..240')
    args.ssh_options = transport_options()
    if args.dry_run:
        dry_plan(args.case, args.threads, args.ssh_options)
    else:
        live(args)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
