"""Measure real x86 serialization cost at the wrapper's default five seconds."""
import os
import pathlib
import re
import subprocess
import time
root = pathlib.Path(__file__).resolve().parents[1]
out = root / 'build/snapshot-cost'
out.mkdir(parents=True, exist_ok=True)
# Same medium model, enough runtime for several five-second publications.
(out/'params.lua').write_text((root/'workunits/medium/params.lua').read_text().replace('timeEvolve = 3.945', 'timeEvolve = 0.25').replace('tstop     = 4.0', 'tstop     = 0.25'))
exe = pathlib.Path(os.environ.get('KNC_COST_APP', root/'build/x86/milkyway_nbody.exe'))
start = time.monotonic()
with (out/'stdout.txt').open('w') as stdout, (out/'stderr.txt').open('w') as stderr:
    subprocess.run([str(exe), '-f', str(out/'params.lua'), '-h', str(root/'workunits/medium/input.hist'),
                    '-z', str(out/'histogram.txt'), '--seed', '670828913', '--nthreads', '1',
                    '--ignore-checkpoint', '--checkpoint-interval=-1', '--snapshot-interval', '5', '1024'],
                   cwd=out, env=dict(os.environ, OMP_NUM_THREADS='1'), stdout=stdout, stderr=stderr, check=True)
elapsed = time.monotonic()-start
m = re.search(r'KNC snapshot writes=(\d+) cost_seconds=([\d.]+)', (out/'stderr.txt').read_text())
assert m, 'missing snapshot cost measurement'
writes, cost = int(m[1]), float(m[2])
assert writes >= 3, (writes, elapsed)
assert cost/elapsed < .01, (cost, elapsed)
assert (out/'snapshot').stat().st_size == 320048
result = f'PASS snapshot cost: {writes} writes, {cost:.6f}s / {elapsed:.3f}s = {100*cost/elapsed:.5f}% at 5s interval'
(out/'measurement.txt').write_text(result+'\n')
print(result)
