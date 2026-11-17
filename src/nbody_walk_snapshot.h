#ifndef NBODY_WALK_SNAPSHOT_H
#define NBODY_WALK_SNAPSHOT_H
/* Instrumentation: actual threaded tree and live structures, only in proof builds. */
#if NBODY_WALK_PROOF
#include <stddef.h>
static void nbWalkSnapshotBlock(FILE* meta, FILE* data, const void* p, size_t n)
{
    long offset=ftell(data);
    if(fwrite(p,1,n,data)!=n) abort();
    fprintf(meta,"{\"addr\":\"0x%llx\",\"offset\":%ld,\"length\":%lu},",(unsigned long long)(uintptr_t)p,offset,(unsigned long)n);
}
static void nbWalkSnapshot(const NBodyCtx* ctx, const NBodyState* st)
{
    static int done;
    const char* prefix=getenv("NBODY_WALK_CAPTURE");
    const NBodyNode* q;
    char path[2048]; FILE *meta,*data;
    if(!prefix || done++) return;
    snprintf(path,sizeof(path),"%s.json",prefix); meta=fopen(path,"w");
    snprintf(path,sizeof(path),"%s.bin",prefix); data=fopen(path,"wb");
    if(!meta || !data) abort();
    fprintf(meta,"{\"ctx\":\"0x%llx\",\"state\":\"0x%llx\",\"bodies\":\"0x%llx\",\"body_bytes\":%lu,\"nbody\":%u,\"step\":%u,\"layout\":[%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu],\"blocks\":[",
        (unsigned long long)(uintptr_t)ctx,(unsigned long long)(uintptr_t)st,(unsigned long long)(uintptr_t)st->bodytab,
        (unsigned long)sizeof(Body),st->nbody,st->step,
        (unsigned long)sizeof(NBodyNode),(unsigned long)sizeof(Body),(unsigned long)sizeof(NBodyCell),
        (unsigned long)offsetof(NBodyNode,pos),(unsigned long)offsetof(NBodyNode,mass),
        (unsigned long)offsetof(NBodyNode,next),(unsigned long)offsetof(NBodyNode,type),
#if NBODY_WALK_HOT
        (unsigned long)offsetof(NBodyNode,rcrit2),
#else
        (unsigned long)offsetof(NBodyCell,rcrit2),
#endif
        (unsigned long)offsetof(NBodyCell,more),(unsigned long)offsetof(NBodyCell,stuff),
        (unsigned long)offsetof(NBodyState,tree),(unsigned long)offsetof(NBodyCtx,eps2));
    nbWalkSnapshotBlock(meta,data,ctx,sizeof(*ctx));
    nbWalkSnapshotBlock(meta,data,st,sizeof(*st));
    nbWalkSnapshotBlock(meta,data,st->bodytab,st->nbody*sizeof(Body));
    for(q=(const NBodyNode*)st->tree.root;q;q=isCell(q)?More(q):Next(q))
        if(isCell(q)) nbWalkSnapshotBlock(meta,data,q,sizeof(NBodyCell));
    fprintf(meta,"{}]}\n"); fclose(data); fclose(meta);
}
#else
#define nbWalkSnapshot(ctx,st) ((void)0)
#endif
#endif
