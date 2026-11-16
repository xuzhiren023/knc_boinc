"""Render the S5-01 document from recorded tool envelopes, never hand estimates."""
import json
from pathlib import Path
ROOT = Path('twin/flags')
e = json.loads((ROOT/'evidence.json').read_text())
build = json.loads((ROOT/'build-manifest.json').read_text())
inputs = e['inputs']
lines = ['# Gravity compiler flags: S5-01', '',
         '**Verdict: too close for the twin.** No card run was made. The table is a model prediction, not measured card speed.', '',
         'Four required variants only; no optional variants were added. All share `-g -fopenmp -fno-strict-aliasing -march=knc -std=gnu99`, '
         '`-ffp-contract=off`, `-fno-math-errno`, and unchanged bundled crlibm objects. No fast-math options, reassociation, approximation, or contraction was enabled. '
         '`V2` receives no explicit `-O2` because that would override the `-mphinix` expansion to `-O3`.', '',
         'Inputs were fixed before running: the original S1-05 small capture, plus S1-06 large first-force-step bodies **0, 128, 256, 384** '
         '(20,000 bodies, seed 670828913, one host reference thread). Expected XYZ accelerations are independent x86 binary64 bytes. '
         'The unspecified fourth vector lane is excluded consistently with the original captures. No body was excluded after seeing results. '
         'S14-37 x87 double rounding remains a model defect; equality here uses exact bits with no ULP tolerance.', '',
         'The original large snapshot was copied read-only from the S1-06 worktree. `build-manifest.json` records SHA-256 hashes of its original files, '
         'the small capture, every unchanged linked object, and all variant objects/binaries. Adjacent snapshot blocks were coalesced with overlap byte-equality checks '
         'and split into bounded 64 KiB files: addresses and initialized bytes are preserved. These remain `init.memory` file blocks.', '',
         'A whole-function extraction is first attempted for each binary with `from_binary.py --function nbGravity`, retaining entry, return, encodings and the cold error call. '
         'The installed 0.4.0 adapter still needs the S1-05 region cut: whole-function simulate rejects the undeclared `nbReportTreeIncest` even when unexecuted. '
         'Including `nbReportTreeIncest` and `fprintf@plt` was also attempted; the adapter reports an indirect transfer as unsupported when executed, '
         'but then refuses to emit a kernel because aggregate functional coverage is false. S14-20 is therefore incomplete in this installed adapter.', '',
         '**V0 and V3 need a region cut with this installation.** The boundary is the start of the cold call setup (two moves before `nbReportTreeIncest`). '
         'Every preceding binary instruction record is unchanged, including normal return and output stores. The original branch target becomes a sentinel. '
         'Each of the 10 available functional traces confirms that the sentinel is never executed and the normal return is executed. '
         'No costed stub, made-up latency, missing-memory default, or changed arithmetic is used. '
         'The full extraction, refused full simulate, exact boundary and retained-record equality are retained in the evidence.', '',
         'One unit is **one nbGravity call / one body / one context**. Each call starts cold at memory level with line tracking and all-predicted branches. '
         'Profile `card-7120-measured`, hash `'+e['variants'][0]['cases']['small']['simulate']['profile']['hash']+'`, is frozen in every batch. '
         'Each input has its own batch over all variants passing every input; ranking across different input work is not attempted. Automatic batch queue generation is disabled because the two explicit prepare-native attempts below handle the V0/nominee handoff.', '',
         '| Variant | gravity flags | functional | predicted cycles/call: small / L0 / L128 / L256 / L384 | change vs V0 in the same order | result_class | limiting_constraints |',
         '|---|---|---|---|---|---|---|']
base = e['variants'][0]
for v in e['variants']:
    cycles, deltas, statuses, classes, limits = [], [], [], set(), set()
    for name in inputs:
        c = v['cases'][name]
        statuses.append(c['functional']['status'])
        s = c['simulate']
        if s['status'] == 'ok':
            n = s['prediction']['predicted_cycles_per_unit']
            b = base['cases'][name]['simulate']['prediction']['predicted_cycles_per_unit']
            cycles.append('%g'%n)
            deltas.append('%+.2f%%'%(100*(n/b-1)))
            classes.add(s['prediction']['result_class']['class'])
            limits.update(x['constraint'] for x in s.get('limiting_constraints', []))
        else:
            cycles.append(s['status']); deltas.append('n/a')
    status = 'all 5 exact' if set(statuses) == {'ok'} else ', '.join(statuses)
    lines.append('| %s | `%s` | %s | %s | %s | %s | %s |' %
                 (v['name'], v['flags'], status, ' / '.join(cycles), ' / '.join(deltas), ', '.join(sorted(classes)) or 'n/a', ', '.join(sorted(limits)) or 'n/a'))
lines += ['', 'A negative change is fewer predicted cycles. V0 and V3 match all five exact outputs. V1 and V2 have no standalone `nbGravity` symbol: `-O3` inlines it into `nbMapForceBody._omp_fn.0` (and its other caller). Whole-function extraction is refused for each fixed input. No kernel, functional pass, or timing is invented for them; they are excluded from batch because exact numerical qualification is unavailable. Their complete card binaries remain available. Adding no-inline or keep-inline flags would change this experiment or model an unused out-of-line copy, so those flags were not added.', '',
          'Batch output (actual tool ranking; ties retain manifest order). Its bound-gap diagnostic is not used: the known S14-27 dependency-critical-path defect can put a reported lower bound above simulation.', '']
for name, batch in e['batches'].items():
    rows = batch['prediction']['candidates']
    lines.append('- `%s`: %s. %s' % (name, ', '.join(batch['prediction']['ranking'])+' (equal cycles)',
                 '; '.join(r['name']+': '+(r.get('message') or 'no uncertainty message') for r in rows)))
lines += ['', 'Gravity is not a validated shape. Every cycle result is `unvalidated_scenario_estimate`; '
          'the held-out 3.1% median / 39-of-39 ranking evidence belongs to other compiled loop families, not this tree walk. '
          'There is no validated gravity error band. The batches use the handoff\'s conservative 30% uncertainty threshold, and '
          'cold memory beyond L1 is explicitly unvalidated. The top nonbaseline candidate in the small-input batch is `'+e['top_candidate']+'`; '
          'this is only the A/B nominee, not a winner. The model cannot justify choosing it over V0.', '']
schedule = e['schedule']
lines += ['`schedule` on the V0 tree-walk loop (`--method list --max-states 4096`) reports:', '',
          '```text', schedule['status']+': '+schedule['message'], '```', '',
          'The baseline region and original tree-walk loop body were preserved. The explorer refuses an interior label before searching this binary-derived loop, which also contains interior branches; '
          'no reorder gain or cycle estimate is available. A different, simplified straight-line kernel was not substituted.', '',
          '`prepare-native` requests for V0 and the batch-selected nominee report:', '']
for v, r in zip(['V0',e['top_candidate']],e['native']):
    lines += ['```text', v+': '+r['status']+': '+r['message'], '```', '']
lines += ['The original pointer-rich snapshots are sparse over a very large address range. The native exporter cannot pack them into its '
          'single image (32 MiB maximum). No fabricated request or native timing is claimed. '
          'The full linked card binaries are left at `build/flags/V0/milkyway_nbody.mic` and '
          '`build/flags/'+e['top_candidate']+'/milkyway_nbody.mic`; runtimes are in `dist/card/`. '
          '`bash scripts/flags-card-commands.sh` prints a reproducible whole-application A/B run script, also staged as `twin/flags/run-native.sh`. '
          'It covers small at 1/240 threads, medium at 240, large at 60/240, with the same seed. '
          'The lead can run that generated script; no card key was used here. Whole-application timings are a follow-up, not a per-call calibration of these cold snapshots.', '',
          'Model metadata copied from the result envelopes:', '',
          '```json', json.dumps({
              'assumptions': sorted({a for v in e['variants'] for c in v['cases'].values() for a in c['simulate'].get('assumptions',[])}),
              'unsupported': [c['simulate'].get('unsupported') for v in e['variants'] for c in v['cases'].values() if c['simulate'].get('unsupported')],
              'calibration_status':base['cases']['small']['simulate'].get('calibration_status'),
              'parameters_used_assumed_or_derived':e['model_metadata']}, indent=2), '```', '',
          'Full tool envelopes, traces and reconstructed kernels are regenerated under ignored `twin/flags/` paths; '
          '`evidence.json`, `build-manifest.json`, `run.log` and `run-native.sh` are the compact review artifacts.', '',
          'Rerun from Git Bash (pinned sources already present):', '', '```bash',
          'mkdir -p build/tmp', 'export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"',
          'export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"',
          'export PYTHONDONTWRITEBYTECODE=1',
          '# Restore the original large capture if absent: bash twin/capture_multicore.sh',
          'bash twin/run_flags.sh > twin/flags/run.log 2>&1',
          'python twin/write_flags_report.py',
          'bash scripts/flags-card-commands.sh > twin/flags/run-native.sh',
          'python tests/test_twin_flags.py', '```', '',
          'Not proven: output equality beyond the fixed five bodies, hardware ordering gains, gravity model error, '
          'steady-state cache behaviour, whole-application speedup, or the cold error path. '
          'The schedule and native-export refusals need the twin owner\'s attention; final speed decisions require the lead\'s card run.']
Path('docs/twin-flags.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
