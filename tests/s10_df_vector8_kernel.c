/* Test-only instrumentation and static access, excluded from production. */
#include "nbody_mixeddwarf.c"
#include <stdio.h>
#include <float.h>
double kncSnapshotInterval;
int main(void)
{
    crlibm_init(); omp_set_num_threads(4);
    Dwarf a={0}, b={0};
    a.type=Plummer; a.mass=12.0; a.scaleLength=0.4;
    b.type=Cored; b.mass=40.0; b.scaleLength=1.1;
    b.r1=0.6; b.rc=0.3; b.rcut=5.0;
    set_model_params(&a); set_model_params(&b);
    unsigned samples=0, comparisons=0;
    double node_error=0, gamma_error=0, maxrel=0;
    int finite=1, isolation=1;
    for (int cut=0;cut<3;++cut) {
        if(cut==1) {b.rcut=0.0;set_model_params(&b);}
        if(cut==2) {
            a.mass=1.74668; a.scaleLength=0.386382;
            b.mass=(a.mass/0.0420765)*(1.0-0.0420765);
            b.scaleLength=(a.scaleLength/0.20556)*(1.0-0.20556);
            b.r1=1.21041*b.scaleLength; b.rc=2.87629*b.scaleLength; b.rcut=4.0*b.scaleLength;
            set_model_params(&a);set_model_params(&b);
        }
        for(int block=0;block<24;++block) {
            double x[8], out[8];
            for(int j=0;j<8;++j) {
                x[j]=0.01+(8*block+j)*0.043;
                if(block==22) x[j]=b.r1+(j-4)*0.0007;
                if(block==23) x[j]=5.0+(j-4)*0.0007;
            }
            for(int dark=0;dark<2;++dark) {
                double energy=0.3*potential(x[0],&a,&b);
                df8_nodes(x,8,&a,&b,energy,dark,out);
                for(int j=0;j<8;++j) {
                    double ref=fun(x[j],&a,&b,energy,dark);
                    double e=fabs(out[j]-ref)/(1.0+fabs(ref));
                    if(e>node_error)node_error=e;
                    finite &= isfinite(out[j]); ++samples;
                }
                for(int n=1;n<8;++n) {
                    double partial[8]; df8_nodes(x,n,&a,&b,energy,dark,partial);
                    for(int j=0;j<n;++j) isolation &= memcmp(&out[j],&partial[j],8)==0;
                }
            }
        }
        /* Calibrate the quantity consumed by golden-section and rejection
         * comparisons, using identical r,v and exact roots in both paths. */
        for(int ir=0;ir<24;++ir) {
            real r=0.02*pow(1.36,ir);
            real esc=0.99*sqrt(fabs(2.0*potential(r,&a,&b)));
            for(int iv=1;iv<=7;++iv) for(int dark=0;dark<2;++dark) {
                real v=esc*(iv/8.0);
                df8_exact=1; real exact=dist_fun(v,r,&a,&b,dark);
                df8_exact=0; real fast=dist_fun(v,r,&a,&b,dark);
                real rel=fabs(fast-exact)/(fabs(exact)+fabs(fast)+DBL_MIN);
                if(rel>maxrel) maxrel=rel;
                finite &= isfinite(fast)&&isfinite(exact); ++comparisons;
            }
        }
    }
    D8 aa={0.3,1.0,2.5,3.0,8.0,20.0,2.5,1.0};
    D8 xx={0.0,0.01,0.6,2.0,15.0,50.0,4.0,100.0};
    D8 gg=d8_gamma(aa,xx,255);
    D8 log_input={0.003,0.37,0.9,1.1,2.7,6.3,19.1,103.7};
    D8 log_result=d8_log(log_input,255), atan_result=d8_atan(log_input,255);
    int scalar_math_exact=1;
    for(int j=0;j<8;++j) {
        real lr=mw_log(log_input[j]), ar=mw_atan(log_input[j]);
        real lg=log_result[j], ag=atan_result[j];
        scalar_math_exact &= memcmp(&lr,&lg,8)==0 && memcmp(&ar,&ag,8)==0;
    }
    for(int j=0;j<8;++j) {
        double ref=UpperIncompleteGammaFunc(aa[j],xx[j]);
        double e=fabs(gg[j]-ref)/(fabs(ref)+DBL_MIN);
        if(e>gamma_error)gamma_error=e;
        finite &= isfinite(gg[j]);
    }
    int fallback=1;
    for(int t=Plummer;t<=Cored;++t) if(t!=Cored) {
        Dwarf c=b;c.type=t;fallback &= !df_special_ready(&a,&c);
    }
    Dwarf cold=b;cold.p0=0;fallback &= !df_special_ready(&a,&cold);
    printf("{\"samples\":%u,\"finite\":%s,\"mixed_gamma_lanes\":%s,\"partial_lane_isolation\":%s,\"unsupported_original\":%s,\"max_node_normalized_error\":%.17g,\"max_gamma_relative_error\":%.17g,\"comparisons\":%u,\"max_normalized_difference\":%.17g,\"scalar_log_atan_exact\":%s,\"scalar_log_atan_selected\":%s}\n",
        samples,finite?"true":"false",gamma_error<1e-12?"true":"false",isolation?"true":"false",fallback?"true":"false",node_error,gamma_error,comparisons,maxrel,scalar_math_exact?"true":"false",NBODY_DF_VECTOR8_SCALAR_LOG_ATAN?"true":"false");
    return !finite || !isolation || !fallback || gamma_error>=1e-12 || node_error>=0.01 || (NBODY_DF_VECTOR8_SCALAR_LOG_ATAN && !scalar_math_exact);
}
