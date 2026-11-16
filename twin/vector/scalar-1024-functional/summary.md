# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T16:46:38Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-1024.json (sha256 cbbbf1fc5efe...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (2 mismatches)

**2 mismatch(es) against expected outputs; first: {"where": "mem[0x60000000]+8", "got": "69ab9aa33d856240", "want": "6aab9aa33d856240"}**

## Assumptions
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/vector/scalar-1024.json --max-steps 2000000 --max-seconds 900 --trace --out twin/vector/scalar-1024-functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\scalar-1024-functional
Python execution time: 41.422 s (not KNC time)
