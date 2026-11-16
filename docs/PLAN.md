# knc-boinc plan

Lead: Claude (plans, writes tickets, reviews, merges to local `main`, runs the card). Engineers: Codex sessions started
by `tools/codex_run.sh`, one per ticket. Owner: decides scope, card time and anything sent to a BOINC project.
Started 2026-11-15 (EST).

## Goal

One MilkyWay@home N-body workunit runs on the KNC card as a single BOINC task using all 240 threads, started by the
BOINC client on the owner's Windows laptop, with suspend/resume/quit working and a screensaver showing the simulation.

## Done when (project acceptance)

1. The card build of `milkyway_nbody` and the x86 build produce the same result on the same workunit, within a tolerance
   stated and justified before the comparison (Sprint 1).
2. The knc-twin skill's `functional` check of the compiled force-loop kernel matches the host reference, and its
   `simulate`/`bounds` give a per-core prediction the card run can be held to (Sprint 1, before card time).
3. `knc_wrapper.exe` runs the workunit end to end on the card from the laptop: inputs staged, progress reported,
   suspend/resume/abort forwarded to the card process, checkpoint and restart, outputs returned (Sprint 2, 4).
4. `knc_nbody_graphics.exe` shows live particles from the card in a window and full screen (Sprint 3).
5. `docs/TRY-IT.md` takes the owner from a clean laptop to a running task, step by step (Sprint 4).

Nothing is returned to the MilkyWay@home server by us. Attaching the laptop to the real project is the owner's step in
the guide, after the offline check passes.

## Architecture and decisions

| # | Decision | Why |
|---|---|---|
| D1 | Card app = upstream `milkyway_nbody`, pinned commit, built **without** BOINC (standalone), OpenMP, no OpenCL, `-O2 -march=knc -fopenmp` with GCC-KNC; shared runtimes in `lib/` beside `bin/` (RPATH `$ORIGIN/../lib`). | BOINC lives on the host; the card app only computes. -O2 is GCC-KNC's safe default (open -O3 ICEs). |
| D2 | No CMake on the laptop: a hand-written Makefile plus a checked-in config header replaces upstream's CMake for both builds. | Only compilers present: GCC-KNC (k1om) and Cygwin g++ (x86). |
| D3 | x86 reference = same sources built with Cygwin g++ (SSE2 double). | Same code, other ISA: the comparison isolates the compiler and FP model. |
| D4 | Host wrapper = Windows exe built with Cygwin g++ and the BOINC API library. Sprint 2 starts with a spike on whether the BOINC API built this way uses the Win32 shared-memory protocol the Windows client expects. If not, the fallback is a portable MinGW-w64 toolchain, which needs the owner's OK to download. | No MinGW or MSVC on the laptop. |
| D5 | Transport = Windows OpenSSH (`ssh`, `scp`) with the owner's card key from a config file; remote run dir per task under `/tmp/knc-boinc/`; remote PID file; suspend/resume/abort = `kill -STOP/-CONT/-KILL` over ssh. | The stock BOINC wrapper would suspend only the local ssh process. |
| D6 | Progress, checkpoint and snapshot files written by a small patch to the card app; the wrapper polls them (default every 10 s) and relays progress to BOINC. | Standalone build has no BOINC API on the card. |
| D7 | Screensaver = our own `knc_nbody_graphics.exe` (Win32 + legacy OpenGL, Cygwin build) reading BOINC graphics shared memory that the wrapper fills from card snapshots. | The 2012 MilkyWay viewer needs GLFW and OpenGL 3.2, neither available here, and was unstable. |
| D8 | Pre-card validation uses the knc-twin skill (owner 2026-11-15): `functional` on the compiled force kernel with recorded inputs and host-reference outputs, `simulate`/`bounds` for a per-core prediction. The real card gives the final whole-program result. | The twin covers functions and loops, not whole programs; the card is shared and often busy. |
| D9 | Card runs: lead only, through GCC-KNC's `tools/card_run` (ledger, card-sharing rules); never during another project's timed job. Correctness runs only, no timing claims except where stated. | Shared card rules. |

## Sprints (one-week cadence compressed: each sprint = plan, build, review, demo, retro note)

| Sprint | Goal | Tickets |
|---|---|---|
| 1 | N-body runs on the card and matches x86 | S1-01 sources, x86 build, sample workunit, compare tool; S1-02 card build and card-run package; S1-03 knc-twin kernel check |
| 2 | One task from the host | S2-01 BOINC API spike (D4); S2-02 `knc_wrapper` with a fake-card test mode; S2-03 `app_info.xml` and package layout |
| 3 | Screensaver | S3-01 card snapshots and wrapper relay to graphics shared memory; S3-02 `knc_nbody_graphics` |
| 4 | End to end and guide | S4-01 lead end-to-end card run (standalone BOINC API mode) and x86 comparison; S4-02 TRY-IT guide |

Each ticket: acceptance written before work, red-then-green where a test can fail first, engineer report in the ticket,
lead review against the acceptance (tests read, doubtful steps rerun), merge, sprint review note in `docs/sprints/`.

## Risks

- N-body is chaotic: card and x86 results may drift apart on long runs. Sprint 1 measures drift against run length
  and sets the tolerance from MilkyWay's own validator rule, not from our result.
- BOINC API under Cygwin (D4) may not interoperate with the Windows client: the spike decides early.
- Card availability: card steps wait for free turns; knc-twin covers the kernel meanwhile.
- MilkyWay's real workunits carry parameters chosen by the server; the guide's offline check uses a sample workunit from
  the upstream test suite.
