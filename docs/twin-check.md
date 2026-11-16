# S1-05: knc-twin 0.4.0 rerun

The unchanged 0.4.0 engine passes the four-instruction `fildl` repro (exact
+0.0, bits `0000000000000000`) and all 16 `log_rn` cases. The earlier S1-04
integer-width mismatch is resolved. The full compiled `log_rn` and `p_accu`
bodies, ELF constants and captured ABI input are retained. Expected bits come
from the S1-04 independent Cygwin x86 probe, never from the twin.
`twin/log-diagnosis.json`, `log-memory.md`, and the width diagnostic describe
the historical S1-04 failure; current cases are in `twin/log-rerun.json` and
`twin/log-cases/*/result.json`.

Gravity validate, functional, simulate and bounds all return `ok`. Its
captured acceleration matches the independent host output. No card comparison:
the card run has not happened. These are model results, not measured card timings.

## Region boundary and reference evidence

The gravity region was cut at the error branch because S14-20 has not landed:
the adapter refuses the indirect fprintf PLT path even when it never executes.
`from_binary.py` first extracts the complete built `nbGravity` without an
invented callee stub. `twin/cut_gravity.py` keeps the first 202 instruction
records exactly, with their operands, encodings, addresses, dependencies,
output stores, stack epilogue and normal return unchanged. At `.A_4050b2`,
before the cold call setup for `nbReportTreeIncest`, it places an exit label.
The branch at `0x405044` still targets that label. The error block and later
unreachable padding are excluded. Neither application source nor shared twin
code is changed. Full-function conversion evidence remains in `conversion.json`;
`gravity-region.json` describes the narrower executable region.

The functional trace executes 3,040 instructions, reaches the normal return,
and never reaches the exit sentinel. At `0x405044`, `je .A_4050b2` is **not
taken**. `twin/gravity-execution.json` retains this evidence. A fresh host
reference (`bash scripts/run_x86.sh small 1`, seed 670828913, 64 bodies) exits
zero; stdout and stderr have zero `tree-incest` diagnostics. The captured
warning gates are `quietErrors=0` and `treeIncest=0`, so the first error would
print. `twin/gravity-reference.json` records output byte counts and hashes,
command, and histogram hash. This establishes absence only for this measured
input, not arbitrary gravity inputs.

## Per-call model cycles

Both simulations use one context, `card-7120-measured`, cold `line_tracking`
memory, predicted branches and x87 control word `0x027f` (53-bit precision).
Each unit is one captured call; the log timing is for the captured 1.0 input,
not an average of the 16 cases.

| Region | simulate cycles/call | result_class | bounds cycles/call | result_class |
| --- | ---: | --- | ---: | --- |
| log_rn | 2,778 | unvalidated_scenario_estimate | 2,597 | conditional_bound |
| nbGravity, cold error region excluded | 33,622 | unvalidated_scenario_estimate | 43,656 | conditional_bound |

The gravity lower bound **exceeds** its simulation prediction. Both commands
return `ok`; these are the exact engine outputs. This is an unresolved
model inconsistency, so do not treat the pair as a consistent timing interval
or use it to choose close variants. No model correction is attempted here.
Both bounds identify `dependency_critical_path` as the binding term. Simulation
constraints and all returned assumptions follow below. Neither kernel declares
a validated `provenance.shape`; no calibrated forecast is claimed.

## Functional cases

| Case | Input bits | Independent expected log bits | 0.4.0 status |
| --- | --- | --- | --- |
| fixed-0 | `3ff0000000000000` | `0000000000000000` | ok |
| fixed-1 | `4000000000000000` | `3fe62e42fefa39ef` | ok |
| fixed-2 | `3fe0000000000000` | `bfe62e42fefa39ef` | ok |
| fixed-3 | `4005bf0a8b145769` | `3ff0000000000000` | ok |
| fixed-4 | `01a56e1fc2f8f359` | `c085963447f87fb5` | ok |
| fixed-5 | `7e37e43c8800759c` | `4085963447f87fb5` | ok |
| fixed-6 | `0000000000000001` | `c0874385446d71c3` | ok |
| seed-000 | `19da1f73ec6906a6` | `c07a6545de94439c` | ok |
| seed-001 | `6e31af6fc6c8067d` | `4080083b8318a15c` | ok |
| seed-002 | `0e0122140689a848` | `c0814e0ca441c4ed` | ok |
| seed-003 | `485848feb9fdcdf7` | `40575322c86f0918` | ok |
| seed-004 | `6d8de8d3c6f53eba` | `407f9ee0cb5ce0ec` | ok |
| seed-005 | `2deb627b54e3ce01` | `c068f90749b8da98` | ok |
| seed-006 | `15922e36193a367c` | `c07d5d3767eaa1f7` | ok |
| seed-007 | `2e442c5fcdd6991b` | `c0687db9608c87b8` | ok |
| captured | `3ff0000000000000` | `0000000000000000` | ok |

## Returned fields

Missing fields are written as `"<absent>"`, distinct from null.

### validate

- `status`: `"ok"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- assumed/derived `parameters_used`: `{}`
- `calibration_status`: shared entry 1 below.

### functional

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "ZF/SF after imul are architecturally undefined; the model leaves them unchanged"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- assumed/derived `parameters_used`: `{}`
- `calibration_status`: shared entry 2 below.

### simulate

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "ZF/SF after imul are architecturally undefined; the model leaves them unchanged", "line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic", "TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled", "L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)", "memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled", "front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)", "front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)", "instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)", "a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing", "register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies", "x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores", "sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[{"constraint": "x87_serial", "context_cycles": 11594}, {"constraint": "miss_stall", "context_cycles": 11381}, {"constraint": "dependency", "context_cycles": 4898}, {"constraint": "spacing", "context_cycles": 1976}]`
- top-level `result_class`: `"<absent>"`
- `prediction.result_class`: `{"class": "unvalidated_scenario_estimate", "reasons": ["the kernel declares no provenance.shape, so no held-out validation can vouch for it", "TLB, L2 hardware prefetcher and memory service sub-models are part of the memory domain (scenario: tlb=auto, hardware_prefetcher=auto, memory_service=auto)", "the trace misses L1 (86 L2, 53 memory accesses): cache behaviour is modeled, not validated"]}`
- assumed/derived `parameters_used`: `{"frontend.taken_branch_core_bubble_cycles": {"source": "S8-01 C10 fixed-direction row: 6.22 per branch at one thread, 17.02 at four (three issues plus about one core cycle per unit); R02 ch.4 one-clock refill bubble. Hidden at one thread by the same-context spacing. Scope: forward transfers only (S8-01 C9 register chains at two threads show no cost for the loop back-edge).", "status": "derived", "unit": "core issue cycles lost after a taken branch", "value": 1}, "l2.hw_prefetch_depth_lines": {"source": "S6-03 memory.load_rt 37.35 ticks per sequential line at one thread with the hardware prefetcher active: the HWP sub-model reproduces 37.4 with depth 16 (40.2 at 12, 51.4 at 8); at four threads it gives 85.5 against 77.9 (see references/validation.md)", "status": "derived", "unit": "lines ahead per confirmed stream", "value": 16}, "latency.branch_taken_bubble": {"source": "S8-01 C9: loop costs about 2 ticks per vector op plus 2 per loop branch at one thread (the branch costs its issue slot only)", "status": "derived", "unit": "cycles", "value": 0}, "latency.memory": {"source": "S6-03 memory.load_lat 356.53 per dependent hop at one thread (idle) minus the first-level TLB miss of 29 cycles (tlb.l1_miss_penalty_cycles): the measured chain touches a new 4 KiB page at every hop and the TLB sub-model charges that miss explicitly. 0.2.x used 357 and double-counted it when the TLB was modeled.", "status": "derived", "unit": "cycles", "value": 328}, "latency.scalar_extend_extra": {"source": "evidence E (estimate), inferred: plain integer sign- or zero-extension costs what mov does; no KNC source (R02 p.34 Table 3-1 lists no MOVSX/MOVZX; never measured on the card). Lead decision 2026-11-15.", "status": "assumed", "unit": "cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto", "value": 0}, "latency.store_to_load_same_line": {"source": "S8-12 C9 memory chain u1 11.07 per link = folded-load add (4) + store-to-load path; spill_reload.lat 12.11 = path + plain load (5)", "status": "derived", "unit": "cycles after a store issues before a load of the same line sees the data", "value": 7}, "latency.x87_control": {"source": "prior from the published Pentium (P5) instruction timings (FLDCW 7 clocks; FNSTCW and FNSTSW are 2). Not measured on KNC; all three are charged the FLDCW value.", "status": "assumed", "unit": "cycles", "value": 7}, "latency.x87_load": {"source": "S12-31 gas_0 488.9 and adj_0 433.5 cycles per 27-product row fix the sum of this value and the fmull memory form (operand read plus multiply) at 7 cycles; the split 3 + (1 + 3) keeps the measured x87 multiply latency of 3 and the documented one-cycle scalar load (R08)", "status": "derived", "unit": "cycles from issue until the loaded value is on the x87 stack", "value": 3}, "latency.x87_mem_operand_load": {"source": "see latency.x87_load: the sum is measured, the split is assumed (R08: one-cycle scalar load)", "status": "derived", "unit": "cycles for the memory operand of an x87 arithmetic instruction before the operation starts", "value": 1}, "latency.x87_move": {"source": "evidence E (estimate), inferred: same pipeline as the measured x87 add (S6-03 x87_add.lat 3.02), no KNC source for fld/fst/fxch/fldz; fld from memory uses the load latency instead", "status": "assumed", "unit": "cycles", "value": 3}, "latency.x87_sqrt": {"source": "prior from the published Pentium (P5) instruction timings (FSQRT 70 clocks): the KNC core derives from the P54C design (R01 section 2.1) and the P5 figures that could be checked on the card agree (FDIV 39 vs 39.25 measured in S6-03; IMUL 10 in R02 p.56). Not measured on KNC.", "status": "assumed", "unit": "cycles", "value": 70}, "pairing.extend_v_pairs": {"source": "evidence E (estimate), inferred: treated like the other scalar integer ops of R02 p.34 Table 3-1, which does not list them; no KNC source. Lead decision 2026-11-15.", "status": "assumed", "unit": "boolean: may movslq, movs*, movz*, cltq, cltd, cqto issue in the V slot", "value": true}, "pairing.load_store_pair": {"source": "S6-03 spill_reload.rt at four threads: 1.07 core cycles per vector store plus reload, so a U-pipe load and a V-pipe store issue in one cycle; the L1 access limit is applied to loads only", "status": "derived", "unit": "boolean", "value": true}, "pairing.u_instruction_can_be_branch": {"source": "evidence E (estimate), model assumption without a KNC source: an instruction after a control transfer in the same issue slot is not paired", "status": "assumed", "unit": "boolean", "value": false}, "store.load_after_store_interlock_cycles": {"source": "S6-03 spill_reload.rt 4.20/4.26 per pair at two/four threads and S8-12 C9 memory chains u2/u4 8.56/8.30 per link at one thread (two issues plus four cycles); vector rows only, applied to scalar stores as well (assumed)", "status": "derived", "unit": "cycles after a store before the same context may issue a load", "value": 4}, "x87.mem_operand_serializes": {"source": "S12-31 microbench (card windows 3 and 5): the row loop costs two cycles per issue plus a constant whatever follows fmull (faddp directly, or add and cmp first), so the instructions after an x87 memory-operand instruction do not issue while it completes", "status": "derived", "unit": "boolean", "value": true}}`
- `calibration_status`: shared entry 1 below.

### bounds

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "ZF/SF after imul are architecturally undefined; the model leaves them unchanged", "bound under line_tracking: each line costs its cold level once and L1 afterwards (capacity and prefetch timing ignored)", "memory concurrency bound: distinct missing lines x level latency / 8 outstanding misses per core; ignores the L2 hardware prefetcher"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- `prediction.result_class`: `{"class": "conditional_bound", "conditions": "valid under the model's resource and latency assumptions listed in 'assumptions'; a bound on this model, not a hardware guarantee"}`
- assumed/derived `parameters_used`: `{"latency.memory": {"source": "S6-03 memory.load_lat 356.53 per dependent hop at one thread (idle) minus the first-level TLB miss of 29 cycles (tlb.l1_miss_penalty_cycles): the measured chain touches a new 4 KiB page at every hop and the TLB sub-model charges that miss explicitly. 0.2.x used 357 and double-counted it when the TLB was modeled.", "status": "derived", "unit": "cycles", "value": 328}, "latency.scalar_extend_extra": {"source": "evidence E (estimate), inferred: plain integer sign- or zero-extension costs what mov does; no KNC source (R02 p.34 Table 3-1 lists no MOVSX/MOVZX; never measured on the card). Lead decision 2026-11-15.", "status": "assumed", "unit": "cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto", "value": 0}, "latency.x87_control": {"source": "prior from the published Pentium (P5) instruction timings (FLDCW 7 clocks; FNSTCW and FNSTSW are 2). Not measured on KNC; all three are charged the FLDCW value.", "status": "assumed", "unit": "cycles", "value": 7}, "latency.x87_move": {"source": "evidence E (estimate), inferred: same pipeline as the measured x87 add (S6-03 x87_add.lat 3.02), no KNC source for fld/fst/fxch/fldz; fld from memory uses the load latency instead", "status": "assumed", "unit": "cycles", "value": 3}, "latency.x87_sqrt": {"source": "prior from the published Pentium (P5) instruction timings (FSQRT 70 clocks): the KNC core derives from the P54C design (R01 section 2.1) and the P5 figures that could be checked on the card agree (FDIV 39 vs 39.25 measured in S6-03; IMUL 10 in R02 p.56). Not measured on KNC.", "status": "assumed", "unit": "cycles", "value": 70}}`
- `calibration_status`: shared entry 1 below.

### hot/validate

- `status`: `"ok"`
- `functional_check`: `{"status": "not_run"}`
- `assumptions`: `[]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- assumed/derived `parameters_used`: `{}`
- `calibration_status`: shared entry 1 below.

### hot/functional

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- assumed/derived `parameters_used`: `{}`
- `calibration_status`: shared entry 2 below.

### hot/simulate

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged", "line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic", "TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled", "L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)", "memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled", "front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)", "front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)", "instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)", "a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing", "register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies", "x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores", "sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[{"constraint": "miss_stall", "context_cycles": 1751}, {"constraint": "x87_serial", "context_cycles": 730}, {"constraint": "spacing", "context_cycles": 98}, {"constraint": "dependency", "context_cycles": 53}]`
- top-level `result_class`: `"<absent>"`
- `prediction.result_class`: `{"class": "unvalidated_scenario_estimate", "reasons": ["the kernel declares no provenance.shape, so no held-out validation can vouch for it", "TLB, L2 hardware prefetcher and memory service sub-models are part of the memory domain (scenario: tlb=auto, hardware_prefetcher=auto, memory_service=auto)", "the trace misses L1 (0 L2, 7 memory accesses): cache behaviour is modeled, not validated"]}`
- assumed/derived `parameters_used`: `{"frontend.taken_branch_core_bubble_cycles": {"source": "S8-01 C10 fixed-direction row: 6.22 per branch at one thread, 17.02 at four (three issues plus about one core cycle per unit); R02 ch.4 one-clock refill bubble. Hidden at one thread by the same-context spacing. Scope: forward transfers only (S8-01 C9 register chains at two threads show no cost for the loop back-edge).", "status": "derived", "unit": "core issue cycles lost after a taken branch", "value": 1}, "l2.hw_prefetch_depth_lines": {"source": "S6-03 memory.load_rt 37.35 ticks per sequential line at one thread with the hardware prefetcher active: the HWP sub-model reproduces 37.4 with depth 16 (40.2 at 12, 51.4 at 8); at four threads it gives 85.5 against 77.9 (see references/validation.md)", "status": "derived", "unit": "lines ahead per confirmed stream", "value": 16}, "latency.branch_taken_bubble": {"source": "S8-01 C9: loop costs about 2 ticks per vector op plus 2 per loop branch at one thread (the branch costs its issue slot only)", "status": "derived", "unit": "cycles", "value": 0}, "latency.mask_op": {"source": "S6-03 kand.lat 2.08 bounds it at <=2; 1 assumed like scalar", "status": "assumed", "unit": "cycles", "value": 1}, "latency.memory": {"source": "S6-03 memory.load_lat 356.53 per dependent hop at one thread (idle) minus the first-level TLB miss of 29 cycles (tlb.l1_miss_penalty_cycles): the measured chain touches a new 4 KiB page at every hop and the TLB sub-model charges that miss explicitly. 0.2.x used 357 and double-counted it when the TLB was modeled.", "status": "derived", "unit": "cycles", "value": 328}, "latency.scalar_extend_extra": {"source": "evidence E (estimate), inferred: plain integer sign- or zero-extension costs what mov does; no KNC source (R02 p.34 Table 3-1 lists no MOVSX/MOVZX; never measured on the card). Lead decision 2026-11-15.", "status": "assumed", "unit": "cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto", "value": 0}, "latency.store_to_load_same_line": {"source": "S8-12 C9 memory chain u1 11.07 per link = folded-load add (4) + store-to-load path; spill_reload.lat 12.11 = path + plain load (5)", "status": "derived", "unit": "cycles after a store issues before a load of the same line sees the data", "value": 7}, "latency.vector_load_l1": {"source": "S6-03 spill_reload.lat 12.11 = store-to-load path (7, from c9.memory.u1) + load-to-use; R08 documents 3 for vector loads", "status": "derived", "unit": "cycles, L1 hit plain vector load to dependent use", "value": 5}, "latency.x87_compare": {"source": "assumed equal to the measured x87 add latency", "status": "assumed", "unit": "cycles", "value": 3}, "latency.x87_control": {"source": "prior from the published Pentium (P5) instruction timings (FLDCW 7 clocks; FNSTCW and FNSTSW are 2). Not measured on KNC; all three are charged the FLDCW value.", "status": "assumed", "unit": "cycles", "value": 7}, "latency.x87_load": {"source": "S12-31 gas_0 488.9 and adj_0 433.5 cycles per 27-product row fix the sum of this value and the fmull memory form (operand read plus multiply) at 7 cycles; the split 3 + (1 + 3) keeps the measured x87 multiply latency of 3 and the documented one-cycle scalar load (R08)", "status": "derived", "unit": "cycles from issue until the loaded value is on the x87 stack", "value": 3}, "latency.x87_mem_operand_load": {"source": "see latency.x87_load: the sum is measured, the split is assumed (R08: one-cycle scalar load)", "status": "derived", "unit": "cycles for the memory operand of an x87 arithmetic instruction before the operation starts", "value": 1}, "latency.x87_move": {"source": "evidence E (estimate), inferred: same pipeline as the measured x87 add (S6-03 x87_add.lat 3.02), no KNC source for fld/fst/fxch/fldz; fld from memory uses the load latency instead", "status": "assumed", "unit": "cycles", "value": 3}, "pairing.extend_v_pairs": {"source": "evidence E (estimate), inferred: treated like the other scalar integer ops of R02 p.34 Table 3-1, which does not list them; no KNC source. Lead decision 2026-11-15.", "status": "assumed", "unit": "boolean: may movslq, movs*, movz*, cltq, cltd, cqto issue in the V slot", "value": true}, "pairing.load_store_pair": {"source": "S6-03 spill_reload.rt at four threads: 1.07 core cycles per vector store plus reload, so a U-pipe load and a V-pipe store issue in one cycle; the L1 access limit is applied to loads only", "status": "derived", "unit": "boolean", "value": true}, "pairing.u_instruction_can_be_branch": {"source": "evidence E (estimate), model assumption without a KNC source: an instruction after a control transfer in the same issue slot is not paired", "status": "assumed", "unit": "boolean", "value": false}, "store.load_after_store_interlock_cycles": {"source": "S6-03 spill_reload.rt 4.20/4.26 per pair at two/four threads and S8-12 C9 memory chains u2/u4 8.56/8.30 per link at one thread (two issues plus four cycles); vector rows only, applied to scalar stores as well (assumed)", "status": "derived", "unit": "cycles after a store before the same context may issue a load", "value": 4}, "x87.mem_operand_serializes": {"source": "S12-31 microbench (card windows 3 and 5): the row loop costs two cycles per issue plus a constant whatever follows fmull (faddp directly, or add and cmp first), so the instructions after an x87 memory-operand instruction do not issue while it completes", "status": "derived", "unit": "boolean", "value": true}}`
- `calibration_status`: shared entry 1 below.

### hot/bounds

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range", "OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged", "bound under line_tracking: each line costs its cold level once and L1 afterwards (capacity and prefetch timing ignored)", "memory concurrency bound: distinct missing lines x level latency / 8 outstanding misses per core; ignores the L2 hardware prefetcher"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- `prediction.result_class`: `{"class": "conditional_bound", "conditions": "valid under the model's resource and latency assumptions listed in 'assumptions'; a bound on this model, not a hardware guarantee"}`
- assumed/derived `parameters_used`: `{"latency.mask_op": {"source": "S6-03 kand.lat 2.08 bounds it at <=2; 1 assumed like scalar", "status": "assumed", "unit": "cycles", "value": 1}, "latency.memory": {"source": "S6-03 memory.load_lat 356.53 per dependent hop at one thread (idle) minus the first-level TLB miss of 29 cycles (tlb.l1_miss_penalty_cycles): the measured chain touches a new 4 KiB page at every hop and the TLB sub-model charges that miss explicitly. 0.2.x used 357 and double-counted it when the TLB was modeled.", "status": "derived", "unit": "cycles", "value": 328}, "latency.scalar_extend_extra": {"source": "evidence E (estimate), inferred: plain integer sign- or zero-extension costs what mov does; no KNC source (R02 p.34 Table 3-1 lists no MOVSX/MOVZX; never measured on the card). Lead decision 2026-11-15.", "status": "assumed", "unit": "cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto", "value": 0}, "latency.vector_load_l1": {"source": "S6-03 spill_reload.lat 12.11 = store-to-load path (7, from c9.memory.u1) + load-to-use; R08 documents 3 for vector loads", "status": "derived", "unit": "cycles, L1 hit plain vector load to dependent use", "value": 5}, "latency.x87_compare": {"source": "assumed equal to the measured x87 add latency", "status": "assumed", "unit": "cycles", "value": 3}, "latency.x87_control": {"source": "prior from the published Pentium (P5) instruction timings (FLDCW 7 clocks; FNSTCW and FNSTSW are 2). Not measured on KNC; all three are charged the FLDCW value.", "status": "assumed", "unit": "cycles", "value": 7}, "latency.x87_move": {"source": "evidence E (estimate), inferred: same pipeline as the measured x87 add (S6-03 x87_add.lat 3.02), no KNC source for fld/fst/fxch/fldz; fld from memory uses the load latency instead", "status": "assumed", "unit": "cycles", "value": 3}}`
- `calibration_status`: shared entry 1 below.

### fildl-repro

- `status`: `"ok"`
- `functional_check`: `{"checked": 1, "mismatches": [], "status": "ok"}`
- `assumptions`: `["x87 precision control is 53-bit: results round to that significand with the extended exponent range"]`
- `unsupported`: `[]`
- `limiting_constraints`: `[]`
- top-level `result_class`: `"<absent>"`
- assumed/derived `parameters_used`: `{}`
- `calibration_status`: shared entry 2 below.

### Shared calibration_status values

1. `{"held_out_validation_cases": 160, "not_validated_shapes": {"x87_sparse_rows_l1": {"evidence": "S12-30 small cases, 16 held-out rows, one thread", "median_abs_error_pct": 16.0, "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate", "worst_abs_error_pct": 17.9}}, "note": "Simulated/analytical outputs are model results, never native measurements. ", "state": "imported_microbenchmarks_with_compiled_heldout_check", "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).", "synthetic": false, "validated_shapes": {"l1_l2_dependent_loads": {"evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains", "median_abs_error_pct": 2.0, "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)", "worst_abs_error_pct": 14.0}, "l1_resident_stores_prefetch_pairing": {"evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing", "median_abs_error_pct": 2.0, "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing", "worst_abs_error_pct": 12.0}, "register_vector_chain_l1": {"evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads", "median_abs_error_pct": 1.0, "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)", "worst_abs_error_pct": 11.0}, "scalar_mask_l1": {"evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4", "median_abs_error_pct": 1.0, "note": "scalar integer and mask chains, pairing, address-generation interlock", "worst_abs_error_pct": 5.0}, "x87_register_chain": {"evidence": "S6-03 x87_add/mul/div .lat/.rt rows", "median_abs_error_pct": 1.0, "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured", "worst_abs_error_pct": 3.0}, "x87_row_loop_l1": {"evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread", "median_abs_error_pct": 2.9, "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included", "worst_abs_error_pct": 3.8}, "x87_sparse_rows_l2": {"evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread", "median_abs_error_pct": 3.7, "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2", "worst_abs_error_pct": 6.6}, "x87_sparse_rows_memory_stream": {"evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread", "median_abs_error_pct": 3.7, "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads", "worst_abs_error_pct": 4.1}}}`

2. `null`

## Reproduce

From Git Bash at the worktree root, with the existing pinned upstream sources:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
make -C mk -j4 card
make -C mk -j4 x86
bash scripts/run_x86.sh small 1
python C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py capabilities --out twin/capabilities --force
python C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py functional twin/fildl-repro.json --trace --out twin/fildl-repro --force
bash twin/run_hot.sh
bash twin/run.sh
python twin/write_report.py
python tests/test_twin_040.py
python tests/test_twin.py
```

The committed capture files and independent S1-04 expected bits are reused.
Full disassemblies, extracted kernels, final memory snapshots, gravity trace
and issue logs remain ignored by `twin/.gitignore`. Compact results and the
16 functional traces remain reviewable evidence. The card executable and
runtimes are staged under `dist/card/`; `scripts/card-check.sh` prints the
lead's run instructions. No card access, downloads, installs or git writes
were performed.
