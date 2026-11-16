/* Compiled contiguous-body driver. nbGravity is the unchanged local function
 * from a copy of the card app's nbody_grav object (symbol visibility only). */
#include "nbody_priv.h"
extern mwvector nbGravity(const NBodyCtx*, NBodyState*, const Body*);
void nbGravityChunk(mwvector *out, const NBodyCtx *ctx, NBodyState *st,
                    const Body *first, unsigned count)
{
    unsigned i;
    for (i = 0; i < count; ++i)
        out[i] = nbGravity(ctx, st, first + i);
}
