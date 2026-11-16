/* Same crlibm objects and numerical initialization as the application. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <complex.h>
#include "crlibm.h"
static uint64_t bits(double x) { uint64_t u; memcpy(&u,&x,8); return u; }
static double value(uint64_t u) { double x; memcpy(&x,&u,8); return x; }
static void row(const char *id, const char *fn, double x, double y, double z) {
    printf("%s %s %016llx %016llx %016llx\n",id,fn,
           (unsigned long long)bits(x),(unsigned long long)bits(y),(unsigned long long)bits(z));
}
static void probe(const char *id, double x) {
#define U(f) row(id,#f,x,0.0,f(x))
    U(log_rn); U(log1p_rn); U(log10_rn); U(exp_rn); U(expm1_rn);
    U(sin_rn); U(cos_rn); U(tan_rn); U(asin_rn); U(acos_rn); U(atan_rn);
    U(sinh_rn); U(cosh_rn);
    U(sqrt); U(atan); U(sin); U(cos); U(tan); U(asin); U(acos);
    U(log); U(log10); U(exp2); U(exp10); U(exp); U(sinh); U(cosh); U(tanh);
    U(fabs); U(floor); U(ceil); U(round); U(trunc); U(log2); U(acosh); U(asinh); U(atanh);
    row(id,"pow_rn",x,0.5,pow_rn(x,0.5));
    row(id,"pow_rn",x,2.0,pow_rn(x,2.0));
    row(id,"pow_rn",x,1.2345,pow_rn(x,1.2345));
    row(id,"pow",x,1.2345,pow(x,1.2345));
    row(id,"hypot",x,2.0,hypot(x,2.0));
    { double sn,cs; sincos(x,&sn,&cs); row(id,"sincos.sin",x,0.0,sn); row(id,"sincos.cos",x,0.0,cs); }
    { double complex z=csqrt(x+I*0.5); row(id,"csqrt.re",x,0.5,creal(z)); row(id,"csqrt.im",x,0.5,cimag(z)); }
    { double complex z=cpow(x+I*0.5,1.2345+I*0.25); row(id,"cpow.re",x,0.5,creal(z)); row(id,"cpow.im",x,0.5,cimag(z)); }
    row(id,"atan2",x,2.0,atan2(x,2.0));
    row(id,"fmod",x,2.0,fmod(x,2.0));
    row(id,"ldexp",x,3.0,ldexp(x,3));
    { int e; double r=frexp(x,&e); row(id,"frexp",x,(double)e,r); }
    { double i; double r=modf(x,&i); row(id,"modf",x,i,r); }
#undef U
}

int main(int argc, char **argv) {
    uint64_t saved = crlibm_init();
    const double fixed[] = {1.0,2.0,0.5,0x1.5bf0a8b145769p+1,1e-300,1e300,0x0.0000000000001p-1022};
    unsigned i; uint64_t seed=UINT64_C(0x670828913); char id[40];
    FILE *f; uint64_t captured;
    if (argc != 2 || !(f=fopen(argv[1],"rb"))) { fputs("usage: libm_probe captured-log-input.bin",stderr); return 2; }
    if (fread(&captured,8,1,f)!=1 || fgetc(f)!=EOF) { fclose(f); return 2; }
    fclose(f);
    for(i=0;i<sizeof(fixed)/sizeof(fixed[0]);++i) { sprintf(id,"fixed-%u",i); probe(id,fixed[i]); }
    for(i=0;i<384;++i) {
        seed=seed*UINT64_C(6364136223846793005)+UINT64_C(1442695040888963407);
        /* Finite positive values, varied exponents and mantissas. */
        sprintf(id,"seed-%03u",i);
        probe(id,value(((seed>>52)%2046+1)<<52 | (seed&UINT64_C(0xfffffffffffff))));
    }
    probe("captured",value(captured));
    crlibm_exit(saved);
    return ferror(stdout) ? 3 : 0;
}
