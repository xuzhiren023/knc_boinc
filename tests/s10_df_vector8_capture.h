/* Instrumentation for the S10-09 capture TU only. */
#include "s10_df_capture.h"
static unsigned s10_guard_triggers, s10_node_records[2];
static FILE* s10_node_file;
static void s10_nodes_open(void)
{
    const char* name=getenv("S10_NODE_TRACE");
    if (!name) return;
    s10_node_file=fopen(name,"wb");
    if (!s10_node_file) abort();
    uint32_t header[2]={1,sizeof(Dwarf)};
    if (fwrite(header,sizeof(header),1,s10_node_file)!=1) abort();
}
static void s10_nodes_close(void)
{ if(s10_node_file && fclose(s10_node_file)) abort(); s10_node_file=NULL; }
static void s10_nodes_capture(const real*,size_t,const Dwarf*,const Dwarf*,real,mwbool,const real*);
