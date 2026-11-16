# S1-06: large-case gravity multi-core check

**Incomplete: no supported 128-body/context scaling result.** The question whether gravity retains its per-core speed from one to eight cores remains unanswered. The runs below are explicitly one-body diagnostics, not the requested slice experiment. All successful timing outputs have result class `unvalidated_scenario_estimate`. No card run or card speed claim is made.

## Work and captured inputs

The actual loop in `nbody/src/nbody_grav.c` has `schedule(dynamic, 4096 / sizeof(accels[0]))`. The verified x86/card `mwvector` size is 32 bytes, so each dynamically acquired contiguous chunk contains 128 bodies (the final chunk has 32). At 20,000 bodies there are 157 chunks, not 240 nonempty thread slices. Chunk ownership at 240 threads is runtime dependent; it is not a static `20000/240` partition. The target experiment would give each of the 4 or 32 contexts a distinct full 128-body chunk, maintaining that size in all configurations.

`twin/capture_multicore.sh` extends the S1-03 prepare_capture.py/capture_log.c host instrumentation without changing pinned upstream code or card code. It snapshots the first force step of the actual large workunit at seed 670828913 with one x86 thread: ctx, state, eps2, all 20,000 bodies, and every reachable threaded-tree node. Raw bytes are init.memory file blocks with their original pointer addresses. Offset node blocks are repacked into small files with byte equality checks, avoiding repeated whole-file hashing by the unchanged loader. Expected XYZ accelerations for the first 4,096 bodies are independently written by the host; unspecified vector w is excluded. `capture-summary.json` records layout agreement and zero tree-incest diagnostics. Full generated captures and kernels are ignored.

The application was rebuilt from unchanged sources/flags first with `mk/Makefile` for card and x86, exporting TMPDIR, TMP and TEMP to `$PWD/build/tmp` before compiling. The rebuilt card app and the unchanged S1-05 `nbGravity` region are reused: all 202 binary records are retained, followed by the same cold-error exit sentinel. The normal return and output stores remain. No arithmetic, dependency, encoding, stub or model parameter is changed. `twin/run.sh` and `twin/cut_gravity.py` regenerate/check the region.

## Why the requested result is unavailable

1. The S1-05 region is a single nbGravity call (one body), with no caller loop over bodies. The supported input format offers no sequence of independently initialized function calls in a stream. Replacing it with a hand-written loop or multiplying a cold single-body time by 128 would not preserve the requested binary region and cache history. The binary caller nbMapForceBody._omp_fn.0 calls GOMP_loop_nonmonotonic_dynamic_start/next; retaining it requires OpenMP runtime modeling (unit/ring rejects stubs and synchronization). A faithful compiled body-loop driver or engine support for repeated calls with per-call arguments is needed.
2. The actual sample-loop probe returns `unsupported`: "loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled". The region's loop iterates tree nodes, not bodies. Unit/ring dispatch also bypasses the core sampler; adding --sample-loop cannot be taken as proof of sampled multi-core execution.
3. The requested compare commands reject core versus unit/ring. Compare requires equal scale, profile hash and unit_of_work. Unit/ring automatically loads multicore-assumed.json, so even the same named card-7120-measured profile yields a different hash from core. The 4 versus 32 total bodies also gives different aggregate work counts. No result envelope has been rewritten to bypass these checks.

4. Unit/ring diagnostics fail exact functional comparison against the independent x86 capture. The first difference is body 1024 Y: got 0x4062853da39aab69 versus expected 0x4062853da39aab6a. Six components differ across the 32 bodies. This does not establish a model or compiler defect: no card result or instruction-level native oracle is available. No tolerance, kernel, or expected bits were changed; no timing from a functional_mismatch run is reported.

## Diagnostic commands and table

`bash twin/run_multicore.sh` executes simulate at core (1 x 4), unit (8 x 4) and ring (8 x 4), always with card-7120-measured, functional traces, cold-memory line tracking and all-predicted branches. Each context computes only the first body of its assigned 128-body chunk: body indices 0, 128, ..., 3968 (baseline uses the first four). Thus the runs have equal **one-body** work per context, and do not measure chunk reuse or a steady-state tree footprint. They are not sample-loop extrapolations. Runs have a 1,740-second engine budget, below 30 minutes. An external 1,790-second timeout also caps each simulation process, including initialization. The complete command output is in the Engineer report and `twin/multicore/run.log`.

Per-context cycles/body below use each context's completion field when exposed; the per-core completion envelope is also reported. The engine's aggregate predicted_cycles_per_unit divides by all detailed bodies and is **not** per-context latency. L2 miss fraction is `memory / (l2_hits + memory)` from the reported access-level counters (not an independently measured cache-line miss rate). Ring and memory queue waits are not mutually exclusive processor stall-cycle counters and cannot be summed into a stall share.

| Diagnostic | Status | Context completion cycles/body (range; exact values below) | Per-core completion envelope | L2 miss fraction | Ring/memory stall share |
|---|---|---|---|---|---|
| core (one body/context) | ok | 432228..572779 | 572779 | 0.564661 | unavailable: no separated share in result.json |
| unit | functional_mismatch | unavailable | unavailable | unavailable | unavailable |
| ring | functional_mismatch | unavailable | unavailable | unavailable | unavailable |

These diagnostics do not establish a 1-to-8-core change for 128-body slices. No absolute cycle prediction above is a card-speed finding. S1-05 found gravity bounds **43,656** above simulate **33,622** on the same kernel: an open twin defect. Only simulate and compare are used for this multi-core investigation; bounds is not used as a timing interval. Even after the blockers are fixed, report the relative change from one to eight cores, with this caveat.

## Exact result evidence

### core

```json
{
  "status": "ok",
  "message": "predicted 572779 core cycles (143194.750 per unit) for 146712 dynamic instructions on 4 context(s); unvalidated_scenario_estimate",
  "python_execution_seconds": 31.6182,
  "functional_check": {
    "checked": 4,
    "mismatches": [],
    "status": "ok"
  },
  "assumptions": [
    "x87 precision control is 53-bit: results round to that significand with the extended exponent range",
    "ZF/SF after imul are architecturally undefined; the model leaves them unchanged",
    "line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic",
    "TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled",
    "L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)",
    "memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled",
    "front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)",
    "front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)",
    "instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)",
    "a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing",
    "register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies",
    "x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores",
    "sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source"
  ],
  "unsupported": [],
  "limiting_constraints": [
    {
      "constraint": "x87_serial",
      "context_cycles": 545586
    },
    {
      "constraint": "resource",
      "context_cycles": 515164
    },
    {
      "constraint": "miss_stall",
      "context_cycles": 294719
    },
    {
      "constraint": "dependency",
      "context_cycles": 281969
    }
  ],
  "calibration_status": {
    "held_out_validation_cases": 160,
    "not_validated_shapes": {
      "x87_sparse_rows_l1": {
        "evidence": "S12-30 small cases, 16 held-out rows, one thread",
        "median_abs_error_pct": 16.0,
        "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate",
        "worst_abs_error_pct": 17.9
      }
    },
    "note": "Simulated/analytical outputs are model results, never native measurements. ",
    "state": "imported_microbenchmarks_with_compiled_heldout_check",
    "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).",
    "synthetic": false,
    "validated_shapes": {
      "l1_l2_dependent_loads": {
        "evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains",
        "median_abs_error_pct": 2.0,
        "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)",
        "worst_abs_error_pct": 14.0
      },
      "l1_resident_stores_prefetch_pairing": {
        "evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing",
        "median_abs_error_pct": 2.0,
        "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing",
        "worst_abs_error_pct": 12.0
      },
      "register_vector_chain_l1": {
        "evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads",
        "median_abs_error_pct": 1.0,
        "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)",
        "worst_abs_error_pct": 11.0
      },
      "scalar_mask_l1": {
        "evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4",
        "median_abs_error_pct": 1.0,
        "note": "scalar integer and mask chains, pairing, address-generation interlock",
        "worst_abs_error_pct": 5.0
      },
      "x87_register_chain": {
        "evidence": "S6-03 x87_add/mul/div .lat/.rt rows",
        "median_abs_error_pct": 1.0,
        "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured",
        "worst_abs_error_pct": 3.0
      },
      "x87_row_loop_l1": {
        "evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread",
        "median_abs_error_pct": 2.9,
        "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included",
        "worst_abs_error_pct": 3.8
      },
      "x87_sparse_rows_l2": {
        "evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread",
        "median_abs_error_pct": 3.7,
        "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2",
        "worst_abs_error_pct": 6.6
      },
      "x87_sparse_rows_memory_stream": {
        "evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread",
        "median_abs_error_pct": 3.7,
        "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads",
        "worst_abs_error_pct": 4.1
      }
    }
  },
  "result_class": {
    "class": "unvalidated_scenario_estimate",
    "reasons": [
      "the kernel declares no provenance.shape, so no held-out validation can vouch for it",
      "TLB, L2 hardware prefetcher and memory service sub-models are part of the memory domain (scenario: tlb=auto, hardware_prefetcher=auto, memory_service=auto)",
      "the trace misses L1 (1020 L2, 1323 memory accesses): cache behaviour is modeled, not validated"
    ]
  },
  "parameters_used": {
    "frontend.taken_branch_core_bubble_cycles": {
      "source": "S8-01 C10 fixed-direction row: 6.22 per branch at one thread, 17.02 at four (three issues plus about one core cycle per unit); R02 ch.4 one-clock refill bubble. Hidden at one thread by the same-context spacing. Scope: forward transfers only (S8-01 C9 register chains at two threads show no cost for the loop back-edge).",
      "status": "derived",
      "unit": "core issue cycles lost after a taken branch",
      "value": 1
    },
    "l2.hw_prefetch_depth_lines": {
      "source": "S6-03 memory.load_rt 37.35 ticks per sequential line at one thread with the hardware prefetcher active: the HWP sub-model reproduces 37.4 with depth 16 (40.2 at 12, 51.4 at 8); at four threads it gives 85.5 against 77.9 (see references/validation.md)",
      "status": "derived",
      "unit": "lines ahead per confirmed stream",
      "value": 16
    },
    "latency.branch_taken_bubble": {
      "source": "S8-01 C9: loop costs about 2 ticks per vector op plus 2 per loop branch at one thread (the branch costs its issue slot only)",
      "status": "derived",
      "unit": "cycles",
      "value": 0
    },
    "latency.memory": {
      "source": "S6-03 memory.load_lat 356.53 per dependent hop at one thread (idle) minus the first-level TLB miss of 29 cycles (tlb.l1_miss_penalty_cycles): the measured chain touches a new 4 KiB page at every hop and the TLB sub-model charges that miss explicitly. 0.2.x used 357 and double-counted it when the TLB was modeled.",
      "status": "derived",
      "unit": "cycles",
      "value": 328
    },
    "latency.scalar_extend_extra": {
      "source": "evidence E (estimate), inferred: plain integer sign- or zero-extension costs what mov does; no KNC source (R02 p.34 Table 3-1 lists no MOVSX/MOVZX; never measured on the card). Lead decision 2026-11-15.",
      "status": "assumed",
      "unit": "cycles added to the plain mov/ALU (register form) or scalar load (memory form) latency of movslq, movs*, movz*, cltq, cltd, cqto",
      "value": 0
    },
    "latency.store_to_load_same_line": {
      "source": "S8-12 C9 memory chain u1 11.07 per link = folded-load add (4) + store-to-load path; spill_reload.lat 12.11 = path + plain load (5)",
      "status": "derived",
      "unit": "cycles after a store issues before a load of the same line sees the data",
      "value": 7
    },
    "latency.x87_control": {
      "source": "prior from the published Pentium (P5) instruction timings (FLDCW 7 clocks; FNSTCW and FNSTSW are 2). Not measured on KNC; all three are charged the FLDCW value.",
      "status": "assumed",
      "unit": "cycles",
      "value": 7
    },
    "latency.x87_load": {
      "source": "S12-31 gas_0 488.9 and adj_0 433.5 cycles per 27-product row fix the sum of this value and the fmull memory form (operand read plus multiply) at 7 cycles; the split 3 + (1 + 3) keeps the measured x87 multiply latency of 3 and the documented one-cycle scalar load (R08)",
      "status": "derived",
      "unit": "cycles from issue until the loaded value is on the x87 stack",
      "value": 3
    },
    "latency.x87_mem_operand_load": {
      "source": "see latency.x87_load: the sum is measured, the split is assumed (R08: one-cycle scalar load)",
      "status": "derived",
      "unit": "cycles for the memory operand of an x87 arithmetic instruction before the operation starts",
      "value": 1
    },
    "latency.x87_move": {
      "source": "evidence E (estimate), inferred: same pipeline as the measured x87 add (S6-03 x87_add.lat 3.02), no KNC source for fld/fst/fxch/fldz; fld from memory uses the load latency instead",
      "status": "assumed",
      "unit": "cycles",
      "value": 3
    },
    "latency.x87_sqrt": {
      "source": "prior from the published Pentium (P5) instruction timings (FSQRT 70 clocks): the KNC core derives from the P54C design (R01 section 2.1) and the P5 figures that could be checked on the card agree (FDIV 39 vs 39.25 measured in S6-03; IMUL 10 in R02 p.56). Not measured on KNC.",
      "status": "assumed",
      "unit": "cycles",
      "value": 70
    },
    "pairing.extend_v_pairs": {
      "source": "evidence E (estimate), inferred: treated like the other scalar integer ops of R02 p.34 Table 3-1, which does not list them; no KNC source. Lead decision 2026-11-15.",
      "status": "assumed",
      "unit": "boolean: may movslq, movs*, movz*, cltq, cltd, cqto issue in the V slot",
      "value": true
    },
    "pairing.load_store_pair": {
      "source": "S6-03 spill_reload.rt at four threads: 1.07 core cycles per vector store plus reload, so a U-pipe load and a V-pipe store issue in one cycle; the L1 access limit is applied to loads only",
      "status": "derived",
      "unit": "boolean",
      "value": true
    },
    "pairing.u_instruction_can_be_branch": {
      "source": "evidence E (estimate), model assumption without a KNC source: an instruction after a control transfer in the same issue slot is not paired",
      "status": "assumed",
      "unit": "boolean",
      "value": false
    },
    "store.load_after_store_interlock_cycles": {
      "source": "S6-03 spill_reload.rt 4.20/4.26 per pair at two/four threads and S8-12 C9 memory chains u2/u4 8.56/8.30 per link at one thread (two issues plus four cycles); vector rows only, applied to scalar stores as well (assumed)",
      "status": "derived",
      "unit": "cycles after a store before the same context may issue a load",
      "value": 4
    },
    "x87.mem_operand_serializes": {
      "source": "S12-31 microbench (card windows 3 and 5): the row loop costs two cycles per issue plus a constant whatever follows fmull (faddp directly, or add and cmp first), so the instructions after an x87 memory-operand instruction do not issue while it completes",
      "status": "derived",
      "unit": "boolean",
      "value": true
    }
  },
  "per_context": {
    "0": {
      "0": {
        "completion": 524052,
        "dynamic_instructions": 40319,
        "first_issue": 0,
        "issued": 40319,
        "last_issue": 524049,
        "pairs": 1308,
        "stall_cycles": {
          "agi": 96,
          "core_busy": 9045,
          "dependency": 76636,
          "flags": 10453,
          "miss_stall": 64989,
          "not_picked": 17826,
          "resource": 144145,
          "spacing": 27413,
          "store_interlock": 2477,
          "x87_serial": 131959
        }
      },
      "1": {
        "completion": 572779,
        "dynamic_instructions": 42477,
        "first_issue": 1,
        "issued": 42477,
        "last_issue": 572776,
        "pairs": 1380,
        "stall_cycles": {
          "agi": 102,
          "core_busy": 9466,
          "dependency": 80580,
          "flags": 7158,
          "miss_stall": 91867,
          "not_picked": 17027,
          "resource": 133689,
          "spacing": 28757,
          "store_interlock": 2608,
          "x87_serial": 160426
        }
      },
      "2": {
        "completion": 432228,
        "dynamic_instructions": 25064,
        "first_issue": 2,
        "issued": 25064,
        "last_issue": 432225,
        "pairs": 863,
        "stall_cycles": {
          "agi": 96,
          "core_busy": 7390,
          "dependency": 50970,
          "flags": 6001,
          "miss_stall": 85821,
          "not_picked": 13639,
          "resource": 95197,
          "spacing": 16882,
          "store_interlock": 1403,
          "x87_serial": 130626
        }
      },
      "3": {
        "completion": 493583,
        "dynamic_instructions": 38852,
        "first_issue": 3,
        "issued": 38852,
        "last_issue": 493580,
        "pairs": 1255,
        "stall_cycles": {
          "agi": 87,
          "core_busy": 8596,
          "dependency": 73783,
          "flags": 10291,
          "miss_stall": 52042,
          "not_picked": 17691,
          "resource": 142133,
          "spacing": 26390,
          "store_interlock": 2396,
          "x87_serial": 122575
        }
      }
    }
  },
  "memory": {
    "cold_level": "memory",
    "stats": {
      "accesses": 56741,
      "hw_prefetch_hits": 0,
      "hw_prefetches": 10511,
      "inflight_waits": 696,
      "l1_hits": 54398,
      "l2_hits": 1020,
      "memory": 1323,
      "memory_service_waits": 10759,
      "outstanding_limit_stalls": 0,
      "prefetches": 0,
      "prefetches_useless": 0,
      "store_misses": 12,
      "tlb_misses": 953
    },
    "submodels": [
      "tlb",
      "hardware_prefetcher",
      "memory_service"
    ],
    "type": "line_tracking",
    "warm_ranges": 0
  },
  "background": null
}
```

### unit

```json
{
  "status": "functional_mismatch",
  "message": "candidate produced wrong results (6 mismatches); its timing is not reported as a valid result",
  "python_execution_seconds": 133.9548,
  "functional_check": {
    "checked": 32,
    "mismatches": [
      {
        "got": "69ab9aa33d856240",
        "want": "6aab9aa33d856240",
        "where": "mem[0x60008000]+8"
      },
      {
        "got": "f671a67973c008c0",
        "want": "ee71a67973c008c0",
        "where": "mem[0x6000b000]+16"
      },
      {
        "got": "a8bcf9cb3bde4940",
        "want": "a7bcf9cb3bde4940",
        "where": "mem[0x6000d000]+8"
      },
      {
        "got": "fb030bfe709661c0",
        "want": "fc030bfe709661c0",
        "where": "mem[0x60018000]+0"
      },
      {
        "got": "0ea184676cd260c0",
        "want": "0da184676cd260c0",
        "where": "mem[0x60019000]+0"
      },
      {
        "got": "b35c50a7b8ef3d40",
        "want": "b45c50a7b8ef3d40",
        "where": "mem[0x6001c000]+16"
      }
    ],
    "status": "mismatch"
  },
  "assumptions": [
    "x87 precision control is 53-bit: results round to that significand with the extended exponent range",
    "ZF/SF after imul are architecturally undefined; the model leaves them unchanged"
  ],
  "unsupported": [],
  "limiting_constraints": [],
  "calibration_status": {
    "note": "Simulated/analytical outputs are model results, never native measurements. ",
    "state": "unvalidated",
    "statement": "Low-core scaling and independent full-card validation pending.",
    "synthetic": false
  },
  "result_class": null,
  "parameters_used": {}
}
```

### ring

```json
{
  "status": "functional_mismatch",
  "message": "candidate produced wrong results (6 mismatches); its timing is not reported as a valid result",
  "python_execution_seconds": 129.7895,
  "functional_check": {
    "checked": 32,
    "mismatches": [
      {
        "got": "69ab9aa33d856240",
        "want": "6aab9aa33d856240",
        "where": "mem[0x60008000]+8"
      },
      {
        "got": "f671a67973c008c0",
        "want": "ee71a67973c008c0",
        "where": "mem[0x6000b000]+16"
      },
      {
        "got": "a8bcf9cb3bde4940",
        "want": "a7bcf9cb3bde4940",
        "where": "mem[0x6000d000]+8"
      },
      {
        "got": "fb030bfe709661c0",
        "want": "fc030bfe709661c0",
        "where": "mem[0x60018000]+0"
      },
      {
        "got": "0ea184676cd260c0",
        "want": "0da184676cd260c0",
        "where": "mem[0x60019000]+0"
      },
      {
        "got": "b35c50a7b8ef3d40",
        "want": "b45c50a7b8ef3d40",
        "where": "mem[0x6001c000]+16"
      }
    ],
    "status": "mismatch"
  },
  "assumptions": [
    "x87 precision control is 53-bit: results round to that significand with the extended exponent range",
    "ZF/SF after imul are architecturally undefined; the model leaves them unchanged"
  ],
  "unsupported": [],
  "limiting_constraints": [],
  "calibration_status": {
    "note": "Simulated/analytical outputs are model results, never native measurements. ",
    "state": "unvalidated",
    "statement": "Low-core scaling and independent full-card validation pending.",
    "synthetic": false
  },
  "result_class": null,
  "parameters_used": {}
}
```

### compare-unit

```json
{
  "status": "incompatible",
  "message": "results are not comparable: scale differs: 'core' vs 'unit'; profile hash differs (2058f0ec2d80 vs c6fec8a100f7): the model changed between baseline and candidate; unit of work differs: {'count': 4, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'} vs {'count': 32, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'}; candidate status is functional_mismatch, not ok",
  "python_execution_seconds": 0.0967,
  "functional_check": {
    "status": "not_run"
  },
  "assumptions": [
    "candidate functional check: mismatch (its timing stands without a verified result)"
  ],
  "unsupported": [],
  "limiting_constraints": [],
  "calibration_status": null,
  "result_class": null,
  "parameters_used": {},
  "incompatibilities": [
    "scale differs: 'core' vs 'unit'",
    "profile hash differs (2058f0ec2d80 vs c6fec8a100f7): the model changed between baseline and candidate",
    "unit of work differs: {'count': 4, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'} vs {'count': 32, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'}",
    "candidate status is functional_mismatch, not ok"
  ]
}
```

### compare-ring

```json
{
  "status": "incompatible",
  "message": "results are not comparable: scale differs: 'core' vs 'ring'; profile hash differs (2058f0ec2d80 vs c6fec8a100f7): the model changed between baseline and candidate; unit of work differs: {'count': 4, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'} vs {'count': 32, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'}; candidate status is functional_mismatch, not ok",
  "python_execution_seconds": 0.0806,
  "functional_check": {
    "status": "not_run"
  },
  "assumptions": [
    "candidate functional check: mismatch (its timing stands without a verified result)"
  ],
  "unsupported": [],
  "limiting_constraints": [],
  "calibration_status": null,
  "result_class": null,
  "parameters_used": {},
  "incompatibilities": [
    "scale differs: 'core' vs 'ring'",
    "profile hash differs (2058f0ec2d80 vs c6fec8a100f7): the model changed between baseline and candidate",
    "unit of work differs: {'count': 4, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'} vs {'count': 32, 'description': 'one body per context, first body of distinct 128-body chunks; diagnostic only'}",
    "candidate status is functional_mismatch, not ok"
  ]
}
```

### sample-blocker

```json
{
  "status": "unsupported",
  "message": "loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled",
  "python_execution_seconds": 0.2894,
  "functional_check": {
    "status": "not_run"
  },
  "assumptions": [],
  "unsupported": [
    "loop sampling currently needs exactly one context; interleaved sampled contexts are not modeled"
  ],
  "limiting_constraints": [],
  "calibration_status": {
    "held_out_validation_cases": 160,
    "not_validated_shapes": {
      "x87_sparse_rows_l1": {
        "evidence": "S12-30 small cases, 16 held-out rows, one thread",
        "median_abs_error_pct": 16.0,
        "note": "random-column sparse products into a 32 KiB x: uniformly 12 to 18% slow (L1 conflict misses under true LRU, input instance), rankings right; the error exceeds the 10% bar, so results stay unvalidated_scenario_estimate",
        "worst_abs_error_pct": 17.9
      }
    },
    "note": "Simulated/analytical outputs are model results, never native measurements. ",
    "state": "imported_microbenchmarks_with_compiled_heldout_check",
    "statement": "Core timing is inherited from core-x100-measured (measured or derived on this card: S6-03, S8-01, S8-12, S12-31). Predictions were compared with 119 characterization rows (held-out median error 0.9/0.4/1.6% at 1/2/4 threads, ranking 0.989) and with 105 held-out compiled rows from the binaries that ran on the card (S12-31 row loops, HPCG kernels L2-resident and memory-bound, S12-30 sparse products): median error 3.1%, right winner 39 of 39 pairs more than 5% apart. The decision bar's error and ranking criteria are met; its breadth (loops from at least five M4 programs) is not: shapes outside validated_shapes are unvalidated_scenario_estimate. Recording run of the final engine (profile hash 2058f0ec...).",
    "synthetic": false,
    "validated_shapes": {
      "l1_l2_dependent_loads": {
        "evidence": "S6-03 l1.load_lat/rt, l2.load_lat/rt, memory.load_lat, masked/convert store-reload chains",
        "median_abs_error_pct": 2.0,
        "note": "pointer chases and independent loads with L1/L2-resident or cold footprints; independent store/reload pairs are over-charged (spill_reload.rt +78%)",
        "worst_abs_error_pct": 14.0
      },
      "l1_resident_stores_prefetch_pairing": {
        "evidence": "S6-03 l1.store_normal, masked_store rows, store_stream rows, C2 prefetch pairing",
        "median_abs_error_pct": 2.0,
        "note": "stores to resident lines, no-read stores, vprefetch0/1 pairing",
        "worst_abs_error_pct": 12.0
      },
      "register_vector_chain_l1": {
        "evidence": "S6-03 vector .lat/.rt rows, swizzles, conversions, C7, C9 register chains at 1/2/4 threads",
        "median_abs_error_pct": 1.0,
        "note": "L1-resident vector arithmetic with register dependencies, pairing and loop control; worst case vpaddd.rt at two threads (measured 2.32, a flagged row)",
        "worst_abs_error_pct": 11.0
      },
      "scalar_mask_l1": {
        "evidence": "S6-03 scalar_add/xor, kmov/kand/kxor rows, pair.* rows, agi.gap0-4",
        "median_abs_error_pct": 1.0,
        "note": "scalar integer and mask chains, pairing, address-generation interlock",
        "worst_abs_error_pct": 5.0
      },
      "x87_register_chain": {
        "evidence": "S6-03 x87_add/mul/div .lat/.rt rows",
        "median_abs_error_pct": 1.0,
        "note": "x87 register chains and the divider occupancy; memory-form x87 chains not separately measured",
        "worst_abs_error_pct": 3.0
      },
      "x87_row_loop_l1": {
        "evidence": "S12-31 microbench, 65 held-out variants (tests/heldout_native/s12-31-microbench), one thread",
        "median_abs_error_pct": 2.9,
        "note": "x87 sparse row products with data in L1, converted from the binary with code layout; padding, prefixes and loop-body order included",
        "worst_abs_error_pct": 3.8
      },
      "x87_sparse_rows_l2": {
        "evidence": "S12-31 HPCG toy, 16 held-out kernels (ComputeSPMV_ref, ComputeSYMGS_ref, eight builds), one thread",
        "median_abs_error_pct": 3.7,
        "note": "HPCG-shaped x87 sparse rows with the matrix resident in L2",
        "worst_abs_error_pct": 6.6
      },
      "x87_sparse_rows_memory_stream": {
        "evidence": "S12-31 HPCG 104-cubed SpMV, 8 held-out builds, one thread",
        "median_abs_error_pct": 3.7,
        "note": "the same shape streaming from memory on one thread (TLB, L2 prefetcher and memory service modeled); not validated at several threads",
        "worst_abs_error_pct": 4.1
      }
    }
  },
  "result_class": null,
  "parameters_used": {}
}
```

## What is not modeled and what the card can check

Only eight cores execute detailed instructions in unit/ring. Ring defaults to 60 total active cores: the remaining **52** generate synthetic previous-epoch traffic; they do not walk the tree or compute accelerations. Unit has no synthetic background. The 61-position contracted ring geometry, physical-address surrogates, TD/channel maps, service parameters and symmetry feedback are assumptions or derived quantities, not recovered hardware wiring. Placement/epoch sensitivity is pending. Private inclusive LRU caches are approximations. Banks, refresh, turnaround, OS behavior, OpenMP scheduling/barriers, synchronization and the rest of the program are outside this region. A first-body cold start cannot represent warm per-chunk reuse.

The lead can check the large workunit at **60 vs 240 threads** using the S1-04 runner/launch pattern. `bash scripts/multicore-card-commands.sh` prints both commands; `dist/card/multicore-commands.sh` contains the handoff. It stages the app and runtimes and writes receipts/output under runs/card. No card invocation is used here. Compare numerical results and repeated elapsed timings. Whole-program timing includes other phases; validating gravity cycles or stall attribution requires force-phase timing and hardware counters. Record actual dynamic chunk distribution, since there are only 157 chunks.

## Reproduction

```bash
bash twin/capture_multicore.sh
bash scripts/run_x86.sh large 1
bash scripts/run_x86.sh small 1
bash twin/run.sh
bash twin/run_multicore.sh  # nonzero: compare refusals are findings
python twin/write_multicore_report.py
python tests/test_twin_multicore.py  # remains failing until slices/compare supported
bash scripts/multicore-card-commands.sh  # print only
```

No downloads, installs, git writes or shared-toolchain/skill edits are needed. The Engineer report records the remaining acceptance failure; successful diagnostics do not waive it.
