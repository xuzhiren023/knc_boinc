#ifndef NBODY_WALK_PROFILE_H
#define NBODY_WALK_PROFILE_H
/* Instrumentation only; never enable in candidate timing builds. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#ifndef NBODY_WALK_PROFILE
#define NBODY_WALK_PROFILE 0
#endif
#ifndef NBODY_WALK_PROOF
#define NBODY_WALK_PROOF 0
#endif
#if NBODY_WALK_PROFILE && (!defined(_OPENMP) || NBODY_VECTOR_GRAVITY)
#error WALK_PROFILE requires scalar gravity with OpenMP
#endif
#if NBODY_WALK_PROFILE
#include <omp.h>
typedef struct {
    uint64_t nodes, interactions, cells, bodies;
    double walk, active;
    int team;
} NBWalkProfile;
static __thread NBWalkProfile nbWalkThread;
#define NB_WALK_ENTER uint64_t nb_nodes=0, nb_hits=0, nb_cells=0; double nb_start=omp_get_wtime()
#define NB_WALK_NODE (++nb_nodes)
#define NB_WALK_HIT(q) (++nb_hits, nb_cells += isCell(q))
#define NB_WALK_LEAVE do { nbWalkThread.walk += omp_get_wtime()-nb_start; \
    nbWalkThread.nodes += nb_nodes; nbWalkThread.interactions += nb_hits; \
    nbWalkThread.cells += nb_cells; ++nbWalkThread.bodies; } while (0)
static void nbWalkProfilePrint(const NBodyState* st, const NBWalkProfile* rows)
{
    int i, team=rows[0].team;
    for(i=0;i<team;++i) {
        const NBWalkProfile* r=rows+i;
        fprintf(stderr,"WALK_PROFILE step=%u thread=%d team=%d bodies=%llu nodes=%llu interactions=%llu cells=%llu walk=%.9f active=%.9f\n",
            st->step,i,team,(unsigned long long)r->bodies,(unsigned long long)r->nodes,
            (unsigned long long)r->interactions,(unsigned long long)r->cells,r->walk,r->active);
    }
}
#else
#define NB_WALK_ENTER ((void)0)
#define NB_WALK_NODE ((void)0)
#define NB_WALK_HIT(q) ((void)0)
#define NB_WALK_LEAVE ((void)0)
#endif
#if NBODY_WALK_PROOF
/* Full xyz stream, no hashes standing in for force equality. */
static void nbWalkProof(const NBodyState* st)
{
    const char* path=getenv("NBODY_WALK_FORCE_DUMP");
    static FILE* file;
    unsigned i;
    if(!path) return;
    if(!file) { file=fopen(path,"wb"); if(!file) abort(); setvbuf(file,NULL,_IOFBF,1024*1024); }
    for(i=0;i<st->nbody;++i) {
        real xyz[3]={st->acctab[i].x,st->acctab[i].y,st->acctab[i].z};
        if(fwrite(xyz,1,sizeof(xyz),file)!=sizeof(xyz)) abort();
    }
}
#else
#define nbWalkProof(st) ((void)0)
#endif
#endif
