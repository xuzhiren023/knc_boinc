# knc-twin functional: OK

- Engine 0.4.0, 2026-11-16T17:18:27Z
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S6-03\twin\vector\vector-2048.json (sha256 20d2882882f7...)
- Scale: region; representation: normalized-records
- Functional check: ok

**executed 705562 dynamic instructions; all 9 expected items match**

## Result
- dynamic_instructions: 705562
- contexts: 1
- functional_check_status: ok
- checked_items: 9
- mismatches: 0

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- vcvtpd2ps writes 8 floats to the low lanes and zeroes the upper 8 (assumed)
- vrsqrt23ps is approximate on the hardware (R27 gives a relative-error bound, not the bit pattern); the twin substitutes the correctly rounded value, so values that depend on its exact bits are not bit-exact (calibration plan: capture the hardware table)
- vcvtfxpntpd2dq/udq write the 8 results to the low lanes and zero the upper 8 (assumed)
- vrcp23ps is approximate on the hardware (R27 gives a relative-error bound, not the bit pattern); the twin substitutes the correctly rounded value, so values that depend on its exact bits are not bit-exact (calibration plan: capture the hardware table)
- out-of-range or NaN double-to-int conversion produced the x86 integer indefinite; KNC-specific value not verified
- ZF/SF after imul are architecturally undefined; the model leaves them unchanged

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/vector/vector-2048.json --max-steps 2000000 --max-seconds 900 --trace --out twin/vector/vector-2048-functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S6-03\twin\vector\vector-2048-functional
Python execution time: 82.920 s (not KNC time)
