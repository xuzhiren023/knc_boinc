# knc-twin analytical_bound: OK

- Engine 0.4.0, 2026-11-16T12:49:02Z
- Profile card-7120-measured v0.3.0 (hash 2058f0ec2d80...)
- Calibration: imported_microbenchmarks_with_compiled_heldout_check. Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).
- Input C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\log-kernel.json (sha256 67c25b73695e...)
- Scale: core; representation: normalized-records
- Functional check: ok

**trace lower bound: 2597 cycles (binding term: dependency_critical_path); conditional_bound**

## Result
- result_class: conditional_bound
- kind: trace_lower_bound
- lower_bound_cycles: 2597
- binding_term: dependency_critical_path
- statement: No schedule of these dynamic instructions on this core model can complete in fewer cycles than the largest term; the terms are independent optimistic constraints (issue slots, same-context spacing, resource occupancy, dependency chains, memory concurrency).

| bound term | cycles |
|---|---:|
| dependency_critical_path | 2597 |
| memory_concurrency | 287 |
| per_context_issue_spacing | 203 |
| core_issue_events | 102 |
| x87_unit_occupancy | 92 |
| l1_port | 33 |

| context | dynamic_instructions | min_issue_events | spacing_bound_cycles | critical_path_cycles |
|---|---|---|---|---|
| 0 | 136 | 102 | 203 | 2597 |

## Assumptions
- x87 precision control is 53-bit: results round to that significand with the extended exponent range
- OF after a shift by more than 1 is architecturally undefined; the model leaves it unchanged
- bound under line_tracking: each line costs its cold level once and L1 afterwards (capacity and prefetch timing ignored)
- memory concurrency bound: distinct missing lines x level latency / 8 outstanding misses per core; ignores the L2 hardware prefetcher

## Parameters consulted
| parameter | value | status | unit |
|---|---|---|---|
| core.min_issue_gap_same_context | 2 | documented | cycles between two issue events of one context |
| l1.accesses_per_cycle | 1 | documented | L1 data accesses per core cycle (loads and stores, not prefetches) |
| l1.outstanding_demand_misses_per_core | 8 | documented | cache lines |
| latency.l2_hit | 24 | measured | cycles |
| latency.mask_op | 1 | assumed | cycles |
| latency.memory | 328 | derived | cycles |
| latency.scalar_alu | 1 | documented | cycles |
| latency.scalar_extend_extra | 0 | assumed | cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto |
| latency.scalar_load_l1 | 3 | measured | cycles |
| latency.vector_load_l1 | 5 | derived | cycles, L1 hit plain vector load to dependent use |
| latency.x87_add | 3 | measured | cycles |
| latency.x87_compare | 3 | assumed | cycles |
| latency.x87_control | 7 | assumed | cycles |
| latency.x87_move | 3 | assumed | cycles |
| latency.x87_mul | 3 | measured | cycles |
| occupancy.x87_mul | 2 | measured | core cycles |
| pairing.v_eligible_classes | ['scalar_alu', 'scalar_rmw', 'scalar_load', 'scalar_store', 'branch', 'mask_op', 'vector_store', 'vector_packstore', 'prefetch_l1', 'prefetch_l2'] | documented | instruction classes that may issue on the V pipe |

Invocation: `C:/Users/xuzhi/.claude/skills/knc-twin/scripts/knc_twin.py bounds twin/log-kernel.json --profile card-7120-measured --out twin/hot/bounds --force`
Artifacts: C:\Users\xuzhi\Documents\knc-boinc\.work\S1-05\twin\hot\bounds
Python execution time: 0.522 s (not KNC time)
