# Engineer rules (Codex sessions)

You implement one ticket from `work/tickets/`. The ticket is the only channel to the lead.

- Work only inside this repository (C:/Users/xuzhi/Documents/knc-boinc). Read-only: the GCC-KNC toolchain at
  C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/ and the knc-twin skill at C:/Users/xuzhi/.claude/skills/knc-twin/.
  Never write to the gcc_knc repository.
- You work in the ticket's worktree (`.work/<ID>`, branch `ticket/<ID>`, made by the lead). The sandbox cannot write
  `.git`, so do not commit: leave your changes in the work tree; the lead reviews the diff and commits it.
- No card access: you have no card key. Leave card binaries and a run script; the lead runs the card.
- Downloads: only the pinned upstream sources named in a ticket, through `scripts/fetch.sh`. No other downloads or installs.
- Tests: write the acceptance test first and run it failing when a test can fail first (paste that failing output in
  your report); then make it pass.
  Keep tests proportionate: one test per acceptance point, no duplicates.
- Toolchain (bash, Git for Windows): card compiler `C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-{gcc,g++}`,
  binutils `.../toolchain/cross/bin/k1om-mpss-linux-*`, Cygwin x86 g++ `.../toolchain/cygwin/bin/g++` (prepend
  `.../toolchain/cygwin/bin` to PATH). Card runtimes to ship: `.../gcc-knc-16.2.0/k1om-mpss-linux/lib64/`.
  GCC-KNC docs: `gcc_knc/docs/USING.md`. No CMake, MinGW or MSVC on this laptop.
- Finish by appending `## Engineer report` to the ticket: what you did, how to rerun the tests, what is not proven,
  questions.
- Speed work (owner 2026-11-16): a gain the compiler could make (vectorization, scheduling, vector math, prefetch,
  scalar double off x87) belongs in GCC-KNC: report it in your Engineer report with a reduced repro and the
  `-fopt-info-vec-missed` or knc-twin evidence; the lead files it as a GCC-KNC ticket. What is outside the
  compiler's control (algorithm, data layout, bit-exact ordering, exact-fallback logic) you write by hand with IMCI
  intrinsics or vector code in our patches.
