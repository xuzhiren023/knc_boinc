"""S7-01: six 1.96 references, scalar/chunk4/vector identity, first-force bytes.

Run from the repository root with the supplied Cygwin tools on PATH and local
TMPDIR/TMP/TEMP. --record replaces the checked-in reference after verification.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from force_chunk_matrix import run, science
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


def sha(data):
    return hashlib.sha256(data).hexdigest()


def saved(path):
    return b''.join(line for line in (path / 'histogram.txt').read_bytes().splitlines(keepends=True)
                    if not line.startswith(b'# Generated '))


def main():
    os.chdir(ROOT)
    (ROOT / 'build/tmp').mkdir(parents=True, exist_ok=True)
    # Instrument a copy, leaving the pinned patch state intact. Capture XYZ
    # only: the unused fourth mwvector lane is not a science value.
    source = (ROOT / 'third_party/milkywayathome_client_196/nbody/src/nbody_grav.c').read_text()
    needle = '    return nbIncestStatusCheck(ctx, st);'
    assert source.count(needle) == 1
    source = source.replace(needle, '''    if (getenv("KNC_ACCEL_CAPTURE")) {
        FILE* f = fopen(getenv("KNC_ACCEL_CAPTURE"), "wb");
        unsigned i;
        if (!f || st->nbody < 4096 || st->treeIncest) exit(2);
        for (i = 0; i < 4096; ++i) {
            real xyz[3] = {st->acctab[i].x, st->acctab[i].y, st->acctab[i].z};
            if (fwrite(xyz, sizeof(real), 3, f) != 3) exit(2);
        }
        if (fclose(f)) exit(2);
        exit(0);
    }
''' + needle)
    (ROOT / 'build/s7-capture.c').write_bytes(source.encode())
    variants = [('default', 'build/x86', 0, None),
                ('chunk4', 'build/s7/x86-chunk4', 0, 4),
                ('vector4', 'build/s7/x86-vector4', 1, 4)]
    evidence = {'tag': 'nbody_1.96', 'commit': '1e640779f1cabf88aaa49e4db569cfe7e09016c4',
                'seed': 670828913, 'references': {}, 'inputs': {}, 'accelerations': {}}
    for case in ('small', 'medium', 'large'):
        for name in ('params.lua', 'input.hist'):
            p = Path('workunits') / case / name
            evidence['inputs'][p.as_posix()] = sha(p.read_bytes())
    refs = {}
    acceleration = None
    for variant, out, vector, chunk in variants:
        options = ['TARGET=x86', 'OUT=../' + out, 'VECTOR_GRAVITY=' + str(vector)]
        if chunk is not None:
            options.append('FORCE_CHUNK=' + str(chunk))
        with open('build/s7-' + variant + '-build.log', 'w') as log:
            subprocess.run(['make', '-C', 'mk', '-j6'] + options + ['program'],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
            subprocess.run(['make', '-C', 'mk', '-f', '../tests/nbody-196.mk'] + options + ['capture'],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        for case in ('small', 'medium', 'large'):
            for threads in (1, 12):
                key = case + '-' + str(threads)
                _, path = run((case, '196-' + variant, threads, out + '/milkyway_nbody.exe'))
                if variant == 'default':
                    refs[key] = path
                    evidence['references'][key] = {
                        'likelihood': science(path)[0],
                        'science_sha256': sha(json.dumps(science(path)).encode()),
                        'saved_histogram_sha256_without_generated_timestamp': sha(saved(path))}
                reference = refs[case + '-1']
                assert compare.compare(reference, path, compare.TOLERANCE) == 0
                assert science(reference) == science(path), 'scientific tokens: ' + str(path)
                assert saved(reference) == saved(path), 'saved histogram: ' + str(path)
                print('PASS %s %s: bit-identical likelihood, printed/saved histograms' % (variant, key), flush=True)
        # Same large input, seed and first force step, independent of final likelihood.
        for threads in (1, 12):
            target = ROOT / out / ('accel-%d.bin' % threads)
            target.unlink(missing_ok=True)
            command = [str(ROOT/out/'capture.exe'), '-f', 'workunits/large/params.lua',
                       '-h', 'workunits/large/input.hist', '--seed', '670828913',
                       '--nthreads', str(threads), '--ignore-checkpoint', '20000']
            with open('build/s7-%s-accel-%d.log' % (variant, threads), 'w') as log:
                subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, OMP_DYNAMIC='FALSE', OMP_NUM_THREADS=str(threads),
                                        KNC_ACCEL_CAPTURE=str(target)))
            data = target.read_bytes()
            assert len(data) == 4096 * 24
            if acceleration is None:
                acceleration = data
            assert data == acceleration, 'first-force acceleration bytes: ' + str(target)
            evidence['accelerations'][variant + '-' + str(threads)] = sha(data)
            print('PASS %s-%d: 4096 XYZ accelerations byte-identical (%d bytes)' %
                  (variant, threads, len(data)), flush=True)
    baseline = ROOT / 'tests/references/nbody-1.96.json'
    if sys.argv[1:] == ['--record']:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes((json.dumps(evidence, indent=2) + '\n').encode())
    else:
        assert not sys.argv[1:], 'usage: nbody_196_matrix.py [--record]'
        assert evidence == json.loads(baseline.read_text()), '1.96 reference changed'
    print('PASS 18 full runs, six first-force captures, 1/12 threads and scalar/default/chunk4/vector4 identity', flush=True)


if __name__ == '__main__':
    main()
