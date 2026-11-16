# S1-04: logarithm mismatch diagnosis and card handoff

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

For the 1.0 input, dynamic step `31` at `a49727d` is
`fildl 0x8(%rsp)` (machine bytes `db 44 24 08`). The preceding 64-bit store
put `0x3ff0000000000000` in that slot; the subsequent **32-bit** store of edi
wrote zero into its low four bytes. Earlier state follows the integer
exponent calculation `(0x3ff00000 >> 20) - 1023 = 0`; the snapshots retain all
preceding register/stack results. `fildl` must load the signed low 32-bit
integer **0**, regardless of the old high bytes. The engine's ISA table
assigns it `mem_size=8`, loading **4.6071824188000174e+18** instead.
This introduces the huge exponent term in the logarithm calculation.
The retained intermediate snapshots are `twin/log-cases/log-one-intermediates.json`.

The independent Cygwin x86 executable from `probes/fildl_host.c` executes
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
| fixed-0 | `3ff0000000000000` | `0000000000000000` | `functional_mismatch` |
| fixed-1 | `4000000000000000` | `3fe62e42fefa39ef` | `functional_mismatch` |
| fixed-2 | `3fe0000000000000` | `bfe62e42fefa39ef` | `functional_mismatch` |
| fixed-3 | `4005bf0a8b145769` | `3ff0000000000000` | `functional_mismatch` |
| fixed-4 | `01a56e1fc2f8f359` | `c085963447f87fb5` | `functional_mismatch` |
| fixed-5 | `7e37e43c8800759c` | `4085963447f87fb5` | `functional_mismatch` |
| fixed-6 | `0000000000000001` | `c0874385446d71c3` | `functional_mismatch` |
| seed-000 | `19da1f73ec6906a6` | `c07a6545de94439c` | `functional_mismatch` |
| seed-001 | `6e31af6fc6c8067d` | `4080083b8318a15c` | `functional_mismatch` |
| seed-002 | `0e0122140689a848` | `c0814e0ca441c4ed` | `functional_mismatch` |
| seed-003 | `485848feb9fdcdf7` | `40575322c86f0918` | `functional_mismatch` |
| seed-004 | `6d8de8d3c6f53eba` | `407f9ee0cb5ce0ec` | `functional_mismatch` |
| seed-005 | `2deb627b54e3ce01` | `c068f90749b8da98` | `functional_mismatch` |
| seed-006 | `15922e36193a367c` | `c07d5d3767eaa1f7` | `functional_mismatch` |
| seed-007 | `2e442c5fcdd6991b` | `c0687db9608c87b8` | `functional_mismatch` |
| captured | `3ff0000000000000` | `0000000000000000` | `functional_mismatch` |

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
| small / 1 | 0 | True | 52.361 |
| small / 4 | 0 | True | 56.929 |
| medium / 1 | 0 | True | 672.498 |
| medium / 4 | 0 | True | 290.674 |
| large / 1 | 0 | True | 222.346 |
| large / 12 | 0 | True | 27.084 |

`runs/x86/*-compare.txt` retain strict between-thread likelihood comparisons
(absolute difference < 1e-10, histogram values diagnostic). Histograms include
a generation timestamp, so their raw file hashes are identities, not a
numerical comparison. The new small/1 result also matches the historical
profile reference exactly (build/errno-small-reference-compare.txt). The capture and historical profile remain the independent
S1-03 measurements. The new binary/package identities are in
`twin/build-manifest.json`; the new references are in `twin/reference-runs.json`.

## Historical host profile and numerical policy

- `log_rn`: 43.67% self time, 30.50 sampled host seconds.
- `_mcount_private`: 30.77% self time, 21.49 sampled host seconds.
- `pow_rn`: 9.25% self time, 6.46 sampled host seconds.
- `__fentry__`: 5.87% self time, 4.10 sampled host seconds.
- `nbGravity`: 1.75% self time, 1.22 sampled host seconds.

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

### Gravity validate

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity functional

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity simulate

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity bounds

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a42f4b2 calls 'fprintf', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `{"held_out_validation_cases": 160, "not_validated_shapes": {"x87_sparse_rows_l1": {"evidence": "S12-30 small cases, 16 held-out rows, one thread", "median_abs_error_pct": 16.0, "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate", "worst_abs_error_pct": 17.9}}, "note": "Simulated/analytical outputs are model results, never native measurements. ", "state": "imported_microbenchmarks_with_compiled_heldout_check", "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).", "synthetic": false, "validated_shapes": {"l1_l2_dependent_loads": {"evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains", "median_abs_error_pct": 2.0, "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)", "worst_abs_error_pct": 14.0}, "l1_resident_stores_prefetch_pairing": {"evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing", "median_abs_error_pct": 2.0, "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing", "worst_abs_error_pct": 12.0}, "register_vector_chain_l1": {"evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads", "median_abs_error_pct": 1.0, "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)", "worst_abs_error_pct": 11.0}, "scalar_mask_l1": {"evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4", "median_abs_error_pct": 1.0, "note": "scalar integer and mask chains, pairing, address-generation interlock", "worst_abs_error_pct": 5.0}, "x87_register_chain": {"evidence": "S6-03 x87_add/mul/div .lat/.rt rows", "median_abs_error_pct": 1.0, "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured", "worst_abs_error_pct": 3.0}, "x87_row_loop_l1": {"evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread", "median_abs_error_pct": 2.9, "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included", "worst_abs_error_pct": 3.8}, "x87_sparse_rows_l2": {"evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread", "median_abs_error_pct": 3.7, "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2", "worst_abs_error_pct": 6.6}, "x87_sparse_rows_memory_stream": {"evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread", "median_abs_error_pct": 3.7, "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads", "worst_abs_error_pct": 4.1}}}`
- `parameters_used`: `{}`

### Measured hotspot validate

- `status`: `"ok"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- `calibration_status`: `{"held_out_validation_cases": 160, "not_validated_shapes": {"x87_sparse_rows_l1": {"evidence": "S12-30 small cases, 16 held-out rows, one thread", "median_abs_error_pct": 16.0, "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate", "worst_abs_error_pct": 17.9}}, "note": "Simulated/analytical outputs are model results, never native measurements. ", "state": "imported_microbenchmarks_with_compiled_heldout_check", "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).", "synthetic": false, "validated_shapes": {"l1_l2_dependent_loads": {"evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains", "median_abs_error_pct": 2.0, "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)", "worst_abs_error_pct": 14.0}, "l1_resident_stores_prefetch_pairing": {"evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing", "median_abs_error_pct": 2.0, "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing", "worst_abs_error_pct": 12.0}, "register_vector_chain_l1": {"evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads", "median_abs_error_pct": 1.0, "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)", "worst_abs_error_pct": 11.0}, "scalar_mask_l1": {"evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4", "median_abs_error_pct": 1.0, "note": "scalar integer and mask chains, pairing, address-generation interlock", "worst_abs_error_pct": 5.0}, "x87_register_chain": {"evidence": "S6-03 x87_add/mul/div .lat/.rt rows", "median_abs_error_pct": 1.0, "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured", "worst_abs_error_pct": 3.0}, "x87_row_loop_l1": {"evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread", "median_abs_error_pct": 2.9, "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included", "worst_abs_error_pct": 3.8}, "x87_sparse_rows_l2": {"evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread", "median_abs_error_pct": 3.7, "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2", "worst_abs_error_pct": 6.6}, "x87_sparse_rows_memory_stream": {"evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread", "median_abs_error_pct": 3.7, "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads", "worst_abs_error_pct": 4.1}}}`
- `parameters_used`: `"<absent>"`

### Measured hotspot functional

- `status`: `"functional_mismatch"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"checked": 1, "mismatches": [{"got": "0x43c628b76e3a7b61", "want": "0x0000000000000000", "where": "ctx0.zmm0[0]"}], "status": "mismatch"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Measured hotspot simulate

- `status`: `"functional_mismatch"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"checked": 1, "mismatches": [{"got": "0x43c628b76e3a7b61", "want": "0x0000000000000000", "where": "ctx0.zmm0[0]"}], "status": "mismatch"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- `calibration_status`: `{"held_out_validation_cases": 160, "not_validated_shapes": {"x87_sparse_rows_l1": {"evidence": "S12-30 small cases, 16 held-out rows, one thread", "median_abs_error_pct": 16.0, "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate", "worst_abs_error_pct": 17.9}}, "note": "Simulated/analytical outputs are model results, never native measurements. ", "state": "imported_microbenchmarks_with_compiled_heldout_check", "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).", "synthetic": false, "validated_shapes": {"l1_l2_dependent_loads": {"evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains", "median_abs_error_pct": 2.0, "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)", "worst_abs_error_pct": 14.0}, "l1_resident_stores_prefetch_pairing": {"evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing", "median_abs_error_pct": 2.0, "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing", "worst_abs_error_pct": 12.0}, "register_vector_chain_l1": {"evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads", "median_abs_error_pct": 1.0, "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)", "worst_abs_error_pct": 11.0}, "scalar_mask_l1": {"evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4", "median_abs_error_pct": 1.0, "note": "scalar integer and mask chains, pairing, address-generation interlock", "worst_abs_error_pct": 5.0}, "x87_register_chain": {"evidence": "S6-03 x87_add/mul/div .lat/.rt rows", "median_abs_error_pct": 1.0, "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured", "worst_abs_error_pct": 3.0}, "x87_row_loop_l1": {"evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread", "median_abs_error_pct": 2.9, "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included", "worst_abs_error_pct": 3.8}, "x87_sparse_rows_l2": {"evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread", "median_abs_error_pct": 3.7, "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2", "worst_abs_error_pct": 6.6}, "x87_sparse_rows_memory_stream": {"evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread", "median_abs_error_pct": 3.7, "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads", "worst_abs_error_pct": 4.1}}}`
- `parameters_used`: `{}`

### Measured hotspot bounds

- `status`: `"functional_mismatch"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"checked": 1, "mismatches": [{"got": "0x43c628b76e3a7b61", "want": "0x0000000000000000", "where": "ctx0.zmm0[0]"}], "status": "mismatch"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- `calibration_status`: `{"held_out_validation_cases": 160, "not_validated_shapes": {"x87_sparse_rows_l1": {"evidence": "S12-30 small cases, 16 held-out rows, one thread", "median_abs_error_pct": 16.0, "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate", "worst_abs_error_pct": 17.9}}, "note": "Simulated/analytical outputs are model results, never native measurements. ", "state": "imported_microbenchmarks_with_compiled_heldout_check", "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).", "synthetic": false, "validated_shapes": {"l1_l2_dependent_loads": {"evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains", "median_abs_error_pct": 2.0, "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)", "worst_abs_error_pct": 14.0}, "l1_resident_stores_prefetch_pairing": {"evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing", "median_abs_error_pct": 2.0, "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing", "worst_abs_error_pct": 12.0}, "register_vector_chain_l1": {"evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads", "median_abs_error_pct": 1.0, "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)", "worst_abs_error_pct": 11.0}, "scalar_mask_l1": {"evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4", "median_abs_error_pct": 1.0, "note": "scalar integer and mask chains, pairing, address-generation interlock", "worst_abs_error_pct": 5.0}, "x87_register_chain": {"evidence": "S6-03 x87_add/mul/div .lat/.rt rows", "median_abs_error_pct": 1.0, "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured", "worst_abs_error_pct": 3.0}, "x87_row_loop_l1": {"evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread", "median_abs_error_pct": 2.9, "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included", "worst_abs_error_pct": 3.8}, "x87_sparse_rows_l2": {"evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread", "median_abs_error_pct": 3.7, "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2", "worst_abs_error_pct": 6.6}, "x87_sparse_rows_memory_stream": {"evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread", "median_abs_error_pct": 3.7, "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads", "worst_abs_error_pct": 4.1}}}`
- `parameters_used`: `{}`

### Minimal fildl repro functional

- `status`: `"functional_mismatch"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"checked": 1, "mismatches": [{"got": "0x43cff80000000000", "want": "0x0000000000000000", "where": "ctx0.zmm0[0]"}], "status": "mismatch"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

## Reproduce

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
