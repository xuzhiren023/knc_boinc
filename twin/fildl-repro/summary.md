# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.3.1, 2026-11-16T06:15:11Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\fildl-repro.json (sha256 7a7dbe845ae4...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "ctx0.zmm0[0]", "got": "0x43cff80000000000", "want": "0x0000000000000000"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range

Invocation: `C:\Users\xuzhi\.claude\skills\knc-twin\scripts\knc_twin.py functional twin\fildl-repro.json --trace --out twin/fildl-repro --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\fildl-repro
Python execution time: 0.014 s (not KNC time)
