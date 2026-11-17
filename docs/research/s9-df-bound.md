# S9-05: reuse and certified eight-node experiment

`DF_REUSE=1` is an exact common-sample transformation, restricted to initialized
Plummer, generalized Hernquist, NFW and cored models. It does not declare the
lazy samplers pure. Five samples per selected density and per potential replace
both overlapping five-point stencils; potential center samples also supply the
integrand's center potential. The coefficients, reciprocals, addition order,
root search, quadrature recurrence and RNG calls are unchanged. King, Einasto,
and uninitialized models keep their original sampler calls. This is a
Performance patch; default zero.

`DF_VECTOR=1` requires reuse and is a separate Performance experiment, default
zero. `DF_STATS=1` is a separate Instrumentation patch. It counts velocity
attempts and exact body replays, with no counters in the performance patch.
The experiment uses eight-double GCC vector types, explicit KNC vector log/atan
ABI calls, IEEE division/square root, no reassociation or contraction, and
`-mveclibabi=knc -fno-math-errno`. The host experiment uses correctly rounded
bundled log_rn/atan_rn, inside the same one-ULP envelope; it does not execute KNC
libknc_vmath or prove its implementation. Its accuracy contract comes from the
local GCC-KNC `docs/USING.md`, section 6, and the local vector-math sources.
Plummer and cored profiles are supported. Cored samples above the density cutoff
use the exact scalar samplers (the incomplete-gamma expression has no vector
accuracy contract). Other profile combinations use the exact generator.

## Error enclosure

The target is the **rounded upstream expression graph**, not an analytic
continuum distribution function. Finite-difference truncation error is common
to both paths and is not part of the discrepancy. Each vector quantity is a
ball `(v,e)` with the invariant `|v - scalar_reference| <= e`. Input radii and
model parameters are the identical binary64 values; initial radii are generated
by the exact serial recurrence. All five shifted radii are formed with the
same rounded additions/subtractions as upstream, before starting their balls.
Constants computed by upstream arithmetic are also propagated through balls.

Write epsilon = DBL_EPSILON. For each arithmetic result, the implementation
adds `4 epsilon (|v| + t)` to the propagated operand error t. This covers BOTH
rounding graphs, since unit roundoff is epsilon/2. Every nonnegative bound is
inflated by `(1 + 32 epsilon)` and `32 DBL_MIN`; this covers the fewer than 16
rounded operations used to compute each bound and gradual underflow. For
addition/subtraction t = ea + eb. For multiplication,
`t = |a| eb + |b| ea + ea eb`. For division,
`t = (ea + |v| eb) / lower`, where lower is an outward lower bound on
`|b| - eb`; a nonpositive lower makes the bound infinite. Absolute value is
1-Lipschitz. Negation is exact. Repeated products use upstream's grouping.

For log, `t = ea / lower(a-ea)` bounds input perturbation by the mean value
theorem; nonpositive domains produce an infinite bound. For atan the derivative
is at most one, so t = ea. The additional `8 epsilon |v|` covers a one-ULP vector
answer and correctly rounded crlibm answer, including the outward-bound
arithmetic. For sqrt, use
`|sqrt(a+da)-sqrt(a)| <= sqrt(a) |da|/(a-|da|)` and the same arithmetic rounding
allowance. IEEE special cases, invalid/nonfinite bounds, overflow risk, and
zero-containing denominators are uncertifiable and request exact replay.
Subnormal errors are covered by the DBL_MIN allowances, not flush-to-zero.
The stipulated execution environment is round-to-nearest, binary64 precision,
gradual underflow, IEEE options, and no floating-point traps (the application's
crlibm environment); the capture hook checks x87 precision/rounding on workers.

The first derivative uses coefficients (1,-8,-1,8) in upstream order and the
second (-1,16,-30,16,-1). Their balls include sample error amplified by 1/(12h)
and 1/(12h^2), h=0.001, and cancellation does not discard absolute error. The
two potential derivatives are added in their original order. Balls propagate
through `d2rho / dpsi - drho*d2psi / (dpsi*dpsi)` and the reciprocal square root
of `abs(energy-potential)`. If either zero-substitution branch could be taken,
the node bound is infinite. This avoids making an approximate branch choice.

Quadrature stores the original nodes/weights, computes eight nodes per block
with OpenMP across blocks, and accumulates weights in order. The absolute node
error sum is `sum |c_i w_i| E_i`. Both weighted product/sum graphs are covered
by gamma_(8n) times the sum of absolute weighted values **plus** node errors,
with DBL_MIN allowances. A final factor 1000 is extra conservatism (not an
empirical fit). The finite-difference bound is never replaced by a measured
maximum ULP error. The extra factor also dominates rounding in the positive
node-error accumulation (n is capped by the original 100000-panel limit).
`dist_fun` scales the quadrature bound, adding a product-rounding allowance.

The guarded golden-section comparisons require disjoint balls, with an
additional subtraction-rounding margin. The acceptance comparison is
`u*abs(dist_max) < abs(d)` with propagated numerator/maximum errors and the
reference quotient's rounding allowance. A zero-containing maximum, NaN,
infinite bound, or overlapping comparison always marks uncertainty. On any
uncertainty the saved dSFMT state from the start of this body's velocity is
restored, the entire velocity is recomputed by the exact path, and only that
result and RNG state are retained. Root finding, energy and escape velocity
stay exact; no bound is needed for their comparisons. Thus induction over
certified comparisons preserves the same selected velocities and RNG stream.
Byte comparisons are an independent check on this reasoning.

## Selection rule

Measure core-small at 12 threads once per candidate. Keep the vector path only
with byte-identical bodies, identical likelihood bits, fewer than half of
bodies replaying, and lower measured generation time. A rejected experiment
is retained as disabled reproducible evidence, not selected for the final full
run or card handoff. The exact reuse build is the final candidate in that case.
Native card gains and native vector accuracy remain unproven without card
execution by the lead.

## Observed result and stop

One measured run each, sequentially at 12 threads: exact base 30.1570679 s;
exact reuse 18.2441604 s; guarded vector experiment 41.9036431 s. All three
produce the same 224,000 body bytes and likelihood -2357.2164009575326
(`-0x1.26a6ecc1b36dap+11`). The vector experiment replayed 3,245/4,000 bodies
(81.125%), so it was stopped and archived outside the fetch patch sequence.
The final source contains only exact reuse; the final core correctness check
also matches. It is not an extra timing observation used for the gain claim.

The independent host kernel check passes 2,048 potential/density sample
enclosures, 1,024 integrand-node enclosures and three guarded comparisons,
including core/cutoff boundaries. These checks detect implementation errors;
they do not replace the conditional arithmetic argument above.

KNC compile of the archived experiment fails with `unsupported KNC register
ABI mode` on by-value aggregates of two vectors. Reduced repro:
`probes/s9_df_ball_abi.c`; full/error diagnostics in `build/s9/df/vector-compile.log`
and `build/s9/df/ball-abi.txt`. No vector card binary or native certification
is claimed. The mandatory host fallback stop already rejects this candidate;
no additional vector performance work is done. The exact-reuse card binary
builds and passes knc_lint.
