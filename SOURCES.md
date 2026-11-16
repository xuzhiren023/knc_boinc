# Pinned science sources

Selected 2026-11-15 from https://milkyway.cs.rpi.edu/milkyway/apps.php:
ordinary N-body is distributed as 1.96; N-body with Orbit Fitting is distributed
as 1.97 (Windows/Linux x86-64 and Linux ARM64, dated 2026-10-28).
The newest release tag matching a currently distributed N-body version is
therefore `nbody_1.97`; the source's `nbody/CMakeLists.txt:24-29` confirms 1.97.
This reference intentionally uses the newer Orbit Fitting version.

- Repository: https://github.com/Milkyway-at-home/milkywayathome_client.git
- Tag: `nbody_1.97` (not the redundant `_lite` alias)
- Commit: `d78c48fc9905ee309e28ae4b76ad2f6fda901ef8`
- Fetch: `bash scripts/fetch.sh`, shallow clone, no recursive submodules;
  repeat calls verify HEAD and the expected patch state and do no network work.
- Main licence: GPL-3.0-or-later, upstream `COPYING` and source notices.

Only libraries already bundled in this commit are compiled:

| Library | Version | Licence / upstream notice |
| --- | --- | --- |
| Lua | 5.1.4 | MIT, `lua/COPYRIGHT` |
| popt | 1.17 fork | permissive MIT-style Red Hat notice, `popt/COPYING` |
| dSFMT | 2.1 | BSD-3-Clause, `dSFMT/LICENSE.txt` |
| CORE-MATH functions | bundled snapshots | MIT, notices in `milkyway/src/milkyway_math_funcs.c` |
| crlibm | bundled 9c4c1c7e5f87f29535488b605ce38777e1a8b004 | LGPL-2.1-or-later, `crlibm/COPYING` and source notices |

No BOINC, glfw, glm, tao, graphics, OpenCL, crlibm or external dependency is
fetched separately. The upstream checkout includes other bundled directories;
`mk/sources.mk` is the exact list used by the standalone executable.

`patches/popt-cygwin.patch` prevents redeclaring Cygwin's `glob_pattern_p`.
`patches/core-math-cygwin.patch` selects the existing portable round-to-even
fallback on Cygwin: GCC's builtin otherwise emits an unavailable `roundeven`
libm symbol. Both patches are applied idempotently by `scripts/fetch.sh`.

Math uses `NBODY_CRLIBM=1`, matching upstream's production default (S1-02).
Upstream 1.97 unconditionally uses its bundled CORE-MATH implementations for
`erf`, `cbrt` and gamma functions (`milkyway/include/milkyway_math_double.h`);
these remain enabled, as required by this pinned source. No fast-math flags.

The additional S1-02 patches select existing portable CORE-MATH paths on K1OM
and let crlibm find the checked-in config header. See `patches/README.md` for
the complete patch inventory and reasons.
