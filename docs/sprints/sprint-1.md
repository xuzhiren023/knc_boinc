# Sprint 1 review: card build, x86 agreement on the card

Card run: 2026-11-16, 13:51-14:19Z, inside gcc-knc card turn `claude-turn-s14-w11-20261116T132450`, Xeon Phi 7120
at 192.168.1.100. Binary and package from `.work/S1-04` (`dist/card/`), compared with the x86 references in
`.work/S1-04/runs/x86/` by `scripts/compare.py` (pass: likelihood |diff| < 1e-10, upstream rule).

| Job | Threads | Card wall time | Likelihood (card) | vs x86 |
|---|---:|---:|---|---|
| libm probe (20,776 rows) | 1 | 44 s | n/a | crlibm 6,272/6,272 rows bit-identical; system libm differs in 1,825 rows |
| small (64 bodies) | 240 | 336 s | -438.53479019222766 | identical, histogram identical |
| medium (1,024 bodies) | 240 | 1,225 s | -450.77212158403989 | identical |
| large (20,000 bodies, 0.05 Gyr) | 240 | 61 s | -4894.200373110275 | identical |

Wall times include card_run staging (about 15 s). Skipped for time: small at 60 threads, end-to-end run (S4-01).

## Findings

- **Numerics.** GCC-KNC's card build gives bit-identical likelihoods to the x86 build on all three cases. crlibm
  (upstream default) plus the 53-bit x87 control word is what makes this hold; the system libm would not:
  card glibc 2.21 vs Cygwin differ in sin/cos/tan for huge arguments (x87 range) and in pow (up to 318 ULP).
  The N-body app takes its math from crlibm.
- **Speed depends on body count, through the app's OpenMP chunk.** `nbody_grav.c` uses
  `schedule(dynamic, 4096 / sizeof(accels[0]))` = 128 bodies per chunk (S1-06). Small has 1 chunk, medium 8, large
  157, so at 240 threads only 1, 8 and 157 threads compute forces. Laptop x86 for comparison: small 52 s (1 thread),
  medium 672 s (1) / 291 s (4), large 222 s (1) / 27 s (12). Medium is slower on the card than on one laptop core;
  large, the size of real MilkyWay tasks, is 3.6x faster than one laptop core. A smaller chunk for KNC would not
  change results (forces per body are independent) and is a candidate patch.
- **Card admission.** Plain card_run jobs are refused while another project has a live queue row, even inside an
  open turn; within a granted turn, use `--benchmark` (exclusive). The end-to-end script and the printed card
  commands need the same, and the end-to-end script's ssh must use card_run's known_hosts
  (`gcc_knc/.work/_state/card/known_hosts`): `~/.ssh/known_hosts` holds an old key for the card.
