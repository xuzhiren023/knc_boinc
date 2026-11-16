# knc-twin timing_prediction: UNSUPPORTED

- Engine 0.3.1, 2026-11-16T05:39:29Z
- Scale: core; representation: None
- Functional check: not_run

**streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})**

Details: `{"callee": "sqrt", "instruction": "a405216"}`

## Unsupported / not modeled
- streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py simulate twin/kernel.json --profile card-7120-measured --out twin/simulate --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-03\twin\simulate
Python execution time: 0.079 s (not KNC time)
