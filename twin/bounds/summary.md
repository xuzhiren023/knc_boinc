# knc-twin analytical_bound: UNSUPPORTED

- Engine 0.3.1, 2026-11-16T05:39:30Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Scale: core; representation: None
- Functional check: not_run

**streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})**

Details: `{"callee": "sqrt", "instruction": "a405216"}`

## Unsupported / not modeled
- streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py bounds twin/kernel.json --profile card-7120-measured --out twin/bounds --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-03\twin\bounds
Python execution time: 0.073 s (not KNC time)
