"""S8 acceptance: real large runs, phase contract, exact reference outputs."""
import math
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare
from check_vector_card import scientific_tokens
sys.path.insert(0, str(ROOT / 'tests'))
from nbody_196_matrix import saved

def main():
    os.chdir(ROOT)
    variants = [('x86-timers', 12), ('x86-timers', 1)]
    if '--static' in sys.argv:
        variants = [('x86-timers-static', 12)]
    reference = ROOT.parent / 'S7-01/runs/force-chunk/large-chunk196-default-t12'
    for variant, threads in variants:
        exe = ROOT / 'build/s8' / variant / 'milkyway_nbody.exe'
        assert exe.is_file(), 'missing S8 build: ' + str(exe)
        out = ROOT / 'runs/s8' / ('%s-t%d' % (variant, threads))
        out.mkdir(parents=True, exist_ok=True)
        cmd = [str(exe), '-f', 'workunits/large/params.lua', '-h', 'workunits/large/input.hist',
               '-z', str(out / 'histogram.txt'), '-c', str(out / 'checkpoint'),
               '--seed', '670828913', '--nthreads', str(threads), '--print-histogram',
               '--ignore-checkpoint', '--checkpoint-interval=-1', '20000']
        (out / 'command.txt').write_text(repr(cmd) + '\n')
        with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
            subprocess.run(cmd, stdout=stdout, stderr=stderr, check=True,
                           env=dict(os.environ, OMP_DYNAMIC='FALSE', OMP_NUM_THREADS=str(threads)))
        text = (out / 'stderr.txt').read_text()
        phases = re.findall(r'^PHASE (\w+) ([0-9.]+) (\d+)$', text, re.M)
        names = ['nbMakeTree', 'nbMapForceBody', 'advancePosVel', 'advanceVelocities',
                 'get_likelihood', 'final_histogram_likelihood', 'setup', 'steps', 'whole_run']
        assert [p[0] for p in phases] == names, phases
        assert all(math.isfinite(float(s)) and float(s) >= 0 for _, s, _ in phases)
        calls = {n: int(c) for n, _, c in phases}
        assert calls['steps'] > 0
        assert calls['nbMakeTree'] == calls['nbMapForceBody'] == calls['steps'] + 1
        assert calls['advancePosVel'] == calls['advanceVelocities'] == calls['steps']
        assert calls['get_likelihood'] <= calls['steps']
        assert calls['setup'] == calls['whole_run'] == calls['final_histogram_likelihood'] == 1
        assert 'PHASE' not in (out / 'stdout.txt').read_text()
        # mw_printf emits the result contract to stderr in this standalone build.
        assert text.rfind('</search_likelihood') < text.index('PHASE')
        print('%s threads=%d' % (variant, threads), flush=True)
        for phase in phases:
            print('PHASE ' + ' '.join(phase), flush=True)
        assert compare.compare(reference, out, compare.TOLERANCE) == 0
        assert scientific_tokens(reference) == scientific_tokens(out)
        assert saved(reference) == saved(out)
        print('PASS bit-identical likelihood, printed/saved histograms', flush=True)

if __name__ == '__main__':
    main()
