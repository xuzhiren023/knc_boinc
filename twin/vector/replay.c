/* Replay actual captured bytes, relocating only fields read by the gravity walk.
 * The expected file is the independent S1-06 host capture, never regenerated. */
#include "nbody_priv.h"
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "replay_blocks.h"
extern mwvector nbGravity(const NBodyCtx*, NBodyState*, const Body*);
extern unsigned nbGravity8(mwvector*, const NBodyCtx*, NBodyState*, const Body*, unsigned);
double kncSnapshotInterval = 0;
static void *relocate(const void *p) {
    uintptr_t v=(uintptr_t)p;
    size_t lo=0,hi=sizeof(blocks)/sizeof(blocks[0]);
    if (!v) return NULL;
    while(lo<hi) { size_t m=(lo+hi)/2; if(blocks[m].addr<=v) lo=m+1; else hi=m; }
    if(!lo || v-blocks[lo-1].addr>=blocks[lo-1].size) abort();
    return blocks[lo-1].data+(v-blocks[lo-1].addr);
}
int main(int argc,char **argv) {
    size_t n,i; FILE *f,*out;
    NBodyCtx *ctx; NBodyState *st; Body *bodies;
    if(argc!=2) return 2;
    f=fopen("twin/vector/replay.bin","rb"); if(!f) return 2;
    for(n=0;n<sizeof(blocks)/sizeof(blocks[0]);++n) {
        blocks[n].data=malloc(blocks[n].size);
        if(!blocks[n].data || fseek(f,blocks[n].offset,SEEK_SET) ||
           fread(blocks[n].data,1,blocks[n].size,f)!=blocks[n].size) abort();
    }
    fclose(f);
    ctx=relocate((void*)CTX_ADDR); st=relocate((void*)STATE_ADDR);
    bodies=relocate(st->bodytab);
    ctx->eps2=relocate(ctx->eps2); st->tree.root=relocate(st->tree.root);
    st->bodytab=bodies;
    for(n=0;n<sizeof(blocks)/sizeof(blocks[0]);++n) if(blocks[n].kind==1) {
        NBodyCell *cell=(NBodyCell*)blocks[n].data;
        cell->cellnode.next=relocate(cell->cellnode.next);
        cell->more=relocate(cell->more);
    }
    for(i=0;i<20000;++i) bodies[i].bodynode.next=relocate(bodies[i].bodynode.next);
    out=fopen(argv[1],"wb"); if(!out) return 2;
    for(i=0;i<4096;i+=8) {
        mwvector a[8]; unsigned l;
#if NBODY_VECTOR_GRAVITY
        if (nbGravity8(a,ctx,st,bodies+i,8)) return 1;
#else
        for(l=0;l<8;++l) a[l]=nbGravity(ctx,st,bodies+i+l);
#endif
        for(l=0;l<8;++l) if(fwrite(&a[l],1,24,out)!=24) abort();
    }
    fclose(out);
    return st->treeIncest ? 1 : 0;
}
