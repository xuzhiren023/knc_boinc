# S10-09 relaxed eight-node quadrature experiment

`DF_VECTOR8=1` requires `DF_SPECIAL=1`, reuse, parallel quadrature and OpenMP.
Both it and `DF_VECTOR8_GUARD` default off. The Performance patch is
`patches/zzzzzzz-nbody-df-vector8.patch`; `src/nbody_df_vector8.h` is its
Performance helper. The release configuration keeps both options off.

The original quadrature recurrence builds the same nodes and coefficients.
Each worker gathers eight adjacent nodes, computes Plummer and cored samples,
five-point density/potential stencils, both derivatives and the integrand in
GCC vector types, then scatters the results back into the original intervals.
The last partial block duplicates a valid input only in inactive lanes; stores
are bounded by the active count. The caller sums nodes serially in the
original order with the original truncated quadrature constants. Stencil and
node expression grouping is retained. The relaxed transcendental calls use the
installed libknc_vmath lane-core ABI (atan2(x,1) for double atan). Fixed sqrt
loops and vector arithmetic are lowered by GCC-KNC. No fast-math is enabled.

The incomplete gamma implementation follows pinned nbody_mass.c: Lanczos
log-gamma, the 100-iteration series or continued fraction, the same convergence
tests (3e-7), and the same 1e-30 continued-fraction floor. Each lane freezes
its state at convergence. Series and fraction lanes can coexist. Invalid
arguments return NaN; cap exhaustion emits a diagnostic. Model setup, roots,
radius generation, RNG calls and unsupported/nested/pipelined quadrature
remain on the existing arithmetic path.

The optional empirical guard compares each fast-dependent golden-section
profile decision and rejection ratio against a relative margin. Bracket and
termination comparisons use only exact geometry, unchanged by the relaxed
math. A nonfinite decision or a gap within the margin marks the velocity for
replay. The complete pre-velocity dSFMT state is restored, and that velocity
is regenerated with exact specialized nodes. It can still differ from exact
on unmeasured inputs: the margin is empirical, not an interval bound.

The calibration kernel compares identical radius/velocity inputs in exact and
fast distribution functions, including the actual workunit model, cored
branch boundaries, cutoff/no-cutoff models and mixed gamma branches. Its
maximum normalized difference is inflated 1000x. `calibration.json` records
the samples, maximum, selected margin and policy. Production builds contain
no guard counter or capture I/O. Test-only capture source records triggers,
initial bodies after CM correction, and initialized dSFMT words/index at each
body end before correction. `tests/s10_df_vector8_capture.h` additionally
captures 32 real eight-node batches for each component during core-small.
The capture binary has the same instrumentation for all timing variants;
only the fast core-small run also writes the bounded real-node sample.

Use bash; every build creates build/tmp and exports TMPDIR/TMP/TEMP to
$PWD/build/tmp. `scripts/test-s10-df-vector8.sh --measure` builds and runs the
authorized short cases sequentially, with make -j2 and OMP_NUM_THREADS=4.
The owner canceled further full captures at 19:45Z; `--full` and the driver's
117676 case are rejected. Default invocation
checks retained evidence without regenerating bodies. Raw measurements,
commands, options, body/RNG traces and compiled artifacts are under
`build/s10/df-vector8` and `runs/s10-df-vector8`.

The lead-only `build/s10/df-vector8/card-window.sh` runs release, vector8 and
guarded core-small/real-steps at 240 threads through this repository's
`tools/card_run --transfer tcp-large`, stages the matching runtimes, retains
receipts, and reports likelihood differences. Predictions and their recording
time are frozen in prediction.json / prediction-both.json and copied to the
final handoff manifest. Native acceptance requires the lead's completed card
receipts. `scripts/test-s10-df-vector8.sh --card` requires the exact likelihood
match for both log/atan modes on both cases; ordinary offline acceptance skips
that test while the required receipts are missing. Server acceptance remains
unproven.

Compiler evidence: `probes/s10_df_vector8_repro.c` reduces the mixed
transcendental-loop and data-dependent gamma-series blockers. Build with
`bash scripts/s10-df-vector8-compiler.sh` after card builds; it retains
-fopt-info-vec-missed diagnostics, linked disassembly, library provenance,
capabilities, worker audits and captured-input node audits. These compiler
opportunities belong to GCC-KNC; no scheduling, prefetch or approximate
polynomial tuning is in this patch.

The lead's additional twin request uses `probes/s10_df_vector8_twin.c`:
a diagnostic card binary exposing pointer-only entry wrappers for the original
scalar specialization and actual df8_nodes. `from_binary` keeps complete
functions, includes available callees, and separately audits callee targets if
a complete conversion fails. The real captures are marshaled with verified
KNC Dwarf offsets and tail padding, and four contexts receive distinct output
buffers. No unsupported instruction is silently discarded, and no external
call gets an invented cycle cost. All adapter, functional and simulation
statuses are retained. Only successful supported results can supply cycles;
a failed or partial audit cannot establish numerical agreement or speed.
The requested profile is card-7120-measured; the L1/all-predicted scenario is
an optimistic, unvalidated scenario for this kernel shape. knc-twin does not
replace the native card window.

The initial KNC build rejected a function returning three D8 vectors with
`unsupported KNC register ABI mode`. Forced inlining did not avoid the front-end
ABI check. The helper now writes the aggregate through a pointer, retaining
its expression graph. Compile the reduced probe with
`-DREPRO_AGGREGATE_ABI` to reproduce; compiler-aggregate.txt retains that failure.

Current twin limitation (0.4.0): complete scalar conversion fails on btc/bts
and an absolute jump table in crlibm helpers. Complete vector conversion also
finds unsupported x87 integer conversion forms in installed vector-math
callees. The supported caller and helpers were extracted with the unsupported
call targets cut; functional and one-core/four-context simulation both stop
at the real `__knc_vmath_core_pow_8.part.0` call to `core`. That target was
independently audited and is unsupported. Results are `status: unsupported`,
`result_class: null`, with no cycles per node or predicted ratio. The complete
raw status/assumptions/unsupported/calibration/parameter fields are copied in
`twin-node-results.json`. The scalar functional/timing runs cannot start
because conversion fails. No unsupported code was replaced or given a
fabricated result/cost; this leaves the lead's additional twin validation
requirement unproven pending expanded twin support.

The frozen real-node input is `build/s10/df-vector8/twin-node-inputs.bin`, so
later short host timing repeats cannot overwrite the twin's input provenance.
All 512 lanes have a host fast-versus-exact bit/ULP comparison. One lane differs
by 6,065,920 ULP at the integrand (absolute difference about 9.35e-27). Finite
differences amplify the library's small per-call errors: the library's ULP
contract is not an ULP contract on the final integrand. This host comparison
is separate from, and does not substitute for, a successful KNC twin check.

## Owner comparison added in the ticket

Both log/atan modes are retained, per the owner's final refinement.
`DF_VECTOR8_SCALAR_LOG_ATAN=1` extracts each active lane, calls exact scalar
crlibm log_rn/atan_rn, and inserts the result. The remaining samples,
stencils, sqrt/div arithmetic, exp/pow lane-core calls and masked gamma
recurrences remain vector operations. Its default is 0 (the all-vector
comparison); both experiments still require the off-by-default DF_VECTOR8.
The `scalar` and `scalar-guard` build variants use this option, with their
own calibration-scalar.json and kernel-scalar.json. They receive the same
core-small/real-steps capture comparisons as `vector8` and `guard`.

The card window now contains ten jobs: exact reference plus both modes and
both optional guards for each short case. `prediction-both.json` freezes the
expanded predictions and retains the earlier six-job prediction.json record.
`python scripts/s10-df-vector8.py stage window` writes the reviewable window
and prediction without hashing unfinished host runs; final `stage` writes the
complete evidence manifest. The scalar-log/atan diagnostic audit is invoked
with `python scripts/twin-s10-df-vector8.py scalar` and uses its own frozen
real-node capture and result files ending in -scalar.json.

The 19:45Z owner note supersedes all earlier full-generation requests. The
exact reference had already completed at 19:42:15Z (110,000 bodies, 657.681 s)
before that cancellation. No full variant capture started; no full capture was
running when the note was discovered. `full-cancellation.json` records this
state, and further launches are hard-disabled. The prior reference artifact is
retained as historical evidence and is excluded from current acceptance.
