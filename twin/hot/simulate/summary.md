# knc-twin timing_prediction: OK

- Engine 0.4.0, 2026-11-16T12:49:01Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-kernel.json (sha256 67c25b73695e...)
- Scale: core; representation: normalized-records
- Functional check: ok

**predicted 2778 core cycles (2778.000 per unit) for 136 dynamic instructions on 1 context(s); unvalidated_scenario_estimate**

## Result
- result_class: unvalidated_scenario_estimate
- predicted_cycles: 2778
- predicted_cycles_per_unit: 2778
- issue_span_cycles: 2776
- unit_of_work: one log_rn call, first real small input
- unit_count: 1
- dynamic_instructions: 136
- issue_events: 125
- core_issue_utilization: 0.045
- pair_fraction: 0.1618
- kind: timing_prediction_core_cycles
- functional_exactness: exact

| context | dynamic_instructions | issued | pairs | first_issue | last_issue | completion |
|---|---|---|---|---|---|---|
| 0 | 136 | 136 | 11 | 0 | 2775 | 2778 |

## Limiting constraints
- constraint=miss_stall, context_cycles=1751
- constraint=x87_serial, context_cycles=730
- constraint=spacing, context_cycles=98
- constraint=dependency, context_cycles=53

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic
- TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled
- L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)
- memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled
- front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)
- front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)
- instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)
- a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing
- register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies
- x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores
- sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source

## Parameters consulted
| parameter | value | status | unit |
|---|---|---|---|
| core.contexts | 4 | documented | hardware threads per core |
| core.min_issue_gap_same_context | 2 | documented | cycles between two issue events of one context |
| frontend.slow_prefix_decode_cycles | 2 | documented | decode cycles per prefix |
| frontend.taken_branch_core_bubble_cycles | 1 | derived | core issue cycles lost after a taken branch |
| l1.accesses_per_cycle | 1 | documented | L1 data accesses per core cycle (loads and stores, not prefetches) |
| l1.demand_load_miss_stalls_context | True | documented | boolean |
| l1.outstanding_demand_misses_per_core | 8 | documented | cache lines |
| l1.size_bytes | 32768 | documented | bytes |
| l1.store_miss_stalls_context | True | measured | boolean |
| l1.ways | 8 | documented | ways |
| l2.hw_prefetch_depth_lines | 16 | derived | lines ahead per confirmed stream |
| l2.hw_prefetch_max_stride_lines | 2 | documented | lines |
| l2.hw_prefetch_streams | 16 | documented | streams per core |
| l2.hw_prefetch_trains_on_stores | True | documented | boolean |
| l2.size_bytes | 524288 | documented | bytes |
| l2.ways | 8 | documented | ways |
| latency.agi_cycles | 3 | measured | cycles |
| latency.branch_taken_bubble | 0 | derived | cycles |
| latency.mask_op | 1 | assumed | cycles |
| latency.memory | 328 | derived | cycles |
| latency.scalar_alu | 1 | documented | cycles |
| latency.scalar_extend_extra | 0 | assumed | cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto |
| latency.scalar_load_l1 | 3 | measured | cycles |
| latency.store_to_load_same_line | 7 | derived | cycles after a store issues before a load of the same line sees the data |
| latency.vector_load_l1 | 5 | derived | cycles, L1 hit plain vector load to dependent use |
| latency.x87_add | 3 | measured | cycles |
| latency.x87_compare | 3 | assumed | cycles |
| latency.x87_control | 7 | assumed | cycles |
| latency.x87_load | 3 | derived | cycles from issue until the loaded value is on the x87 stack |
| latency.x87_mem_operand_load | 1 | derived | cycles for the memory operand of an x87 arithmetic instruction before the operation starts |
| latency.x87_move | 3 | assumed | cycles |
| latency.x87_mul | 3 | measured | cycles |
| memory.core_service_cycles_per_line | 20 | measured | core cycles between memory fills for one core (sequential stream, hardware prefetcher active) |
| occupancy.x87_mul | 2 | measured | core cycles |
| pairing.dependent_pairs_allowed | [['cmp', 'jcc'], ['test', 'jcc']] | documented | U/V pairs allowed despite a flag dependency |
| pairing.encoding_rules | {'max_bytes': 8, 'no_displacement_and_immediate': True, 'no_vex_mvex_with_disp32': True} | documented | rules |
| pairing.extend_v_pairs | True | assumed | boolean: may movslq, movs*, movz*, cltq, cltd, cqto issue in the V slot |
| pairing.load_store_pair | True | derived | boolean |
| pairing.u_instruction_can_be_branch | False | assumed | boolean |
| pairing.v_eligible_classes | ['scalar_alu', 'scalar_rmw', 'scalar_load', 'scalar_store', 'branch', 'mask_op', 'vector_store', 'vector_packstore', 'prefetch_l1', 'prefetch_l2'] | documented | instruction classes that may issue on the V pipe |
| pairing.v_nop_pairs | False | measured | boolean |
| pairing.x87_pairs_with_scalar | False | measured | boolean |
| store.load_after_store_interlock_cycles | 4 | derived | cycles after a store before the same context may issue a load |
| tlb.l1_entries_4k | 64 | measured | pages |
| tlb.l1_miss_penalty_cycles | 29 | measured | cycles |
| x87.mem_operand_serializes | True | derived | boolean |

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py simulate twin/log-kernel.json --profile card-7120-measured --out twin/hot/simulate --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\hot\simulate
Python execution time: 0.519 s (not KNC time)
