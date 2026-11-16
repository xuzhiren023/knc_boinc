# Gravity compiler flags: S5-01

**Verdict: too close for the twin.** No card run was made. The table is a model prediction, not measured card speed.

Four required variants only; no optional variants were added. All share `-g -fopenmp -fno-strict-aliasing -march=knc -std=gnu99`, `-ffp-contract=off`, `-fno-math-errno`, and unchanged bundled crlibm objects. No fast-math options, reassociation, approximation, or contraction was enabled. `V2` receives no explicit `-O2` because that would override the `-mphinix` expansion to `-O3`.

Inputs were fixed before running: the original S1-05 small capture, plus S1-06 large first-force-step bodies **0, 128, 256, 384** (20,000 bodies, seed 670828913, one host reference thread). Expected XYZ accelerations are independent x86 binary64 bytes. The unspecified fourth vector lane is excluded consistently with the original captures. No body was excluded after seeing results. S14-37 x87 double rounding remains a model defect; equality here uses exact bits with no ULP tolerance.

The original large snapshot was copied read-only from the S1-06 worktree. `build-manifest.json` records SHA-256 hashes of its original files, the small capture, every unchanged linked object, and all variant objects/binaries. Adjacent snapshot blocks were coalesced with overlap byte-equality checks and split into bounded 64 KiB files: addresses and initialized bytes are preserved. These remain `init.memory` file blocks.

A whole-function extraction is first attempted for each binary with `from_binary.py --function nbGravity`, retaining entry, return, encodings and the cold error call. The installed 0.4.0 adapter still needs the S1-05 region cut: whole-function simulate rejects the undeclared `nbReportTreeIncest` even when unexecuted. Including `nbReportTreeIncest` and `fprintf@plt` was also attempted; the adapter reports an indirect transfer as unsupported when executed, but then refuses to emit a kernel because aggregate functional coverage is false. S14-20 is therefore incomplete in this installed adapter.

**V0 and V3 need a region cut with this installation.** The boundary is the start of the cold call setup (two moves before `nbReportTreeIncest`). Every preceding binary instruction record is unchanged, including normal return and output stores. The original branch target becomes a sentinel. Each of the 10 available functional traces confirms that the sentinel is never executed and the normal return is executed. No costed stub, made-up latency, missing-memory default, or changed arithmetic is used. The full extraction, refused full simulate, exact boundary and retained-record equality are retained in the evidence.

One unit is **one nbGravity call / one body / one context**. Each call starts cold at memory level with line tracking and all-predicted branches. Profile `card-7120-measured`, hash `2058f0ec2d803051ea99b503bb10920e40ea33e9f84f19ea060727bc6aa3e468`, is frozen in every batch. Each input has its own batch over all variants passing every input; ranking across different input work is not attempted. Automatic batch queue generation is disabled because the two explicit prepare-native attempts below handle the V0/nominee handoff.

| Variant | gravity flags | functional | predicted cycles/call: small / L0 / L128 / L256 / L384 | change vs V0 in the same order | result_class | limiting_constraints |
|---|---|---|---|---|---|---|
| V0 | `-O2` | all 5 exact | 33622 / 466272 / 492667 / 322087 / 449293 | +0.00% / +0.00% / +0.00% / +0.00% / +0.00% | unvalidated_scenario_estimate | dependency, miss_stall, spacing, x87_serial |
| V1 | `-O3` | not_run, not_run, not_run, not_run, not_run | not_run / not_run / not_run / not_run / not_run | n/a / n/a / n/a / n/a / n/a | n/a | n/a |
| V2 | `-mphinix -ffp-contract=off` | not_run, not_run, not_run, not_run, not_run | not_run / not_run / not_run / not_run / not_run | n/a / n/a / n/a / n/a / n/a | n/a | n/a |
| V3 | `-O2 -funroll-loops` | all 5 exact | 33622 / 466272 / 492667 / 322087 / 449293 | +0.00% / +0.00% / +0.00% / +0.00% / +0.00% | unvalidated_scenario_estimate | dependency, miss_stall, spacing, x87_serial |

A negative change is fewer predicted cycles. V0 and V3 match all five exact outputs. V1 and V2 have no standalone `nbGravity` symbol: `-O3` inlines it into `nbMapForceBody._omp_fn.0` (and its other caller). Whole-function extraction is refused for each fixed input. No kernel, functional pass, or timing is invented for them; they are excluded from batch because exact numerical qualification is unavailable. Their complete card binaries remain available. Adding no-inline or keep-inline flags would change this experiment or model an unused out-of-line copy, so those flags were not added.

Batch output (actual tool ranking; ties retain manifest order). Its bound-gap diagnostic is not used: the known S14-27 dependency-critical-path defect can put a reported lower bound above simulation.

- `small`: V0, V3 (equal cycles). V0: memory behaviour beyond L1 is modeled, not validated; V3: memory behaviour beyond L1 is modeled, not validated; within 30% of the baseline: too close for the model to rank
- `large-0`: V0, V3 (equal cycles). V0: memory behaviour beyond L1 is modeled, not validated; V3: memory behaviour beyond L1 is modeled, not validated; within 30% of the baseline: too close for the model to rank
- `large-128`: V0, V3 (equal cycles). V0: memory behaviour beyond L1 is modeled, not validated; V3: memory behaviour beyond L1 is modeled, not validated; within 30% of the baseline: too close for the model to rank
- `large-256`: V0, V3 (equal cycles). V0: memory behaviour beyond L1 is modeled, not validated; V3: memory behaviour beyond L1 is modeled, not validated; within 30% of the baseline: too close for the model to rank
- `large-384`: V0, V3 (equal cycles). V0: memory behaviour beyond L1 is modeled, not validated; V3: memory behaviour beyond L1 is modeled, not validated; within 30% of the baseline: too close for the model to rank

Gravity is not a validated shape. Every cycle result is `unvalidated_scenario_estimate`; the held-out 3.1% median / 39-of-39 ranking evidence belongs to other compiled loop families, not this tree walk. There is no validated gravity error band. The batches use the handoff's conservative 30% uncertainty threshold, and cold memory beyond L1 is explicitly unvalidated. The top nonbaseline candidate in the small-input batch is `V3`; this is only the A/B nominee, not a winner. The model cannot justify choosing it over V0.

`schedule` on the V0 tree-walk loop (`--method list --max-states 4096`) reports:

```text
unsupported: explored region contains an interior label
```

The baseline region and original tree-walk loop body were preserved. The explorer refuses an interior label before searching this binary-derived loop, which also contains interior branches; no reorder gain or cycle estimate is available. A different, simplified straight-line kernel was not substituted.

`prepare-native` requests for V0 and the batch-selected nominee report:

```text
V0: invalid_input: the kernel's memory blocks span 42944845376 bytes (0x4c7000 to 0xa0002c640); prepare-native relocates one contiguous image of at most 33554432 bytes. Place the kernel's arrays near its data sections (or drop data sections it does not use) before exporting a native request.
```

```text
V3: invalid_input: the kernel's memory blocks span 42944845376 bytes (0x4c7000 to 0xa0002c640); prepare-native relocates one contiguous image of at most 33554432 bytes. Place the kernel's arrays near its data sections (or drop data sections it does not use) before exporting a native request.
```

The original pointer-rich snapshots are sparse over a very large address range. The native exporter cannot pack them into its single image (32 MiB maximum). No fabricated request or native timing is claimed. The full linked card binaries are left at `build/flags/V0/milkyway_nbody.mic` and `build/flags/V3/milkyway_nbody.mic`; runtimes are in `dist/card/`. `bash scripts/flags-card-commands.sh` prints a reproducible whole-application A/B run script, also staged as `twin/flags/run-native.sh`. It covers small at 1/240 threads, medium at 240, large at 60/240, with the same seed. The lead can run that generated script; no card key was used here. Whole-application timings are a follow-up, not a per-call calibration of these cold snapshots.

Model metadata copied from the result envelopes:

```json
{
  "assumptions": [
    "L2 hardware prefetcher sub-model: a stream per 4 KiB page after two accesses with the same stride (<= 2 lines), prefetching 16 lines ahead within the page into L2; prefetched fills do not use L1 demand-miss slots (assumed)",
    "TLB sub-model: 64-entry fully associative LRU first-level DTLB for 4096-byte pages; a miss adds 29 cycles; second-level TLB reach and page walks are not modeled",
    "ZF/SF after imul are architecturally undefined; the model leaves them unchanged",
    "a taken forward branch, call or return costs the core 1 issue cycle(s) for the prefetch-buffer refill (R02 ch.4; S8-01 C10 fixed-direction row at four threads); loop back-edges pay nothing (S8-01 C9 at two threads); hidden at one thread by the same-context spacing",
    "front end: crossing a 16-byte or 64-byte boundary and the loop-head offset cost nothing (S12-31 mis_4..mis_60 within 0.45 ns per row)",
    "front end: instruction bytes come from the listing; each two-cycle prefix (66, 67, lock, segment, rep: R02 p.56) delays that instruction's issue to 2 cycles per prefix after the previous issue of its context, which the 2-cycle same-context spacing hides for one prefix (S12-31 padding rows); an instruction with such a prefix does not pair (assumed)",
    "instruction cache: code is assumed resident in the L1 instruction cache (steady-state hot region)",
    "line_tracking: true LRU replacement stands in for the hardware's pseudo-LRU; the L1 and L2 are modeled as private to the core with no coherence traffic",
    "memory service sub-model: one memory fill per 20 core cycles for this core (measured sequential-stream rate, includes the hardware prefetcher); card-level sharing not modeled",
    "register results are available to any context's dependent instruction exactly latency cycles after issue; no bypass penalties beyond the measured latencies",
    "sign/zero extensions (movslq, movs*, movz*, cltq) cost a plain mov or scalar load plus latency.scalar_extend_extra and pair per pairing.extend_v_pairs: evidence E, inferred, no KNC source",
    "x87 instructions issue on U only (register-file diagram, R01) and alone (S12-31); a memory-operand x87 load or arithmetic instruction holds its context until its result is complete; x87 stores retire like scalar stores",
    "x87 precision control is 53-bit: results round to that significand with the extended exponent range"
  ],
  "unsupported": [],
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
  "parameters_used_assumed_or_derived": {
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
  }
}
```

Full tool envelopes, traces and reconstructed kernels are regenerated under ignored `twin/flags/` paths; `evidence.json`, `build-manifest.json`, `run.log` and `run-native.sh` are the compact review artifacts.

Rerun from Git Bash (pinned sources already present):

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
# Restore the original large capture if absent: bash twin/capture_multicore.sh
bash twin/run_flags.sh > twin/flags/run.log 2>&1
python twin/write_flags_report.py
bash scripts/flags-card-commands.sh > twin/flags/run-native.sh
python tests/test_twin_flags.py
```

Not proven: output equality beyond the fixed five bodies, hardware ordering gains, gravity model error, steady-state cache behaviour, whole-application speedup, or the cold error path. The schedule and native-export refusals need the twin owner's attention; final speed decisions require the lead's card run.
