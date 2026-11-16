# Status

Lead-maintained. Last update: 2026-11-16 EST.

| Sprint | State |
|---|---|
| 1 | S1-01..S1-04 merged; card run staged, waits for the gcc-knc lead's "go"; S1-05 (twin rerun) waits for knc-twin 0.4.0 + S14-20 |
| 2 | S2-01..S2-04 merged |
| 3 | S3-01, S3-02 merged |
| 4 | S4-01 merged (end-to-end script, not yet run on the card); S4-02 guide merged as a draft, final pass after the card run |

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
  log(1.0) in the twin (expected 0). S1-04: twin defect (fildl read 8 bytes, filds 4), confirmed by the knc-twin session; fix in engine 0.4.0 (gcc-knc S14-19), PLT cold-path support S14-20; rerun is S1-05.

## Not proven yet

- Card run and x86 agreement (likelihood |diff| < 1e-10, upstream rule).
- The real Windows BOINC client with the Cygwin-built API (Sprint 4, needs BOINC installed).
- Live card graphics feed (screensaver tested offline with demo snapshots only).
- The guide followed verbatim by the lead.

## Lead notes

- 2026-11-16: card window 10 (gcc-knc turn claude-turn-s14-w10) closed at 11:15Z without our jobs (gcc-knc wait-loop bug). Staged jobs and conditions carry over to the next gcc-knc card turn; start only on its "go".

- Never edit tools/codex_run.sh while a session runs: bash reads scripts as it goes (S2-02 exit 127).
- Do not remove a ticket worktree before its built artifacts (dist/, runs/) are no longer needed: they are gitignored.
