# knc-twin functional: FUNCTIONAL_MISMATCH

- Engine 0.4.0, 2026-11-16T13:41:44Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-07\twin\x87-rounding-repro.json (sha256 2873f9b957ac...)
- Scale: region; representation: normalized-records
- Functional check: mismatch (1 mismatches)

**1 mismatch(es) against expected outputs; first: {"where": "mem[0x2000][0]", "got": "0xbf1202b59a43239e", "want": "0xbf1202b59a43239f"}**

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/x87-rounding-repro.json --out twin/x87-rounding-repro --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-07\twin\x87-rounding-repro
Python execution time: 0.013 s (not KNC time)
