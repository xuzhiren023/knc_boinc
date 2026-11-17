/* Compile to assembly on both targets to audit every capture-bound offset. */
#include "nbody_types.h"
#include <stddef.h>
const unsigned long s10_layout[]={sizeof(NBodyNode),sizeof(Body),sizeof(NBodyCell),
    offsetof(NBodyNode,pos),offsetof(NBodyNode,mass),offsetof(NBodyNode,next),offsetof(NBodyNode,type),
#if NBODY_WALK_HOT
    offsetof(NBodyNode,rcrit2),
#else
    offsetof(NBodyCell,rcrit2),
#endif
    offsetof(NBodyCell,more),offsetof(NBodyCell,stuff),offsetof(NBodyState,tree),offsetof(NBodyCtx,eps2),offsetof(NBodyCtx,useQuad)};
