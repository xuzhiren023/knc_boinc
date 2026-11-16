"""S1-04: render evidence and all returned status fields without guessed timing."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name): return json.loads((ROOT/name).read_text())
def fields(name):
    r=read(name)
    keys=('status','result_class','functional_check','assumptions','unsupported','limiting_constraints','calibration_status','parameters_used')
    return '\n'.join('- `'+k+'`: `'+json.dumps(r.get(k,'<absent>'),sort_keys=True)+'`' for k in keys)
d=read('twin/log-diagnosis.json')
first=d['first_divergence']
profile={}
for line in (ROOT/'twin/profile/gprof.txt').read_text().splitlines():
    cols=line.split()
    if len(cols)>=4 and cols[-1] in ('log_rn','pow_rn','nbGravity','_mcount_private','__fentry__'):
        try: float(cols[0]);float(cols[2])
        except ValueError: continue
        profile.setdefault(cols[-1],(cols[0],cols[2]))
# Every distinct dynamically read range and all its byte origins. Full reads
# (including bytes, call case and instruction) stay in log-diagnosis.json.
ranges={}
for row in d['memory_reads']:
    key=(int(row['addr'],16),row['bytes'])
    entry=ranges.setdefault(key,{'sources':set(),'insns':set(),'cases':set(),'sections':set()})
    entry['sources'].update(row['sources']);entry['insns'].add(row['instruction']);entry['cases'].add(row['case'])
    if row['section']:entry['sections'].add(row['section'])
lines=['# Dynamic log_rn / p_accu memory inventory','',
       'All ranges are half-open. Byte-for-byte initialization/store provenance is audited independently of the engine\'s line-granular allocation. Full read values and case identifiers: `log-diagnosis.json`. These are extraction/functional metadata, not cycle results.','',
       '| Range | Read bytes | Section | Origin(s) / instruction(s) |',
       '| --- | ---: | --- | --- |']
for (a,n),entry in sorted(ranges.items()):
    lines.append('| `0x%x..0x%x` | %d | %s | %s; reads: %s |'%(a,a+n,n,', '.join(sorted(entry['sections'])) or 'stack', '; '.join(sorted(entry['sources'])), ', '.join(sorted(entry['insns']))))
(ROOT/'twin/log-memory.md').write_text('\n'.join(lines)+'\n')
refs=[]
for case,threads in [('small',1),('small',4),('medium',1),('medium',4),('large',1),('large',12)]:
    p=ROOT/f'runs/x86/{case}-{threads}'
    r={'case':case,'threads':threads,'kind':'host_reference_after_fno_math_errno'}
    for name in ('exit.txt','seconds.txt','command.txt'):
        r[name]=(p/name).read_text().strip() if (p/name).exists() else None
    r['histogram_present']=(p/'histogram.txt').exists()
    r['histogram_sha256']=hashlib.sha256((p/'histogram.txt').read_bytes()).hexdigest() if r['histogram_present'] else None
    refs.append(r)
(ROOT/'twin/reference-runs.json').write_text(json.dumps(refs,indent=2)+'\n')
s='''# S1-04: logarithm mismatch diagnosis and card handoff

**Verdict: the observed log_rn twin mismatch is a twin ISA/model defect.**
The tables are present and correctly loaded. `fildl` incorrectly reads eight
bytes instead of four. This finding does not prove the card binary is correct;
the native card probe awaits the lead. Gravity still returns `unsupported`,
now for the error routine's `fprintf` call after `sqrt` became inline `fsqrt`.
There is no valid predicted per-call cycle figure or bound for either kernel.

## Input completeness

`twin/log-memory.md` lists every distinct range read across the rerun paths;
`twin/log-diagnosis.json` records **every dynamic read**, its instruction,
input case, byte value, and per-byte initialization/store provenance.
`twin/diagnose_log.py` instruments a read-only import of the unchanged engine.
It rejects reads of any uninitialized byte, including holes within a memory
line (the engine itself checks only whether the line exists). No audited read
is uninitialized. Every `.rodata` read matches the linked card ELF exactly.

The adapter loads the full allocated `.rodata` section as inline hex in
`init.memory[0]`, including crlibm argument-reduction tables and constants;
`init.memory[1]` is the ELF's zero-initialized `.bss`. The table inventory names
the actual accessed offsets; no table is synthesized from host values.
`init.memory[2]` loads `capture/log-input.bin` at `0x60000000`; it is archival
input storage and is not dereferenced by the function. The scalar argument is
the exact captured bits in low zmm0. For generated probe cases only this ABI
argument and the independent expected output change. The entry stack contains
the interpreter's caller-return sentinel, followed by actual stores from the
unaltered prologue/body. Stack reads cite those defining store instructions.
No `memory_default` is used. `p_accu` is included in the complete extraction;
only paths actually executed by the unchanged twin are claimed by this audit,
not all paths that correct hardware could take after the first divergence.
None of these faulty-model executions enters p_accu; it has no dynamic reads
in this run, although its complete compiled body remains included.

## First divergent instruction and minimal repro

'''
s+=f'''For the 1.0 input, dynamic step `{first['step']}` at `{first['id']}` is
`fildl 0x8(%rsp)` (machine bytes `db 44 24 08`). The preceding 64-bit store
put `0x3ff0000000000000` in that slot; the subsequent **32-bit** store of edi
wrote zero into its low four bytes. Earlier state follows the integer
exponent calculation `(0x3ff00000 >> 20) - 1023 = 0`; the snapshots retain all
preceding register/stack results. `fildl` must load the signed low 32-bit
integer **0**, regardless of the old high bytes. The engine's ISA table
assigns it `mem_size=8`, loading **{first['twin_value']}** instead.
This introduces the huge exponent term in the logarithm calculation.
The retained intermediate snapshots are `twin/log-cases/log-one-intermediates.json`.

'''
s+='''The independent Cygwin x86 executable from `probes/fildl_host.c` executes
`fildl` on that same eight-byte slot and returns bits `0x0000000000000000`;
`twin/fildl-host.txt` retains its output. The four-instruction standalone
`twin/fildl-repro.json` has no crlibm dependency: unchanged engine functional
execution returns `functional_mismatch` (`0x43cff80000000000` vs zero).
The engine's integer x87 width table also gives `filds` four bytes rather
than two; that is source inspection, not a separately executed repro.
No shared skill, ISA table, compiler or toolchain file was modified. Forward
the minimal JSON, result/trace, x86 source/output and engine ISA SHA-256 in
`log-diagnosis.json` to the twin owner. DB /0 denotes m32int; floating-point
`fldl` is correctly m64fp and must not receive the integer-width correction.

The full `log_rn`/`p_accu` extraction has no unresolved symbols or undeclared
callees. Its unchanged validate/functional/simulate/bounds reruns are under
`twin/hot/`. The original captured input and all fixed/seeded cases below
were executed with the unchanged engine. Expected bits are from the x86 probe,
never from the twin. Functional bits and instruction counts are **functional
metadata**, not timing predictions. A separate local diagnostic changes only the copied per-instruction fildl
specification from eight bytes to four and reruns the captured log(1.0).
`twin/fildl-width-diagnostic.json` records an exact +0.0 match. This establishes
causality for the original mismatch; it is not an unchanged-engine result or
a timing prediction. The shared engine and the production kernels remain
untouched.

| Probe case | Input bits | Expected x86 log bits | Twin status |
| --- | --- | --- | --- |
'''
for c in d['cases']:s+=f"| {c['case']} | `{c['input_bits']}` | `{c['expected_bits']}` | `{c['status']}` |\n"
s+='''
## Card probe and compare

`probes/libm_probe.c` prints input and output bits for 1.0, 2.0, 0.5,
the nearest double to e, 1e-300, 1e300, the minimum positive subnormal,
384 deterministic seeded finite positive values, and the exact captured log
input. The captured row uses the actual eight-byte file; there was no captured
pow argument pair in S1-03. Other functions are tested on that same scalar plus
the documented fixed binary arguments, not falsely described as captured calls.
The probe includes every linked crlibm family used through milkyway's double
math mappings and the application's linked libm math functions (including
complex sqrt/pow, sincos, exp2/exp10 and hypot). See
`twin/app-undefined-symbols.txt` for the linked libm inventory. Non-math
library dependencies such as fegetround are not numerical result probes.
The row format is `case function input_bits second_argument_bits result_bits`;
frexp/modf put the returned exponent/integer part in the fourth field. For
complex pow the fixed exponent is 1.2345+0.25i and the input is x+0.5i;
real and imaginary outputs get separate rows.

Both targets use `mk/sources.mk` flags, `crlibm_init`/`crlibm_exit`, and link the
**same existing crlibm object files as their respective application**.
`twin/probe-manifest.json` records object/probe hashes and the host row count.
The card executable is `dist/card/libm_probe.mic`, with the app's packaged
compiler runtimes and a successful `dist/card/probe-knc-lint.txt` check.
`scripts/probe-launch.sh` sets the staged runtime path and runs the probe.
`scripts/probe-commands.sh` only prints the card_run/compare commands; its
output is saved in `dist/card/probe-commands.sh`. The compare tool accepts the
runner's final successful JSON receipt, rejects malformed/empty/failed output,
and reports the first 20 exact-bit differences plus the total. It compares
NaN payloads/signs exactly too: a domain-result difference alone is not a
wrong-code diagnosis. The lead must preserve stdout, stderr and the receipt.
No card access was attempted and no native card outcome is claimed.

## Gravity and upstream flags

Upstream `third_party/milkywayathome_client/CMakeLists.txt:288-300` defines
`extra_gcc_math_flags` with `-fno-math-errno` and applies it to GCC/Clang C builds;
the following C++ block applies the same list. Adopted this flag in the common
flags for both builds (and the profiling-build override). All objects rebuilt.
The new card disassembly of `nbGravity` contains two `fsqrt` instructions and
no sqrt call. Its full error routine still tail-calls `fprintf`. The adapter
cannot include the indirect PLT/GOT closure; `twin/closure-attempt.txt` retains
the diagnostic. All four gravity steps were rerun and now report fprintf as
the unsupported callee. No branch or error routine was removed; no callee
cycle cost was invented. Thus full gravity functional agreement and timing
remain unproven even though the sqrt blocker was removed.

Fresh x86 reference execution after this flag (process metadata):

| Workunit / threads | Exit | Histogram present | Host elapsed seconds |
| --- | --- | --- | --- |
'''
for r in refs:s+=f"| {r['case']} / {r['threads']} | {r['exit.txt'] or 'pending'} | {r['histogram_present']} | {r['seconds.txt'] or 'pending'} |\n"
s+='''
`runs/x86/*-compare.txt` retain strict between-thread likelihood comparisons
(absolute difference < 1e-10, histogram values diagnostic). Histograms include
a generation timestamp, so their raw file hashes are identities, not a
numerical comparison. The new small/1 result also matches the historical
profile reference exactly (build/errno-small-reference-compare.txt). The capture and historical profile remain the independent
S1-03 measurements. The new binary/package identities are in
`twin/build-manifest.json`; the new references are in `twin/reference-runs.json`.

## Historical host profile and numerical policy

'''
for name,(pct,sec) in profile.items():s+=f'- `{name}`: {pct}% self time, {sec} sampled host seconds.\n'
s+='''
Those are the inherited S1-03 Cygwin gprof **host sampling measurements**,
not new card/twin predictions; profiling overhead is substantial. No unfilled
template placeholders remain. The captured x87 control word remains `0x027f`
(53-bit precision, nearest rounding), FTZ/DAZ false. Expected low-double output
comparison is exact. One function call is the unit of work. Cold line-tracked
memory, all-predicted branches, warm instruction cache and one context remain
the declared scenario; no N-body or logarithm timing shape is calibrated.

## Verbatim engine result fields

`"<absent>"` means absent in the returned envelope, not a returned JSON null.
No error/partial trace is used as a cycle figure. Calibration numbers below
belong to the engine profile, not to this experiment's measured accuracy.

'''
for label,path in [('Gravity',''),('Measured hotspot','hot/')]:
    for cmd in ('validate','functional','simulate','bounds'):
        s+=f'### {label} {cmd}\n\n'+fields(f'twin/{path}{cmd}/result.json')+'\n\n'
s+='### Minimal fildl repro functional\n\n'+fields('twin/fildl-repro/result.json')+'\n\n'
s+='''## Reproduce

From Git Bash at the worktree root:

```bash
bash probes/reproduce.sh       # rebuild both apps, probes, six references, twin reruns
# Or, with existing built app/captures:
bash probes/build.sh
bash twin/run.sh               # expected exit 1: unsupported fprintf
bash twin/run_hot.sh           # expected exit 1: functional_mismatch
python twin/diagnose_log.py    # unchanged functional cases + minimal repro + memory audit
python twin/write_report.py
python tests/test_libm_probe.py
python tests/test_twin.py
# Lead only, prints commands without contacting the card:
bash scripts/probe-commands.sh
# Small standalone repro, no application build needed:
python C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/fildl-repro.json --trace --out build/fildl-check --force
```

All build entry scripts create build/tmp and export TMPDIR, TMP and TEMP to
$PWD/build/tmp before compiling. Builds use the prescribed Cygwin and KNC tools.
All source/probe/rerun changes are left for lead review; no git write commands,
installs, alternate downloads or shared toolchain writes were performed.
'''
(ROOT/'docs/twin-check.md').write_text(s,encoding='utf-8')
files=[ROOT/'build/x86/milkyway_nbody.exe']+list((ROOT/'dist/card').glob('*'))
manifest=[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files) if p.is_file()]
(ROOT/'twin/build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
