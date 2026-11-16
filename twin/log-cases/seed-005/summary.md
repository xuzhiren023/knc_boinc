# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.3.1, 2026-11-16T06:14:51Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\log-cases\seed-005.json (sha256 134a767b6de5...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "ctx0.zmm0[0]", "got": "0x43c6271df2cec811", "want": "0xc068f90749b8da98"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:\Users\xuzhi\.claude\skills\knc-twin\scripts\knc_twin.py functional twin\log-cases\seed-005.json --trace --out twin\log-cases\seed-005 --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\log-cases\seed-005
Python execution time: 1.419 s (not KNC time)
