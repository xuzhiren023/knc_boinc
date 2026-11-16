# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T16:42:01Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-0.json (sha256 479600c55bb6...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (2 mismatches)

**2 mismatch(es) against expected outputs; first: {"where": "mem[0x60000020]+16", "got": "d28d437ec0994740", "want": "d18d437ec0994740"}**

## Assumptions
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/vector/scalar-0.json --max-steps 2000000 --max-seconds 900 --trace --out twin/vector/scalar-0-functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-0-functional
Python execution time: 68.674 s (not KNC time)
