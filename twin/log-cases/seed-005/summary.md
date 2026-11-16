# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T12:48:52Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-cases\seed-005.json (sha256 25483b2438d9...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 138 dynamic instructions; all 1 expected items match**

## Result
- dynamic_instructions: 138
- contexts: 1
- functional_check_status: ok
- checked_items: 1
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged

Invocation: `C:\Users\xuzhi\.claude\skills\knc-twin\scripts\knc_twin.py functional twin\log-cases\seed-005.json --trace --out twin\log-cases\seed-005 --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-cases\seed-005
Python execution time: 1.194 s (not KNC time)
