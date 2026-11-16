# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T16:44:22Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\vector-1024.json (sha256 65e0c61d5213...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 654829 dynamic instructions; all 9 expected items match**

## Result
- dynamic_instructions: 654829
- contexts: 1
- functional_check_status: ok
- checked_items: 9
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/vector/vector-1024.json --max-steps 2000000 --max-seconds 900 --trace --out twin/vector/vector-1024-functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-01\twin\vector\vector-1024-functional
Python execution time: 80.089 s (not KNC time)
