"""Generate the current multicore finding from compact, independently checked evidence."""
import json
from pathlib import Path
root=Path('twin/multicore')
isolation=json.loads((root/'isolation.json').read_text())
chunk=json.loads((root/'chunk-evidence.json').read_text())
full=json.loads((root/'full-chunk-attempt.json').read_text())
assert all(full['runs'][n]['status']=='budget_exhausted' for n in ('baseline','unit','ring'))
assert all(chunk['runs'][n]['status']=='functional_mismatch' for n in ('baseline','unit','ring'))
assert all(chunk['runs'][n]['status']=='incompatible' for n in ('compare-unit','compare-ring'))
lines=['The twin is the odd one out: all six bodies still differ alone at core scale, while native x87 at 53-bit precision matches the x86 SSE reference exactly.',
'', '# S1-07 gravity arithmetic and compiled chunk driver', '',
'knc-twin 0.4.0 remains unchanged. The cause is **double rounding** in `_x87_binop`: it first rounds to the 64-bit F80 significand, then converts to F80_P53. The code comment claiming that this is innocuous is incorrect (64 is less than 2*53+2). This is a core arithmetic defect, rather than evidence of a multi-core defect.', '',
'The card likelihood must match x86 within 1e-10. A real x87-versus-SSE difference would matter to that requirement, but none is observed in these 18 native components. This does not prove whole-run likelihood agreement or card behavior; the lead still needs the card comparison.', '',
'## First differing operation', '',
'For body 1024, arithmetic operation 3460 (zero-based ordinal 3459), binary instruction `0x404fd1` / `fmul`, is the first arithmetic result that differs from a native replay of the same operands in the same order. All preceding arithmetic results match. The exact binary64 operands are `0xbf3982440b271580` and `0x3fc697fb0ebad540`. The twin returns `0xbf1202b59a43239e`; native x87 with control word `0x027f` returns `0xbf1202b59a43239f`. The exact product minus the midpoint between these adjacent doubles is `-48721223/81129638414606681695789005144064`, so the native result is closer. Rounding first to 64 bits lands exactly on the binary64 midpoint (asserted by the checker), erasing that distinction.', '',
'`twin/x87-rounding-repro.json` reduces this to a load, multiply, store and return. Its independent native expected value is preserved; `functional` returns `functional_mismatch`. No instruction or expected result in the real gravity region was rewritten. The skill/toolchain copies outside this repository were only read.', '',
'## Isolation and native checks', '',
'`twin/isolate_multicore.sh` reuses `prepare_multicore.py` and runs each requested body at `--scale core`, one context, with `card-7120-measured`. A read-only Interpreter subclass records every arithmetic operation from the unchanged model. `x87_oracle.c`, compiled with `-mfpmath=387`, executes those operations with PC=53; every operand is checked for exact binary64 representability. The audit includes square roots. Differences after the first one use the twin path operands; they are not claimed to be an independent end-to-end native trajectory.', '',
'An independent end-to-end check builds the actual pinned `nbody_grav.c` source with the common host flags plus `-mfpmath=387`. The remaining app objects, tree construction, seed and first force step stay those of the x86 reference. `x87_capture.h` sets `0x027f`. All 18 XYZ output components for the six bodies match the SSE capture bit for bit. This second check resolves whether the SSE reference is the odd one out.', '',
'| Body | Isolated core status | Arithmetic operations audited | First differing instruction | Native-operation differences |',
'|---|---|---:|---|---:|']
for run in isolation['core_runs']:
    first=run['operation_differences'][0]
    lines.append('| %d | %s | %d | `%s` / `%s` | %d |'%(run['body'],run['status'],run['arithmetic_operations_checked'],first['id'],first['instruction'],len(run['operation_differences'])))
lines += ['', 'The six final differing components are the same as S1-06, including the eight-ULP Z difference at body 1408; the other five are one ULP. The tickets 1-ULP description does not cover every component.', '',
'The card likelihood must match x86 within `1e-10`. These host checks find no x87-PC53 versus SSE difference for the six bodies, so they do **not** demonstrate a card/x86 numerical incompatibility. They do not prove the final card likelihood: there is no card access, and repeated force steps and likelihood accumulation remain untested on hardware.', '',
'## Compiled 128-body driver and remaining blockers', '',
'`gravity_chunk.c` calls the real `nbGravity` on each contiguous body in order. `chunk.mk` compiles it with the same GCC-KNC common flags and `-march=knc`, and links it with the card app objects. `objcopy --globalize-symbol=nbGravity` acts on a new copy of the gravity object, changing symbol visibility only. The original object is untouched. `from_binary.py --function nbGravityChunk --with-callee nbGravity` extracts the linked driver and callee: 253 full records, 249 after the S1-05 cold-error cut/sentinel. The compiled loop, calls, returns, output stores and all normal gravity instructions remain.', '',
'The callee comparison checks every retained record against the app extraction after stripping adapter label namespaces. One linker relocation moves the single-precision constant from 5018460 to 5018716; its four initialized bytes are checked equal. The executed records retain the linkers addresses. There is no hot instruction rewriting, OpenMP stub or source-level gravity replacement.', '',
'The actual OpenMP schedule is `dynamic, 4096 / sizeof(accels[0])`: 32-byte vectors give 128-body chunks, 157 chunks for 20,000 bodies, with a final 32-body chunk. Each context starts a distinct chunk at 0,128,...,3968. The compiled-driver baseline is now **unit 1 core x 4 contexts**, candidates are **unit 8 x 4** and **ring 8 x 4**. Input snapshots and independent expected XYZ bytes come from the reused `capture_multicore.sh` / `prepare_multicore.py` tooling; expected vector padding is excluded.', '',
'All three configured 128-body/context smoke attempts stopped with `budget_exhausted` in their deliberately short 60-second engine budgets. These are partial execution, not completed chunk results and not evidence that a chunk took more than 30 minutes. No 30-minute timeout fallback or complete 128-body run is claimed. A two-body/context diagnostic then exercises the compiled callers repetition with equal work per context in all configurations. It is only a diagnostic, not a substitute for the requested 128-body experiment. The unresolved arithmetic defect blocks a valid scaling conclusion even if a longer run finishes.', '',
'| Configuration | 128-body smoke status | Two-body/context diagnostic status |',
'|---|---|---|']
for name in ('baseline','unit','ring'):
    lines.append('| %s | %s | %s |'%(name,full['runs'][name]['status'],chunk['runs'][name]['status']))
lines += ['',
'The two-body baseline differs at body 1 Z: got `0x404799c07e438dd2`, expected `0x404799c07e438dd1`. This output is a prefix of the 128-body chunk and is not overwritten by later calls, so the full chunk cannot pass the unchanged exact functional check. Spending the full 30-minute budget cannot resolve this known correctness blocker.', '',
'No relative change in cycles per body is available. No timing from a mismatching or partial run is reported. After the arithmetic fix, `compare` still needs an equal-per-context comparison policy: it rejects actual aggregate work counts 8 versus 64 (512 versus 4096 for full chunks), and unit versus ring scales. The unit baseline fixes the profile-hash difference, but does not remove these checks. No envelope, hash or work count was altered to bypass them.', '',
'`tests/test_twin_multicore.py` keeps the 128-body scaling acceptance as an expected failure named `test_128_body_scaling_blocked_by_twin_x87_double_rounding`. The isolation/document and artifact-ignore acceptance checks pass. The full experiment remains incomplete; main has no unexpected failing test.', '',
'Every successful diagnostic timing output is an `unvalidated_scenario_estimate`. Only eight detailed cores execute instructions; the other 52 active cores in ring scale supply synthetic background traffic. S1-05 gravity bounds **43,656** above simulate **33,622** remain an open twin defect, so only simulate/compare are used here. Absolute cycles are not a scaling finding. L2 miss, ring/memory processor-stall share and a valid 1-to-8-core ratio are unavailable for the requested experiment. Queue wait totals cannot be relabeled as processor stall shares.', '',
'## Reproduce and card handoff', '',
'From Git Bash with the pinned sources already present:', '',
'```bash', 'mkdir -p build/tmp',
'export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"',
'bash twin/capture_multicore.sh # builds mk/Makefile card and x86 first',
'bash twin/replay_x87.sh > build/s1-07-x87.log 2>&1',
'bash twin/isolate_multicore.sh > build/s1-07-isolation.log 2>&1 # expected repro mismatch',
'python twin/check_x87_replay.py',
'CHUNK_MAX_SECONDS=60 bash twin/run_chunks.sh 128 > build/s1-07-chunks128.log 2>&1',
'python twin/summarize_chunks.py full-chunk-attempt.json',
'bash twin/run_chunks.sh 2 > build/s1-07-chunks2.log 2>&1 # retains failures',
'python twin/summarize_chunks.py chunk-evidence.json',
'python twin/write_s1_07_report.py', 'python tests/test_twin_multicore.py',
'```', '',
'`run_chunks.sh` defaults to 128 bodies/context and 1,740 seconds per engine run, with an external 1,790-second timeout. `CHUNK_MAX_SECONDS` may shorten that budget but cannot exceed 1,740. Completed diagnostics stayed below 30 minutes. Capture/node blocks, full kernels, traces and large per-body/chunk envelopes remain ignored; compact evidence is tracked.', '',
'The rebuilt app and runtimes are in `dist/card`; the linked driver ELF is `build/gravity_chunk.mic` (its normal entry still runs the app; the driver symbol is the twin entry). `scripts/multicore-card-commands.sh` prints the S1-04 large 60/240-thread commands, also saved as `dist/card/multicore-commands.sh`. The lead runs these later. Compare repeated force-phase timings and likelihoods, and collect hardware counters for attribution; whole-program elapsed time does not validate this region.', '',
'## Exact result metadata', '',
'Compact evidence is in `twin/multicore/isolation.json`, `full-chunk-attempt.json` and `chunk-evidence.json`. Fields below are copied from diagnostic envelopes; only assumed/derived `parameters_used` entries are retained. An absent result_class stays null. Failed envelopes provide no timing prediction.', '', '```json']
metadata={name:{key:run.get(key) for key in ('status','assumptions','unsupported','limiting_constraints','calibration_status','result_class','parameters_used')} for name,run in chunk['runs'].items()}
lines += [json.dumps(metadata,indent=2),'```','']
Path('docs/twin-multicore.md').write_text('\n'.join(lines))
print('Wrote docs/twin-multicore.md; scaling remains explicitly blocked')
