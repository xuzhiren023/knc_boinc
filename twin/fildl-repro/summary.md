# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T12:53:24Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\fildl-repro.json (sha256 7a7dbe845ae4...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 4 dynamic instructions; all 1 expected items match**

## Result
- dynamic_instructions: 4
- contexts: 1
- functional_check_status: ok
- checked_items: 1
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/fildl-repro.json --trace --out twin/fildl-repro --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\fildl-repro
Python execution time: 0.007 s (not KNC time)
