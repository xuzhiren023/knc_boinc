# Reproducible standalone workunits

Both cases use unmodified `nbody/tests/orphan_models/model_1.lua` from
`nbody_1.97`, copied as `params.lua`. The model takes its particle count from
the command line; `small` uses 64 and `medium` uses 1024. Both use seed
670828913 (upstream's `RunTestUnits.lua:25`) and the original evolution time
3.945, timestep calculation, external potential and quadrupole tree settings.
These are parameterized upstream test cases, not new science models.

Each `input.hist` is an exact LF-normalized copy of upstream
`nbody/tests/orphan_models/orphan_model_histogram_3`. It has the model's matching
34 lambda bins / one beta bin and a modern tagged, metadata-bearing format.
The older `orphan_model_histogram_1` is a legacy four-column file incompatible
with this version's reader. These checks compare runs against each other;
the upstream test's stored likelihood for 10000 bodies is not a reference for
these lower particle counts. The small case is for speed and reproducibility,
not scientific convergence. All copied data/source retain upstream's licence
(GPL-3.0-or-later); see `SOURCES.md` and upstream `COPYING`.

Run in Git Bash from this repository root. Prepare and build:

```bash
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh && make -C mk x86
python -m unittest discover tests
bash scripts/run_x86.sh
```

The exact single-thread command lines are:

```bash
export OMP_DYNAMIC=FALSE OMP_NUM_THREADS=1
build/x86/milkyway_nbody.exe -f workunits/small/params.lua -h workunits/small/input.hist -z runs/x86/small-1/histogram.txt -c runs/x86/small-1/checkpoint --seed 670828913 --nthreads 1 --ignore-checkpoint --checkpoint-interval=-1 64
build/x86/milkyway_nbody.exe -f workunits/medium/params.lua -h workunits/medium/input.hist -z runs/x86/medium-1/histogram.txt -c runs/x86/medium-1/checkpoint --seed 670828913 --nthreads 1 --ignore-checkpoint --checkpoint-interval=-1 1024
```

Create the output directories first. For four threads set `OMP_NUM_THREADS=4`,
pass `--nthreads 4` and change each output path suffix to `-4`. The runner does
this automatically, captures stdout/stderr, histogram, exit status, elapsed
wall seconds and command line in `runs/x86/<case>-<threads>/`. To rerun only
one combination: `bash scripts/run_x86.sh medium 1`.

```bash
python scripts/compare.py runs/x86/small-1 runs/x86/small-4
python scripts/compare.py runs/x86/medium-1 runs/x86/medium-4
```

The comparator requires one `<search_likelihood>` in stdout/stderr, a nonempty
numeric `histogram.txt`, matching bin identities and matching metadata shape.
It reports absolute and relative differences for the likelihood and all
numeric histogram fields (including errors and metadata). The default strict
absolute tolerance `< 1e-10` comes from upstream
`nbody/tests/RunTestUnits.lua:137-139` for likelihoods. **Proposed rule:** apply
that same bound to histogram numeric fields; no upstream end-to-end histogram
acceptance threshold was found. Relative differences are diagnostic only.
`--tolerance VALUE` overrides the absolute bound explicitly. Missing,
malformed and non-finite data fail. Comments contain timestamps and are
ignored, so full histogram files need not be byte-identical even when all
science values are. This is not a production BOINC validator.

For byte identity of the scientific results, compare the likelihood token and
histogram content after removing `#` comments and blank lines. Timings,
OpenMP diagnostics and generated timestamps make full logs unsuitable for
byte identity. The engineer report records both the numeric and byte checks.
