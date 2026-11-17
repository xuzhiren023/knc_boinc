/* Reduced compiler item: even concrete cored samples retain scalar calls.
 * Release: -O2 -march=knc -fno-math-errno -ffp-contract=off -mveclibabi=knc
 * Compare -fopt-info-vec-missed with log_rn versus plain log, and the gamma
 * variant. No handwritten polynomial/scheduling substitute belongs here. */
#include <math.h>
extern double log_rn(double);
extern double UpperIncompleteGammaFunc(double, double);
void df_crlibm(int n, const double *restrict x, double *restrict y)
{
    for (int i = 0; i < n; ++i) y[i] = log_rn(x[i]);
}
void df_libm(int n, const double *restrict x, double *restrict y)
{
    for (int i = 0; i < n; ++i) y[i] = log(x[i]);
}
void df_gamma(int n, const double *restrict x, double *restrict y)
{
    for (int i = 0; i < n; ++i) y[i] = UpperIncompleteGammaFunc(3.0, x[i]);
}
void df_libm_atan(int n, const double *restrict x, double *restrict y)
{
    for (int i = 0; i < n; ++i) y[i] = atan(x[i]);
}
void df_libm_exp(int n, const double *restrict x, double *restrict y)
{
    for (int i = 0; i < n; ++i) y[i] = exp(x[i]);
}
