# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T12:52:46Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\kernel.json (sha256 eb85ac709722...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 3040 dynamic instructions; all 1 expected items match**

## Result
- dynamic_instructions: 3040
- contexts: 1
- functional_check_status: ok
- checked_items: 1
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/kernel.json --trace --out twin/functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\functional
Python execution time: 1.217 s (not KNC time)
