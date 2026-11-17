#!/usr/bin/env python3
"""Offline S9 staging, profile placement, and sequential host correctness proof."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import struct
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(str(ROOT))
S9 = ROOT / 'build/s9'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='\n') as f:
        f.write(text)


def science(case, threads):
    args = ['-f', 'params.lua', '-h', 'input.hist', '--print-histogram',
            '--nthreads', str(threads), '--ignore-checkpoint', '--checkpoint-interval=-1']
    if case == 'core-small':
        return args + ['--seed', '65477096', '-np', '14', '-p', '4.90652', '1',
                       '0.386382', '0.20556', '1.74668', '0.0420765', '46.125',
                       '15.623', '-215.279', '114.242', '181.825', '353270', '1.21041', '2.87629']
    return args + ['--seed', '670828913', str({'small': 64, 'medium': 1024, 'large': 20000}[case])]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_strip():
    # GCC records OUT relative to mk as /cygdrive/<drive>/<root>/mk/../build/s9/variant.
    return len(ROOT.as_posix()[3:].split('/')) + 2 + 4


def source_hashes():
    paths = [ROOT / 'mk/Makefile', ROOT / 'mk/sources.mk']
    for folder in ('third_party/milkywayathome_client_196', 'config', 'src'):
        paths += [p for p in (ROOT / folder).rglob('*') if p.suffix in ('.c', '.cc', '.h')]
    return {str(p.relative_to(ROOT)).replace(chr(92), '/'): digest(p) for p in sorted(paths)}


def stage():
    manifest = {v: digest(S9 / v / 'milkyway_nbody.mic') for v in ('card-base', 'card-pgo-train')}
    manifest['sources'] = source_hashes()
    manifest['train_options'] = (S9 / 'card-pgo-train/.training-options').read_text()
    write(S9 / 'manifest.json', json.dumps(manifest, indent=2) + '\n')
    prologue = '#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")/../.."\nmkdir -p build/s9/card-results\n'
    def job(variant, case, label, reason, env, threads=240, training=False):
        prefix = 'build/s9/card-results/' + label
        args = ['python', 'tools/card_run',
                '--benchmark', '--threads', '240', '--timeout', '900', '--receipt', prefix + '.json',
                '--file', 'build/s9/' + variant + '/milkyway_nbody.mic',
                '--file', 'workunits/' + case + '/params.lua', '--file', 'workunits/' + case + '/input.hist']
        for lib in ('libstdc++.so.6', 'libgcc_s.so.1', 'libgomp.so.1'):
            args += ['--file', 'build/s9/runtimes/' + lib]
        if training:
            args += ['--file', 'build/s9/pgo-path.env', '--collect', 'claude-profiles.tar.gz', '--collect-dir', prefix,
                     'scripts/pgo-card-train.sh']
        else:
            args += ['scripts/card-launch-env.sh', 'OMP_NUM_THREADS=' + str(threads)] + env + ['./milkyway_nbody.mic']
        args += science(case, threads)
        return '# Reason: ' + reason + '\n' + ' '.join(shlex.quote(a) for a in args) + ' > ' + prefix + '.txt 2>&1\n'
    setup = 'export GCOV_PREFIX_STRIP=' + str(prefix_strip()) + chr(10)
    parents = {p.relative_to(S9 / 'card-pgo-train').parent.as_posix()
               for p in (S9 / 'card-pgo-train').rglob('*.o')}
    for parent in sorted(parents):
        setup += 'mkdir -p "$GCOV_PREFIX/card-pgo-train/' + parent + '"' + chr(10)
    write(S9 / 'pgo-path.env', setup)
    training = prologue
    for case in ('core-small', 'large'):
        training += job('card-pgo-train', case, 'train-' + case,
                        'Train ' + case + ' once at 240 threads; return normal-exit counters.', [], training=True)
    write(S9 / 'pgo-train.sh', training)
    # Reserve all 240 contexts for a clean benchmark while varying the application team.
    settings = [
        (240, 'close', 'threads', True, 'Keep all contexts busy; avoid sleep/wakeup overhead.'),
        (240, 'spread', 'threads', True, 'Spread workers across the reserved contexts.'),
        (180, 'spread', 'cores', True, 'Three contexts per core may reduce contention.'),
        (120, 'spread', 'cores', True, 'Two contexts per core may improve cache availability.'),
        (240, 'close', 'cores', True, 'Compare core places with individual thread places.'),
        (180, 'close', 'threads', True, 'Test compact placement with three contexts per core worth of workers.'),
        (120, 'close', 'threads', True, 'Test compact placement with fewer active workers.'),
        (240, 'spread', 'cores', False, 'Control for active waiting using the runtime default wait policy.')]
    jobs = prologue
    for i, (threads, bind, places, active, reason) in enumerate(settings, 1):
        env = ['OMP_PROC_BIND=' + bind, 'OMP_PLACES=' + places]
        if active:
            env += ['OMP_WAIT_POLICY=active', 'GOMP_SPINCOUNT=infinite']
        jobs += job('card-base', 'large', 'threads-' + str(i), reason, env, threads)
    write(S9 / 'card-threads.sh', jobs)


def remove_directory(path):
    resolved = path.resolve()
    relative = resolved.relative_to(S9.resolve())
    if not relative.parts:
        raise ValueError('refusing to remove the S9 artifact root')
    if resolved.exists():
        shutil.rmtree(str(resolved))


def copy_profiles(source, dest):
    profiles = list(source.rglob('*.gcda'))
    if not profiles:
        raise ValueError('no profiles in ' + str(source))
    # Clear old counters so absent training units cannot silently use stale data.
    for old in dest.rglob('*.gcda'):
        old.unlink()
    for path in profiles:
        target = dest / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(target))
    print('Placed {} profiles in {}'.format(len(profiles), dest))


def import_card():
    manifest = json.loads((S9 / 'manifest.json').read_text())
    if source_hashes() != manifest['sources']:
        raise ValueError('sources changed after training build; rebuild and retrain')
    if digest(S9 / 'card-pgo-train/milkyway_nbody.mic') != manifest['card-pgo-train']:
        raise ValueError('training binary changed after staging')
    if (S9 / 'card-pgo-train/.training-options').read_text() != manifest['train_options']:
        raise ValueError('training configuration changed after staging')
    for case in ('core-small', 'large'):
        receipt = json.loads((S9 / ('card-results/train-' + case + '.json')).read_text())
        if (receipt.get('result_class'), receipt.get('exit_code'), receipt.get('program_exit_code')) != ('program', 0, 0):
            raise ValueError('unsuccessful card receipt: ' + case)
        capture = S9 / ('card-results/train-' + case + '.txt')
        output = capture.read_text()
        if 'libgcov profiling error' in output or 'profiling:' in output:
            raise ValueError('card profile write error: ' + case)
        compare.likelihood(output, capture)
        source = S9 / ('card-results/train-' + case + '/claude-profiles.tar.gz')
        dest = S9 / 'profiles' / case
        count = unpack_profiles(source, dest, 'card-pgo-train')
        print('{}: imported {} profiles'.format(case, count))


def unpack_profiles(source, dest, variant):
    remove_directory(dest)
    dest.mkdir(parents=True)
    count = 0
    with tarfile.open(str(source), 'r:gz') as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith('.gcda'):
                continue
            parts = PurePosixPath(member.name).parts
            if '..' in parts or variant not in parts:
                raise ValueError('unexpected profile path: ' + member.name)
            relative = Path(*parts[parts.index(variant) + 1:])
            if relative.is_absolute() or not str(relative).endswith('.gcda'):
                raise ValueError('invalid profile path')
            target = dest / relative
            if not (S9 / variant / relative.with_suffix('.o')).is_file():
                raise ValueError('unknown profile unit: ' + str(relative))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            count += 1
    if not count:
        raise ValueError('empty profile archive')
    return count



def run_x86(variant, case, label):
    out = S9 / 'x86-runs' / label / case
    out.mkdir(parents=True, exist_ok=True)
    args = science(case, 12)
    args[1] = str(ROOT / 'workunits' / case / 'params.lua')
    args[3] = str(ROOT / 'workunits' / case / 'input.hist')
    env = dict(os.environ, OMP_NUM_THREADS='12', OMP_DYNAMIC='FALSE')
    # Exercise the same relocated archive/placement path as the card workflow.
    env.pop('GCOV_PREFIX', None)
    env.pop('GCOV_PREFIX_STRIP', None)
    if label == 'train':
        prefix = (out / 'gcda').as_posix()
        env['GCOV_PREFIX'] = '/cygdrive/' + prefix[0].lower() + prefix[2:]
        env['GCOV_PREFIX_STRIP'] = str(prefix_strip())
        for obj in (S9 / variant).rglob('*.o'):
            (out / 'gcda' / variant / obj.relative_to(S9 / variant).parent).mkdir(parents=True, exist_ok=True)
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        subprocess.run([str(S9 / variant / 'milkyway_nbody.exe')] + args,
                       cwd=str(out), env=env, stdout=stdout, stderr=stderr, check=True)
    output = compare.captured_output(out)
    if 'libgcov profiling error' in output or 'profiling:' in output:
        raise ValueError('host profile write error')
    compare.likelihood(output, out)
    return out


def proof_x86(reuse_base=False, reuse_pgo=False):
    proof = {}
    for case in ('small', 'medium', 'large'):
        a = S9 / 'x86-runs/base' / case if reuse_base else run_x86('x86-base', case, 'base')
        b = S9 / 'x86-runs/pgo' / case if reuse_pgo else run_x86('x86-pgo', case, 'pgo')
        cmd = [sys.executable, 'scripts/compare.py', str(a), str(b)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        av, bv = [compare.likelihood(compare.captured_output(p), p) for p in (a, b)]
        ab, bb = [struct.pack('>d', v).hex() for v in (av, bv)]
        if ab != bb:
            raise ValueError(case + ': likelihood bits differ')
        if case == 'small':
            train = S9 / 'x86-runs/train/small'
            training_bits = struct.pack('>d', compare.likelihood(compare.captured_output(train), train)).hex()
            if training_bits != ab:
                raise ValueError('instrumented small likelihood bits differ')
        proof[case] = dict(threads=12, baseline_bits=ab, pgo_bits=bb, compare=result,
                           baseline_sha256=digest(S9 / 'x86-base/milkyway_nbody.exe'),
                           pgo_sha256=digest(S9 / 'x86-pgo/milkyway_nbody.exe'))
        print(case + ': ' + result + 'exact likelihood bits: ' + ab, flush=True)
    write(S9 / 'x86-proof.json', json.dumps(proof, indent=2) + '\n')


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'stage':
        stage()
    elif action == 'import-card':
        import_card()
    elif action == 'clean-merged':
        remove_directory(S9 / 'profiles/merged')
    elif action == 'place-card':
        copy_profiles(S9 / 'profiles/merged', S9 / 'card-pgo-train')
    elif action == 'train-x86':
        for old in (S9 / 'x86-pgo-train').rglob('*.gcda'):
            old.unlink()
        training = S9 / 'x86-runs/train/small'
        remove_directory(training / 'gcda')
        run_x86('x86-pgo-train', 'small', 'train')
        with tarfile.open(str(training / 'claude-profiles.tar.gz'), 'w:gz') as archive:
            archive.add(str(training / 'gcda'), arcname='gcda')
        unpack_profiles(training / 'claude-profiles.tar.gz', S9 / 'profiles/x86', 'x86-pgo-train')
    elif action == 'place-x86':
        copy_profiles(S9 / 'profiles/x86', S9 / 'x86-pgo-train')
    elif action == 'proof-x86':
        proof_x86('--reuse-base' in sys.argv[2:], '--reuse-pgo' in sys.argv[2:])
    else:
        raise ValueError('unknown action ' + action)
