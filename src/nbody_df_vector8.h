/* Performance: relaxed eight-node Plummer/cored integrand, default off.
 * GCC vector expressions lower to IMCI; libknc_vmath's lane-core ABI accepts
 * raw IEEE words and an active-lane mask on both the host and KNC.
 * No fast-math, reassociation or parallel quadrature reduction is permitted. */
#ifndef NBODY_DF_VECTOR8_H
#define NBODY_DF_VECTOR8_H
#ifndef NBODY_DF_VECTOR8_SCALAR_LOG_ATAN
#define NBODY_DF_VECTOR8_SCALAR_LOG_ATAN 0
#endif
#include <stdint.h>
typedef double D8 __attribute__((vector_size(64)));
typedef long long M8 __attribute__((vector_size(64)));
extern int __knc_vmath_core_log_8(const uint64_t*, unsigned, const uint64_t*, uint64_t*);
extern int __knc_vmath_core_exp_8(const uint64_t*, unsigned, const uint64_t*, uint64_t*);
extern int __knc_vmath_core_pow_8(const uint64_t*, const uint64_t*, unsigned, const uint64_t*, uint64_t*);
extern int __knc_vmath_core_atan2_8(const uint64_t*, const uint64_t*, unsigned, const uint64_t*, uint64_t*);
static inline D8 d8_splat(double x) { return (D8){x,x,x,x,x,x,x,x}; }
static inline D8 d8_select(M8 m, D8 yes, D8 no)
{ return (D8)((m & (M8)yes) | (~m & (M8)no)); }
static inline D8 d8_abs(D8 x) { return d8_select(x < 0.0, -x, x); }
static inline unsigned d8_bits(M8 m)
{
    unsigned bits = 0;
    for (int i=0; i<8; ++i) if (m[i]) bits |= 1u << i;
    return bits;
}
static inline D8 d8_sqrt(D8 x)
{
    D8 y;
    /* Compiler-first: this fixed loop is vectorized by GCC-KNC, including
     * the backend's correctly rounded IMCI sqrt lowering. */
    for (int i=0; i<8; ++i) y[i] = sqrt(x[i]);
    return y;
}
static inline D8 d8_log(D8 x, unsigned mask)
{
    D8 out = d8_splat(0.0);
#if NBODY_DF_VECTOR8_SCALAR_LOG_ATAN
    /* Owner comparison: preserve exact crlibm for these calls per lane. */
    for (int i=0;i<8;++i) if (mask&(1u<<i)) out[i]=mw_log(x[i]);
#else
    __knc_vmath_core_log_8((const uint64_t*)&x, mask, (const uint64_t*)&out, (uint64_t*)&out);
#endif
    return out;
}
static inline D8 d8_exp(D8 x, unsigned mask)
{
    D8 out = d8_splat(0.0);
    __knc_vmath_core_exp_8((const uint64_t*)&x, mask, (const uint64_t*)&out, (uint64_t*)&out);
    return out;
}
static inline D8 d8_pow(D8 x, D8 y, unsigned mask)
{
    D8 out = d8_splat(0.0);
    __knc_vmath_core_pow_8((const uint64_t*)&x, (const uint64_t*)&y, mask, (const uint64_t*)&out, (uint64_t*)&out);
    return out;
}
static inline D8 d8_atan(D8 x, unsigned mask)
{
    D8 one = d8_splat(1.0), out = d8_splat(0.0);
#if NBODY_DF_VECTOR8_SCALAR_LOG_ATAN
    for (int i=0;i<8;++i) if (mask&(1u<<i)) out[i]=mw_atan(x[i]);
#else
    __knc_vmath_core_atan2_8((const uint64_t*)&x, (const uint64_t*)&one, mask, (const uint64_t*)&out, (uint64_t*)&out);
#endif
    return out;
}
static D8 d8_gammln(D8 z, unsigned mask)
{
    static const double coeff[14] = {57.1562356658629235,-59.5979603554754912,
        14.1360979747417471,-0.491913816097620199,.339946499848118887e-4,
        .465236289270485756e-4,-.983744753048795646e-4,.158088703224912494e-3,
        -.210264441724104883e-3,.217439618115212643e-3,-.164318106536763890e-3,
        .844182239838527433e-4,-.261908384015814087e-4,.368991826595316234e-5};
    D8 y=z, tmp=z+4.7421875+0.5, ag=d8_splat(0.999999999999997092);
    tmp = (z+0.5)*d8_log(tmp,mask)-tmp;
    for (int j=0; j<14; ++j) { y += 1.0; ag += coeff[j]/y; }
    tmp += d8_log(2.5066282746310005*ag/z,mask);
    return tmp;
}
/* Same gser/gcf algorithms, 100-iteration cap and convergence tests as
 * nbody_mass.c. Every lane freezes its state after its own convergence test.
 * Series and continued-fraction lanes may coexist in the same IMCI vector. */
static D8 d8_gamma(D8 a, D8 x, unsigned mask)
{
    D8 zero=d8_splat(0.0), one=d8_splat(1.0);
    M8 valid = (M8){0};
    for (int i=0; i<8; ++i) valid[i] = (mask & (1u<<i)) ? -1LL : 0;
    M8 invalid = valid & ((x < 0.0) | (a <= 0.0));
    M8 series = valid & ~invalid & (x < a+1.0);
    M8 fraction = valid & ~invalid & ~series;
    D8 gln=d8_gammln(a,mask);
    D8 gamma=d8_exp(gln,mask);
    D8 ap=a, del=one/a, sum=del;
    M8 active=series & (x > 0.0);
    for (int n=1; n<=100 && d8_bits(active); ++n)
    {
        ap=d8_select(active,ap+1.0,ap);
        del=d8_select(active,del*(x/ap),del);
        sum=d8_select(active,sum+del,sum);
        active &= ~(d8_abs(del) < d8_abs(sum)*3.0e-7);
    }
    if (d8_bits(active)) mw_printf("WARNING: vector gser did not converge (mask=%u)\n",d8_bits(active));
    unsigned sm=d8_bits(series & (x > 0.0));
    D8 sp=sum*d8_exp(-x+a*d8_log(x,sm)-gln,sm);
    sp=d8_select(x <= 0.0,zero,sp);
    D8 b=x+1.0-a;
    b=d8_select(d8_abs(b)<1.0e-30,d8_splat(1.0e-30),b);
    D8 c=d8_splat(1.0/1.0e-30), d=one/b, h=d;
    active=fraction;
    for (int i=1; i<=100 && d8_bits(active); ++i)
    {
        D8 an=-(double)i*((double)i-a);
        b=d8_select(active,b+2.0,b);
        D8 nd=an*d+b, nc=b+an/c;
        nd=d8_select(d8_abs(nd)<1.0e-30,d8_splat(1.0e-30),nd);
        nc=d8_select(d8_abs(nc)<1.0e-30,d8_splat(1.0e-30),nc);
        d=d8_select(active,one/nd,d); c=d8_select(active,nc,c);
        D8 step=d*c;
        h=d8_select(active,h*step,h);
        active &= ~(d8_abs(step-1.0)<3.0e-7);
    }
    if (d8_bits(active)) mw_printf("WARNING: vector gcf did not converge (mask=%u)\n",d8_bits(active));
    unsigned fm=d8_bits(fraction);
    D8 cf=d8_exp(-x+a*d8_log(x,fm)-gln,fm)*h;
    D8 q=d8_select(series,one-sp,cf);
    q=d8_select(invalid,d8_splat(NAN),q);
    return gamma*q;
}
static D8 d8_plummer_pot(const Dwarf* m, D8 r)
{ return m->mass/d8_sqrt(r*r+m->scaleLength*m->scaleLength); }
static D8 d8_plummer_den(const Dwarf* m, D8 r)
{
    D8 t=1.0+(r/m->scaleLength)*(r/m->scaleLength);
    return (3.0/(4.0*M_PI))*(m->mass/cube(m->scaleLength))*(1.0/d8_sqrt(t*t*t*t*t));
}
static D8 d8_cored_den(const Dwarf* m, D8 r, unsigned mask)
{
    M8 tail=(m->rcut != 0.0) ? (M8)(r>m->rcut) : (M8){0};
    unsigned tm=d8_bits(tail)&mask;
    D8 t=1.0+r/m->scaleLength;
    D8 out=m->ps/((r/m->scaleLength)*(t*t));
    D8 core=m->p0/(1.0+(r/m->rc)*(r/m->rc));
    out=d8_select(r<=m->r1,core,out);
    if (tm) {
        D8 t=m->pcut*d8_pow(r/m->rcut,d8_splat(m->delta),tm)*d8_exp(-(r-m->rcut)/m->rdecay,tm);
        out=d8_select(tail,t,out);
    }
    return out;
}
static D8 d8_cored_pot(const Dwarf* m, D8 r, unsigned mask)
{
    M8 tail=(m->rcut != 0.0) ? (M8)(r>m->rcut) : (M8){0};
    M8 core=(r<=m->r1)&~tail;
    M8 outer=~core&~tail;
    unsigned cm=d8_bits(core)&mask, om=d8_bits(outer)&mask, tm=d8_bits(tail)&mask;
    D8 out=d8_splat(0.0);
    if (cm) {
        D8 p=-4.0*M_PI*m->p0*sqr(m->rc)*
            (d8_log(sqr(m->rc)+r*r,cm)*(1.0/2.0)+(m->rc*d8_atan(r/m->rc,cm)*(1.0/r)))
            -m->psi_iso_r1+m->psi_nfw_r1+(m->m_iso_r1-m->m_nfw_r1)*(1.0/m->r1);
        out=d8_select(core,p,out);
    }
    if (om) {
        D8 p=4.0*M_PI*m->ps*cube(m->scaleLength)*(1.0/r)*d8_log(1.0+r/m->scaleLength,om)
            +(m->m_iso_r1-m->m_nfw_r1)*(1.0/r);
        out=d8_select(outer,p,out);
    }
    if (m->rcut != 0.0) {
        out += -m->psi_nfw_cut-(m->m_iso_r1-m->m_nfw_r1)*(1.0/m->rcut)
            +m->psi_cut_cut+(m->m_nfw_cut+m->m_iso_r1-m->m_nfw_r1)*(1.0/m->rcut);
    }
    if (tm) {
        D8 p=4.0*M_PI*m->pcut*d8_pow(d8_splat(m->rcut),d8_splat(-m->delta),tm)
            *d8_exp(d8_splat(m->rcut/m->rdecay),tm)*d8_pow(d8_splat(m->rdecay),d8_splat(m->delta+3),tm)
            *(((m->gamma1-d8_gamma(d8_splat(m->delta+3),r/m->rdecay,tm))*(1.0/r))
            +(d8_gamma(d8_splat(m->delta+2),r/m->rdecay,tm)*(1.0/m->rdecay)))
            +(m->m_nfw_cut+m->m_iso_r1-m->m_nfw_r1)*(1.0/r);
        out=d8_select(tail,p,out);
    }
    return out;
}
typedef struct { D8 first, second, center; } D8Derivatives;
static inline __attribute__((always_inline)) void d8_stencil(D8Derivatives* out,D8 mm,D8 m,D8 pp,D8 p,D8 c)
{
    const real h=0.001;
    D8Derivatives d;
    D8 p1=1.0*mm,p2=-8.0*m,p3=-1.0*pp,p4=8.0*p;
    real denom=1.0/(12.0*h);
    d.first=(p1+p2+p3+p4)*denom;
    p1=-1.0*pp; p2=16.0*p; p3=-30.0*c; p4=16.0*m;
    D8 p5=-1.0*mm; denom=1.0/(12.0*h*h);
    d.second=(p1+p2+p3+p4+p5)*denom; d.center=c;
    *out=d;
}
static __attribute__((noinline)) void df8_nodes(const real* x, size_t lanes,
    const Dwarf* a,const Dwarf* b,real energy,mwbool dark,real* output)
{
    D8 r;
    /* Duplicate a valid node in the terminal partial block; never read past x. */
    for (int i=0;i<8;++i) r[i]=x[i<(int)lanes?i:0];
    unsigned mask=(1u<<lanes)-1u;
    const real h=0.001;
    D8Derivatives p1,p2,den;
    d8_stencil(&p1,d8_plummer_pot(a,r-2.0*h),d8_plummer_pot(a,r-h),
        d8_plummer_pot(a,r+2.0*h),d8_plummer_pot(a,r+h),d8_plummer_pot(a,r));
    d8_stencil(&p2,d8_cored_pot(b,r-2.0*h,mask),d8_cored_pot(b,r-h,mask),
        d8_cored_pot(b,r+2.0*h,mask),d8_cored_pot(b,r+h,mask),d8_cored_pot(b,r,mask));
    if (dark) d8_stencil(&den,d8_cored_den(b,r-2.0*h,mask),d8_cored_den(b,r-h,mask),
        d8_cored_den(b,r+2.0*h,mask),d8_cored_den(b,r+h,mask),d8_cored_den(b,r,mask));
    else d8_stencil(&den,d8_plummer_den(a,r-2.0*h),d8_plummer_den(a,r-h),
        d8_plummer_den(a,r+2.0*h),d8_plummer_den(a,r+h),d8_plummer_den(a,r));
    D8 first=p1.first+p2.first, second=p1.second+p2.second;
    first=d8_select(first==0.0,d8_splat(1.0e-6),first);
    D8 num=den.second*(1.0/first)-den.first*second*(1.0/(first*first));
    D8 diff=d8_abs(energy-(p1.center+p2.center));
    M8 singular=diff==0.0;
    if (d8_bits(singular)&mask) {
        D8 shifted=d8_abs(energy-(d8_plummer_pot(a,r+0.0001)+d8_cored_pot(b,r+0.0001,mask)));
        diff=d8_select(singular,shifted,diff);
    }
    D8 result=num*(1.0/d8_sqrt(diff));
    for (size_t i=0;i<lanes;++i) output[i]=result[i];
}
#endif
