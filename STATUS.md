# Status

Lead-maintained. Last update: 2026-11-16 EST.

| Sprint | State |
|---|---|
| 1 | Card run done 2026-11-16 (docs/sprints/sprint-1.md); S1-06/S1-07 merged, chunk scaling waits for knc-twin S14-37 |
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
- knc-twin 0.4.0 (S1-05): fildl repro +0.0 and all 16 crlibm log_rn cases match x86 bits, so the S1-03 mismatch was
  a twin defect, not GCC-KNC wrong code. Gravity functional ok with the region cut before the never-taken cold error
  branch (until gcc-knc S14-20). Gravity timing: simulate 33,622 cycles/call (unvalidated estimate). The bounds
  critical-path term (43,656) charges every first touch full cold latency, so it is a cold-start scenario, not a
  floor; the real bound term is memory_concurrency 5,658 (knc-twin session, fix as gcc-knc S14-27 after S14-20).

- Card (7120, 240 threads) gives likelihoods bit-identical to x86 on small, medium and large (card run 2026-11-16);
  crlibm 6,272/6,272 probe rows bit-identical. Card wall: small 336 s, medium 1,225 s, large 61 s (app's 128-body
  OpenMP chunk limits small/medium to 1/8 busy threads).
- S1-07: the 1-ULP twin gravity mismatch is a knc-twin x87 double-rounding defect (gcc-knc S14-37); native x87
  PC=53 matches SSE bit for bit.

## Not proven yet

- End-to-end run on the card (S4-01): needs --benchmark admission and card_run's known_hosts first.
- The real Windows BOINC client with the Cygwin-built API (Sprint 4, needs BOINC installed).
- Live card graphics feed (screensaver tested offline with demo snapshots only).
- The guide followed verbatim by the lead.

## Lead notes

- 2026-11-16: card window 10 (gcc-knc turn claude-turn-s14-w10) closed at 11:15Z without our jobs (gcc-knc wait-loop bug). Staged jobs and conditions carry over to the next gcc-knc card turn; start only on its "go".

- Never edit tools/codex_run.sh while a session runs: bash reads scripts as it goes (S2-02 exit 127).
- Do not remove a ticket worktree before its built artifacts (dist/, runs/) are no longer needed: they are gitignored.
