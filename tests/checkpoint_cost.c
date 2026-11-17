/* Instrumentation: exercise the real checkpoint scheduler/writer with 110k
 * synthetic bodies, without generating/evolving a full science task. */
#include "nbody_types.h"
#include "nbody_checkpoint.h"
#include "milkyway_alloc.h"
#include <time.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
double kncSnapshotInterval=0;
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(void){
    NBodyCtx ctx={0};NBodyState st={0};struct stat info;
    st.nbody=110000;st.bodytab=mwCallocA(st.nbody,sizeof(Body));
    st.bestLikelihoodBodyTab=mwCallocA(st.nbody,sizeof(Body));
    st.checkpointResolved="cost.chk";
    /* Touch distinct data across both real body arrays. */
    for(unsigned i=0;i<st.nbody;i++){Mass(&st.bodytab[i])=i*.001;st.bestLikelihoodBodyTab[i]=st.bodytab[i];}
    for(int interval=1;interval<=120;interval+=119){
        ctx.checkpointT=interval;st.lastCheckpoint=time(NULL);
        double start=now(),cost=0;unsigned writes=0;
        while(now()-start<10){
            if(nbTimeToCheckpoint(&ctx,&st)){
                double t=now();if(nbWriteCheckpoint(&ctx,&st))return 1;
                cost+=now()-t;++writes;
            }
            usleep(10000);
        }
        size_t bytes=0;if(writes){if(stat("cost.chk",&info))return 1;bytes=info.st_size;}
        printf("checkpoint_interval=%d bodies=%u writes=%u bytes_per_write=%zu wall_seconds=%.6f writer_seconds=%.6f writer_fraction=%.6f\n",interval,st.nbody,writes,bytes,now()-start,cost,cost/(now()-start));
        if(interval==1 && !writes)return 2;
    }
    unlink("cost.chk");mwFreeA(st.bodytab);mwFreeA(st.bestLikelihoodBodyTab);return 0;
}
