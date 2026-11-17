# Real 117676 step benchmark

`params.lua` derives from the captured 117676 Lua in `workunits/117676/`.
As in `core-small`, only three assignments change: `totalBodies = 20000`,
`totalLightBodies = 1818` (approximately the original 1:10 light/dark ratio),
and `evolveTime = 128 * get_timestep() / (2.0 - best_like_start)` immediately
before `revOrbTime` and the original best-likelihood extension. The resulting
forward evolution is 128 steps. The backward orbit is shortened consistently.
The physical timestep, potential (Miyamoto-Nagai disk, Hernquist sphere,
NFW-mass halo), two-component mixed dwarf, LMC settings, fixed internal RNG
seed, likelihood settings and fourteen arguments remain unchanged.

`OCS_data_2025_north_194.hist` is byte-identical to the captured 117676 histogram
also used by `core-small`. The historical comments in that observed histogram
describe its generating model, not this simulation's potential.

Arguments (options must precede the positional parameters):

```text
--seed 65477096 --nthreads 12 --print-histogram --ignore-checkpoint --checkpoint-interval=-1 -np 14 -p 4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 15.623 -215.279 114.242 181.825 353270 1.21041 2.87629
```

See `docs/benchmarks.md` for the benchmark protocol and retained outputs.
`bash scripts/run-real-benchmarks.sh` builds with the release options plus
phase timers and records one run per case/build, sequentially at 12 threads.
It refuses to reuse any run directory. It also runs full 117676 once; do not
rerun it to improve a timing. `python tests/test_real_benchmarks.py` checks
the retained evidence without executing simulations.

`bash scripts/real-benchmark-window.sh` is a lead-only, two-job card window;
it stages the S10-01 release-timers binary and compiler runtimes through this
checkout's `tools/card_run`. It has not been executed by this ticket.
