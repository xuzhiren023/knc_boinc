# S8 model: N-body 1.96 on the KNC card vs the laptop (knc-optimize step 2)

Card: 7120, 240 threads, 1.238 GHz; scalar double is x87. Laptop: 6 cores / 12 threads. Numerical contract:
bit-identical likelihood vs x86 (project rule |diff| < 1e-10; all builds so far are bit-identical).
Measured = window 12 (2026-11-16) card phase timers (S8-01) and laptop runs; predicted = model below.

## Large case (20,000 bodies, 110 steps, Plummer)

| Term | Formula / source | T_meas card | T_meas laptop 12 thr | T_pred after change | Assumption |
|---|---|---:|---:|---:|---|
| Tree build (serial) | S8-01 timer, 111 builds | 13.19 s | 1.58 s | 1-2 s (S8-02) | insertion split over >= 64 subtrees; top levels, threadTree serial |
| Force walk | S8-01 timer | 13.00 s | 24.96 s | 13.0 s | unchanged; T_lb pending (interaction count x ~20-25 FP64 ops / peak) |
| Integrators, setup, final | S8-01 timers | 1.5 s | 0.8 s | 1.4 s | static integrator -0.1 s |
| Whole run | | 27.4 s | 26.9 s (21.9 s static build) | ~16 s | |

Serial-thread ratio card/laptop on x87 tree code: 13.19 / 1.11 = 11.9x (one laptop core). Card force is 1.9x the
laptop at 12 threads. Thread sweep (60/120/240) agrees: ~27 s did not shrink with threads.

## Real workunit 117676 (110,000 bodies, mixed dwarf, 1,568 steps)

| Term | Source | T_meas laptop 12 thr | T_pred card today | T_pred card after S8-03 (+S8-02) |
|---|---|---:|---:|---:|
| Body generation (serial) | S7-02 live step samples | ~4,560 s | ~54,000 s (11.9x) | 54,000 x ((1-f) + f/82) |
| Steps | S7-02 | ~920 s | unknown (tree serial) | ~550 s (large-case ratio) |
| Total | | 5,488 s | ~15 h | f = 0.99: ~0.5 h; f = 0.95: ~1.1 h; f = 0.90: ~1.9 h |

f = share of generation spent in `fun` evaluations inside `gauss_quad` (S8-03 measures it on the laptop). 82x =
330 nodes in two waves of 240 threads with each thread at ~half speed at 4 threads per core (assumed), against one
thread. The laptop runs overlapped (not isolated). The 11.9x transfer from tree code to `fun` is an assumption until
S8-04 (knc-twin cycles per `fun`) or a card run of core-small.

## Decision rule tonight (window 12, cap 02:59Z)
Launch 117676 only with a build that beats the laptop on the large case (S8-02) and whose real-task prediction
fits the window with margin (S8-03 f >= ~0.97 and a core-small card check that matches the prediction).
