# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T16:39:57Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\vector-0.json (sha256 efe8e60f81c8...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "mem[0x60000020]+16", "got": "d28d437ec0994740", "want": "d18d437ec0994740"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/vector/vector-0.json --max-steps 2000000 --max-seconds 900 --trace --out twin/vector/vector-0-functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\vector-0-functional
Python execution time: 73.662 s (not KNC time)
