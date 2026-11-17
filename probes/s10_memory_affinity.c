/* Card harness: print only the runner-authorized CPUs, grouped by real siblings. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { int cpu, package, core; } Row;
static int number(int cpu, const char* field)
{
    char path[256]; int n; FILE* f;
    snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/topology/%s",cpu,field);
    f=fopen(path,"r");
    if (!f || fscanf(f,"%d",&n)!=1) { fprintf(stderr,"cannot read %s\n",path); exit(2); }
    fclose(f); return n;
}
static int cmp(const void* a, const void* b)
{
    const Row* x=a; const Row* y=b;
    if (x->package!=y->package) return x->package-y->package;
    if (x->core!=y->core) return x->core-y->core;
    return x->cpu-y->cpu;
}
int main(void)
{
    cpu_set_t allowed; Row rows[CPU_SETSIZE]; int i,n=0;
    if (sched_getaffinity(0,sizeof(allowed),&allowed)) { perror("sched_getaffinity"); return 2; }
    for(i=0;i<CPU_SETSIZE;++i) if(CPU_ISSET(i,&allowed)) {
        rows[n++]=(Row){i,number(i,"physical_package_id"),number(i,"core_id")};
    }
    if(n!=240) { fprintf(stderr,"need 240 authorized CPUs, got %d\n",n);return 2; }
    qsort(rows,n,sizeof(*rows),cmp);
    for(i=0;i<n;i+=4) {
        int j;
        for(j=1;j<4;++j) if(rows[i].package!=rows[i+j].package || rows[i].core!=rows[i+j].core) {
            fprintf(stderr,"authorized CPU set does not have four siblings/core\n");return 2;
        }
        if(i && rows[i].package==rows[i-1].package && rows[i].core==rows[i-1].core) return 2;
    }
    for(i=0;i<n;++i) printf("%s%d",i?" ":"",rows[i].cpu);
    puts(""); return 0;
}
