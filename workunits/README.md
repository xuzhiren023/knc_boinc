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

## S1-02 crlibm and card runs

Both builds now enable the bundled crlibm production default. Histogram numeric
and schema differences are diagnostics; the verdict is only the likelihood's
strict absolute difference < 1e-10. Missing, malformed or non-finite result data
still fails as invalid input. The earlier proposed histogram tolerance is retired.

The runner now adds upstream `--print-histogram` (`main.c:354-356`), which writes
a histogram to stderr. Standalone builds suppress the BOINC XML wrappers, so
the comparator recognizes the `n =` header and consumes exactly lambdaBins *
betaBins rows; it also accepts the tagged BOINC form. `compare.py` accepts a run directory or one file
containing captured stdout/stderr. With captures present it compares that printed
histogram in preference to histogram.txt. This is the final-state histogram;
the saved file can instead describe the best-likelihood timestep. Comparisons
must use the same representation on both sides. No output patch is needed.

`large/` copies the same upstream model and input histogram, with 20,000 bodies
passed on the command line. This is the ticket's fallback count: a current public
production parameter file with a verifiable particle count was not located on
2026-11-15. The official news archive
<https://milkyway.cs.rpi.edu/milkyway/old_news.php> reports a historic reduction
to 20k (12 May 2015), but also later 40k run names (16 June 2021); neither proves
current production settings. Thus 20,000 is a stated fallback, not a verified
current production count. The large model alone shortens `timeEvolve` from
3.945 to 0.05 Gyr and reverse-orbit `tstop` from 4.0 to 0.05 Gyr to bound
reference time while exercising the 20,000-body tree and force calculation
and placing the dwarf in the observed histogram region. All other model
settings remain the upstream test's. This bounded case does not establish
long-term numerical agreement for a full production-duration workunit.

Run the large x86 references at 1 and 12 threads:

```bash
bash scripts/run_x86.sh large '1 12'
python scripts/compare.py runs/x86/large-1 runs/x86/large-12
```

Build and print the four lead-only card commands (small 240/60, medium 240,
large 240 threads):

```bash
make -C mk card
bash scripts/card-check.sh
```

The printer creates only `runs/card/` and prints quoted commands, never invokes
card_run. Run the printed lines from the repository root. Each stages the ELF,
all bundled runtime libraries and both inputs explicitly with --file. A staged
shell launcher exports OMP_NUM_THREADS and OMP_DYNAMIC=FALSE, then execs the ELF;
--threads reserves the corresponding runner layout and --nthreads configures
upstream. Each line captures stdout/stderr together to `runs/card/CASE-THREADS.txt`
and writes a separate JSON receipt. The 43,200-second timeout accommodates large
unoptimized card runs; it is a deadline, not a runtime estimate. The package is
below the runner's default 64 MiB staging cap, without copying card GCC 5 libs.

After the lead verifies program exit zero in the receipt, compare for example:

```bash
python scripts/compare.py runs/x86/small-1 runs/card/small-240.txt
python scripts/compare.py runs/x86/small-1 runs/card/small-60.txt
python scripts/compare.py runs/x86/medium-1 runs/card/medium-240.txt
python scripts/compare.py runs/x86/large-1 runs/card/large-240.txt
```
