/* Reduced compiler item from mixeddwarf.c:fun. Normal (non-singular) path.
 * Build twice, with/without -DSAMPLES_READ_ONLY. The real dispatchers lazily
 * initialize model parameters, so that promise needs a proven ready-model API.
 * Preserve the exact five-point expressions and their FP addition order. */
#ifdef SAMPLES_READ_ONLY
#define READ_ONLY __attribute__((pure))
#else
#define READ_ONLY
#endif
extern double sample_potential(const void *, double) READ_ONLY;
extern double sample_density(const void *, double) READ_ONLY;
static inline double first(double (*f)(const void *, double), const void *m, double x)
{
    const double h = .001;
    double p1 = 1.0*f(m,x-2.0*h), p2 = -8.0*f(m,x-h);
    double p3 = -1.0*f(m,x+2.0*h), p4 = 8.0*f(m,x+h);
    return (p1+p2+p3+p4)*(1.0/(12.0*h));
}
static inline double second(double (*f)(const void *, double), const void *m, double x)
{
    const double h = .001;
    double p1 = -1.0*f(m,x+2.0*h), p2 = 16.0*f(m,x+h), p3 = -30.0*f(m,x);
    double p4 = 16.0*f(m,x-h), p5 = -1.0*f(m,x-2.0*h);
    return (p1+p2+p3+p4+p5)*(1.0/(12.0*h*h));
}
double s8_df_node(double x, double energy, const void *a, const void *b)
{
    double dp = first(sample_potential,a,x)+first(sample_potential,b,x);
    double ddp = second(sample_potential,a,x)+second(sample_potential,b,x);
    double dr = first(sample_density,a,x), ddr = second(sample_density,a,x);
    if (dp == 0.0) dp = 1e-6;
    double numerator = ddr*(1.0/dp)-dr*ddp*(1.0/(dp*dp));
    double diff = __builtin_fabs(energy-(sample_potential(a,x)+sample_potential(b,x)));
    return numerator*(1.0/__builtin_sqrt(diff));
}
