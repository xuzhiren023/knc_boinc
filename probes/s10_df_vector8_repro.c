/* Compiler items: build at release -O2 -march=knc -mveclibabi=knc
 * -fno-math-errno -ffp-contract=off -fopt-info-vec-missed=... */
#include <math.h>
/* An output pointer is needed for this aggregate return in the actual helper;
 * always_inline alone does not avoid the target ABI diagnostic.
 * Compile -DREPRO_AGGREGATE_ABI to reproduce the GCC-KNC ABI diagnostic. */
#ifdef REPRO_AGGREGATE_ABI
typedef double V8 __attribute__((vector_size(64)));
typedef struct { V8 first,second,center; } ThreeVectors;
ThreeVectors df8_aggregate(V8 x) { ThreeVectors d={x,x,x}; return d; }
#endif
void df8_calls(const double *restrict x,double *restrict y) {
    for(int i=0;i<8;++i) y[i]=log(x[i])+atan(x[i])+exp(x[i])+pow(x[i],3.1);
}
void df8_series(const double *restrict x,double a,double *restrict out) {
    for(int i=0;i<8;++i) {
        double ap=a, del=1.0/a, sum=del;
        for(int n=1;n<=100;++n) {
            ap+=1.0; del*=x[i]/ap; sum+=del;
            if(fabs(del)<fabs(sum)*3.0e-7) break;
        }
        out[i]=sum;
    }
}
