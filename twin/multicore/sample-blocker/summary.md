# knc-twin timing_prediction: UNSUPPORTED

- Engine 0.4.0, 2026-11-16T13:08:45Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-06\twin\multicore\core.json (sha256 6ebdddecd11d...)
- Scale: core; representation: normalized-records
- Functional check: not_run

**loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled**

## Unsupported / not modeled
- loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py sample-loop twin/multicore/core.json --scale core --profile card-7120-measured --loop .A_404ef5 --max-seconds 60 --out twin/multicore/sample-blocker --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-06\twin\multicore\sample-blocker
Python execution time: 0.289 s (not KNC time)
