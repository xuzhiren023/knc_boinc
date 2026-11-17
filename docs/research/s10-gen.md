# S10-03 generation study

## Timer plan (recorded before measurement)

`GEN_PROFILE=1` enables a caller-thread nested wall-clock stack. Its exclusive
buckets sum to the total generator wall time: `nodes` (parallel node evaluation,
team launch and barrier), `quad_serial` (node recurrence/allocation and ordered
accumulation), `dist_serial` (energy, search expansion, root finding), `max`
(golden-section decisions), `rejection` (velocity rejection decisions), `radius`
(radius rejection including density), `rng`, `components`, and residual `body`
(setup, per-body assignments, center corrections, Lua publication).
Inclusive max/rejection times are also printed, so their children must not be
added again. Serial fallback quadrature stays in quad_serial. RNG is time in
local mwXrandom calls and mwRandomUnitPoint (including its coordinate scaling),
not a timer in every library draw. Worker node evaluations never mutate timer
state. Counters give totals/means and per-body min/max integrals and radius /
velocity attempts; rng_calls counts actual dSFMT draws in these routines.

Timers are off by default. Clock calls and extra RNG wrapper stores can perturb
tiny phases; node dispatch wall time includes OpenMP overhead. Host data can
rank candidates but cannot establish the native KNC split. The baseline uses
S9-05 options because S10-01 release.env is absent in this worktree at start:
O2, tree=2, derivative reuse, parallel quad, static integrate, chunk=4;
vector gravity/walk layout off, phase timers on.

Initial prior: of the reported 46.9 s card setup, nodes/team overhead 28 s,
serial quadrature 7 s, root/search 10 s, radius/RNG/other body work 1.9 s.
This is a testable prior, not a native measurement. The staged baseline job
will resolve it before the lead judges any performance gain.

## Selection after baseline profile

The first 12-thread core-small capture measured 33.512683 s total:
32.045437 s nodes/dispatch, 1.260299 s dist root/search, 0.126615 s serial
quadrature, 0.080332 s other exclusive phases. Of serial time outside nodes,
root/search is 85.90%. Inclusive max finding is 27.531215 s; inclusive rejection
is 5.925073 s. Counts: 59181 integrals (14.79525/body, range 13..51), 10247
velocity attempts (2.56175/body, 1..39), 61168 radius attempts (15.292/body,
1..547), 188040 RNG draws. These are host observations, not KNC timings.

Selected candidate: `GEN_PIPELINE=1`, default off and only active with parallel
quadrature, initialized read-only supported models, and a serial caller. Each
current integral's existing node team also evaluates the root/search preparation
for both possible next golden-section velocities. Their coordinates use the
same stored x0/x1/x2/x3, constants and expression grouping as the original next
iteration. The actual comparison still executes in its original place; only the
bitwise matching candidate bounds are consumed. Both preparations use the
original search expansion, first sign-changing interval, NaN handling, bisection
midpoints, tolerance, iteration limits and fallback. No RNG is called. Workers
write separate slots, and the team barrier publishes them before reuse. The
consumer copies its prepared bounds before the next team overwrites the slots.
Unsupported/lazy models, nested callers, no-OpenMP, and option off use the
original path. A one-worker team computes both slots, so there is no reliance
on a minimum thread count. This is speculative algorithmic overlap, not a
compiler vectorization or scalar scheduling workaround.

Initial card prediction revised using host serial ranking (before any card run):
baseline setup 46.9 s = node team 30.0, root/search 15.0, serial quadrature 1.5,
other body work 0.4 s. About 49k/59k integral preparations belong to maximum
finding; all but its first preparation per body can hit (about 45k/59k, 76%).
Ideal removal is roughly 11 s of caller root work. Speculative preparation adds
work to two node workers and may become the team's tail: predict selected
setup 39 s (range 35..50 s), root/search on caller 3..5 s, node/team 30..43 s.
No speedup is assumed if the speculative tail exceeds the saved serial work.
The host node time is dominated by different threading costs; it is not scaled
wholesale into a card performance claim. Separate profile-off and profile-on
binaries let the lead distinguish timer overhead.

## Final host candidate and limits

The first implementation let preparation workers perform their original node
chunks afterward. Its profile-on generation took 49.321879 s. The final option
reserves two workers while preparation is active; all other workers distribute
the independent nodes. Teams of one/two workers evaluate both preparations
before their normal node shares. Quadrature accumulation still uses original
interval order. This reduced profile-on generation to 43.180450 s, but did not
beat the baseline's 33.505396 s. Final profile-off generation took 41.273101 s.
These are individual host observations, with other engineer tasks on the laptop;
no statistical speedup or cross-machine scaling claim follows.

Final profile partition: nodes 42.625723 s, serial quadrature 0.120449 s,
root/search 0.342592 s, all other exclusive work 0.164114 s; total
43.252879 s includes capture/publication overhead outside the capture timer.
Caller root/search is 72.82% lower; the team time rises. All counts and their
per-body ranges are unchanged. Both candidate captures are byte-identical to
the independent 4000-body reference, with likelihood -0x1.26a6ecc1b36dap+11
and every histogram row identical.

The final selection is this exact, reserved-worker experiment, left off by
default. It is **not a recommended release enablement** based on host timing.
The native card trial is needed to test whether its greater node parallelism
makes the overlap worthwhile. The two-job window compares profile-on baseline
and profile-on candidate with identical release fallback options; the third,
profile-off candidate binary is also provided, without an extra scheduled job.
Full generation is checked only once with the final profile-off host binary.

Radius, RNG and component arithmetic were not selected: their combined measured
exclusive time is small next to root/search. Speculating a bisection tree within
each root would add repeated synchronization to a phase with little work per
level. The chosen lookahead reuses the quadrature team that already exists and
speculates only RNG-free bounds. Speculation across whole bodies would also
need to predict how many dSFMT draws the current rejection loops consume; this
experiment avoids that additional state and discard logic.
