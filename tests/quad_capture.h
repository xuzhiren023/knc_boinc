/* Test-only instrumentation: shared by pristine and patched generator TUs. */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

static double s8_capture_start(void)
{
    unsigned short parent;
    __asm__ volatile ("fnstcw %0" : "=m" (parent));
    int mismatch = 0;
    /* The app calls crlibm_init before any generator/force worker is born. */
    #pragma omp parallel reduction(+:mismatch)
    {
        unsigned short worker;
        __asm__ volatile ("fnstcw %0" : "=m" (worker));
        mismatch += worker != parent;
    }
    fprintf(stderr, "S8_X87_CW=%04x worker_mismatches=%d\n", parent, mismatch);
    if (mismatch || (parent & 0x0f00) != 0x0200) abort();
    return omp_get_wtime();
}

static void s8_capture_end(double start, unsigned int count,
                           const real* x, const real* y, const real* z,
                           const real* vx, const real* vy, const real* vz,
                           const real* mass)
{
    double seconds = omp_get_wtime() - start;
    const char* path = getenv("S8_INITIAL_BODIES");
    if (!path) abort();
    FILE* out = fopen(path, "wb");
    if (!out) abort();
    unsigned int i;
    for (i = 0; i < count; ++i)
    {
        real row[7] = {x[i], y[i], z[i], vx[i], vy[i], vz[i], mass[i]};
        if (fwrite(row, sizeof(real), 7, out) != 7) abort();
    }
    if (fclose(out)) abort();
    fprintf(stderr, "S8_GENERATION_SECONDS=%.9f\n", seconds);
    if (getenv("S8_GENERATION_ONLY")) exit(0);
}
