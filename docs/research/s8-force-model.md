# S8-08 force walk model

Model prepared before correctness runs; counted inputs will be filled from the
host debug traversal. Existing measurement: large, 20,000 bodies, 111 force maps,
13.0 s scalar and 13.1 s vector on the card at 240 threads (ticket S8-08).
The installed model-first skill is unavailable; knc-optimize's minimal accounting
procedure is used. knc-twin 0.4.0 capabilities and validation were read first.

| Term | Formula | Counted inputs / source | Scope / assumptions |
|---|---|---|---|
| FP64 peak floor | operations / 1.2e12 | interactions and node visits, debug counters | Ideal entire card; 1.2 TFLOPS from ticket; not attainable x87 throughput |
| Scalar additive service scenario | (adds*1.03 + multiplies*2.0 + divides*37.94) / (60*1.232e9) | x87 core reciprocal throughput at four contexts, knc-optimize machine.md | TSC ticks; assumes no overlapping x87 services, omits sqrt, loads, control and stalls; only matching forms |
| Logical node bytes | fields read per visited/accepted/opened node | 24 position + 2 type; cell adds 8 rcrit; selected link 8; accepted adds 8 mass; quad adds 48 | Source field demand, excludes repeated target loads, spills, cache reuse and prefetches |
| Distinct lines | sum of per-body 64-byte line-set sizes | host debug counters, actual allocated tree | Footprint across walks; never a miss counter or channel-byte measurement |
| Latency scenario | lines * latency / (240 * concurrent chains per thread) | Idle L2 24.42 ticks or memory 356.53 ticks, 1.232 GHz, machine.md | All counted lines assumed misses at selected level, one chain/thread; actual residency, overlap, loaded latency unknown |
| Shared bandwidth scenario | distinct-lines*64 / 186.14e9 | machine.md read sweep | Counts every per-walk distinct line as a cold read; reuse makes this an overestimate of traffic; sweep rate is measured, not a proven ceiling |
| Copy/scatter | O(cells+bodies) per map | contiguous layout and pointer-remap hash | Allocation, copy, remap, force scatter included in nbMapForceBody timer |

The latency hypothesis is provisional. Distinct lines cannot prove a latency
bottleneck without cache-residency and loaded-latency data. Arithmetic, including
scalar x87 divides/sqrt and branch/address work, remains a competing term.
No whole-card prediction follows by multiplying a one-core twin throughput.
The force phase's 13.0/27.4 share caps an otherwise free optimization at 1.90x
whole-program speedup before copy cost (reported S8 baseline, other phases fixed).

The layout changes ownership and order of a transient force view, which requires
application knowledge (original body indices, self identity, test particles,
union lifetime after hackQuad). It is application work under AGENTS.md. Arithmetic
vectorization or missed legal prefetch transformations belong to GCC-KNC; emitted
code and a reduced pointer-walk repro will be retained for that review.

## Counted large run

Host debug scalar reference, seed 670828913, 20,000 bodies, 111 force maps,
12 threads. Full per-step rows: `runs/force-chunk/large-chunkwalk-model-t12/stderr.txt`.
These are scalar shadow traversals of the actual tree, not PMU events. Lines count
position/type, cell opening radius, selected successor link, mass when accepted,
quad when used, and the target's position/type; software hints, spills, stack and
allocator traffic are excluded. Unique sets reset for each body; reuse between
bodies is intentionally not removed. Host addresses/alignment affect occupancy.

| Count | Whole run | Per body walk (2,220,000 walks) |
|---|---:|---:|
| Body-cell interactions | 697,048,696 | 313.986 |
| Body-body interactions | 195,818,758 | 88.207 |
| Nodes visited | 1,087,300,798 | 489.775 |
| Distinct 64-byte line touches | 2,413,473,249 | 1087.150 |

Work accounting: V = node visits, I = accepted interactions (excludes self), C =
accepted cells. Distance costs 8 ops/visit; monopole adds 10 ops/interaction
(including sqrt and two divides); quadrupoles add 38 ops/cell. Thus the rough
20-25 ops/interaction monopole estimate must be expanded for this useQuad=true
case. Integer address/control, self/opening/softening branches, loads/stores and
sqrt occupancy beyond its one operation count are not included in this FP total.

| Model term | Formula / inputs | Value (whole large run) | Classification |
|---|---|---:|---|
| FP64 operations | 8V + 10I + 38C | 44,114,931,372 | Counted source-level operations |
| Compute T_lb at ideal FP64 peak | ops / 1.2 TFLOPS | 0.036762 s | Optimistic peak floor, excludes address/control |
| x87 additive service scenario | A=18766655550, M=21275576068, D=3179832300; (1.03A+2M+37.94D)/(60*1.232e9) | 2.469205 s | Conditional floor only if these services serialize; sqrt/load/control omitted |
| x87 compute T_lb with overlap allowed | max(1.03A,2M,37.94D)/(60*1.232e9) | 1.632073 s | Conditional on matching measured throughput forms; no cross-unit serialization assumed |
| Logical node demand | 34V+8(cell visits)+8I+48C | 84.684 GB | Source fields, no cache reuse or hints |
| Per-walk line footprint bytes | L*64 | 154.462 GB | Repeated across bodies, not physical channel bytes |
| L2 latency scenario | L*24.42/(240*1.232e9*concurrency) | 0.199327 s at concurrency=1 | Assumes every line is an idle L2 miss/hit service; not a proven floor |
| Memory latency scenario | L*356.53/(240*1.232e9*concurrency) | 2.910158 s at concurrency=1 | Idle latency, all counted lines cold; loaded latency unknown |
| Cold-read bandwidth scenario | L*64/186.14e9 | 0.829818 s | Reported read sweep, assumes no cross-walk cache reuse |
| T_meas card | S8-08 ticket, scalar / vector | 13.0 / 13.1 s | Existing card measurements, not reproduced |

**Dominant modeled term:** the all-cold memory-latency scenario, followed by
scalar x87 issue cost. The simple model still leaves substantial time unexplained:
loaded latency, branches, address dependencies, sqrt, spills, cache conflicts and
imbalance are unmeasured. Layout/prefetch is a latency experiment, not a promised
speedup. Concurrency and residency are unknown, so the latency formula is a
scenario estimate, not a valid unconditional T_lb. T_pred for the candidate stays
unknown until a successful applicable twin run or native timing. No compiler
speedup is claimed from these counts.

## Twin attempts (fresh card binaries, real trees)

All eight functions were extracted with from_binary.py from the staged card
executables, with original bytes, lengths, calls, prologue and return retained.
The x86/card layout arrays match for all 23 sizes/offsets used by the snapshot.
Real 20,000-body original and packed trees were dumped from maps labeled step
zero (upstream labels two maps zero; the last snapshot is retained). All node
and body bytes, raw addresses, context and state were bound to init.memory.
Snapshot SHA-256 is in each kernel's provenance, alongside the binary SHA-256.
The core experiment has four contexts; ring has eight tiles with four contexts
each and default synthetic background. One scalar target or eight vector targets
run per context; these are finite walk diagnostics, not a complete force step.
No expected twin outputs are asserted; exactness is independently checked on x86.

| Variant | Scale | Contexts | status (returned) | result_class (returned) | CLI host seconds |
|---|---|---:|---|---|---:|
| walk-reference | core | 4 | unsupported | field absent | 0.703 |
| walk-reference | ring | 32 | unsupported | field absent | 0.781 |
| walk-reference-vec | core | 4 | budget_exhausted | field absent | 31.516 |
| walk-reference-vec | ring | 32 | budget_exhausted | field absent | 34.078 |
| walk-layout | core | 4 | unsupported | field absent | 0.688 |
| walk-layout | ring | 32 | unsupported | field absent | 0.750 |
| walk-layout-vec | core | 4 | budget_exhausted | field absent | 31.500 |
| walk-layout-vec | ring | 32 | budget_exhausted | field absent | 34.859 |

Every prediction field is null. Scalar functions are refused because the full
binary contains the cold nbReportTreeIncest call without a costed callee stub;
no cost was invented and no cold block was removed. Vector attempts stop at the
30-second Python budget during functional interpretation, before a timing result.
The default functional step cap is also retained. These statuses are the answer;
partial execution is not a prediction or a functional pass. No core/card speedup,
calibrated forecast or multicore ranking is available. Ring would remain an
unvalidated scenario even if it completed, per capabilities/validation.md.

Exact assumptions, unsupported forms, limiting constraints, calibration_status,
parameters_used (when returned), messages, commands and result digests are in
`s8-force-twin.json`. Unsupported cases return empty assumptions/constraints and
null calibration_status. Budget cases return empty assumptions/constraints,
empty parameters_used and the imported-microbenchmark calibration statement;
this walk shape is not among its validated shapes. No external reciprocal table
or profile overlay was supplied. CLI wall time includes startup; engine-reported
Python seconds are retained separately. Capabilities and adapter commands were
not individually wall-timed.

Timed simulate host seconds: 134.875000; engine Python seconds: 129.770600.
