#ifndef NBODY_WALK_ORDER_H
#define NBODY_WALK_ORDER_H
/* Performance: change only target order. Original nodes and force slots stay put. */
#ifndef NBODY_WALK_ORDER
#define NBODY_WALK_ORDER 0
#endif
#if NBODY_WALK_ORDER && (NBODY_VECTOR_GRAVITY || NBODY_WALK_LAYOUT)
#error WALK_ORDER requires scalar gravity and the original tree layout
#endif
#if NBODY_WALK_ORDER
static int* nbWalkOrder(const NBodyCtx* ctx, const NBodyState* st)
{
    const NBodyNode* q;
    int used = 0;
    int* order;
    /* A Lua closure may have side effects depending on its call order. */
    if (ctx->potentialType == EXTERNAL_POTENTIAL_CUSTOM_LUA) return NULL;
    order = mwMalloc(st->nbody * sizeof(*order));
    for (q = (const NBodyNode*)st->tree.root; q; q = isCell(q) ? More(q) : Next(q)) {
        if (!isCell(q)) {
            ptrdiff_t index = (const Body*)q - st->bodytab;
            if (index < 0 || index >= st->nbody || used >= st->nbody) abort();
            order[used++] = (int)index;
        }
    }
    /* Massless targets are absent from the tree. Preserve their calculation
     * and every unusual/incomplete tree case by retaining generation order. */
    if (used != st->nbody) { free(order); return NULL; }
    return order;
}
#endif
#endif
