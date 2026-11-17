# S8-03 mixed-dwarf generator regression

`params.lua` is the workunit 117676 input copied from
`.work/S7-02/runs/real/inputs/EMD_v196_OCS_north_orbit_core_fitting_110k_bodies.lua`.
Only three assignments differ: total bodies 110000 -> 4000, light bodies
10000 -> 364 (preserving the approximate 1:10 light/dark ratio), and the
evolve time -> `32 * get_timestep() / (2.0 - best_like_start)` before computing
the backward orbit and applying the original best-likelihood extension. This
gives 32 forward steps and a correspondingly short backward orbit.
The physical timestep, model parameters, LMC settings, internal fixed RNG
seed, best-likelihood settings and histogram are unchanged.
The histogram is a byte-identical copy of `OCS_data_2025_north_194.hist`.

The real command-line seed and fourteen arguments remain:

```text
--seed 65477096 -np 14 -p 4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629
```

Run from Git Bash at the repository root:

```sh
bash scripts/build-parallel-quad.sh
bash scripts/test-parallel-quad.sh
```

Both scripts create `build/tmp` and export TMPDIR/TMP/TEMP before compiling.
The x86 script builds a pristine pinned generator and the patched generator
with identical test-only timing and body-capture hooks. Other source files
use the ordinary patched standalone 1.96 build. It runs pristine/12 and
patched/1,4,12 sequentially, writing `runs/s8-quad/`. Each `initial-bodies.bin`
contains 4000 rows of seven native little-endian binary64 values in body
order: corrected x, y, z, vx, vy, vz and mass, immediately before Lua body
creation. There are no structure padding bytes. Generation timing includes
model setup, sampling and center-of-mass corrections; it excludes dump I/O.
The timer starts after the test's worker-control-word check. Total is bash
wall time for the whole app, including capture I/O and evolution.

`python tests/test_parallel_quad.py` rechecks the existing artifacts with
`scripts/compare.py`, exact likelihood bits, exact histogram values and
byte-for-byte body data. `python tests/quad-kernel.py` compiles and tests the
actual extracted quadrature functions for interval edge cases, original
callback counts, parallel worker participation and serial fallback.
Before invoking the kernel compiler directly, create `build/tmp` and export
TMPDIR/TMP/TEMP to `$PWD/build/tmp`, with the Cygwin bin directory on PATH.

The card build excludes the S8-01 and S8-02 patches. It produces
`build/s8/card-quad/milkyway_nbody.mic` and the three compiler runtimes under
`dist/card/`. `bash scripts/quad-card-command.sh` prints the lead-only
240-thread benchmark command; it never accesses the card.
