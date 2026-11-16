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
