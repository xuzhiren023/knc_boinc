/* Instrumentation only: compiled into a separate host object, never card. */
#include <stdint.h>
#include <stddef.h>
static FILE *capture_meta;
static int capture_blocks;
static const void *capture_seen[4096];
static int capture_nodes;
static void capture_block(const void *p, size_t n) {
    char path[100]; FILE *f;
    sprintf(path,"twin/capture/block-%d.bin",capture_blocks);
    f=fopen(path,"wb"); if(!f || fwrite(p,1,n,f)!=n) abort(); fclose(f);
    fprintf(capture_meta,"%s{\"addr\":\"0x%llx\",\"file\":\"capture/block-%d.bin\"}",capture_blocks?",":"",(unsigned long long)(uintptr_t)p,capture_blocks);
    ++capture_blocks;
}
static void capture_node(const NBodyNode *q) {
    int i; if(!q) return;
    for(i=0;i<capture_nodes;i++) if(capture_seen[i]==q) return;
    if(capture_nodes==4096) abort(); capture_seen[capture_nodes++]=q;
    capture_block(q,isBody(q)?sizeof(Body):sizeof(NBodyCell));
    capture_node(Next(q)); if(isCell(q)) capture_node(More(q));
}
static int capture_begin(const NBodyCtx *ctx,NBodyState *st,const Body *p) {
    unsigned short cw;
    static int done; if(done++) return 0;
    __asm__ volatile("fnstcw %0" : "=m"(cw));
    capture_meta=fopen("twin/capture.json","w"); if(!capture_meta) abort();
    fprintf(capture_meta,"{\"init\":{\"registers\":{\"rdi\":\"0x60000000\",\"rsi\":\"0x%llx\",\"rdx\":\"0x%llx\",\"rcx\":\"0x%llx\",\"rbp\":0,\"rbx\":0},\"memory\":[",(unsigned long long)(uintptr_t)ctx,(unsigned long long)(uintptr_t)st,(unsigned long long)(uintptr_t)p);
    capture_block(ctx,sizeof(*ctx)); capture_block(st,sizeof(*st));
    capture_block(ctx->eps2,ctx->eps2_size*ctx->eps2_size*sizeof(real));
    capture_node((NBodyNode*)st->tree.root);
    fprintf(capture_meta,"]},\"expected\":{\"memory\":[{\"addr\":\"0x60000000\",\"file\":\"capture/expected.bin\"}]},\"unit_of_work\":{\"description\":\"one nbGravity call, first body of first small tree\",\"count\":1},\"scenario\":{\"memory\":{\"type\":\"line_tracking\",\"cold_level\":\"memory\"},\"branch\":{\"type\":\"all_predicted\"}},\"numerical_policy\":{\"rounding\":\"rn\",\"ftz\":false,\"daz\":false,\"x87_control_word\":\"0x%04x\"}}\n",cw);
    fclose(capture_meta); return 1;
}
static void capture_end(mwvector a) {
    FILE *f=fopen("twin/capture/expected.bin","wb");
    /* Compare physical acceleration only; w is unspecified by upstream vector helpers. */
    if(!f || fwrite(&a,1,3*sizeof(real),f)!=3*sizeof(real)) abort(); fclose(f);
}
