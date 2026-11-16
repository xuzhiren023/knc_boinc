# Status

Lead-maintained. Last update: 2026-11-16 EST.

| Sprint | State |
|---|---|
| 1 | S1-01, S1-02 merged; S1-03 (knc-twin kernel check) running; card run waits for a free turn |
| 2 | S2-01 merged; S2-02 (wrapper) running; S2-03 next |
| 3 | Planned |
| 4 | Planned |

## Proven

- MilkyWay N-body 1.97 (pinned `d78c48fc`) builds standalone for x86 (Cygwin) and for the card (GCC-KNC, K1OM,
  knc_lint pass), both with crlibm (upstream default); card startup sets x87 53-bit precision (disassembly).
- x86 references (crlibm): small -438.534790192227661, medium -450.772121584039894, large (20k bodies, 0.05 Gyr)
  -4894.200373110274995; 1 vs 4/12 OpenMP threads identical.
- BOINC 8.2.8 app API built with Cygwin g++ on the Win32 paths passes an offline fake-client protocol test
  (progress, checkpoint, suspend/resume/quit, graphics shmem, standalone).

## Not proven yet

- Card run and x86 agreement (likelihood |diff| < 1e-10, upstream rule).
- The real Windows BOINC client with the Cygwin-built API (Sprint 4, needs BOINC installed).
- Wrapper, screensaver, guide.

## Lead notes

- Do not remove a ticket worktree before its built artifacts (dist/, runs/) are no longer needed: they are gitignored.
