# N-body benchmark set

Speed work uses real-workunit models. `large` spends about 75% of force time
in the synthetic Freeman-disk potential (Bessel functions), unlike the captured
workunits' Miyamoto-Nagai disk, Hernquist sphere and NFW-mass halo. Keep
`large`, `small` and `medium` as correctness cases only.

| Case | Measures | Input Lua; histogram | Bodies; forward steps | Current card time |
| --- | --- | --- | --- | --- |
| core-small | Mixed-dwarf generation, including setup; only a short evolution | `workunits/core-small/params.lua`; `OCS_data_2025_north_194.hist` in the same directory | 4,000 (364 light); 32 | 47.95 s |
| real-steps | Real potential and mixed-dwarf step phase; report setup separately | `workunits/real-steps/params.lua`; `OCS_data_2025_north_194.hist` in the same directory | 20,000 (1,818 light); 128 | To measure with the staged window |
| full 117676 | Headline total time, occasional runs only | `workunits/117676/params.lua`; `workunits/core-small/OCS_data_2025_north_194.hist` | 110,000 (10,000 light); 1,568 | 1,673 s |
| large | Correctness only: shortened upstream model_1, Freeman disk | `workunits/large/params.lua`; `input.hist` in the same directory | 20,000; 110 | Historical only; excluded from speed scoring |
| small | Correctness only: upstream model_1 | `workunits/small/params.lua`; `input.hist` in the same directory | 64; original evolution | Not measured by this ticket |
| medium | Correctness only: upstream model_1 | `workunits/medium/params.lua`; `input.hist` in the same directory | 1,024; original evolution | Not measured by this ticket |

Card totals above are the owner's current measurements supplied in S10-06,
not runs made by this engineer. Full 117676 is approximately 79% setup
(1,319 s); its 1,568 steps cost approximately 0.19 s force and 0.026 s tree
each. These rounded phase figures need not sum exactly to 1,673 s.
They do not establish the new real-steps timing.

All three real-model cases use the same seed and fourteen parameters:

```text
--seed 65477096 --nthreads 12 --print-histogram --ignore-checkpoint --checkpoint-interval=-1 -np 14 -p 4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629
```

Each command also supplies `-f LUA -h HISTOGRAM -z OUTPUT_HISTOGRAM` before
the positional parameters. Real Lua fixes its internal PRNG seed to 34086709.
For small/medium/large, use the corresponding Lua and histogram with
`--seed 670828913 --nthreads 12 --print-histogram --ignore-checkpoint
--checkpoint-interval=-1` followed by `64`, `1024` or `20000`, respectively.

## X86 references and measurement protocol

The selected best-build configuration is `config/release.env`: `-O2`, tree 4,
DF reuse, parallel quadrature, static integration and force chunk 4; scalar
gravity and no walk layout, PGO or experimental fast path. This ticket adds
only `PHASE_TIMERS=1` to obtain the phase split. It builds with the supplied
Cygwin GCC through `mk/Makefile`, without changing science or release options.
The stock executable is the captured 1.96 mt application at
`.work/S7-02/runs/real/inputs/milkyway_nbody_1.96_windows_x86_64__mt.exe`.

Run each requested reference once, sequentially, at 12 threads and normal
priority, with `OMP_DYNAMIC=FALSE`, on an otherwise idle laptop. No sweeps,
no concurrent compilations or simulations, and at most one full 117676 x86
run. A two-second Windows CPU accounting sample above 15% prevents a new run;
the sample and priority are recorded with each result. This is a preflight
check, not proof that unrelated processes stayed idle throughout a run.
The stock BOINC application opens its own `stderr.txt`; each run therefore
has a distinct working directory. Checkpoints are disabled and ignored.

The runner retains raw outputs, input/executable hashes, exact argv, UTC start,
wall time and all `PHASE` records under `tests/references/real-benchmarks/`.
`measurement.json` identifies the binary and inputs of each run. The identical
finite likelihood and histogram values are checked between release and stock
for core-small and real-steps; generated timestamps are not science data.

<!-- MEASUREMENTS -->
| Case | Release, 12 threads | Stock 1.96, 12 threads | Status |
| --- | --- | --- | --- |
| core-small | Pending | Pending | No new reference run started |
| real-steps | Pending | Pending | No reference run started |
| full 117676 | Pending total and phases | Historical 5,858.735 s only | The one allowed current full run is unstarted |

S10-06 measurement blocker, 2026-11-17: the first preflight found 97.53% CPU
busy. Twenty-one further samples over ten minutes ranged from 65.43% to
100%; none met the idle gate. Read-only process inspection found the S10-05
full-special `capture.exe` and a BOINC stock application, among other jobs.
No benchmark process was started, no reference output was fabricated, and no
other job was interrupted. The acceptance reference check remains failing.
Run the staged x86 harness after an idle window is available; until then this
ticket does not provide today's full 117676 x86 time or new real-model outputs.
<!-- /MEASUREMENTS -->

Historical correctness references (not new speed results): S10-01 release
12-thread wall times were small 159.563 s, medium 329.968 s and large 32.359 s
in `.work/S10-01/runs/s10/{small,medium,large}-t12/`. S8-09's stock 1.96
12-thread large run was 23.078 s in
`.work/S8-09/runs/s8-09/final/bench-stock-196-large/`. Stock small/medium
times were not recorded. Their scientific references are
`tests/references/nbody-1.96.json`; all three S10-01 results match those
likelihoods exactly. These historical timings are not a contemporaneous idle
comparison and must not be used to claim a speedup. Historical full 117676
stock time was 5,858.735 s (`.work/S7-02/runs/real/stock-12/status.json`);
that run predates the current release and has no phase timers.
Historical core-small release time was 72.265 s
(`.work/S10-01/runs/s10/core-small-t12/`); stock was 149.344 s
(`.work/S8-09/runs/s8-09/final/bench-stock-196-core-small/`). Historical
large card `PHASE whole_run` was 30.610028089 s
(`.work/S8-09/runs/card/s8-09/batch-3-large-240.txt`). These are provenance
for archived references, not additional runs or current idle comparisons.

## Rerun and card handoff

```bash
# Existing local pinned upstream sources and supplied toolchain are required.
# On an idle laptop; creates local tmp and exports TMPDIR, TMP and TEMP first:
bash scripts/run-real-benchmarks.sh
# Offline acceptance only; never reruns science:
python tests/test_real_benchmarks.py
bash -n scripts/run-real-benchmarks.sh scripts/real-benchmark-window.sh
# Lead only, during an authorized card window:
bash scripts/real-benchmark-window.sh
```

The x86 runner refuses to overwrite any existing run directory, even after an
interruption. Preserve those records; do not delete and rerun full 117676 to
improve a number. The card window stages two sequential 240-thread jobs with
the S10-01 `card-release-timers/milkyway_nbody.mic`, three GCC-KNC runtime
libraries and each case's two inputs via this repository's `tools/card_run`.
After landing into another checkout, set `CARD_BINARY` to the retained binary
path if needed. Results and receipts go to `runs/card/real-benchmarks/`.

Before accepting a card number, verify the receipt reports program exit zero
and compare its output with the retained x86 reference:

```bash
python scripts/compare.py tests/references/real-benchmarks/core-small-release runs/card/real-benchmarks/core-small.txt
python scripts/compare.py tests/references/real-benchmarks/real-steps-release runs/card/real-benchmarks/real-steps.txt
```

`PHASE setup` includes the initial tree/force call, which is also included in
tree/force totals. `whole_run - setup` measures the post-setup phase including
final reporting; tree/force totals cannot simply be added to setup. Divide
tree/force totals by their call counts for inclusive per-call averages; there
is one initial call in addition to the forward steps. Report raw phases and
the total, and avoid calling total real-steps time a pure step measurement.
