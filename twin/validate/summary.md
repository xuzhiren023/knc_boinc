# knc-twin validation: UNSUPPORTED

- Engine 0.3.1, 2026-11-16T06:09:50Z
- Functional check: not_run

**streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})**

Details: `{"callee": "fprintf", "instruction": "a42f4b2"}`

## Unsupported / not modeled
- streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py validate twin/kernel.json --profile card-7120-measured --out twin/validate --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\validate
Python execution time: 0.100 s (not KNC time)
