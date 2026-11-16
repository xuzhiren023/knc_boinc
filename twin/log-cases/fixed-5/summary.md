# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.3.1, 2026-11-16T06:14:11Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\log-cases\fixed-5.json (sha256 7ad5d3dd4781...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "ctx0.zmm0[0]", "got": "0x43c625e80668ab5c", "want": "0x4085963447f87fb5"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:\Users\xuzhi\.claude\skills\knc-twin\scripts\knc_twin.py functional twin\log-cases\fixed-5.json --trace --out twin\log-cases\fixed-5 --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\log-cases\fixed-5
Python execution time: 1.882 s (not KNC time)
