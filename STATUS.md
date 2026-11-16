# Status

Lead-maintained. Last update: 2026-11-15 23:59 EST.

| Sprint | State |
|---|---|
| 1 | In progress: S1-01 merged; S1-02 (card build) running; S1-03 (knc-twin) next |
| 2 | S2-01 (BOINC API on Cygwin spike) running in parallel |
| 3 | Planned |
| 4 | Planned |

## Proven

- MilkyWay N-body 1.97 (pinned `d78c48fc`) builds standalone on x86 with a hand-written Makefile and runs the two
  sample workunits; 1 and 4 OpenMP threads give identical likelihoods (S1-01, Codex; lead reviewed).

## Not proven yet

- Card build, card run, x86 vs card agreement (S1-02, card turn).
- Build with crlibm (upstream default) and 53-bit x87 precision on the card (S1-02 review findings).
- Wrapper, screensaver, guide (Sprints 2-4).
