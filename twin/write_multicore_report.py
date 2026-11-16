"""Publish only ok diagnostic predictions; preserve refusals as findings."""
import json
from pathlib import Path
root=Path('twin/multicore')
def load(name):
    path=root/name/'result.json'
    if not path.exists():
        return {'status':'no_result', 'message':'No result envelope: command did not finish; no prediction available'}
    return json.loads(path.read_text())
lines=['# S1-06: large-case gravity multi-core check', '',
'**Incomplete: no supported 128-body/context scaling result.** The question whether gravity retains its per-core speed from one to eight cores remains unanswered. The runs below are explicitly one-body diagnostics, not the requested slice experiment. All successful timing outputs have result class `unvalidated_scenario_estimate`. No card run or card speed claim is made.', '',
'## Work and captured inputs', '',
'The actual loop in `nbody/src/nbody_grav.c` has `schedule(dynamic, 4096 / sizeof(accels[0]))`. The verified x86/card `mwvector` size is 32 bytes, so each dynamically acquired contiguous chunk contains 128 bodies (the final chunk has 32). At 20,000 bodies there are 157 chunks, not 240 nonempty thread slices. Chunk ownership at 240 threads is runtime dependent; it is not a static `20000/240` partition. The target experiment would give each of the 4 or 32 contexts a distinct full 128-body chunk, maintaining that size in all configurations.', '',
'`twin/capture_multicore.sh` extends the S1-03 prepare_capture.py/capture_log.c host instrumentation without changing pinned upstream code or card code. It snapshots the first force step of the actual large workunit at seed 670828913 with one x86 thread: ctx, state, eps2, all 20,000 bodies, and every reachable threaded-tree node. Raw bytes are init.memory file blocks with their original pointer addresses. Offset node blocks are repacked into small files with byte equality checks, avoiding repeated whole-file hashing by the unchanged loader. Expected XYZ accelerations for the first 4,096 bodies are independently written by the host; unspecified vector w is excluded. `capture-summary.json` records layout agreement and zero tree-incest diagnostics. Full generated captures and kernels are ignored.', '',
'The application was rebuilt from unchanged sources/flags first with `mk/Makefile` for card and x86, exporting TMPDIR, TMP and TEMP to `$PWD/build/tmp` before compiling. The rebuilt card app and the unchanged S1-05 `nbGravity` region are reused: all 202 binary records are retained, followed by the same cold-error exit sentinel. The normal return and output stores remain. No arithmetic, dependency, encoding, stub or model parameter is changed. `twin/run.sh` and `twin/cut_gravity.py` regenerate/check the region.', '',
'## Why the requested result is unavailable', '',
'1. The S1-05 region is a single nbGravity call (one body), with no caller loop over bodies. The supported input format offers no sequence of independently initialized function calls in a stream. Replacing it with a hand-written loop or multiplying a cold single-body time by 128 would not preserve the requested binary region and cache history. The binary caller nbMapForceBody._omp_fn.0 calls GOMP_loop_nonmonotonic_dynamic_start/next; retaining it requires OpenMP runtime modeling (unit/ring rejects stubs and synchronization). A faithful compiled body-loop driver or engine support for repeated calls with per-call arguments is needed.',
'2. The actual sample-loop probe returns `unsupported`: "loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled". The region\'s loop iterates tree nodes, not bodies. Unit/ring dispatch also bypasses the core sampler; adding --sample-loop cannot be taken as proof of sampled multi-core execution.',
'3. The requested compare commands reject core versus unit/ring. Compare requires equal scale, profile hash and unit_of_work. Unit/ring automatically loads multicore-assumed.json, so even the same named card-7120-measured profile yields a different hash from core. The 4 versus 32 total bodies also gives different aggregate work counts. No result envelope has been rewritten to bypass these checks.', '',
'4. Unit/ring diagnostics fail exact functional comparison against the independent x86 capture. The first difference is body 1024 Y: got 0x4062853da39aab69 versus expected 0x4062853da39aab6a. Six components differ across the 32 bodies. This does not establish a model or compiler defect: no card result or instruction-level native oracle is available. No tolerance, kernel, or expected bits were changed; no timing from a functional_mismatch run is reported.', '', '## Diagnostic commands and table', '',
'`bash twin/run_multicore.sh` executes simulate at core (1 x 4), unit (8 x 4) and ring (8 x 4), always with card-7120-measured, functional traces, cold-memory line tracking and all-predicted branches. Each context computes only the first body of its assigned 128-body chunk: body indices 0, 128, ..., 3968 (baseline uses the first four). Thus the runs have equal **one-body** work per context, and do not measure chunk reuse or a steady-state tree footprint. They are not sample-loop extrapolations. Runs have a 1,740-second engine budget, below 30 minutes. An external 1,790-second timeout also caps each simulation process, including initialization. The complete command output is in the Engineer report and `twin/multicore/run.log`.', '',
'Per-context cycles/body below use each context\'s completion field when exposed; the per-core completion envelope is also reported. The engine\'s aggregate predicted_cycles_per_unit divides by all detailed bodies and is **not** per-context latency. L2 miss fraction is `memory / (l2_hits + memory)` from the reported access-level counters (not an independently measured cache-line miss rate). Ring and memory queue waits are not mutually exclusive processor stall-cycle counters and cannot be summed into a stall share.', '',
'| Diagnostic | Status | Context completion cycles/body (range; exact values below) | Per-core completion envelope | L2 miss fraction | Ring/memory stall share |',
'|---|---|---|---|---|---|']
for name in ('core','unit','ring'):
    r=load(name)
    if r['status']!='ok':
        lines.append('| %s | %s | unavailable | unavailable | unavailable | unavailable |'%(name,r['status']))
        continue
    p=r['prediction']; rows=p.get('cores',[p]); stats=[x['memory']['stats'] for x in rows]
    miss=sum(x['memory'] for x in stats); hits=sum(x['l2_hits'] for x in stats)
    cycles=[x.get('completion_cycles',x.get('predicted_cycles')) for x in rows]
    completions = [c['completion'] for row in rows for c in row['per_context'].values()]
    lines.append('| %s (one body/context) | ok | %s..%s | %s | %.6f | unavailable: no separated share in result.json |'%(name,min(completions),max(completions),', '.join(str(x) for x in cycles),miss/(miss+hits)))
lines+=['', 'These diagnostics do not establish a 1-to-8-core change for 128-body slices. No absolute cycle prediction above is a card-speed finding. S1-05 found gravity bounds **43,656** above simulate **33,622** on the same kernel: an open twin defect. Only simulate and compare are used for this multi-core investigation; bounds is not used as a timing interval. Even after the blockers are fixed, report the relative change from one to eight cores, with this caveat.', '', '## Exact result evidence', '']
for name in ('core','unit','ring','compare-unit','compare-ring','sample-blocker'):
    r=load(name)
    p=r.get('prediction') or {}
    detail={k:r.get(k) for k in ('status','message','python_execution_seconds','functional_check','assumptions','unsupported','limiting_constraints','calibration_status')}
    detail['result_class']=p.get('result_class')
    detail['parameters_used']={k:v for k,v in (r.get('parameters_used') or {}).items() if v.get('status') in ('assumed','derived')}
    if 'incompatibilities' in r: detail['incompatibilities']=r['incompatibilities']
    if r['status']=='ok':
        detail['per_context']={str(row.get('core',0)):row.get('per_context') for row in p.get('cores',[p])}
        detail['memory']=p.get('memory')
        detail['background']=p.get('background')
    lines+=['### '+name,'','```json',json.dumps(detail,indent=2,ensure_ascii=True),'```','']
lines+=['## What is not modeled and what the card can check', '',
'Only eight cores execute detailed instructions in unit/ring. Ring defaults to 60 total active cores: the remaining **52** generate synthetic previous-epoch traffic; they do not walk the tree or compute accelerations. Unit has no synthetic background. The 61-position contracted ring geometry, physical-address surrogates, TD/channel maps, service parameters and symmetry feedback are assumptions or derived quantities, not recovered hardware wiring. Placement/epoch sensitivity is pending. Private inclusive LRU caches are approximations. Banks, refresh, turnaround, OS behavior, OpenMP scheduling/barriers, synchronization and the rest of the program are outside this region. A first-body cold start cannot represent warm per-chunk reuse.', '',
'The lead can check the large workunit at **60 vs 240 threads** using the S1-04 runner/launch pattern. `bash scripts/multicore-card-commands.sh` prints both commands; `dist/card/multicore-commands.sh` contains the handoff. It stages the app and runtimes and writes receipts/output under runs/card. No card invocation is used here. Compare numerical results and repeated elapsed timings. Whole-program timing includes other phases; validating gravity cycles or stall attribution requires force-phase timing and hardware counters. Record actual dynamic chunk distribution, since there are only 157 chunks.', '',
'## Reproduction', '', '```bash',
'bash twin/capture_multicore.sh',
'bash scripts/run_x86.sh large 1',
'bash scripts/run_x86.sh small 1',
'bash twin/run.sh',
'bash twin/run_multicore.sh  # nonzero: compare refusals are findings',
'python twin/write_multicore_report.py',
'python tests/test_twin_multicore.py  # remains failing until slices/compare supported',
'bash scripts/multicore-card-commands.sh  # print only',
'```', '',
'No downloads, installs, git writes or shared-toolchain/skill edits are needed. The Engineer report records the remaining acceptance failure; successful diagnostics do not waive it.', '']
Path('docs/twin-multicore.md').write_text('\n'.join(lines))
