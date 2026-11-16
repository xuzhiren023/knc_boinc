# Eight-lane gravity prototype (S6-01)

`NBODY_VECTOR_GRAVITY=0` is the default on both architectures. The patch adds
`nbGravity8`; the tree caller selects it only with `VECTOR_GRAVITY=1`. The exact
(all-pairs) algorithm and external-acceleration expressions retain their source.
This is an experiment; promotion of the card default belongs to the lead.

## Layout and bookkeeping

Keep groups of eight contiguous bodies, with no refill. Each lane owns a node
pointer, position, XYZ accumulator and encountered-self flag. Local arrays of
eight doubles present the independent arithmetic to the vectorizer. Guarded
scalar gathers read the eight node pointers, then pack coordinates, softening,
mass and quadrupoles into those arrays. No body is treated as a cell; null lanes
never dereference a pointer. Partial groups retain the real count. Each OpenMP
iteration owns one complete group (`schedule(dynamic,1)`), rather than sharing
lane state between workers. This changes work assignment but no body's sums.

An alternative is a tree SoA rebuilt once each force step, with compact indices
for next/more, positions, masses, cell criteria and quadrupoles. It removes
pointer packing but costs O(nodes) copying, allocation/reuse, mapping host
pointers to indices and additional storage. A uniform representation needs
roughly 104 bytes/node for 11 doubles plus two 64-bit links, before type and
softening index/padding. The captured 29,611 nodes occupy 4,097,760 bytes in the
original layout; another dense representation is several MB and must be paid
on every rebuilt tree. This prototype uses local SoA scratch only, avoiding
that copy. Hardware gather can still serialize by cache line; local staging
also adds stack traffic and scalar control instructions.

## Per-lane order and masks

At each outer iteration a lane visits exactly its current node. Compute
`dx,dy,dz`, then `dz*dz + (dy*dy + dx*dx)`, which is the expanded `mw_sqrv`
with contraction disabled. Body-or-distance opening uses the unsoftened square.
An opened cell follows `More` without interacting. An accepted node follows
`Next`; self sets the encountered flag without contributing. Interactions add
cell `eps2_min` or the body-pair table element before the same `mw_sqrt`,
`mass/r`, then `/d` as upstream. XYZ monopoles are accumulated before quad
phi additions and then quad subtractions. No lane reduction, FMA, approximate
reciprocal or reassociation is allowed. The kernel returns a missing-self bit mask; the group caller calls the same
`nbReportTreeIncest` after the walk, once per offending body. Returning this
mask keeps the full computational kernel free of cold reporting calls, without
cutting or rewriting its compiled instructions for the twin.

Hit and quad masks protect accumulator updates (including signed-zero state).
Inactive arithmetic slots use distance 1 and mass 0; the resulting values are
never added. Guarded memory operations remain scalar where the compiler cannot
prove safe masked loads. Divergence pays for the longest walk in a group,
for visits that open cells without interacting, for quad-only work, and for
packing/reloading sparse lane state. No refill keeps bookkeeping simple but
utilization falls as lanes finish. A refill design would preserve each body's
sequence too, but adds output scatter, per-lane new-body setup, and variable
work accounting. It is deferred.

## Compiler and exactness gates

Read GCC-KNC `docs/USING.md` and `docs/gcc-knc-flags.md`. The backend supports
masked tails, gathers/scatters and `-fopt-info-vec-optimized` / missed reports.
Use `-O2 -march=knc -ffp-contract=off -fno-math-errno`, with no fast math.
The flags document says FP64 division remains scalar x87. The installed
compiler actually lowers a vectorized sqrt/div stage to reciprocal/rsqrt seeds
and FMAs with refinement, even with `-ffp-contract=off`. The evidence-only
`lowering-probe` records this discrepancy; that object is never linked or run.
Under the ticket's literal instruction rule the final prototype uses
`#pragma GCC novector` for that stage. Distance and explicitly masked monopole
arithmetic use zmm; sqrt, divide and quadrupole arithmetic still use x87.
Mask selection uses `vpandq/vpxorq`, preserving inactive bits. This
hybrid does not satisfy the requested x87-free masked walk. No compiler
instruction was rewritten to feed the twin.

53-bit precision does not constrain x87's exponent range. Scalar intermediates
can survive below the binary64 subnormal boundary or above DBL_MAX before a
spill, whereas binary64 vector operations round into their narrower range at
each operation. The application accepts user coordinates, masses and softening;
the parameter checker requires softening entries above REAL_EPSILON, but
places no global bounds on every intermediate coordinate difference, square,
quadrupole product and acceleration. For example finite coordinate differences
above sqrt(DBL_MAX) overflow a binary64 square while fitting the x87 range;
tiny coordinate differences can have subnormal or underflowing squares before
softening is added. Universal bit identity is consequently not established.
The pinned workunits and the finite captured first-step interactions must be
checked independently; success there is evidence only for those inputs. Even
normal-range division/sqrt can expose the twin's S14-37 double-rounding defect.
No tolerance or altered expected bytes can replace the exactness gate.

## Reproduction and current evidence

Commands, exactness, code generation, twin status and unresolved limits are
recorded in `twin/vector/evidence.json` and the ticket's Engineer report.
The acceptance test deliberately fails if required evidence is unavailable;
a stopped/unsupported run is not silently counted as acceptance.

The independent binary64 audit of the captured first 4,096 large bodies checks
79,854,572 primitive operations and reproduces all 98,304 expected bytes.
Its nonzero magnitudes range from 5.095619795767879e-19 to
226086426043.44855; it finds zero subnormal and zero non-finite results. Thus
exponent-range differences do not occur in those captured walks. This says
nothing about every later time step or arbitrary user inputs. See
`twin/vector/range.json` for the audit scope.
