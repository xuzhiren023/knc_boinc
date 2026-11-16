# S1-03: real pre-card twin verdict

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
The flat profile reports `log_rn` at 43.67% self time (30.50 sampled host seconds),
`pow_rn` at 9.25% (6.46 sampled host seconds), and `nbGravity` at {{nbGravity_percent}}%
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

Gravity capture: **capture metadata**, 118 file blocks; expected acceleration [13.016965884860129, 5.9070903059992235, 53.59129570497724].

## Binary coverage and unsupported closure

K1OM objdump disassembles `build/card/milkyway_nbody.mic`; its SHA-256 is `56b848e6fbe84dbde09c17eb9d8727bbc1009ae9ab8442403526b1a28f283b6b` (**binary metadata**). The entire `nbGravity` and `nbReportTreeIncest` are included: 286 instructions (**extraction metadata**). All extracted mnemonics have functional and timing support; `fildll` is the documented ISA alias of `fildq`. No timing-only mnemonic is silently accepted. The remaining callees are `sqrt` and `fprintf`.

`twin/closure-attempt.txt` records the attempt to include their compiled PLT
entries. The adapter refuses the indirect jump through the GOT (`*0xb09bb0`).
`sqrt` is dynamically linked and the tree-error routine tail-calls `fprintf`.
No sourced per-call runtime costs are available. The main extraction retains
these calls, so the four commands faithfully reject the region on the first
undeclared callee (`sqrt`). They do not execute a truncated kernel. The empty
`unsupported` mnemonic coverage array is not proof of a supported call closure.

For the measured hotspot, the entire `log_rn` and `p_accu` are included: 1333 instructions (**extraction metadata**), no unresolved symbols or undeclared callees, no unsupported or timing-only instructions, and no stubs. The functional check reports got `0x43c628b76e3a7b61` versus expected `0x0000000000000000` in `ctx0.zmm0[0]` (**functional output bits**, not cycle results).

The binary also contains a different local function named `p_accu`. Before
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

### Gravity validate

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity functional

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity simulate

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
- `limiting_constraints`: `[]`
- `calibration_status`: `null`
- `parameters_used`: `"<absent>"`

### Gravity bounds

- `status`: `"unsupported"`
- `result_class`: `"<absent>"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `["streams[0]: instruction a405216 calls 'sqrt', which is not in the region and has no entry in the kernel's 'calls' (declare a costed stub: {\"cycles\": N, \"model\": ...})"]`
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

## Cycle comparison and assumptions

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
| small / 1 | 0 | True | 49.215 |
| small / 4 | 0 | True | 40.616 |
| medium / 1 | 0 | True | 502.316 |
| medium / 4 | 0 | True | 158.418 |
| large / 1 | 0 | True | 163.248 |
| large / 12 | 0 | True | 23.784 |

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
