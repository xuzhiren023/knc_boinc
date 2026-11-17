/* Instrumentation: acceptance harness against the actual generator. */
#include "nbody_mixeddwarf.c"
#include <stdio.h>
double kncSnapshotInterval;
static int eq(real a,real b) { return memcmp(&a,&b,sizeof(a))==0; }
int main(void)
{
    crlibm_init(); omp_set_num_threads(4);
    Dwarf a={0},b={0};
    a.type=Plummer;a.mass=1.74668;a.scaleLength=0.386382;
    b.type=Cored;b.mass=(a.mass/0.0420765)*(1.0-0.0420765);
    b.scaleLength=(a.scaleLength/0.20556)*(1.0-0.20556);
    b.r1=1.21041*b.scaleLength;b.rc=2.87629*b.scaleLength;b.rcut=4*b.scaleLength;
    set_model_params(&a);set_model_params(&b);
    int integrals=1,maxima=1,rng=1,limits=1,fallback=1,coverage=1;
    for(int dark=0;dark<2;++dark) for(int ir=0;ir<4;++ir) {
        real r=0.03*pow(4.0,ir),esc=0.99*sqrt(fabs(2*potential(r,&a,&b)));
        real v[12],result[12];
        for(int i=0;i<12;++i)v[i]=esc*(i+1)/13.0;
        dfb_evaluate(v,12,r,&a,&b,dark,result);
        for(int i=0;i<12;++i) integrals &= eq(result[i],dist_fun(v[i],r,&a,&b,dark));
        dfb_active=0;
        real exact=max_finder(dist_fun,r,&a,&b,dark,0.0,0.5*esc,esc,100,1.0e-2);
        dfb_active=1;
        real batched=max_finder(dist_fun,r,&a,&b,dark,0.0,0.5*esc,esc,100,1.0e-2);
        dfb_active=0; maxima &= eq(exact,batched);
        dsfmt_t s,t;dsfmt_init_gen_rand(&s,1234+ir);t=s;
        dfb_active=0;real x=vel_mag_base(r,&a,&b,dark,&s);
        dfb_active=1;real y=vel_mag_base(r,&a,&b,dark,&t);dfb_active=0;
        rng &= eq(x,y) && !memcmp(&s,&t,sizeof(s));
    }
    /* Force acceptance at every offset, across batches, and at the original
     * 1002-attempt limit. The helper must not commit speculative draws. */
    for(int accept=0;accept<=1002;++accept) {
        dsfmt_t real_rng,ref_rng;dsfmt_init_gen_rand(&real_rng,77);ref_rng=real_rng;
        real v=0,u=0;int used=0;
        while(used<1002) {
            real vv[8],uu[8];dfb_draw(&real_rng,8,1.0,vv,uu);
            for(int k=0;k<8 && used<1002;++k) {
                v=gp_random(&real_rng,0.0,1.0);u=gp_random(&real_rng,0.0,1.0);
                rng &= eq(v,vv[k]) && eq(u,uu[k]);
                if(used++==accept) goto done;
            }
        }
        done:
        for(int i=0;i<used;++i){gp_random(&ref_rng,0.0,1.0);gp_random(&ref_rng,0.0,1.0);}
        limits &= !memcmp(&real_rng,&ref_rng,sizeof(real_rng));
    }
    /* Exercise the actual rejection helper through its terminal attempt,
     * with every ratio forced to zero by an infinite envelope. */
    {
        dsfmt_t actual,expected;dsfmt_init_gen_rand(&actual,91);expected=actual;
        real r=0.3,esc=0.99*sqrt(fabs(2*potential(r,&a,&b)));
        dfb_attempts.valid=0;
        real v=dfb_reject(r,esc,INFINITY,&a,&b,0,&actual);
        for(int i=0;i<1002;++i){gp_random(&expected,0.0,1.0);gp_random(&expected,0.0,1.0);}
        limits &= eq(v,0.0) && !memcmp(&actual,&expected,sizeof(actual));
    }
    /* Every vector block has exactly one owner, for undersubscribed and
     * full-card teams, uneven tails and integral counts 1..12. */
    for(int nt=1;nt<=240;++nt) for(int n=1;n<=12;++n) {
        int hits[12][43]={{0}};
        for(int tid=0;tid<nt;++tid) for(int j=0;j<n;++j) {
            size_t lo,hi;dfb_range(tid,nt,j,n,43,&lo,&hi);
            for(size_t k=lo;k<hi;++k)++hits[j][k];
        }
        for(int j=0;j<n;++j)for(int k=0;k<43;++k)coverage &= hits[j][k]==1;
    }
    Dwarf cold=b;cold.p0=0;
    fallback &= !dfb_ready(&a,&cold);
    df8_exact=1;fallback &= !dfb_ready(&a,&b);df8_exact=0;
    #pragma omp parallel reduction(&:fallback)
    { fallback &= !dfb_ready(&a,&b); }
    printf("{\"integrals_bitwise\":%s,\"max_decisions_bitwise\":%s,\"rng_order_exact\":%s,\"limit_exact\":%s,\"fallback_exact\":%s,\"schedule_coverage\":%s}\n",
       integrals?"true":"false",maxima?"true":"false",rng?"true":"false",limits?"true":"false",fallback?"true":"false",coverage?"true":"false");
    return !(integrals&&maxima&&rng&&limits&&fallback&&coverage);
}
