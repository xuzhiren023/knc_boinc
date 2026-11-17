/* Diagnostic card binary: original scalar node and actual eight-node worker.
 * Only entry wrappers are diagnostic. No simplified arithmetic or stub cost. */
#include "nbody_mixeddwarf.c"
#include <stddef.h>
double kncSnapshotInterval;
typedef struct { real energy; size_t lanes; mwbool dark; } Df8TwinArgs;
/* Pointer-only ABI exposes captured arguments without inventing x87 inputs. */
__attribute__((noinline,used,externally_visible))
void df8_twin_vector(const real* x,const Dwarf* a,const Dwarf* b,const Df8TwinArgs* args,real* out)
{ df8_nodes(x,args->lanes,a,b,args->energy,args->dark,out); }
__attribute__((noinline,used,externally_visible))
void df8_twin_scalar(const real* x,const Dwarf* a,const Dwarf* b,const Df8TwinArgs* args,real* out)
{
    for(size_t i=0;i<args->lanes;++i)
        out[i]=args->dark ? dfs_fun_dark(x[i],a,b,args->energy) : dfs_fun_light(x[i],a,b,args->energy);
}
/* Read via objdump to verify captured host data's field offsets on KNC.
 * Trailing Dwarf padding may differ and is padded when marshaling captures. */
const unsigned long df8_twin_layout[] = {sizeof(Dwarf),offsetof(Dwarf,mass),
    offsetof(Dwarf,scaleLength),offsetof(Dwarf,psi_iso_r1)};
int main(void) { return 0; }
