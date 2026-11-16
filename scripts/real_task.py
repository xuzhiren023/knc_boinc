#!/usr/bin/env python3
"""S7-02 read-only BOINC capture and isolated, bounded standalone runs.

Never executes shell text or launches the BOINC client. Generated evidence is
under runs/real (gitignored); original command_line XML text is preserved too.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import struct
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / 'runs/real'
STOCK = 'milkyway_nbody_1.96_windows_x86_64__mt.exe'


def copy_input(source, destination):
    if destination.exists():
        if source.read_bytes() != destination.read_bytes():
            raise ValueError('refusing to overwrite a different captured input: ' + str(destination))
    else:
        shutil.copyfile(source, destination)


def capture(data):
    project = data / 'projects/milkyway.cs.rpi.edu_milkyway'
    state = ET.parse(data / 'client_state.xml').getroot()
    tasks = []
    inputs = REAL / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    for wu in state.findall('workunit'):
        if wu.findtext('app_name') != 'milkyway_nbody':
            continue
        command = wu.findtext('command_line')
        argv = shlex.split(command)
        refs = {ref.findtext('open_name'): ref.findtext('file_name')
                for ref in wu.findall('file_ref')}
        for filename in refs.values():
            assert Path(filename).name == filename
            copy_input(project / filename, inputs / filename)
        lua = (inputs / refs['nbody_parameters.lua']).read_text()
        bodies = int(re.search(r'(?m)^totalBodies\s*=\s*(\d+)', lua)[1])
        # All three captured Lua files round arg[1] to nine decimal places,
        # then extend forward time by (2-best_like_start) for best likelihood.
        assert re.search(r'evolveTime\s*=\s*round\(\s*tonumber\(arg\[1\]\)', lua)
        base = math.floor(float(argv[argv.index('-p') + 1]) * 1e9 + .5) / 1e9
        best = re.search(r'(?m)^use_best_likelihood\s*=\s*(true|false)', lua)[1] == 'true'
        start = float(re.search(r'(?m)^best_like_start\s*=\s*([.\d]+)', lua)[1])
        effective = base * (2 - start) if best else base
        tasks.append(dict(name=wu.findtext('name'), command_line=command,
                          argv=argv, inputs=refs, bodies=bodies,
                          parameter_evolve_gyr=base, effective_evolve_gyr=effective,
                          estimated_card_seconds=61 * bodies / 20000 * effective / .05))
    assert len(tasks) == 4
    copy_input(project / STOCK, inputs / STOCK)
    versions = [v for v in state.findall('app_version')
                if v.findtext('app_name') == 'milkyway_nbody' and v.findtext('version_num') == '196']
    assert len(versions) == 1 and versions[0].findtext('plan_class') == 'mt'
    version = {key: versions[0].findtext(key) for key in
               ('app_name', 'version_num', 'platform', 'plan_class', 'avg_ncpus', 'cmdline')}
    names = {t['name'] for t in tasks}
    results = [dict(name=r.findtext('name'), workunit=r.findtext('wu_name'),
                    identity={key: r.findtext(key) for key in ('version_num', 'platform', 'plan_class')},
                    output_files=[ref.findtext('file_name') for ref in r.findall('file_ref')])
               for r in state.findall('result') if r.findtext('wu_name') in names]
    assert len(results) == 4 and all(not r['output_files'] for r in results)
    manifest = dict(tasks=tasks, app_version=version, results=results,
                    sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in inputs.iterdir() if p.is_file()})
    (REAL / 'tasks.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(tasks, indent=2))


def task():
    return next(t for t in json.loads((REAL / 'tasks.json').read_text())['tasks']
                if t['name'].endswith('_117676'))


def contract(package):
    manifest = json.loads((REAL / 'tasks.json').read_text())
    root = ET.parse(package / 'app_info.xml').getroot()
    assert root.findtext('app/name') == 'milkyway_nbody'
    assert len(root.findall('app_version')) == 1
    version = root.find('app_version')
    assert version.findtext('app_name') == 'milkyway_nbody'
    # BOINC client_state.cpp lookup_app_version() compares exactly these fields
    # in addition to app identity; cs_statefile.cpp uses it for existing results.
    for result in manifest['results']:
        for key, value in result['identity'].items():
            assert version.findtext(key) == value, (result['name'], key, value)
        assert not result['output_files']
    print('PASS package identity matches all four existing milkyway_nbody results: 196/windows_x86_64/mt; BOINC stderr only')


def run(executable, threads, label):
    if Path(label).name != label or label in ('.', '..') or threads < 1:
        raise ValueError('label must be a basename and threads must be positive')
    t = task()
    scratch = REAL / label
    scratch.mkdir(parents=True, exist_ok=False)
    for logical, physical in t['inputs'].items():
        shutil.copyfile(REAL / 'inputs' / physical, scratch / logical)
    # Must precede the positional Lua parameters: upstream POSIXMEHARDER stops
    # option parsing at the first of those numbers. Original argv is unchanged.
    argv = [str(executable.resolve()), '--nthreads', str(threads)] + t['argv']
    (scratch / 'argv.json').write_text(json.dumps(argv, indent=2) + '\n')
    env = os.environ.copy()
    env.pop('KNC_WRAPPER_FILES', None)
    env['OMP_DYNAMIC'] = 'FALSE'
    env['OMP_NUM_THREADS'] = str(threads)
    start = time.monotonic()
    with (scratch / 'stdout.txt').open('wb') as stdout, (scratch / 'stderr.txt').open('wb') as stderr:
        process = subprocess.Popen(argv, cwd=str(scratch), env=env, stdout=stdout, stderr=stderr)
        (scratch / 'pid').write_text(str(process.pid))
        try:
            code = process.wait(timeout=7200)
            timeout = False
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code, timeout = process.returncode, True
    result = dict(returncode=code, timed_out=timeout, seconds=time.monotonic()-start)
    (scratch / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(label, json.dumps(result), flush=True)
    return 124 if timeout else code


def rates():
    """A conservative step rate from the last saved checkpoint, without IPC.

    The common 1.96 checkpoint prefix contains uint32 major/minor/nbody/step
    at byte 128. Reading it does not depend on platform-specific NBodyCtx ABI.
    Periodic checkpoints can lag the app; this is a lower bound, not an ETA.
    """
    for scratch in sorted(REAL.iterdir()):
        if not (scratch / 'pid').is_file():
            continue
        status = scratch / 'status.json'
        elapsed = (json.loads(status.read_text())['seconds'] if status.exists()
                   else time.time() - (scratch / 'pid').stat().st_mtime)
        record = dict(run=scratch.name, elapsed_seconds=elapsed)
        cp = scratch / 'nbody_checkpoint'
        if cp.exists():
            with cp.open('rb') as f:
                header = f.read(144)
            assert header.startswith(b'mwnbody')
            major, minor, bodies, step = struct.unpack_from('<IIII', header, 128)
            assert (major, minor, bodies) == (1, 96, task()['bodies'])
            record.update(last_checkpoint_step=step,
                          saved_steps_per_wall_second_lower_bound=step/elapsed)
        else:
            record['rate'] = 'no checkpoint yet; evolution step rate unavailable'
        print(json.dumps(record))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    cap = sub.add_parser('capture')
    cap.add_argument('--data', type=Path, default=Path('C:/ProgramData/BOINC'))
    runner = sub.add_parser('run')
    runner.add_argument('executable', type=Path)
    runner.add_argument('threads', type=int)
    runner.add_argument('label')
    sub.add_parser('rates')
    binding = sub.add_parser('contract')
    binding.add_argument('package', type=Path)
    args = parser.parse_args()
    if args.action == 'capture':
        capture(args.data)
        return 0
    if args.action == 'rates':
        rates()
        return 0
    if args.action == 'contract':
        contract(args.package)
        return 0
    return run(args.executable, args.threads, args.label)


if __name__ == '__main__':
    raise SystemExit(main())
