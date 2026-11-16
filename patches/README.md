# Pinned upstream patches

`scripts/fetch.sh` applies these idempotently to nbody_1.96. Scalar science follows that tag.

- `popt-cygwin.patch`: do not redeclare Cygwin's existing `glob_pattern_p` (S1-01).
- `crlibm-config-path.patch`: include `crlibm_config.h` through the include
  path rather than requiring a generated header inside the upstream tree.
  This allows the checked-in handwritten configuration in `config/`.

Histogram capture uses upstream `--print-histogram`; no output patch is needed.

- `nbody-wrapper-files.patch` (S2-02): opt-in `KNC_WRAPPER_FILES=1` publishes
  progress at safe simulation steps and acknowledges requested checkpoints
  only after upstream's checkpoint writer succeeds. No science or checkpoint
  layout changes. Version 1.96 stores its fixed
  softening array inline in checkpoints; the 1.97 pointer-repair helper is
  removed. Both x86 and k1om use the same patch. S3-01 adds opt-in
  wall-clock snapshots at safe steps, using the shared S3-02 wire header,
  deterministic subsampling and atomic rename. No body evolution changes.
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
