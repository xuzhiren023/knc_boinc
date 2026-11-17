# Pinned upstream patches

`scripts/fetch.sh` applies these idempotently to nbody_1.96. Scalar science follows that tag.

The GCC-KNC M5 baseline applies only **Correctness/portability** patches. It
excludes both other classes. The ordinary app fetch applies all patches in
filename order; performance and instrumentation options default off in source.
S8-09's selected build options are explicit in `config/s8-09.env`.

| Patch | Class | Selector/default or purpose |
| --- | --- | --- |
| `boinc/cygwin-win32.patch` | Correctness/portability | BOINC Cygwin/Win32 API compatibility |
| `crlibm-config-path.patch` | Correctness/portability | Handwritten configuration include path |
| `nbody-king-const.patch` | Correctness/portability | Compatible read-only callback types |
| `nbody-result-contract.patch` | Correctness/portability | Stock result banner and wrapper contract |
| `nbody-wrapper-files.patch` | Correctness/portability | Wrapper checkpoint/progress/graphics file protocol |
| `popt-cygwin.patch` | Correctness/portability | Avoid duplicate Cygwin declaration |
| `nbody-force-chunk.patch` | Performance | NBODY_FORCE_CHUNK unset preserves upstream scheduling; card build selects 4 |
| `z-nbody-gen-pipeline.patch` | Performance | NBODY_GEN_PIPELINE=0; exact one-step golden-section root/search speculation |
| `zzzzz-nbody-gen-profile.patch` | Instrumentation | NBODY_GEN_PROFILE=0; generator nested wall timers and per-body counts |
| `z-nbody-df-reuse.patch` | Performance | NBODY_DF_REUSE=0; share identical stencil samples |
| `../probes/s9-df-vector/performance.patch` | Performance | NBODY_DF_VECTOR=0; certified eight-node experiment, requires reuse |
| `../probes/s9-df-vector/instrumentation.patch` | Instrumentation | NBODY_DF_STATS=0; vector attempts and exact replays |
| `nbody-parallel-quad.patch` | Performance | NBODY_PARALLEL_QUAD=0 |
| `nbody-static-integrate.patch` | Performance | NBODY_STATIC_INTEGRATE=0 |
| `nbody-tree-variants.patch` | Performance | NBODY_TREE_VARIANT=0 (upstream); 1 CofM, 2 pool |
| `nbody-tree3.patch` | Performance | NBODY_TREE_VARIANT=3 opts into balanced pool and parallel threading; default remains 0 |
| `nbody-tree4.patch` | Performance | NBODY_TREE_VARIANT=4 opts into stable parallel per-level partition; default remains 0 |
| `nbody-vector-gravity.patch` | Performance | NBODY_VECTOR_GRAVITY=0 |
| `zzz-nbody-walk-layout.patch` | Performance | NBODY_WALK_LAYOUT=0 |
| `zz-nbody-phase-timers.patch` | Instrumentation | NBODY_PHASE_TIMERS=0 |
| `zz-nbody-tree-instrumentation.patch` | Instrumentation | Tree subphase timers; NBODY_TREE_IDENTITY=0 |
| `zzzz-nbody-walk-counters.patch` | Instrumentation | Host-only NBODY_WALK_COUNTERS=0 |

Performance patches contain no numerical correctness fix. S8-09 separated the
static integrator from phase timers, tree algorithms from tree timers/identity
checks, and walk layout from debug counter hooks. Applying the complete new
sequence reconstructs the already-tested source unchanged. Counter helpers in
`src/nbody_walk_layout.h` are enabled only by the separate instrumentation
hooks/option; they are compiled out of card timing binaries. The timer patch
precedes tree instrumentation and layout; walk counters are applied last.

- `popt-cygwin.patch`: do not redeclare Cygwin's existing `glob_pattern_p` (S1-01).
- `crlibm-config-path.patch`: include `crlibm_config.h` through the include
  path rather than requiring a generated header inside the upstream tree.
  This allows the checked-in handwritten configuration in `config/`.

Histogram capture uses upstream `--print-histogram`; no histogram output patch is needed.

- `nbody-wrapper-files.patch` (S2-02): opt-in `KNC_WRAPPER_FILES=1` publishes
  progress at safe simulation steps and acknowledges requested checkpoints
  only after upstream's checkpoint writer succeeds. No science or checkpoint
  layout changes. Version 1.96 stores its fixed
  softening array inline in checkpoints; the 1.97 pointer-repair helper is
  removed. Both x86 and k1om use the same patch. S3-01 adds opt-in
  wall-clock snapshots at safe steps, using the shared S3-02 wire header,
  deterministic subsampling and atomic rename. No body evolution changes.
- `nbody-result-contract.patch` (S7-02): when `KNC_WRAPPER_FILES` is enabled,
  emit upstream's `<search_application>` banner in standalone science stderr.
  The wrapper forwards that stream to BOINC, whose captured 196/mt results
  declare no output files. Ordinary standalone output and science arithmetic
  are unchanged.
- `boinc/cygwin-win32.patch` uses the compiler's `__CYGWIN__` guard consistently
  for its compatibility changes, including upstream header/CRT branches; no
  synthetic `__CYGWIN32__` build definition is required.

- `nbody-force-chunk.patch` (S5-02): exposes `NBODY_FORCE_CHUNK` in the two
  gravity loops, two integration loops and guided shared-memory loop. Each
  translation unit retains its original `4096 / sizeof(...)` default; schedule
  kinds and per-body calculations are unchanged. `mk/Makefile` selects 4 for
  card builds and leaves x86 at the upstream default.

- `nbody-vector-gravity.patch` (S6-03, rebased S7-01): opt-in eight-body walk,
  default off. Softening follows 1.96 exactly: sum node/body types and select
  LM/cross/DM from `eps2[3]`, including tree cells. Arithmetic order and
  quadrupoles match the scalar walk. Host chunk4/vector identity is checked
  by `tests/nbody_196_matrix.py`.
- `nbody-king-const.patch` (S7-01): make the King read-only model arguments
  const through its ODE callbacks, matching gauss_quad's callback type.
  GCC 16 otherwise rejects the incompatible function pointer in 1.96.
  No function bodies, constants or arithmetic are changed.

CORE-MATH portability patches were removed: that code does not exist in 1.96.
All remaining patches were checked against pristine 1.96 and regenerated
with its context/line numbers. Fetch also verifies the fully patched state.

- `zz-nbody-phase-timers.patch` (S8-01): `NBODY_PHASE_TIMERS=1` measures
  tree, force, integration, per-step likelihood, final results, setup and
  whole-run wall times using OpenMP. Default off. PHASE records are emitted
  to stderr after results; steps is a count (seconds is zero). Setup includes
  the initial gravity evaluation and overlaps tree/force totals.
  `nbody-static-integrate.patch` separately selects static scheduling for the
  two independent per-body integrator loops with `NBODY_STATIC_INTEGRATE=1`;
  default off. Build with make variables
  `PHASE_TIMERS=1 STATIC_INTEGRATE=1`; `scripts/build-s8.sh` builds the
  requested three variants, `tests/phase_timers.py` checks large-case outputs.
- `nbody-parallel-quad.patch` (S8-03): `NBODY_PARALLEL_QUAD=1` records the
  original mixed-dwarf quadrature recurrence, evaluates its nodes with an
  OpenMP static loop, then accumulates in the original order. The original
  decimal constants, counter exit, sign and expression grouping are retained.
  Nested parallel calls, uninitialized lazy models and unsupported profiles
  use the original serial routine. Default off (`PARALLEL_QUAD=0` in make).
  `scripts/build-parallel-quad.sh` enables it for the scalar chunk-4 card
  binary; `scripts/test-parallel-quad.sh` checks the actual generator against
  pristine 1.96. Capture hooks live only in the test translation units.
- `nbody-tree-variants.patch` (S8-07/S8-09): serial insertion with parallel
  moments or a persistent contiguous arena, stable depth-three partition and
  slab allocation. TREE_VARIANT=0 keeps the upstream algorithm. Pool ownership
  is reset when states are initialized/cloned/restored and released on teardown.
  Its separate instrumentation patch supplies subphase allocation accounting
  and the every-build serial-tree comparison used by the acceptance proof.
- `zzz-nbody-walk-layout.patch` (S8-08/S8-09): a transient walk-order cell/body
  view, guarded successor prefetch, exact original-index force scatter and
  original storage restoration. Allocation/packing/scatter stay inside the
  existing force phase. `zzzz-nbody-walk-counters.patch` adds only debug hooks
  for host traversal/force counters; no timing build enables those counters.

- `nbody-tree3.patch` (S9-04): variant 3 extends the pool with a stable adaptive
  frontier capped at max(2, nbody/(4*threads)) bodies per job. Largest jobs run
  first with dynamic scheduling. Serial top cells preserve octant arithmetic;
  parallel threading uses local boundaries followed by serial successor repair.
  All new algorithm paths require TREE_VARIANT=3. Frontier balance counts and
  model diagnostics belong to `zz-nbody-tree-instrumentation.patch` and require
  TREE_IDENTITY=1; the card timing build excludes them.
- `z-nbody-df-reuse.patch` (S9-05): explicitly reuse the five distinct samples of
  initialized read-only models, retaining all stencil expressions and their
  evaluation order. Center potential samples are shared too. Other profiles
  retain upstream sampling. `DF_REUSE=1`, off by default.
- `../probes/s9-df-vector/performance.patch` (S9-05): separate eight-node vector/ball arithmetic
  experiment using libknc_vmath log/atan and S8-05-style guarded comparisons
  with full RNG replay on uncertainty. Requires `DF_REUSE=1`; off by default.
  See `docs/research/s9-df-bound.md` for the enclosure argument and selection
  rule. Its incomplete-gamma tail samples are exact scalar calls. The final
  selected options and measurements are in the S9-05 Engineer report.
- `../probes/s9-df-vector/instrumentation.patch` (S9-05): instrumentation only, optional
  `DF_STATS=1` counts guarded velocity attempts and exact replays. It is
  separate from both performance patches and does not affect decisions.

The S9-05 vector/stats patches are archived **outside the fetch sequence** after
81.1% core-small exact replay and a host slowdown. They apply after all ordinary
patches, to an isolated experiment tree generated by `scripts/s9-df.py experiment`.
They are not part of the selected card/full-generation source. The named class
for each archived patch remains exclusive. `DF_VECTOR=1` builds require that
isolated source; they cannot silently select an absent implementation.

- `nbody-tree4.patch` (S9-06): variant 4 keeps variant 3's frontier cap,
  insertion, moments and successor repair. Per-level octant paths are computed
  in parallel from exact parent midpoints. Contiguous 64-body tiles count keys;
  per-group prefixes in tile order and ordered local scatters preserve body
  order independently of thread scheduling. Persistent grouping scratch is
  released with the pool. Upper cells are stored child-before-parent after
  reversing breadth order; per-cell octant arithmetic is unchanged. expandBox
  retains variant 3's exact max reduction. No instrumentation is in this patch.

- `z-nbody-gen-pipeline.patch` (S10-03): overlap both possible next
  golden-section root/search preparations with the current quadrature node
  team. Keep the original decision, bisection and RNG order; consume only
  bitwise matching velocity keys. Initialized read-only non-King models only;
  all other paths remain original. `GEN_PIPELINE=1` requires parallel quadrature
  for an active path; default off. This is speculative algorithmic parallelism.
- `zzzzz-nbody-gen-profile.patch` (S10-03): `GEN_PROFILE=1`, default off,
  partitions caller wall time into exclusive generator subphases and reports
  inclusive max/rejection times plus integral/attempt/RNG counts. Node dispatch
  includes team overhead and the implicit barrier. See
  `docs/research/s10-gen.md` for timer semantics, measurements and predictions.
