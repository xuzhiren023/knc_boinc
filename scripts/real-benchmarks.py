"""One sequential 12-thread run per case/build; refuses to overwrite runs.

Use from Git Bash with the Cygwin runtime directory on PATH. Full 117676 is
deliberately release-only and may be run at most once for this ticket.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import compare
from s8_integration import ARGS

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs/real-benchmarks'
REFERENCES = ROOT / 'tests/references/real-benchmarks'
RELEASE = ROOT / 'build/real-benchmarks/x86-release-timers/milkyway_nbody.exe'
STOCK = ROOT.parent / 'S7-02/runs/real/inputs/milkyway_nbody_1.96_windows_x86_64__mt.exe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def idle_load():
    """Read Windows CPU accounting before starting a measured process."""
    def sample():
        values = [ctypes.c_ulonglong() for _ in range(3)]
        if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(v) for v in values)):
            raise ctypes.WinError()
        return [v.value for v in values]
    first = sample()
    time.sleep(2)
    last = sample()
    idle, kernel, user = [b - a for a, b in zip(first, last)]
    return 100 * (1 - idle / (kernel + user))


def arguments(case, threads=12):
    histcase = 'core-small' if case == '117676' else case
    return ['-f', str(ROOT / 'workunits' / case / 'params.lua'), '-h',
            str(ROOT / 'workunits' / histcase / 'OCS_data_2025_north_194.hist'),
            '--seed', '65477096', '--nthreads', str(threads), '--print-histogram',
            '--ignore-checkpoint', '--checkpoint-interval=-1', '-np', '14', '-p'] + ARGS


def run(case, variant):
    if case == '117676' and variant != 'release':
        raise ValueError('full task is release-only; no additional full x86 runs')
    label = case + '-' + variant
    out = RUNS / label
    dest = REFERENCES / label
    if out.exists() or dest.exists():
        raise FileExistsError('retained run/reference exists; refusing another run: ' + label)
    binary = RELEASE if variant == 'release' else STOCK
    binary = binary.resolve()
    baseline = idle_load() if os.name == 'nt' else None
    if baseline is not None and baseline > 15:
        raise RuntimeError('laptop busy before run: %.2f%% CPU; no simulation started' % baseline)
    out.mkdir(parents=True, exist_ok=False)
    cmd = [str(binary), '-z', str(out / 'histogram.txt')] + arguments(case)
    (out / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    env = dict(os.environ, OMP_NUM_THREADS='12', OMP_DYNAMIC='FALSE')
    for name in ('KNC_WRAPPER_FILES', 'S8_INITIAL_BODIES', 'S8_GENERATION_ONLY'):
        env.pop(name, None)
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    # Stock BOINC reopens stderr.txt itself; separate working directories are required.
    flags = {'creationflags': subprocess.NORMAL_PRIORITY_CLASS} if os.name == 'nt' else {}
    with (out / 'stdout.txt').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
        process = subprocess.Popen(cmd, cwd=out, env=env, stdout=stdout, stderr=stderr, **flags)
        (out / 'pid.txt').write_text(str(process.pid) + '\n')
        code = process.wait()
    elapsed = time.monotonic() - start
    text = compare.captured_output(out)
    phases = {name: dict(seconds=float(seconds), calls=int(calls)) for name, seconds, calls in
              re.findall(r'^PHASE (\S+) ([0-9.]+) (\d+)$', text, re.M)}
    info = dict(case=case, variant=variant, threads=12, priority='normal',
                started_utc=started, wall_seconds=elapsed, returncode=code,
                binary=str(binary), binary_sha256=sha(binary), command=cmd,
                pre_run_cpu_percent=baseline,
                inputs={str(Path(cmd[cmd.index(opt) + 1]).relative_to(ROOT)): sha(Path(cmd[cmd.index(opt) + 1]))
                        for opt in ('-f', '-h')}, phases=phases,
                protocol='Sequential; no other benchmark jobs launched by this harness. Laptop otherwise idle requested; external load not certified.')
    if variant == 'release':
        info['release_env_sha256'] = sha(ROOT / 'config/release.env')
        info['build_options'] = binary.with_name('.build-options').read_text()
    (out / 'measurement.json').write_text(json.dumps(info, indent=2) + '\n')
    if code:
        raise RuntimeError(label + ' failed: ' + str(code))
    compare.load_run(out)  # Require finite likelihood and complete histogram.
    if case == 'real-steps' and variant == 'release':
        assert 100 <= phases['steps']['calls'] <= 150
    dest.mkdir(parents=True, exist_ok=False)
    for name in ('stdout.txt', 'stderr.txt', 'histogram.txt', 'measurement.json'):
        if (out / name).exists():
            shutil.copyfile(out / name, dest / name)
    if variant == 'stock':
        assert compare.load_run(REFERENCES / (case + '-release')) == compare.load_run(dest)
    print('PASS %s %.6f s; phases=%s' % (label, elapsed, json.dumps(phases)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=('core-small', 'real-steps', '117676'))
    parser.add_argument('variant', choices=('release', 'stock'))
    args = parser.parse_args()
    run(args.case, args.variant)
