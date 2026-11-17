/* Exercise the production vector ball graph against the scalar samplers and
 * integrand, including core/cutoff transitions and uncertain decisions. */
#include "nbody_mixeddwarf.c"
#include <assert.h>
#include "nbody_phase_timers.h"
double nbPhaseSeconds[NB_PHASE_COUNT];
unsigned long nbPhaseCalls[NB_PHASE_COUNT];
void nbPhaseSetupDone(void) { }
double kncSnapshotInterval;
int main(void)
{
    crlibm_init();
    Dwarf a = EMPTY_DWARF, b = EMPTY_DWARF;
    a.type=Plummer; a.mass=1.74668; a.scaleLength=0.386382;
    b.type=Cored; b.mass=a.mass/0.0420765-a.mass;
    b.scaleLength=a.scaleLength/0.20556-a.scaleLength;
    b.r1=1.21041*b.scaleLength; b.rc=2.87629*b.scaleLength;
    b.rcut=4*b.scaleLength;
    set_model_params(&a); set_model_params(&b);
    unsigned long samples=0,nodes=0,finite=0;
    for(int batch=0;batch<64;++batch)
    {
        DfV r;
        real x[8],value[8],error[8];
        for(int i=0;i<8;++i)
        {
            int k=batch*8+i;
            r[i]=x[i]=0.003*exp((real)k*log(100000.0)/511.0);
            if(k==100) r[i]=x[i]=b.r1;
            if(k==101) r[i]=x[i]=nextafter(b.r1,INFINITY);
            if(k==102) r[i]=x[i]=b.rcut;
            if(k==103) r[i]=x[i]=nextafter(b.rcut,INFINITY);
        }
        for(int m=0;m<2;++m)
        {
            const Dwarf* model=m?&b:&a;
            DfBall pot,den;
            df_samples(model,r,&pot,&den);
            for(int i=0;i<8;++i)
            {
                assert(fabs(pot.v[i]-get_potential(model,r[i]))<=pot.e[i]);
                assert(fabs(den.v[i]-get_density(model,r[i]))<=den.e[i]);
                samples+=2;
            }
        }
        for(int dark=0;dark<2;++dark)
        {
            real energy=0.5*potential(1,&a,&b);
            df_nodes8(x,8,&a,&b,energy,dark,value,error);
            for(int i=0;i<8;++i)
            {
                real reference=fun(x[i],&a,&b,energy,dark);
                assert(isinf(error[i]) || fabs(value[i]-reference)<=error[i]);
                ++nodes; finite+=isfinite(error[i]);
            }
        }
    }
    df_uncertain=0; (void)df_less(1,0.01,1.001,0.01); assert(df_uncertain);
    df_uncertain=0; assert(df_less(1,0.01,2,0.01)); assert(!df_uncertain);
    df_uncertain=0; (void)df_less(1,INFINITY,2,0); assert(df_uncertain);
    printf("PASS sample enclosures=%lu node enclosures=%lu finite=%lu guarded comparisons=3\n",samples,nodes,finite);
    return 0;
}
