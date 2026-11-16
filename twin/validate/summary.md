# knc-twin validation: UNSUPPORTED

- Engine 0.3.1, 2026-11-16T05:39:28Z
- Functional check: not_run

**streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})**

Details: `{"callee": "sqrt", "instruction": "a405216"}`

## Unsupported / not modeled
- streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py validate twin/kernel.json --profile card-7120-measured --out twin/validate --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-03\twin\validate
Python execution time: 0.074 s (not KNC time)
