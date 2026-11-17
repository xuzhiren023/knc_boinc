#ifndef NBODY_WALK_PAGES_H
#define NBODY_WALK_PAGES_H
/* Performance only: dedicated THP-eligible allocations, no policy changes.
 * Native pointers stay 2 MiB aligned. Ordinary mwFreeA/free remains paired. */
#ifndef NBODY_WALK_HUGEPAGES
#define NBODY_WALK_HUGEPAGES 0
#endif
#if NBODY_WALK_HUGEPAGES && defined(__linux__)
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#define NB_WALK_PAGE ((size_t)2097152)
static inline void* nbWalkPageAlloc(size_t bytes)
{
    void* p;
    size_t total;
    if (bytes > SIZE_MAX - NB_WALK_PAGE) abort();
    total = (bytes + NB_WALK_PAGE - 1) & ~(NB_WALK_PAGE - 1);
    if (!total) total = NB_WALK_PAGE;
    if (posix_memalign(&p, NB_WALK_PAGE, total)) return mwMallocA(bytes);
#ifdef MADV_HUGEPAGE
    (void)madvise(p, total, MADV_HUGEPAGE);
#else
    (void)madvise(p, total, 14); /* Linux MADV_HUGEPAGE; old headers may lack it. */
#endif
    /* Advice can fail or be ignored. The untouched original bytes and free
     * protocol are valid with either page size; diagnostics inspect smaps. */
    return p;
}
#else
#define nbWalkPageAlloc(bytes) mwMallocA(bytes)
#endif
#define nbWalkPageFree(p) mwFreeA(p)
#endif
