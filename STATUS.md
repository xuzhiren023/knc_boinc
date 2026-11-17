# Status

Lead-maintained. Last update: 2026-11-16 EST.

| Sprint | State |
|---|---|
| 1 | Card run done 2026-11-16 (docs/sprints/sprint-1.md); S1-06/S1-07 merged, chunk scaling waits for knc-twin S14-37 |
| 2 | S2-01..S2-04 merged |
| 3 | S3-01, S3-02 merged |
| 5 | S5-01 merged (twin cannot rank gravity flags: -O2 = -O2 -funroll-loops code, -O3 inlines; card A/B script ready); S5-02 merged (card force chunk 4, 26 x86 runs bit-identical; card before/after pending) |
| 6 | S6-03 merged: full vector gravity walk (opt-in, off by default), x86 bit-identical, twin functional ok on 4 groups (~272-293k predicted cycles/body, lanes 79-94% busy); scalar twin comparison waits for S14-37 |
| 7 | S7-01 merged: pinned to N-body 1.96 (server's standard app); new x86 refs (small -448.32648945358238, large -4980.4452402155885); waiting for the owner's captured task (S7-02) |
| 4 | S4-01 merged (end-to-end script, not yet run on the card); S4-02 guide merged as a draft, final pass after the card run |

## Proven

- MilkyWay N-body 1.97 (pinned `d78c48fc`) builds standalone for x86 (Cygwin) and for the card (GCC-KNC, K1OM,
  knc_lint pass), both with crlibm (upstream default); card startup sets x87 53-bit precision (disassembly).
- x86 references (crlibm): small -438.534790192227661, medium -450.772121584039894, large (20k bodies, 0.05 Gyr)
  -4894.200373110274995; 1 vs 4/12 OpenMP threads identical.
- BOINC 8.2.8 app API built with Cygwin g++ on the Win32 paths passes an offline fake-client protocol test
  (progress, checkpoint, suspend/resume/quit, graphics shmem, standalone).

- knc_wrapper (S2-02) passes normal finish, suspend/resume, quit/checkpoint/restart, abort and card-unreachable flows
  through real BOINC Win32 IPC with a fake card running the x86 app; restarted output equals uninterrupted.
- knc-twin 0.4.0 (S1-05): fildl repro +0.0 and all 16 crlibm log_rn cases match x86 bits, so the S1-03 mismatch was
  a twin defect, not GCC-KNC wrong code. Gravity functional ok with the region cut before the never-taken cold error
  branch (until gcc-knc S14-20). Gravity timing: simulate 33,622 cycles/call (unvalidated estimate). The bounds
  critical-path term (43,656) charges every first touch full cold latency, so it is a cold-start scenario, not a
  floor; the real bound term is memory_concurrency 5,658 (knc-twin session, fix as gcc-knc S14-27 after S14-20).

- Card (7120, 240 threads) gives likelihoods bit-identical to x86 on small, medium and large (card run 2026-11-16);
  crlibm 6,272/6,272 probe rows bit-identical. Card wall: small 336 s, medium 1,225 s, large 61 s (app's 128-body
  OpenMP chunk limits small/medium to 1/8 busy threads).
- S1-07: the 1-ULP twin gravity mismatch is a knc-twin x87 double-rounding defect (gcc-knc S14-37); native x87
  PC=53 matches SSE bit for bit.

## Not proven yet

- Next card turn batch (about 40 min): from .work/S6-03 `scripts/vector-card-commands.sh` = medium and large at 240,
  card-off (scalar, chunk 4: S5-02 after) and card-on (vector, S6-03), then `scripts/check_vector_card.py`
  (bit-exact vs x86); then from .work/S4-03 `scripts/e2e_card.sh --case large --threads 240 --in-granted-turn`.
  Baseline (chunk 128, scalar) is the Sprint 1 run: medium 1,225 s, large 61 s.

- Card speed-up of S5-02 (chunk 4) on medium/large: next card turn, with the end-to-end large run. Rebuild the card
  objects in a clean build dir (make does not track the -D change).

- End-to-end run on the card (S4-01): needs --benchmark admission and card_run's known_hosts first.
- The real Windows BOINC client with the Cygwin-built API (Sprint 4, needs BOINC installed).
- Live card graphics feed (screensaver tested offline with demo snapshots only).
- The guide followed verbatim by the lead.

## Lead notes

- 2026-11-16: knc-twin moved to its own repo (C:/Users/xuzhi/Documents/knc-twin). Ticket renames: x87 double rounding
  S14-37 -> T1-06; bounds above simulate S14-27 -> T1-03; multicore gaps S14-31 -> T1-05; sparse native image
  S14-39 -> T1-07; never-executed direct call and schedule --block -> T1-04. Lane order: T1-08, T1-06, T1-03,
  T1-04, T1-02, T1-05, T1-07, T1-01. The twin session messages us when T1-06 lands.

- 2026-11-16: card window 10 (gcc-knc turn claude-turn-s14-w10) closed at 11:15Z without our jobs (gcc-knc wait-loop bug). Staged jobs and conditions carry over to the next gcc-knc card turn; start only on its "go".

- 2026-11-16 window 12 (23:03Z): 1.96 card builds on the large case, scalar chunk 4 and vector, both bit-identical
  to x86 (-4980.4452402155885); card time 30.9 s vs 30.7 s, so the vector walk gives no gain on this case.
  S7-02 (in progress): on real workunit 117676 (110k) our x86 build matches the stock 1.96 exe bit for bit
  (-92.418153851030638); stock 98 min, ours 91 min on 12 laptop threads; 1 thread timed out at 2 h. Our stderr
  lacked the `<search_application>` line; S7-02 adds patches/nbody-result-contract.patch.

- 2026-11-16 owner task (via the GCC-KNC lead), starts after window 12's "boinc done": optimize N-body until
  time-to-solution matches a 1-2 TFLOPS GPU. Use skill knc-optimize (6 steps; model step = gcc_knc
  .claude/skills/model-first). First: fix one workunit, a GPU reference time (MilkyWay GPU app or published,
  name the source), the FP precision kept, the KNC bound (references/machine.md); a Model table here plus a short
  summary to the GCC-KNC lead; say so if FP64 puts the target out of reach. Rank one-core variants with knc-twin
  (within ~20% is decided on the card; run twin-generated natives on the host first, T1-15). One staged run list
  per window to the GCC-KNC lead. Compiler defects go to the GCC-KNC lead with a reduced repro.

- 2026-11-16 window 12 thread sweep, scalar chunk-4 card build, large case (card_run card_minutes, includes ~3 s
  staging): 60 thr 41.6 s, 120 thr 36.1 s, 240 thr 30.9 s, all bit-identical. A fit T = S + P/t gives
  S ~ 27 s, P ~ 860 thread-s: ~88% of card time does not shrink with threads. Host fit (6 cores): S ~ 2.7 s.
  The dominant term is serial per-step or setup work on one card thread, not the force loop.

- 2026-11-16 S7-02 merged. Real 117676 on the laptop (12 thr, runs overlapped, not isolated): 5,488 s total, of
  which ~4,560 s is serial body generation (mixed dwarf, Eddington-integral rejection sampling) before step 1;
  1,568 steps take ~920 s. On the card the serial generation would run ~10x slower: this, not the step loop, is
  why real tasks lose on the card. S8-03 parallelizes the quadrature nodes (bit-identical by construction).

- 2026-11-16 window 12, S8-01 phase timers, large case (110 steps), wall seconds:

  | Phase | Card 240 thr | Laptop 12 thr | Laptop 1 thr |
  |---|---:|---:|---:|
  | nbMakeTree (serial) | 13.19 | 1.58 | 1.11 |
  | nbMapForceBody | 13.00 | 24.96 | 142.1 |
  | integrators | 0.18 (0.08 static) | 0.10 | 0.05 |
  | final histogram/likelihood | 0.37 | 0.07 | 0.03 |
  | setup (incl. first gravity) | 0.95 | 0.59 | 1.89 |
  | whole run | 27.42 | 26.89 | 143.4 |

  The card force walk is already ~2x the laptop; the serial tree build is half the card time. Static integrator:
  bit-identical, saves 0.1 s. Parallel tree (S8-02) is the large-case fix; S8-03 the real-task fix.

- 2026-11-16 23:52Z S8-02 card check (large case, parallel tree): nbMakeTree 70.4 s (serial build 13.2 s),
  force 13.4 s, whole 88.0 s, bit-identical. 5x slower on the card (x86 also 2.7x slower); not usable; diagnose
  (malloc/free-list contention, serial partitioning, fork/join per level?) before any rework.
  Same with vector force walk (ptree-vec): force 13.10 s vs scalar 13.39 s: the S6-03 vector walk gives ~2% on
  the force phase on the card (twin predicted lanes 79-94% busy). Add to the pilot-study predictions (S8-06).
  S8-03 (parallel quad): x86 core-small (4,000 bodies, real 117676 args) generation 140.2 s -> 36.9 s at 12 threads,
  bodies byte-identical, likelihood -2357.216400957532642 identical. Card check pending.

- 2026-11-17 00:12Z owner: no BOINC launch tonight; next 4 h: card must dominate x86 by a large margin, results
  still accepted. Packaged build (S8-03 parallel quad, chunk 4, result-contract) passed on the card: core-small
  68 s card_minutes, bit-identical (runs/card/pkg/). Dispatched S8-09 mission (Codex, xhigh effort, owns
  integration, stages card batches in its ticket), S8-07 (tree on the card) and S8-08 (force walk layout), high.

- 2026-11-17 17:47-17:52Z window (tcp-large uploads, no DMA, card clean): S10-05 core-small card_seconds release
  52.61, DF_SPECIAL 52.31, DF_VMATH (1 lane) 52.22; all three likelihoods identical (vmath difference 0.0). The exact
  specialization gives no measurable card gain (host -10.7%); the integrand stays scalar x87 on the card.
- 2026-11-17 17:15-17:29Z window (transport timeout 600 s, laptop loaded): core-small 47.80 s; real-steps (20k bodies, 129
  steps, 117676 Lua) whole 241.4 s = setup 234.2 s + tree 2.28 s + force 4.20 s + likelihood 0.45 s: real tasks are
  generation-dominated even at 20k bodies. S10-05 release core-small ok; S10-05 special upload FAILED (third DMA
  helper deadline today, 32 MB libstdc++); latch set; card run dir removed after checks (boot unchanged, no helpers);
  latch clearing asked of the GCC-KNC lead; card_dma_recover.py card check has a script bug (exit 2).
- 2026-11-17 card uploads: ssh measured ~20 KB/s to the card (48 MB job = ~40 min), owner chose auto (DMA >= 1 MiB).
  17:02Z window: core-small 47.86 s ok (DMA ~1.3 GB/s); real-steps refused at upload: DMA helper deadline, cleanup
  uncertain, on libgomp.so.1 while the laptop was loaded by engineers (second such failure; GCC-KNC lead: do not
  start DMA on a saturated laptop). No latch left, card and host clean. Run card batches only when no engineer runs.
  S10-05 merged: DF_SPECIAL exact (host -10.7% generation); 1-ULP vmath changed 0/4000 and 0/110000 bodies, likelihood
  identical; vectorization still blocked by crlibm/gamma control flow in the node loop.
- 2026-11-17 knc-boinc window 8 (16:02-16:15Z, card clean): S10-02 force candidates no gain (prefetch 12.82, hot 12.70,
  both 12.84 vs 12.71 s; twin predicted no winner). Walk profile: per-thread nbGravity 3.05 s of 12.43 s active force
  loop time, balanced (max 12.64 s): ~75% of the large case's force phase is OUTSIDE the tree walk, in the external
  potential. The large case uses Disk.freeman (Bessel functions); all three real Lua files use Disk.miyamotoNagai.
  The large case is not representative of real tasks for the step phase. Real 117676: setup is 79% of 27.9 min.
- 2026-11-17 FULL REAL WORKUNIT 117676 on the card (15:32-16:00Z, release build, 240 threads, ssh, card clean):
  whole_run 1,673 s (27.9 min): setup (generation + first force map) 1,319 s; 1,568 steps: force 292 s, tree 40.7 s,
  per-step likelihood 17.7 s, integrators 1.9 s. All 8 likelihood tags identical to the stock 1.96 app
  (-92.418153851030638). Laptop references (S7-02, contended runs, old build): stock 5,859 s, ours 5,488 s.
  Laptop generation with DF_REUSE alone 493 s (S9-05): card generation is ~2.7x slower than the laptop's; card steps
  (~350 s) are faster. Receipts: runs/card/real-117676/.
- GCC-KNC S14-44: no-go on lane-0 scalar double (tree-octant model 1.20x < 1.5x bar; exponent range/exceptions
  differ from x87); no existing flag beats -O2 -march=knc -ffp-contract=off by more than 0.7%. Asked whether the model
  changes for today's hot x87 regions (`fun` 34.3 s, force walk 12.7 s). Remaining x87 cost treated as algorithmic.
  Follow-up (lead lead confirmed): no change for `fun`/walk (no IMCI double div/sqrt; crlibm add/mul 4 vs 3 cycles).
  Asked GCC-KNC for correctly rounded 8-lane log/atan in libknc_vmath: bit-identical node values would let the
  integrand run 8 nodes per vector with no fallback (the S9-05 vector path failed at 81% replays on 1-ULP vmath).
  GCC-KNC answer: feasible and bit-identical by definition (quick double-double phase over 8 lanes + per-lane
  rounding test + rare accurate fallback; ~2-4x today's vmath per lane, several times faster than scalar crlibm);
  exp easy, log/atan medium, pow hard; multi-week clean-room library work (crlibm is LGPL); proposed to the owner
  as a GCC-KNC M6 candidate (deferred vmath contract S12-20). Owner's call.
- 2026-11-17 knc-boinc window 6 (15:21-15:27Z, ssh transfers, card clean): S10-01 release large 15.89 s, core-small
  47.95 s, bit-identical. S10-03 card generator split (core-small): parallel nodes 34.3 s, root/search serial 10.9 s,
  quad serial 2.3 s; GEN_PIPELINE setup 47.99 -> 43.71 s (-9%, root/search 2.6 s, nodes 38.9 s), exact. Node phase
  ~580 us per integral (330 nodes over 240 threads, two waves) is the next term.
- 2026-11-17 14:53Z knc-boinc window 5 FAILED (infrastructure): first S10-01 release job, card_run exit 126, DMA
  helper deadline / SCIF endpoint cleanup unresolved during claude-pin upload; leftover /tmp/claude/claude-b03d34bf...
  (claude-dma-active marker, part file); no card processes; turn closed. Holding card jobs until the GCC-KNC lead
  (card_run/card_dma owner) says how to recover. S11-01 merged (BOINC Show graphics/screensaver). S10-01 merged.
- 2026-11-17 knc-boinc window 4 (13:57-13:59Z, closed, card clean): S9-06 TREE_VARIANT=4 large whole 15.89 s
  (pred 15.94), nbMakeTree 2.07 s (partition 0.90, threadTree 0.50), force 12.70 s; bit-identical. Card now beats the
  best x86 build (18.0 s) by 1.13x and stock 1.96 (23.1 s) by 1.45x on large. Force walk is now 80% of the run.
- 2026-11-17 knc-boinc window 3 (13:40-13:42Z, closed, card clean): S9-05 DF_REUSE core-small 47.61 s (was 62.45;
  setup 46.89 vs 61.72), bit-identical; stock 1.96 149.3 s (3.1x). x86 generation 30.2 -> 18.2 s with the same patch,
  so the card gains less (serial generation parts outside `fun`). Full 117676 generation x86 493 s, bytes identical.
  Certified vector integrand rejected (81% exact replays, slower).
- 2026-11-17 knc-boinc window 2 (13:32-13:35Z, closed, card clean): S9-04 TREE_VARIANT=3 large whole 20.95 s (was
  23.99), nbMakeTree 7.08 s: partition 5.93 (serial, dominant), insertion 0.10, CofM 0.15, Quad 0.21, threadTree
  0.55; core-small 62.45 s (generation). Bit-identical. Prediction 2.13 s missed on the serial partition (1.53).
  Card now beats stock 1.96 on large (23.1 s); best x86 18.0 s. Next: parallel exact partition (S9-06).
- 2026-11-17 first knc-boinc window (10:46-11:14Z, turn closed, card clean). S8-07 pool build, all bit-identical.
  Thread settings (large, whole_run): defaults 24.41, DELAY512 24.24, DELAY32 24.91, passive 29.17, spin 30 ms 24.01,
  close 24.05, 180 thr 24.44, 120 thr 25.80: defaults hold (single runs, ~4% spread). PGO (trained on card, core-small
  + large; instrumented runs 458/254 s): large 23.99 -> 23.94 s (0%), core-small 62.37 -> 59.73 s (-4.2%, setup).
  Receipts: runs/card/w-knc1/.
- S9-03 found S9-01's card-base binary was built from an unpatched third_party copy (no pool tree): main and
  S9-01 refetched/re-copied, card-base and card-pgo-train rebuilt (pool symbols present, knc_lint ok), staging
  rerun, GCC-KNC-ordered thread jobs kept. Lesson: refetch main's third_party after merging a patch, before
  dispatching (codex_run copies main's third_party). S9-03 twin phase A blocked: `--block` needs live-in register
  state at block entry; force walk needs a bound tree. No PGO twin prediction yet.
- S9-02 merged: tools/card_run (project knc-boinc), tools/card_turn.py. Turn row auto-queued at 10:45Z by a lead
  waiter (scratchpad w-book.py); it reports when no earlier foreign job is live. S9-01 staged scripts now call
  knc-boinc/tools/card_run.
- 2026-11-17 owner: knc-boinc books its own card windows on the shared ledger (not GCC-KNC turn rows). S9-02 makes a
  local card_run with project "knc-boinc" plus turn-row script. Next window after PhiWeather (~13:30Z): 2 PGO training
  jobs + 8 thread-setting jobs (S9-01, GCC-KNC's order: libgomp defaults first), then the PGO rebuild and its A/B.
- 2026-11-17 GCC-KNC S14-44 is their next ticket: phase 0 = best existing flag set for x87-heavy scalar double
  under our contract (53-bit, no contraction, no fast-math), ranked with knc-twin, plus a staged A/B list (core-small,
  large) for us to run; lane-0 IMCI codegen is a later go/no-go. Waits on the owner freeing the laptop and disk > 30 GB.
- 2026-11-17 window 14 (04:49-05:09Z), 16 jobs, all bit-identical. Large case card seconds (whole / tree / force):
  reference 27.45/13.33/12.98; vector 27.05/13.13/12.79; S8-07 pool 23.72/9.91/12.69 (best); cofm 27.37 (no gain);
  S8-08 walk layout+prefetch 34.62/12.96/20.51 (force +58%: copy/remap/scatter + prefetch, negative); S8-09
  integrated (pool+layout) 30.61. Pool tree split: insertion 3.12 (serial 5.15), hackCofM 2.24 (2.37), threadTree
  1.80, hackQuad 2.48 (2.69), nbNewTree 0.0002 (1.04): parallel CofM/Quad imbalanced (Plummer core in few depth-3
  octants). Core-small 60.9-63.6 s for all builds (generation). Best card large 23.7 s vs best x86 18.0, stock 23.1.
  Next: adaptive frontier (split by body count) for insertion/CofM/Quad, parallel threadTree, drop the walk layout,
  in-place prefetch test; generator: derivative reuse (S8-10 item 1) and certified vector integrand.
- 2026-11-17 ~03:05Z owner: stop loading the laptop. S8-10 stopped (killed; worktree .work/S8-10 kept, no work
  saved). No knc-boinc engineers running. Restart S8-10 only with the owner's OK, ideally capped (fewer threads).
- knc-twin guidance (twin lead, 2026-11-17): regions with cold callees: give the hot-path block range
  (`schedule --block`, T1-04 merged) and treat call sites as boundaries. Indirect calls/jump tables (`fun`
  dispatch) will not be simulated: cut the kernel at the dispatch and model each target as its own kernel (stub
  rule under T1-07 later). Vector walk hit the 30 s budget: use --max-seconds. Gravity reproducer rerun on T1-06
  still pending.
- GCC-KNC S14-48 (dispatched): models the force walk's 4-5x gap, audits emitted walk code vs GCC 5.1.1, bounds a
  next-node prefetch pass; stages hand-prefetch on/off at 1/2/4 threads per core for a GCC-KNC window. Keep
  S8-08's guarded hand prefetch; send its card effect to the GCC-KNC lead when measured.
- Window 12 closed early (~00:25Z, owner let PhiWeather start): "boinc done" sent; card clean (no processes,
  /tmp/claude empty). Next: one staged run list (S8-05, S8-07, S8-08, S8-09) for the GCC-KNC window after PhiWeather.
- Window 12: extension denied; hard stop 02:59:39Z (earlier if PhiWeather is ready: finish the current batch and
  hand over). End: cleanup, ps check, "boinc done" to the GCC-KNC lead; stage remaining checks (S8-05, S8-07,
  S8-08, S8-09) as one run list for the next GCC-KNC window after PhiWeather's ~3 h job.

- Twin use (owner 2026-11-16): knc-twin 0.4 simulates 1 core or up to 8 detailed cores on the ring
  (`simulate --scale ring`, `streams[].core`, 4 contexts per core; multicore results are
  unvalidated_scenario_estimate). Use 1 core with 4 contexts for per-thread speed at 4 threads/core (the 82x
  assumption in docs/research/s8-model.md) and to rank vector `fun` variants; 8-tile for the miss- and
  ring-bound regions: parallel tree insertion (S8-02) and the force walk.

- GCC-KNC has libknc_vmath (double exp/log/pow, atan/atan2, 8 lanes) via -mveclibabi=knc with -fno-math-errno;
  not correctly rounded (crlibm is), so only inside S8-05's guarded fast path. GCC-KNC S14-44 (lane-0 IMCI instead
  of x87) wants our nbMakeTree repro/object after S8-04. knc-optimize "combined vs hand" mode by GCC-KNC detection
  requested from the GCC-KNC lead (owner 2026-11-16).

- Force bound method (GCC-KNC lead): interactions per step (body-cell + body-body, from walk counters) x ~20-25
  FP64 ops / 1.2 TFLOPS FP64 = T_lb; compare with measured 13.0 s. Same count x a GPU's FP64/FP32 rate gives the
  GPU target. Twin only for the inner interaction loop.

- 2026-11-16: twin T1-06 (x87 single rounding) merged and installed; the fmul repro now gives ...9f. After window
  12: rerun the 128-body chunk scaling and the six gravity bodies (light Codex ticket), report any remaining
  difference to the twin session.

- Never edit tools/codex_run.sh while a session runs: bash reads scripts as it goes (S2-02 exit 127).
- Do not remove a ticket worktree before its built artifacts (dist/, runs/) are no longer needed: they are gitignored.
