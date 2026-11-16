S7-01: the current source is standard N-body 1.96. Its vector patch selects
softening from the fixed three-value table using node/body type sums, exactly
as the 1.96 scalar walk does. Run `python tests/nbody_196_matrix.py` for current
whole-run and first-force host identity. `bash scripts/build-vector-gravity.sh`
rebuilds/lints both 1.96 card variants and leaves lead-only commands.
The S6-03 twin captures, timings and range audit below are historical 1.97
evidence; they have not been regenerated for the changed 1.96 layouts.

# Eight-lane gravity (S6-01 / S6-03)

`NBODY_VECTOR_GRAVITY=0` remains the default on both architectures. The patch
adds `nbGravity8`; the tree caller selects it with `VECTOR_GRAVITY=1`. The
all-pairs algorithm and external-acceleration expressions keep their source.
Promotion of the card default belongs to the lead after the card A/B.

## Layout and bookkeeping

Groups contain eight contiguous bodies without refill. Each lane owns a node
pointer, position, XYZ accumulator and encountered-self flag. Guarded scalar
gathers pack coordinates, softening, mass and quadrupoles into local arrays.
No body is treated as a cell; null lanes never dereference a pointer. Partial
groups retain their real count. Each OpenMP iteration owns one complete group
with `schedule(dynamic,1)`, changing work assignment without changing any body's
sum. Missing-self bits return to the caller, which reports each offending body.
The full compiled kernel therefore has no cold reporting call or region cut.

A tree SoA rebuilt every force step could replace pointer packing with compact
indices. It costs O(nodes) copying, storage allocation/reuse and pointer mapping.
Eleven doubles and two links require roughly 104 bytes/node before type,
softening index and padding. The captured 29,611 nodes occupy 4,097,760 bytes in
the original layout; another representation costs several MB each step. Local
SoA scratch avoids that copy. Pointer packing, stack traffic and sparse lane
state still cost instructions and memory operations.

## Per-lane operation order

Each outer iteration visits exactly the lane's current node. Subtract XYZ and
compute `dz*dz + (dy*dy + dx*dx)` with source contraction disabled. Opening uses
the unsoftened square. An opened cell follows `More` without interacting. An
accepted node follows `Next`; self only sets the encountered flag. Add cell
`eps2_min` or the body-pair table element, compute `sqrt(d)`, then `(mass/r)/d`.
Apply the three monopole additions before the quadrupole additions and finally
the quadrupole subtractions. The quad expressions are:

```text
qx = (xx*x + xy*y) + xz*z       (and the corresponding qy, qz rows)
dot = (qx*x + qy*y) + qz*z
inv = 1 / ((d*d)*r)
phi = (2.5*(inv*dot))/d
acc += phi*dr
acc -= inv*qdr
```

There is no horizontal reduction or reassociation. Vector bit selection retains
untouched accumulator bits, including signed zero. Noninteraction slots use
distance 1 and mass 0. Nonquad slots use distance/radius 1 and displacement 0;
unused results never reach the accumulators. Inactive arithmetic is not a
promise to preserve every floating-point exception flag for arbitrary inputs.
Divergence pays for the longest walk, opened cells, quad-only work and packing.
Refill is deferred because it needs output scatter and per-lane body setup.

## Compiler and code generation

Use `-O2 -march=knc -ffp-contract=off -fno-math-errno`, without fast math.
GCC-KNC S10-09 implements correctly rounded V8DF division and sqrt in all
rounding modes with IEEE flags. Its `vrcp23ps` / `vrsqrt23ps` seeds and internal
FMA refinement implement the IEEE operation; `-ffp-contract=off` continues to
prevent contraction of source expressions. The old claims at GCC-KNC
`docs/gcc-knc-flags.md:107-108` were stale, as settled in the ticket. The proof
is GCC-KNC `docs/research/knc-div-sqrt.md` section 3; the 2026-11-12 card regression
checked 268M random operands each plus adversarial and special sets with bad=0.

S6-03 removes `#pragma GCC novector` and explicitly expresses all quadrupole
arithmetic as eight-lane vectors. The softening addition is vectorized too.
The final `nbGravity8` disassembly and opcode inventory are regenerated from the
linked card executable. No x87 add/sub/mul/div/sqrt remains. Remaining x87
instructions move packed scalar values and implement the distance-versus-cell
opening comparison; their exact counts are in `twin/vector/evidence.json`.
Every FMA belongs to a compiler div/sqrt expansion. The old rejected-lowering
probe is removed; the final extracted function is the executed twin kernel.

## Exactness scope and exponent range

x87 PC53 constrains significand precision, not exponent range. Scalar
intermediates can survive below binary64's subnormal range or above DBL_MAX
before a spill; vector operations round to binary64 after each operation.
The application allows user coordinates and masses without global intermediate
bounds. Softening entries must exceed REAL_EPSILON, which does not bound
coordinate differences, squares, quad products or accelerations.

Concrete possible divergences include a coordinate difference `1e200`: its
square fits the x87 exponent range but overflows binary64. A difference `1e-200`
has a square `1e-400`, retained by x87 but rounded to zero by binary64 before
softening. Quadrupole components and displacements near `1e200` similarly
produce products above DBL_MAX, and cancellation or a later reciprocal can
bring a scalar result back into range.

A precise accepted-body example, inferred from the scalar card disassembly:
target position `(0,0,0)`, source position `(2^600,0,0)`, source mass `2^900`,
pair softening `1`, and no quadrupole. These inputs are all finite binary64.
The scalar body path retains `d=2^1200` in x87 (adding 1 rounds back to that
value), computes `r=2^600`, `(mass/r)/d=2^-900`, and contributes `2^-300` to X.
Vector squaring overflows to infinity, so its radius is infinity, its mass
factor is zero, and its X contribution is zero. The scalar object shows no
binary64 spill of d in this body path (offsets 0xcb-0xd7 through 0x74-0x7f
in `build/s6-scalar-grav.disassembly.txt`). This is an instruction-level range
counterexample, not a card measurement or a claim about tree construction for
that artificial input. Universal bit identity is not established.

The independent binary64 range audit covers the first 4,096 large bodies,
79,854,572 primitive operations and all 98,304 captured XYZ bytes. Nonzero
magnitudes span 5.095619795767879e-19 to 226086426043.44855; no subnormal or
nonfinite result occurs. Those walks therefore do not expose the exponent-range
problem. The five whole-workunit x86 cases cover small/medium at 1 and 12 threads
and large at 12; they compare exact likelihood and histogram tokens and saved
histogram bytes, omitting only the generated timestamp. Both macro settings
also replay all 98,304 independent acceleration bytes. These finite inputs do
not prove all later card steps or arbitrary user inputs.

## Twin, tests and handoff

`reproduce.sh` checks capabilities before executing groups 0, 1024, 2048 and
4088. The installed twin 0.4.0 lists the seeds and FMA forms as functional.
Its seeds use correctly rounded stand-ins without captured native seed tables;
that approximation is preserved in assumptions and timing exactness metadata.
Functional expected outputs are the unchanged independent x86 capture. Each
vector run checks eight XYZ blocks and a zero missing-self mask. Cycle results
are reported only when both functional and simulation status are `ok`, and are
`unvalidated_scenario_estimate` model predictions, never card measurements.
Lane occupancy comes from the compiled pointer-check branch in the trace.

Installed `references/handoff-prompt.md` still lists S14-37 as unfixed. Scalar
baselines and vector/scalar ratios are therefore withheld. The S6-02 test split
now requires the full vector codegen and four passing vector groups. Its sole
remaining expected-failure test names the scalar S14-37 blocker; div/sqrt
correct rounding is no longer an expected failure. No tolerance or altered
expected bytes are used to pass functional checks.

From Git Bash at the worktree root, with pinned sources already patched:

```bash
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
bash twin/vector/reproduce.sh ../S1-06/twin/multicore
python tests/test_vector_gravity.py -v
bash scripts/vector-card-commands.sh  # prints commands; does not run the card
```

Only after S14-37 lands, set `TWIN_SCALAR_READY=1` to include scalar baseline
extraction/replays. The default leaves historical scalar evidence untouched.
Card off/on binaries and compiler runtimes are staged in `dist/card/vector-off/`
and `dist/card/vector-on/`. The four printed A/B commands run medium and large
at 240 threads. `scripts/check_vector_card.py` then compares each card result's
printed likelihood and histogram tokens exactly with the x86 macro-off
references. Raw card acceleration bytes and native performance remain unproven.

The installed scalar defect was also confirmed with the existing independent
`twin/x87-rounding-repro.json`: expected `0xbf1202b59a43239f`, twin returned
`0xbf1202b59a43239e`. The compact fresh record is
`twin/vector/s14-37-check.json`; this intentionally mismatching defect probe is
separate from the four passing vector gravity checks.

S6-03 results (2026-11-16): all five x86 matrix cases pass exactly; both macro
settings match all 98,304 capture bytes. All four twin functional checks match
9/9 expected items, and all four simulations return `ok`:

| First body | Predicted cycles/body | Mean active lanes | Lane occupancy |
|---:|---:|---:|---:|
| 0 | 284129.000 | 6.294020 | 78.6752% |
| 1024 | 293383.875 | 7.177966 | 89.7246% |
| 2048 | 285499.000 | 6.369384 | 79.6173% |
| 4088 | 272248.625 | 7.497248 | 93.7156% |

These are one-context, eight-body, first-step model results under the
qualifications above. No vector/scalar performance ratio is available.
