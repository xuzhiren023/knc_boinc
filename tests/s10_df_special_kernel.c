/* Test-only access to static exact and specialized node evaluators. */
#include "nbody_mixeddwarf.c"
#include <stdio.h>
double kncSnapshotInterval;
static int same(real a, real b) { return memcmp(&a, &b, sizeof(a)) == 0; }
static real generic_fun(real r, const Dwarf* a, const Dwarf* b, real e, mwbool d)
{ return fun(r, a, b, e, d); }
int main(void)
{
    crlibm_init();
    Dwarf a = {0}, b = {0};
    a.type = Plummer; a.mass = 12.0; a.scaleLength = 0.4;
    b.type = Cored; b.mass = 40.0; b.scaleLength = 1.1;
    b.r1 = 0.6; b.rc = 0.3; b.rcut = 5.0;
    set_model_params(&a); set_model_params(&b);
    unsigned samples = 0, mismatches = 0;
    for (int cut = 0; cut < 2; ++cut)
    {
        if (cut) { b.rcut = 0.0; set_model_params(&b); }
        for (int i = 1; i <= 160; ++i)
        {
            real r = 0.005 + i * 0.051;
            /* Cover the two cored branch boundaries and stencil crossings. */
            if (i >= 150) r = (i < 155 ? b.r1 : 5.0) + (i % 5 - 2) * 0.001;
            for (int dark = 0; dark < 2; ++dark)
            {
                real e = 0.3 * potential(r, &a, &b);
                real ref = fun(r, &a, &b, e, dark);
                real got = dark ? dfs_fun_dark(r, &a, &b, e) : dfs_fun_light(r, &a, &b, e);
                mismatches += !same(ref, got); ++samples;
                /* Include the exact energy-singularity displacement branch. */
                e = potential(r, &a, &b);
                ref = fun(r, &a, &b, e, dark);
                got = dark ? dfs_fun_dark(r, &a, &b, e) : dfs_fun_light(r, &a, &b, e);
                mismatches += !same(ref, got); ++samples;
            }
        }
    }
    int fallback = 1;
    for (int type = Plummer; type <= Cored; ++type)
    {
        Dwarf other = b; other.type = type;
        if (type == Cored) continue;
        fallback &= !df_special_ready(&a, &other);
    }
    fallback &= df_special_ready(&a, &b);
    Dwarf cold = b; cold.p0 = 0; fallback &= !df_special_ready(&a, &cold);
    /* Arbitrary callbacks must not be mistaken for the science integrand. */
    real x = gauss_quad(fun, 0.01, 2.0, &a, &b, 1.0, FALSE);
    real y = gauss_quad(generic_fun, 0.01, 2.0, &a, &b, 1.0, FALSE);
    mismatches += !same(x, y);
    printf("{\"kernel_samples\":%u,\"kernel_mismatches\":%u,\"unsupported_models_original\":%s}\n",
           samples, mismatches, fallback ? "true" : "false");
#if NBODY_DF_VMATH
    return !mismatches || !fallback;
#else
    return mismatches || !fallback;
#endif
}
