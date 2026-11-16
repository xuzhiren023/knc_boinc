# knc-twin timing_prediction: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T13:19:48Z
- Profile multicore-assumed v1 (hash c6fec8a100f7...)
- Calibration: unvalidated. Low-core scaling and independent full-card validation pending.
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-06\twin\multicore\unit.json (sha256 64e66c18e6e9...)
- Scale: unit; representation: normalized-records
- Functional check: mismatch (6 mismatches)

**candidate produced wrong results (6 mismatches); its timing is not reported as a valid result**

Details: `{"first": {"got": "69ab9aa33d856240", "want": "6aab9aa33d856240", "where": "mem[0x60008000]+8"}}`

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py simulate twin/multicore/unit.json --scale unit --profile card-7120-measured --max-steps 2000000 --max-seconds 1740 --no-issue-log --out twin/multicore/unit --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-06\twin\multicore\unit
Python execution time: 133.955 s (not KNC time)
