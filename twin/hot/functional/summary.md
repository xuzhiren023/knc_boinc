# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.3.1, 2026-11-16T05:56:52Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\log-kernel.json (sha256 21e6c240e39d...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "ctx0.zmm0[0]", "got": "0x43c628b76e3a7b61", "want": "0x0000000000000000"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/log-kernel.json --out twin/hot/functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\hot\functional
Python execution time: 1.364 s (not KNC time)
