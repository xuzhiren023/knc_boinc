# knc-twin timing_prediction: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T16:43:10Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-0.json (sha256 479600c55bb6...)
- Scale: core; representation: normalized-records
- Functional check: mismatch (2 mismatches)

**candidate produced wrong results (2 mismatches); its timing is not reported as a valid result**

Details: `{"first": {"got": "d28d437ec0994740", "want": "d18d437ec0994740", "where": "mem[0x60000020]+16"}}`

## Assumptions
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py simulate twin/vector/scalar-0.json --max-steps 2000000 --max-seconds 900 --profile card-7120-measured --no-issue-log --out twin/vector/scalar-0-simulate --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-0-simulate
Python execution time: 70.584 s (not KNC time)
