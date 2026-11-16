/* Host replay of the real gravity source. All tree construction stays SSE;
 * only this translation unit is built with -mfpmath=387, PC=53. */
#include <stdint.h>
#include <inttypes.h>
static int replay_body;
static int capture_begin(const NBodyCtx *ctx, NBodyState *st, const Body *p) {
    unsigned short cw=0x027f;
    (void)ctx;
    __asm__ volatile("fldcw %0" : : "m"(cw));
    replay_body=(int)(p-st->bodytab);
    return replay_body==1024 || replay_body==1408 || replay_body==1664 ||
           replay_body==3072 || replay_body==3200 || replay_body==3584;
}
static void capture_end(mwvector a) {
    uint64_t xyz[3];
    memcpy(xyz,&a,sizeof(xyz));
    printf("x87 body %d: %016" PRIx64 " %016" PRIx64 " %016" PRIx64 "\n",
           replay_body,xyz[0],xyz[1],xyz[2]);
    if(replay_body==3584) exit(0);
}
