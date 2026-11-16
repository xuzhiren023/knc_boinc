# knc-twin comparison: INCOMPATIBLE

- Engine 0.4.0, 2026-11-16T13:24:14Z
- Input None (sha256 ...)
- Functional check: not_run

**results are not comparable: scale differs: 'core' vs 'unit'; profile hash differs (2058f0ec2d80 vs c6fec8a100f7): the model changed between baseline and candidate; unit of work differs: {'count': 4, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'} vs {'count': 32, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'}; candidate status is functional_mismatch, not ok**

## Assumptions
- candidate functional check: mismatch (its timing stands without a verified result)

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py compare twin/multicore/core/result.json twin/multicore/unit/result.json --out twin/multicore/compare-unit --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-06\twin\multicore\compare-unit
Python execution time: 0.097 s (not KNC time)
