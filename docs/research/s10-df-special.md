# S10-05: concrete mixed-dwarf node evaluation

`DF_SPECIAL=1` requires `DF_REUSE=1`, `PARALLEL_QUAD=1` and OpenMP.
It is off by default, including `config/release.env`. It applies only when the
quadrature callback is `fun`, the light component is Plummer, and the dark
component is initialized Cored. The existing nested/lazy-model serial guards
remain ahead of specialization. Unsupported profiles and callbacks use the
existing quadrature path; active generator pipelining also keeps that path.

The Performance patch is `patches/zzzzzz-nbody-df-special.patch`. Its private
header copies the four concrete potential/density expressions from pinned 1.96,
then substitutes direct function names in the existing reuse stencils. The five
sample order is mm, m, pp, p, center; coefficients, left-to-right additions,
reciprocal grouping, derivative-zero substitution and energy-singularity
fallback are retained. Light/dark dispatch is outside the node loops. The
original quadrature recurrence, interval storage, ordered accumulation and
scalar incomplete-gamma implementation are untouched. There are no RNG calls
in this path and no math relaxations. The host kernel checks node values
bitwise, including cutoff/core stencil crossings and the exact singularity.
Whole-generator proof compares all seven double fields of every core-small
body, all per-body RNG states, the likelihood bits and histogram contract.

## Numerical experiment

`probes/s10-df-vmath/performance.patch` is a separate Performance experiment,
applied to an isolated source tree by `scripts/build-s10-df-special.sh vmath`.
`DF_VMATH=1` is refused by ordinary builds. It never enters the fetch sequence
or release configuration. Gamma and its internal crlibm calls are unchanged;
`pow_rn` is also unchanged. Only the specialized cored log, atan and exp calls
change. There is no uncertainty bound, replay or accept/reject safety net.

The installed library has no double atan entry. Its actual atan2 lane core
computes atan(x) as atan2(x,1). Log and exp use their actual lane cores too.
The pointer ABI with one active lane lets the host execute the same copied
library algorithms, without substituting host libm or the crlibm stand-ins
used in the old S9 experiment. The card uses the installed libknc_vmath with
`-mveclibabi=knc -fno-math-errno`. This measures numerical relaxation even if
whole-node vectorization is still blocked. Mask/call overhead makes these
host timings unsuitable as a projection of a future batched vector path.
The installed archive is byte-identical to `_shared/S10-02/knc/libknc_vmath.a`;
use the matching `_shared/S10-02/host/libknc_vmath.a`, not `vmath-main`.
Hashes are retained in `build/s10/df-special/library-provenance.txt`.
Host/card bit identity of the math library remains a card-window check.

`tests/s10_df_capture.h` is instrumentation in test translation units only.
It writes initialized dSFMT state words plus its index after each body,
excluding struct padding (3076 bytes per record). RNG comparisons happen
before center-of-mass correction; final-body comparisons happen after it.
Consequently a body may differ even while its RNG state is unchanged, and a
later center-of-mass shift can make earlier output rows differ too. The first
RNG divergence index is zero based and names the body whose end state first
differs. Null means no divergence was observed through the final body.

## Reproduction and retained evidence

From a fresh worktree with the pinned, patched upstream sources present:

```bash
bash scripts/test-s10-df-special.sh --full
```

This builds at most two compiler jobs at a time, then runs each core-small
variant once at 12 threads, builds/lints the card artifacts, and runs exactly
one full 117676 generation for each of special and vmath, sequentially.
`full-*-started.json` prevents repeating a long generation. The exact full
capture is also checked against the previously established 1.96 SHA256.
Both full generations stop after writing bodies, before simulation.

For retained proofs, without another generation:

```bash
bash scripts/test-s10-df-special.sh
```

Build logs, missed-vectorization diagnostics, source copies, binary options,
RNG traces, counts, timings and handoff hashes live in
`build/s10/df-special/` and `runs/s10-df-special/`. The lead-only
`build/s10/df-special/card-window.sh` stages release, exact-special and
experimental core-small jobs at 240 threads, with runtime libraries and
predictions recorded before card execution. Its final `card_report` checks the
exact likelihood bits and records the experimental difference and card times.
No card access is used here.

`probes/s10_df_vmath_repro.c` separates the scalar crlibm-call blocker from a
plain-log loop the compiler can vectorize, and from the scalar incomplete-gamma
call. Compiler opportunities remain GCC-KNC work; no scheduling, polynomial
or gamma rewrite is included in the exact patch.

## Compiler and twin evidence

In the actual card compilation, the two specialized loops are at lines 434
and 440 of the retained generator source. Both report unsupported control
flow. Their inlined samples report `log_rn`, `atan_rn`, `exp_rn`, `pow_rn` and
`UpperIncompleteGammaFunc` as memory-clobbering scalar calls. The generic
worker still reports its callback, as expected; that diagnostic does not
belong to the specialized loops. The final short packing blocks also report
that vectorization is not profitable. Nothing here justifies changing the
exact math contract.

The reduced compiler probe gives a useful separation with the same flags:
`df_crlibm` is not vectorized, `df_libm` and `df_libm_exp` vectorize with
64-byte vectors and call `__knc_vmath_log_8` / `__knc_vmath_exp_8`.
`df_gamma` is not vectorized. Plain `atan` also fails to vectorize (unsupported
SLP instances); the installed library has no double atan entry. Its assembly and
`-fopt-info-vec-all` output are retained in `compiler-repro-complete.s` and
`compiler-repro-complete-vec.txt`. Reproduce without a build-system change:

```bash
mkdir -p build/tmp build/s10/df-special
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$shared/toolchain/cygwin/bin:$PATH"
"$shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc" \
  -O2 -march=knc -fno-math-errno -ffp-contract=off -mveclibabi=knc \
  -fopt-info-vec-all=build/s10/df-special/compiler-repro-complete-vec.txt \
  -S probes/s10_df_vmath_repro.c -o build/s10/df-special/compiler-repro-complete.s
```

knc-twin 0.4.0 capabilities were read first. Whole linked functions
`gauss_quad._omp_fn.1` were audited using the binary adapter for both card
variants. Both stop with exit 2: the index division by three compiles to
one-operand `imul` (rdx:rax), unsupported by the twin. Direct scalar math/gamma
and OpenMP calls would also need measured callee costs to simulate this
worker faithfully. No partial kernel was simulated, no cycles or speedups
were inferred, and no captured model table was used. The adapter reports
2096 instructions for exact and 2316 for the experiment; these are static
instruction counts, not dynamic costs. Adapter logs/reports and measured
host wall time live under `twin-*` and `twin-effort.json`. The card-window
predictions are explicitly uncalibrated hypotheses, not twin results.

The binary-adapter audit can be reproduced from bash (exit 2 is the retained
unsupported result; do not substitute a partial region to obtain a timing):

```bash
skill=/c/Users/xuzhi/.claude/skills/knc-twin
shared=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
python "$skill/scripts/knc_twin.py" capabilities \
  --out build/s10/df-special/twin-capabilities-fresh
for variant in special vmath; do
  python "$skill/scripts/from_binary.py" \
    "build/s10/df-special/card-$variant/milkyway_nbody.mic" \
    --function gauss_quad._omp_fn.1 \
    --objdump "$shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe" \
    --out "build/s10/df-special/twin-$variant/kernel.json" \
    --report "build/s10/df-special/twin-$variant/adapter.json"
done
```
