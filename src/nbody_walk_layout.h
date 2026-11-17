#ifndef NBODY_WALK_LAYOUT_H
#define NBODY_WALK_LAYOUT_H
/* S8-08: transient read-only force view. Original tree/body ownership survives
 * every map; no checkpoint or integrator sees the reordered arrays. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#ifndef NBODY_WALK_LAYOUT
#define NBODY_WALK_LAYOUT 0
#endif
#ifndef NBODY_WALK_COUNTERS
#define NBODY_WALK_COUNTERS 0
#endif
#if NBODY_WALK_COUNTERS && defined(__MIC__)
#error Walk counters are host debug instrumentation, never a card timing build
#endif

static inline void nbWalkPrefetch(const NBodyNode* q)
{
#if NBODY_WALK_LAYOUT
    /* Both successor addresses are already in the current node. The selected
     * successor is not known until the opening test. Hints do not dereference
     * NULL, bodies as cells, or pointers beyond the allocated objects. */
    const NBodyNode* next = Next(q);
    const NBodyNode* more = isCell(q) ? More(q) : NULL;
#ifdef __MIC__
    if (next) __asm__ __volatile__("vprefetch0 (%0)" :: "r"(next));
    if (more) __asm__ __volatile__("vprefetch0 (%0)" :: "r"(more));
#else
    if (next) __builtin_prefetch(next, 0, 3);
    if (more) __builtin_prefetch(more, 0, 3);
#endif
#else
    (void)q;
#endif
}

#if NBODY_WALK_LAYOUT
typedef struct { const NBodyNode* old; NBodyNode* copy; } NBWalkLink;
typedef struct {
    NBodyCell* cells;
    Body* bodies;
    mwvector* forces;
    unsigned* original;
    Body* savedBodies;
    mwvector* savedForces;
    NBodyCell* savedRoot;
} NBWalkLayout;
static size_t nbWalkSlot(const NBodyNode* p, size_t mask)
{
    uintptr_t n = (uintptr_t)p >> 4;
    return (size_t)((n ^ (n >> 17)) * (uintptr_t)2654435761u) & mask;
}
static NBodyNode* nbWalkLookup(NBWalkLink* links, size_t mask, const NBodyNode* p)
{
    size_t h;
    if (!p) return NULL;
    h = nbWalkSlot(p, mask);
    while (links[h].old != p) { assert(links[h].old); h = (h+1)&mask; }
    return links[h].copy;
}
static NBWalkLayout nbWalkBegin(NBodyState* st)
{
    NBWalkLayout v;
    const NBodyNode* q;
    size_t nc = 0, nb = 0, cap = 1, c = 0, b = 0, h, i;
    NBWalkLink* links;
    unsigned char* seen;
    memset(&v, 0, sizeof(v));
    v.savedBodies = st->bodytab; v.savedForces = st->acctab; v.savedRoot = st->tree.root;
    for (q = (const NBodyNode*)st->tree.root; q; q = isCell(q) ? More(q) : Next(q))
        if (isCell(q)) ++nc; else ++nb;
    assert(nb <= (size_t)st->nbody);
    while (cap < 2*(nc + st->nbody + 1)) cap *= 2;
    links = (NBWalkLink*)mwCalloc(cap, sizeof(*links));
    seen = (unsigned char*)mwCalloc(st->nbody, 1);
    v.cells = (NBodyCell*)mwMallocA((nc ? nc : 1)*sizeof(*v.cells));
    v.bodies = (Body*)mwMallocA(st->nbody*sizeof(*v.bodies));
    v.forces = (mwvector*)mwMallocA(st->nbody*sizeof(*v.forces));
    v.original = (unsigned*)mwMalloc(st->nbody*sizeof(*v.original));
    for (q = (const NBodyNode*)st->tree.root; q; q = isCell(q) ? More(q) : Next(q))
    {
        NBodyNode* copy;
        if (isCell(q)) { v.cells[c] = *(const NBodyCell*)q; copy = (NBodyNode*)&v.cells[c++]; }
        else {
            i = (const Body*)q - v.savedBodies;
            assert(i < (size_t)st->nbody && !seen[i]); seen[i] = 1;
            v.original[b] = (unsigned)i;
            v.bodies[b] = *(const Body*)q; copy = (NBodyNode*)&v.bodies[b++];
        }
        h = nbWalkSlot(q, cap-1);
        while (links[h].old) h = (h+1)&(cap-1);
        links[h].old = q; links[h].copy = copy;
    }
    /* Zero-mass test particles are absent from the source tree, but remain
     * force targets. Their stale Next field is never followed. */
    for (i = 0; i < (size_t)st->nbody; ++i) if (!seen[i]) {
        v.original[b] = (unsigned)i; v.bodies[b] = v.savedBodies[i];
        Next(&v.bodies[b++]) = NULL;
    }
    assert(b == (size_t)st->nbody);
    for (i = 0; i < nc; ++i) {
        Next(&v.cells[i]) = nbWalkLookup(links, cap-1, Next(&v.cells[i]));
        More(&v.cells[i]) = nbWalkLookup(links, cap-1, More(&v.cells[i]));
    }
    for (i = 0; i < nb; ++i)
        Next(&v.bodies[i]) = nbWalkLookup(links, cap-1, Next(&v.bodies[i]));
    st->tree.root = (NBodyCell*)nbWalkLookup(links, cap-1, (NBodyNode*)v.savedRoot);
    st->bodytab = v.bodies; st->acctab = v.forces;
    free(links); free(seen);
    return v;
}
static void nbWalkEnd(NBodyState* st, NBWalkLayout* v)
{
    unsigned i;
    for (i = 0; i < st->nbody; ++i) v->savedForces[v->original[i]] = v->forces[i];
    st->tree.root = v->savedRoot; st->bodytab = v->savedBodies; st->acctab = v->savedForces;
    mwFreeA(v->cells); mwFreeA(v->bodies); mwFreeA(v->forces); free(v->original);
}
#endif

#if NBODY_WALK_COUNTERS
/* Independent scalar shadow traversal counts source-level node field accesses,
 * not hardware misses. Each body owns a set of 64-byte line tags. These counters
 * deliberately perturb timing and are compiled out of all card builds. */
#include "nbody_walk_capture.h"
typedef struct { uint64_t bc, bb, nodes, lines, order; } NBWalkCount;
typedef struct { uintptr_t tag; uint64_t generation; } NBWalkLine;
static __thread NBWalkLine nbWalkLines[32768];
static __thread uint64_t nbWalkGeneration;
static uint64_t nbWalkHash(uint64_t h, uint64_t x) { return (h ^ x)*UINT64_C(1099511628211); }
static void nbWalkTouch(NBWalkCount* c, const void* p, size_t bytes)
{
    uintptr_t line = (uintptr_t)p >> 6, last = ((uintptr_t)p + bytes-1) >> 6;
    for (; line <= last; ++line) {
        size_t h = (line*2654435761u)&32767;
        while (nbWalkLines[h].generation == nbWalkGeneration && nbWalkLines[h].tag != line) h = (h+1)&32767;
        if (nbWalkLines[h].generation != nbWalkGeneration) {
            nbWalkLines[h].generation = nbWalkGeneration; nbWalkLines[h].tag = line; ++c->lines;
        }
    }
}
static void nbWalkCounts(const NBodyCtx* ctx, const NBodyState* st)
{
    unsigned i;
    const char* enabled = getenv("NBODY_WALK_COUNT");
    nbWalkCapture(ctx, st);
    if (!enabled || !atoi(enabled)) return;
    if (atoi(enabled) > 1 && st->step != 0) return;
    NBWalkCount* counts = (NBWalkCount*)mwCalloc(st->nbody, sizeof(*counts));
    NBWalkCount sum = {0,0,0,0,UINT64_C(1469598103934665603)};
    uint64_t min = UINT64_MAX, max = 0;
#pragma omp parallel for schedule(static)
    for (i = 0; i < st->nbody; ++i) {
        const Body* p = &st->bodytab[i];
        const NBodyNode* q = (const NBodyNode*)st->tree.root;
        NBWalkCount* c = &counts[i];
        c->order = UINT64_C(1469598103934665603); ++nbWalkGeneration;
        nbWalkTouch(c, &Pos(p), 3*sizeof(real)); nbWalkTouch(c, &Type(p), sizeof(body_t));
        while (q) {
            mwvector dr = mw_subv(Pos(q), Pos(p));
            real d = mw_sqrv(dr);
            uint64_t bits;
            memcpy(&bits, &Pos(q).x, sizeof(bits));
            c->order = nbWalkHash(c->order, bits); c->order = nbWalkHash(c->order, (uint64_t)Type(q));
            ++c->nodes;
            nbWalkTouch(c, &Pos(q), 3*sizeof(real)); nbWalkTouch(c, &Type(q), sizeof(body_t));
            if (isCell(q)) nbWalkTouch(c, &Rcrit2(q), sizeof(real));
            if (isBody(q) || d >= Rcrit2(q)) {
                if ((const Body*)q != p) {
                    if (isCell(q)) ++c->bc; else ++c->bb;
                    nbWalkTouch(c, &Mass(q), sizeof(real));
                    if (ctx->useQuad && isCell(q)) nbWalkTouch(c, &Quad(q), sizeof(NBodyQuadMatrix));
                }
                nbWalkTouch(c, &Next(q), sizeof(q)); q = Next(q);
            } else { nbWalkTouch(c, &More(q), sizeof(q)); q = More(q); }
        }
    }
    /* Body targets can be permuted by layout: reduce the per-body sequence
     * fingerprints commutatively, preserving order within each individual walk. */
    sum.order = 0;
    for (i = 0; i < st->nbody; ++i) {
        sum.bc += counts[i].bc; sum.bb += counts[i].bb; sum.nodes += counts[i].nodes; sum.lines += counts[i].lines;
        sum.order += counts[i].order;
        if (counts[i].lines < min) min = counts[i].lines;
        if (counts[i].lines > max) max = counts[i].lines;
    }
    fprintf(stderr, "WALK_COUNT step=%u bodies=%u body_cell=%llu body_body=%llu nodes=%llu lines=%llu min=%llu max=%llu order=%016llx\n",
        st->step, st->nbody, (unsigned long long)sum.bc, (unsigned long long)sum.bb,
        (unsigned long long)sum.nodes, (unsigned long long)sum.lines, (unsigned long long)min,
        (unsigned long long)max, (unsigned long long)sum.order);
    free(counts);
}
static void nbWalkForceHash(const NBodyState* st)
{
    const char* dump = getenv("NBODY_WALK_FORCE_DUMP");
    static FILE* file;
    if (dump && !file) {
        file = fopen(dump, "wb");
        if (file) setvbuf(file, NULL, _IOFBF, 1024*1024);
    }
    unsigned i, j; uint64_t h = UINT64_C(1469598103934665603);
    if (dump && !file) abort();
    for (i = 0; i < st->nbody; ++i) {
        real xyz[3] = {st->acctab[i].x, st->acctab[i].y, st->acctab[i].z};
        const unsigned char* p = (const unsigned char*)xyz;
        if (file && fwrite(xyz, 1, sizeof(xyz), file) != sizeof(xyz)) abort();
        for (j = 0; j < sizeof(xyz); ++j) h = nbWalkHash(h, p[j]);
    }
    fprintf(stderr, "WALK_FORCE step=%u hash=%016llx\n", st->step, (unsigned long long)h);
}
#endif
#endif
