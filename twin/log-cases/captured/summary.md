# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T12:48:58Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-cases\captured.json (sha256 0f311071ff24...)
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

Invocation: `C:\Users\xuzhi\.claude\skills\knc-twin\scripts\knc_twin.py functional twin\log-cases\captured.json --trace --out twin\log-cases\captured --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-cases\captured
Python execution time: 0.949 s (not KNC time)
