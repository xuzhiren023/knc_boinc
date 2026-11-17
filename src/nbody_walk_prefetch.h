#ifndef NBODY_WALK_PREFETCH_H
#define NBODY_WALK_PREFETCH_H
/* Performance only. No allocation, packing, pointer arithmetic or FP changes. */
#ifndef NBODY_WALK_PREFETCH
#define NBODY_WALK_PREFETCH 0
#endif
#ifndef NBODY_WALK_SCHEDULE
#define NBODY_WALK_SCHEDULE 0
#endif
static inline void nbWalkNextPrefetch(const NBodyNode* q)
{
#if NBODY_WALK_PREFETCH
    const NBodyNode* next = Next(q);
    /* Bodies are smaller objects: never evaluate More(body). */
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
#endif
