/* Instrumentation only: included by the diagnostic capture TU. */
#include "s10_df_capture.h"
static unsigned long long dfb_evaluated,dfb_used,dfb_wasted,dfb_batches,dfb_max_batch,dfb_attempts_count,dfb_replays;
static unsigned long long dfb_attempt_histogram[1003],dfb_batch_histogram[13];
#define DFB_EVENT(kind,n) dfb_event_##kind(n)
#define dfb_event_evaluated(n) (dfb_evaluated+=(n))
#define dfb_event_used(n) (dfb_used+=(n))
#define dfb_event_wasted(n) (dfb_wasted+=(n))
#define dfb_event_attempts(n) (dfb_attempts_count+=(n))
static void dfb_event_batch(unsigned n){++dfb_batches;++dfb_batch_histogram[n];if(n>dfb_max_batch)dfb_max_batch=n;}
static void dfb_counts_report(void)
{
    fprintf(stderr,"DFB_COUNTS evaluated=%llu used=%llu wasted=%llu batches=%llu max_batch=%llu attempts=%llu replays=%llu\n",
        dfb_evaluated,dfb_used,dfb_wasted,dfb_batches,dfb_max_batch,dfb_attempts_count,dfb_replays);
    fprintf(stderr,"DFB_ATTEMPT_HIST");
    for(int i=1;i<1003;++i)if(dfb_attempt_histogram[i])fprintf(stderr," %d=%llu",i,dfb_attempt_histogram[i]);
    fprintf(stderr,"\nDFB_BATCH_HIST");
    for(int i=1;i<13;++i)if(dfb_batch_histogram[i])fprintf(stderr," %d=%llu",i,dfb_batch_histogram[i]);
    fprintf(stderr,"\n");
}
