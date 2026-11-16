"""Render the verdict from the actual tool envelopes, never partial cycle values."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((root/path).read_text())
def fields(path):
    k = read(path)
    names = ('status','result_class','functional_check','assumptions','unsupported',
             'limiting_constraints','calibration_status','parameters_used')
    return '\n'.join('- `' + name + '`: `' + json.dumps(k.get(name,'<absent>'),sort_keys=True) + '`'
                     for name in names)
profile_rows = {}
for line in (root/'twin/profile/gprof.txt').read_text().splitlines():
    columns = line.split()
    if len(columns) >= 6 and columns[-1] in ('log_rn','pow_rn','nbGravity','_mcount_private','__fentry__'):
        try:
            float(columns[0]); float(columns[2])
        except ValueError:
            continue
        profile_rows.setdefault(columns[-1],(columns[0],columns[2]))
m = read('twin/capture-manifest.json')
conv = read('twin/conversion.json')['provenance']
hot = read('twin/log-conversion.json')['provenance']
s = '''# S1-03: real pre-card twin verdict

**The compiled gravity kernel has not been shown to match x86.** Its four twin
commands return `unsupported`. The measured overall hotspot, `log_rn`, has a
complete extraction and validates, but returns `functional_mismatch` against
its captured x86 result. Neither experiment supplies a valid predicted
per-call cycle figure or a bound. Card validation remains necessary.

This replaces the earlier network-blocked report. The pinned sources verify
offline; the card and x86 binaries now build. The negative twin verdicts are
actual tool results, not missing experiments. The ticket expressly allows
unsupported behavior as a result; no instruction, branch or callee was removed
to manufacture a pass, and no unmeasured callee cost was supplied.

## Profiling and scope

Cygwin GCC `-O2 -g -pg -fopenmp -fno-strict-aliasing -ffp-contract=off`, followed
by Cygwin `gprof`, profiled the full seeded `small` run with one OpenMP thread.
See `twin/profile/{gmon.out,gprof.txt,stdout.txt,stderr.txt,histogram.txt}`.
The flat profile reports `log_rn` at {{log_rn_percent}}% self time ({{log_rn_seconds}} sampled host seconds),
`pow_rn` at {{pow_rn_percent}}% ({{pow_rn_seconds}} sampled host seconds), and `nbGravity` at {{nbGravity_percent}}%
({{nbGravity_seconds}} sampled host seconds). These are **host sampling measurements**, not twin
result classes or card predictions. Profiling overhead is substantial:
`_mcount_private` is {{_mcount_private_percent}}% and `__fentry__` is {{__fentry___percent}}%. The gravity routine is
not the overall hotspot in this workunit. Both the requested force routine and
the actual measured hotspot were checked; the profile is not used to invent
callee costs or a whole-program speed forecast.

## Capture and ABI evidence

`twin/prepare_capture.py` creates an instrumented copy of `nbody_grav.c` under
`build/`; the pinned source remains untouched. The first real gravity call on
`small` dumps the context, state, softening matrix and every node reachable
through the tree's next/more pointers. The dump occurs before computation;
the expected acceleration comes from the x86 function's returned value.
`twin/capture_helper.h` records the live x87 control word. Only physical x/y/z
acceleration bytes are compared: upstream vector padding w is unspecified.

`twin/capture_log.c` uses the linker's `--wrap=log_rn` to record the first real
scalar input and the return value from the original function, without rewriting
its implementation. The first captured input is 1.0 and the independent host
output is +0.0 (captured data, not timing estimates). The scalar K1OM ABI uses
the low double of zmm0; inactive lanes start at zero and are not compared.
The original raw input is also retained as an `init.memory` file block;
`log_overlay.py` loads the ABI argument and expected return bits from the files.
No synthetic input or twin-produced expected value is used.

The gravity ABI has hidden return storage in rdi, ctx in rsi, state in rdx and
body in rcx. Host pointers are preserved. `twin/layout.c` is compiled for both
host and card; its array agrees on every declared size/offset, including all
fields read by gravity and the included error routine. Trailing zero COFF
section alignment is excluded from that comparison. Layout values and every
capture file's SHA-256 are in `twin/capture-manifest.json`. These are **capture
and extraction metadata**, not prediction result classes. Raw context/state
blocks contain other pointers; no uncaptured memory may be silently read:
`memory_default` is removed from both extracted kernels.

The captured control word is `0x027f` (53-bit x87 precision, round-to-nearest),
matching the application's crlibm initialization. FTZ and DAZ are false.
The comparison tolerance is **zero**: exact output bits for gravity's x/y/z,
and the low scalar double returned by correctly rounded `log_rn`. This does
not imply agreement at a looser tolerance; gravity never reaches comparison.
The log mismatch is large and remains unresolved: this experiment cannot tell
whether the defect lies in the twin/adapter or in the compiled card code.

'''
s += 'Gravity capture: **capture metadata**, ' + str(m['blocks']) + ' file blocks; expected acceleration ' + json.dumps(m['expected_acceleration']) + '.\n\n'
s += '## Binary coverage and unsupported closure\n\n'
s += ('K1OM objdump disassembles `build/card/milkyway_nbody.mic`; its SHA-256 is `' + conv['source_sha256'] + '` (**binary metadata**). '
      'The entire `nbGravity` and `nbReportTreeIncest` are included: ' + str(conv['coverage']['instructions']) + ' instructions (**extraction metadata**). '
      'All extracted mnemonics have functional and timing support; `fildll` is the documented ISA alias of `fildq`. '
      'No timing-only mnemonic is silently accepted. The remaining callees are `sqrt` and `fprintf`.\n\n')
s += '''`twin/closure-attempt.txt` records the attempt to include their compiled PLT
entries. The adapter refuses the indirect jump through the GOT (`*0xb09bb0`).
`sqrt` is dynamically linked and the tree-error routine tail-calls `fprintf`.
No sourced per-call runtime costs are available. The main extraction retains
these calls, so the four commands faithfully reject the region on the first
undeclared callee (`sqrt`). They do not execute a truncated kernel. The empty
`unsupported` mnemonic coverage array is not proof of a supported call closure.

'''
s += ('For the measured hotspot, the entire `log_rn` and `p_accu` are included: ' + str(hot['coverage']['instructions']) +
      ' instructions (**extraction metadata**), no unresolved symbols or undeclared callees, no unsupported or timing-only instructions, and no stubs. '
      'The functional check reports got `0x43c628b76e3a7b61` versus expected `0x0000000000000000` in `ctx0.zmm0[0]` (**functional output bits**, not cycle results).\n\n')
s += '''The binary also contains a different local function named `p_accu`. Before
hotspot extraction, `twin/disambiguate.py` gives duplicate local symbol
annotations unique address-based names. It asserts that addresses, raw bytes,
and instruction text are unchanged after removing the annotations. The actual
logarithm callee at `0x495480` is included; the unrelated local function at
`0x4a76c0` is excluded. `twin/symbol-aliases.json` records this adapter input
normalization. The observed mismatch persists with the faithful call closure.

## Verbatim result status fields

Each command has its own `result.json` and `summary.md`. `"<absent>"` below
means the field is absent in that engine envelope, not returned as JSON null.
In particular these envelopes do not contain `result_class`; no class is
invented for a validation error or failed functional check. No cycle prediction
or partial trace number is promoted to a result. Any numbers embedded in copied
calibration text describe the model's calibration, not this kernel's accuracy.
No assumed/derived `parameters_used` rows were returned for these experiments.

'''
for prefix in ('','hot/'):
    for command in ('validate','functional','simulate','bounds'):
        s += '### ' + ('Measured hotspot ' if prefix else 'Gravity ') + command + '\n\n'
        s += fields('twin/'+prefix+command+'/result.json')+'\n\n'
s += '''## Cycle comparison and assumptions

Predicted gravity cycles per call: **unavailable**, result_class **absent**,
status `unsupported`. Predicted `log_rn` cycles per call: **unavailable**,
result_class **absent**, status `functional_mismatch`. Bounds are likewise
unavailable. There is no valid numeric figure for the lead to compare to card
cycles. This is a negative pre-card result, not a performance claim.

Both scenarios declare one context, cold memory with line tracking and
all-predicted branches, warm instruction cache, and one captured call as the
unit of work. Neither declares a validated N-body/logarithm shape. A successful
future simulation would still require the appropriate result classification;
the skill's held-out validation does not calibrate these shapes. No whole-card
or whole-program estimate is made. The captured calls do not establish
correctness for all timesteps, body types, special inputs, or thread counts.

## Builds, reference runs and card handoff

Fresh card package: `dist/card/milkyway_nbody.mic`, compiler runtime closure,
`runtime-manifest.txt`, `readelf.txt`, and passing `knc-lint.txt`.
`dist/card/lead-commands.sh` contains the commands printed by
`scripts/card-check.sh`; `scripts/card-launch.sh` launches the packaged binary.
No card access was attempted. The lead must run those commands and retain
card receipts/results. The artifact package and reference runs are gitignored
local deliverables; source capture bytes and twin JSON/Markdown are in `twin/`.

Reference run status (**host execution metadata**, not twin predictions):

| case / threads | exit | histogram present | elapsed host seconds |
| --- | --- | --- | --- |
'''
for case,threads in (('small',1),('small',4),('medium',1),('medium',4),('large',1),('large',12)):
    p = root/'runs/x86'/('%s-%s'%(case,threads))
    def txt(name):
        f=p/name
        return f.read_text().strip() if f.is_file() and f.stat().st_size else 'pending'
    s += '| %s / %s | %s | %s | %s |\n'%(case,threads,txt('exit.txt'),(p/'histogram.txt').is_file(),txt('seconds.txt'))
s += '''
The run directories contain command, stdout/stderr, exit code, elapsed time
and histogram. `*-compare.txt` records the between-thread comparison using the
repository's strict absolute likelihood threshold of 1e-10; histogram values
are diagnostic. Capture and profiling histograms were also compared against
the uninstrumented small reference. Failed files from the earlier session are
replaced only by successful fresh runs; do not use a directory marked pending.

## Reproduce

Run from Git Bash in this worktree:

```bash
# Rebuild, profile, recapture, rerun all references and twin checks:
bash twin/reproduce.sh
# Or rerun only the two twin experiments on the existing binary/capture:
bash twin/run.sh            # exit 1: unsupported is the recorded finding
bash twin/run_hot.sh        # exit 1: functional mismatch is the recorded finding
python twin/write_report.py
python tests/test_twin.py
python -m unittest discover -s tests -p test_card.py -v
python -m unittest discover -s tests -p test_compare.py -v
```

The reproduction script creates `build/tmp` and exports TMPDIR, TMP and TEMP
before compiling; it uses only the prescribed Cygwin host tools and KNC tools.
`run.sh` refreshes capabilities, extracts the built function and included
callee, audits every mnemonic and capture file, records the rejected library
closure, and invokes validate/functional/simulate/bounds with the measured
profile for timing and bounds. `run_hot.sh` checks the actual profiled hotspot
with its complete callee. Tool failures are intentionally preserved and do not
prevent the remaining requested commands from producing their own envelopes.
The report is generated from those envelopes, not from hand-entered statuses.
'''
# Refresh host evidence without inventing a twin result classification.
reference_rows = []
for case,threads in (('small',1),('small',4),('medium',1),('medium',4),('large',1),('large',12)):
    directory = root/'runs/x86'/('%s-%s'%(case,threads))
    row = {'case':case,'threads':threads,'kind':'host_reference'}
    for name in ('exit.txt','seconds.txt','command.txt','stdout.txt'):
        path = directory/name
        row[name] = path.read_text().strip() if path.is_file() else None
    path = directory/'histogram.txt'
    row['histogram_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    reference_rows.append(row)
(root/'twin/reference-runs.json').write_text(json.dumps(reference_rows,indent=2)+'\n')
files = [root/'build/x86/milkyway_nbody.exe'] + list((root/'dist/card').glob('*'))
manifest = [{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,
             'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files) if p.is_file()]
(root/'twin/build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for key,(percent,seconds) in profile_rows.items():
    s = s.replace('{{'+key+'_percent}}',percent).replace('{{'+key+'_seconds}}',seconds)
(root/'docs/twin-check.md').write_text(s,encoding='utf-8')
