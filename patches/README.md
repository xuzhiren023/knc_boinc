# Pinned upstream patches

`scripts/fetch.sh` applies these idempotently to nbody_1.97. No algorithms are replaced.

- `popt-cygwin.patch`: do not redeclare Cygwin's existing `glob_pattern_p` (S1-01).
- `core-math-cygwin.patch`: select CORE-MATH's round-to-even fallback because
  Cygwin libm lacks the `roundeven` symbol emitted by its compiler (S1-01).
  S1-02 extends that same fallback to K1OM, which has no SSE round instruction.
- `core-math-knc.patch`: K1OM defines `__x86_64__` but lacks SSE. Exclude it
  from CORE-MATH's x86 intrinsic paths and builtin roundeven selection, using
  the existing fenv and portable round-to-even alternatives instead.
- `crlibm-config-path.patch`: include `crlibm_config.h` through the include
  path rather than requiring a generated header inside the upstream tree.
  This allows the checked-in handwritten configuration in `config/`.

Histogram capture uses upstream `--print-histogram`; no output patch is needed.

- `nbody-wrapper-files.patch` (S2-02): opt-in `KNC_WRAPPER_FILES=1` publishes
  progress at safe simulation steps and acknowledges requested checkpoints
  only after upstream's checkpoint writer succeeds. No science or checkpoint
  layout changes. On wrapper restart it also rebuilds context softening arrays
  from the same Lua input: upstream serializes their pointer values but not
  their contents. Both x86 and k1om use the same patch. S3-01 adds opt-in
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
