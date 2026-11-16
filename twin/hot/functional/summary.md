# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T12:49:00Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-kernel.json (sha256 67c25b73695e...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 136 dynamic instructions; all 1 expected items match**

## Result
- dynamic_instructions: 136
- contexts: 1
- functional_check_status: ok
- checked_items: 1
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/log-kernel.json --out twin/hot/functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\hot\functional
Python execution time: 0.858 s (not KNC time)
