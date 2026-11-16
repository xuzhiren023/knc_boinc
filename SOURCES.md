# Pinned science sources

Selected 2026-11-16 for the standard **N-Body Simulation** app, distributed
as 1.96 on every platform at https://milkyway.cs.rpi.edu/milkyway/apps.php.
The separate Orbit Fitting app uses 1.97 and is outside this build's scope.

- Repository: https://github.com/Milkyway-at-home/milkywayathome_client.git
- Tag: `nbody_1.96` (not the redundant `_lite` alias)
- Commit: `1e640779f1cabf88aaa49e4db569cfe7e09016c4`
- Fetch: `bash scripts/fetch.sh`, shallow clone, no recursive submodules;
  repeat calls verify HEAD and the expected patch state and do no network work.
- Main licence: GPL-3.0-or-later, upstream `COPYING` and source notices.

Only libraries already bundled in this commit are compiled:

| Library | Version | Licence / upstream notice |
| --- | --- | --- |
| Lua | 5.1.4 | MIT, `lua/COPYRIGHT` |
| popt | 1.17 fork | permissive MIT-style Red Hat notice, `popt/COPYING` |
| dSFMT | 2.1 | BSD-3-Clause, `dSFMT/LICENSE.txt` |
| crlibm | bundled 9c4c1c7e5f87f29535488b605ce38777e1a8b004 | LGPL-2.1-or-later, `crlibm/COPYING` and source notices |

No glfw, glm, tao, OpenCL or crlibm dependency is fetched separately.
BOINC is pinned separately below. The upstream checkout includes other bundled directories;
`mk/sources.mk` is the exact list used by the standalone executable.

The science checkout is `third_party/milkywayathome_client_196`.
`patches/popt-cygwin.patch` prevents redeclaring Cygwin's `glob_pattern_p`.
Math uses `NBODY_CRLIBM=1`, matching upstream's production default (S1-02).
Upstream 1.96 uses platform libm for `erf`, `cbrt` and gamma functions;
CORE-MATH and its portability patches belong to 1.97 and are removed.
No fast-math flags. `crlibm-config-path.patch` lets crlibm find the checked-in
configuration. See `patches/README.md` for the full inventory.

## BOINC app-side API (S2-01)

- Repository: https://github.com/BOINC/boinc.git
- Client release tag: `client_release/8.2/8.2.8`
- Peeled commit: `0bb9686b9ea2cb26e342c715026d8059fa58b922`
- Fetch just BOINC: `bash scripts/fetch.sh boinc`; the default fetch supplies
  both pinned repositories. Shallow tag clone, no submodules; subsequent calls
  verify HEAD and patch state without network access.
- Licence: LGPL-3.0-or-later for the app API and library sources (upstream
  `COPYING.LESSER` and per-file notices; see also `COPYING`).
- Build list: `mk/boinc.mk`. Only `api/` and `lib/` app-side pieces; no client,
  manager, server, renderer, OpenGL, curl or SSL build. The host-info XML parser
  also needs the bundled coprocessor/OpenCL/WSL metadata code; no GPU runtime
  is linked or loaded by these tests.
- `patches/boinc/cygwin-win32.patch` fixes Cygwin header/implementation directory
  guards, uses POSIX delete/fopen paths, omits MSVC-only share.h, qualifies
  exception functions, and uses DWORD for three Win32 out parameters.
  `config/boinc/` supplies the minimal config and CRT compatibility helpers.
  Mapping names, SHARED_MEM layout, channel operations and XML are unmodified.
