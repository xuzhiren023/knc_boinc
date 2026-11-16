# knc-twin functional: UNSUPPORTED

- Engine 0.3.1, 2026-11-16T06:09:51Z
- Scale: region; representation: None
- Functional check: not_run

**streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})**

Details: `{"callee": "fprintf", "instruction": "a42f4b2"}`

## Unsupported / not modeled
- streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {"cycles": N, "model": ...})

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/kernel.json --out twin/functional --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-04\twin\functional
Python execution time: 0.091 s (not KNC time)
