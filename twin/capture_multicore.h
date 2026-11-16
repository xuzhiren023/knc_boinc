/* Host-only first-force snapshot; included by prepare_capture.py --multicore.
 * Traverse the actual threaded tree, retaining host pointer addresses. */
#include <stdint.h>
#include <stddef.h>
static FILE *mc_meta, *mc_nodes, *mc_expected;
static const NBodyNode *mc_seen[131072];
static long mc_offset;
static int mc_started, mc_closed;
static const Body *mc_bodies;
static void mc_block(const void *p, size_t n, const char *name) {
    char path[160]; FILE *f;
    snprintf(path,sizeof(path),"twin/multicore/capture/%s.bin",name);
    f=fopen(path,"wb"); if(!f || fwrite(p,1,n,f)!=n) abort(); fclose(f);
    fprintf(mc_meta,"{\"addr\":\"0x%llx\",\"file\":\"capture/%s.bin\"},",(unsigned long long)(uintptr_t)p,name);
}
static void mc_tree(const NBodyNode *q) {
    while(q) {
        size_t h=((uintptr_t)q >> 4) % 131072;
        size_t n=isBody(q)?sizeof(Body):sizeof(NBodyCell);
        while(mc_seen[h] && mc_seen[h]!=q) h=(h+1)%131072;
        if(mc_seen[h]) return;
        mc_seen[h]=q;
        if(fwrite(q,1,n,mc_nodes)!=n) abort();
        fprintf(mc_meta,"{\"addr\":\"0x%llx\",\"file\":\"capture/nodes.bin\",\"offset\":%ld,\"length\":%lu},",(unsigned long long)(uintptr_t)q,mc_offset,(unsigned long)n);
        mc_offset+=(long)n;
        if(isCell(q)) mc_tree(More(q));
        q=Next(q);
    }
}
static int capture_begin(const NBodyCtx *ctx,NBodyState *st,const Body *p) {
    unsigned short cw;
    if(mc_closed) return 0;
    if(mc_started && p==mc_bodies) {
        fclose(mc_expected); mc_closed=1; return 0;
    }
    if(!mc_started) {
        if(p!=st->bodytab || st->nbody!=20000) abort();
        mc_started=1; mc_bodies=st->bodytab;
        __asm__ volatile("fnstcw %0" : "=m"(cw));
        mc_meta=fopen("twin/multicore/capture.json","w");
        mc_nodes=fopen("twin/multicore/capture/nodes.bin","wb");
        mc_expected=fopen("twin/multicore/capture/expected.bin","wb");
        if(!mc_meta || !mc_nodes || !mc_expected) abort();
        fprintf(mc_meta,"{\"init\":{\"registers\":{\"rdi\":\"0x60000000\",\"rsi\":\"0x%llx\",\"rdx\":\"0x%llx\",\"rcx\":\"0x%llx\",\"rbp\":0,\"rbx\":0},\"memory\":[",(unsigned long long)(uintptr_t)ctx,(unsigned long long)(uintptr_t)st,(unsigned long long)(uintptr_t)p);
        mc_block(ctx,sizeof(*ctx),"ctx"); mc_block(st,sizeof(*st),"state");
        mc_block(ctx->eps2,ctx->eps2_size*ctx->eps2_size*sizeof(real),"eps2");
        mc_block(st->bodytab,st->nbody*sizeof(Body),"bodies");
        mc_tree((NBodyNode*)st->tree.root); fclose(mc_nodes);
        /* Empty final block avoids a trailing comma in the streaming metadata. */
        fprintf(mc_meta,"{\"addr\":0,\"hex\":\"\"}]},\"expected\":{\"memory\":[{\"addr\":\"0x60000000\",\"file\":\"capture/expected.bin\",\"offset\":0,\"length\":24}]},\"unit_of_work\":{\"description\":\"one nbGravity call from first large force step (diagnostic only)\",\"count\":1},\"scenario\":{\"memory\":{\"type\":\"line_tracking\",\"cold_level\":\"memory\"},\"branch\":{\"type\":\"all_predicted\"}},\"numerical_policy\":{\"rounding\":\"rn\",\"ftz\":false,\"daz\":false,\"x87_control_word\":\"0x%04x\"},\"capture_layout\":{\"bodies\":%d,\"body_bytes\":%lu,\"vector_bytes\":%lu,\"chunk_bodies\":%lu,\"tree_bytes\":%ld}}\n",cw,st->nbody,(unsigned long)sizeof(Body),(unsigned long)sizeof(mwvector),(unsigned long)(4096/sizeof(mwvector)),mc_offset);
        fclose(mc_meta);
    }
    return p-mc_bodies < 4096;
}
static void capture_end(mwvector a) {
    /* Sequential one-thread traversal: first 32 complete 128-body chunks. */
    if(fwrite(&a,1,3*sizeof(real),mc_expected)!=3*sizeof(real)) abort();
}
