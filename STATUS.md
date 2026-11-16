# Status

Lead-maintained. Last update: 2026-11-16 EST.

| Sprint | State |
|---|---|
| 1 | S1-01..S1-03 merged; S1-04 (log_rn twin mismatch + card probe) running; card run waits for a free turn |
| 2 | S2-01, S2-02 merged; S2-03 (package, app_info.xml) running |
| 3 | Planned |
| 4 | Planned |

## Proven

- MilkyWay N-body 1.97 (pinned `d78c48fc`) builds standalone for x86 (Cygwin) and for the card (GCC-KNC, K1OM,
  knc_lint pass), both with crlibm (upstream default); card startup sets x87 53-bit precision (disassembly).
- x86 references (crlibm): small -438.534790192227661, medium -450.772121584039894, large (20k bodies, 0.05 Gyr)
  -4894.200373110274995; 1 vs 4/12 OpenMP threads identical.
- BOINC 8.2.8 app API built with Cygwin g++ on the Win32 paths passes an offline fake-client protocol test
  (progress, checkpoint, suspend/resume/quit, graphics shmem, standalone).

- knc_wrapper (S2-02) passes normal finish, suspend/resume, quit/checkpoint/restart, abort and card-unreachable flows
  through real BOINC Win32 IPC with a fake card running the x86 app; restarted output equals uninterrupted.
- knc-twin (S1-03): gravity refused (PLT sqrt, no sourced cost); crlibm log_rn returns 0x43c628b76e3a7b61 for
  log(1.0) in the twin (expected 0). Twin defect or GCC-KNC wrong code: S1-04 decides with a card probe.

## Not proven yet

- Card run and x86 agreement (likelihood |diff| < 1e-10, upstream rule).
- The real Windows BOINC client with the Cygwin-built API (Sprint 4, needs BOINC installed).
- Wrapper, screensaver, guide.

## Lead notes

- Never edit tools/codex_run.sh while a session runs: bash reads scripts as it goes (S2-02 exit 127).
- Do not remove a ticket worktree before its built artifacts (dist/, runs/) are no longer needed: they are gitignored.
