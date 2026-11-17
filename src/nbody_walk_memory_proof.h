#ifndef NBODY_WALK_MEMORY_PROOF_H
#define NBODY_WALK_MEMORY_PROOF_H
/* Instrumentation only. A separate diagnostic binary, excluded from timings. */
#ifndef NBODY_WALK_MEMORY_PROOF
#define NBODY_WALK_MEMORY_PROOF 0
#endif
#if NBODY_WALK_MEMORY_PROOF
#include "nbody_walk_pages.h"
static void nbWalkMapping(const char* name, const void* p)
{
    fprintf(stderr, "WALK_MEMORY name=%s address=%p alignment_2m=%u\n", name, p, (unsigned)((uintptr_t)p % 2097152 == 0));
#if defined(__linux__)
    {
        char line[512]; unsigned long lo, hi; int found = 0;
        FILE* f = fopen("/proc/self/smaps", "r");
        if (!f) { fprintf(stderr,"WALK_MEMORY smaps=unavailable\n"); return; }
        while (fgets(line,sizeof(line),f)) {
            if (sscanf(line,"%lx-%lx",&lo,&hi)==2) {
                if (found) break;
                found = (uintptr_t)p >= lo && (uintptr_t)p < hi;
                if (found) fprintf(stderr,"WALK_MEMORY %s mapping=%s",name,line);
            } else if (found && (!strncmp(line,"KernelPageSize:",15) ||
                       !strncmp(line,"MMUPageSize:",12) || !strncmp(line,"AnonHugePages:",14) ||
                       !strncmp(line,"Private_Hugetlb:",16) || !strncmp(line,"Shared_Hugetlb:",15) ||
                       !strncmp(line,"VmFlags:",8))) fprintf(stderr,"WALK_MEMORY %s %s",name,line);
        }
        if (!found) fprintf(stderr,"WALK_MEMORY %s mapping=not-found\n",name);
        fclose(f);
    }
#else
    fprintf(stderr,"WALK_MEMORY %s backing=host-fallback-unproven\n",name);
#endif
}
static void nbWalkMemoryProof(const NBodyState* st)
{
    static int done;
    if (done++) return;
    nbWalkMapping("bodies",st->bodytab);
    if (st->treePool) nbWalkMapping("tree",st->tree.root);
    else { fputs("WALK_MEMORY tree=not-pooled", stderr); fputc(10, stderr); }
}
#else
#define nbWalkMemoryProof(st) ((void)0)
#endif
#endif
