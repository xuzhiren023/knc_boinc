# How we optimize for the card: GCC-KNC, knc-optimize and knc-twin together

Owner decision 2026-11-16: any gain the compiler could make goes into GCC-KNC; what is outside the compiler's control
is written by hand (IMCI intrinsics or vector code) in our patches, by Codex engineers.

| Tool | Role |
|---|---|
| knc-optimize skill | Method: measure, model, dominant term, matching practices, card check, stop rule |
| GCC-KNC | Makes the candidate builds (flags, pragmas, vectorization, prefetch) and keeps the FP contract (`-ffp-contract=off`, x87 PC=53, correctly rounded vector div/sqrt) |
| knc-twin skill | Reads the GCC-KNC binary (`from_binary`) and predicts cycles and the binding constraint per variant: one core (4 contexts) for compute regions, 8-tile ring for miss- or ring-bound regions (multicore = unvalidated estimate) |
| Card | Decides anything the twin cannot separate (within ~20%, multicore, whole program) |

Per hot region:
1. Measure on the card (phase timers) and the laptop; write the Model table (`docs/research/`).
2. Split the dominant term into compiler-fixable and not. Compiler-fixable: missed vectorization
   (`-fopt-info-vec-missed`), missing vector math, scheduling, prefetch, x87 for scalar double, spills. Not:
   algorithm, data layout, parallel decomposition, bit-exact ordering, exact-fallback logic.
3. Compiler-fixable: the engineer reports a reduced repro with the compiler report or twin evidence; the lead sends it
   to the GCC-KNC lead as a ticket. The app does not work around it, except as a dated stopgap named in the ticket.
4. Not compiler-fixable: a Codex ticket writes it by hand in `patches/`, rank variants with the twin, then card.
5. Results stay bit-identical to x86 unless the owner accepts a tolerance.
