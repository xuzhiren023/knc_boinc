# knc-twin analytical_bound: FUNCTIONAL_MISMATCH

- Engine 0.3.1, 2026-11-16T05:44:43Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-03\twin\log-kernel.json (sha256 e70dbe9ca2f6...)
- Scale: core; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**candidate produced wrong results (1 mismatches); its timing is not reported as a valid result**

Details: `{"first": {"got": "0x43c628b76e3a7b61", "want": "0x0000000000000000", "where": "ctx0.zmm0[0]"}}`

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py bounds twin/log-kernel.json --profile card-7120-measured --out twin/hot/bounds --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-03\twin\hot\bounds
Python execution time: 0.546 s (not KNC time)
