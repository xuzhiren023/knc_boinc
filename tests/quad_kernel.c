/* Appends to extracted, actual gauss_quad functions (see quad-kernel.py). */
static unsigned int workers;
static int calls;
static real probe(real x, const Dwarf* a, const Dwarf* b, real energy, mwbool dark)
{
    (void)a; (void)b; (void)dark;
    #pragma omp atomic update
    calls++;
    __atomic_fetch_or(&workers, 1u << omp_get_thread_num(), __ATOMIC_RELAXED);
    return energy + x * x;
}

int main(void)
{
    unsigned short cw = 0x027f;
    __asm__ volatile ("fldcw %0" : : "m" (cw));
    Dwarf model = {Plummer, 1.0};
    const real bounds[][2] = {{1, 10}, {10, 1}, {1, 1.1}, {1, 1}, {0, 1}, {0, 0}, {-1, 2}};
    const int threads[] = {1, 4, 12};
    size_t t, k;
    for (t = 0; t < 3; ++t)
    {
        omp_set_num_threads(threads[t]);
        for (k = 0; k < sizeof(bounds)/sizeof(bounds[0]); ++k)
        {
            calls = 0;
            real expected = gauss_quad_serial(probe, bounds[k][0], bounds[k][1], &model, &model, 0.25, 0);
            int expected_calls = calls;
            calls = 0;
            workers = 0;
            real actual = gauss_quad(probe, bounds[k][0], bounds[k][1], &model, &model, 0.25, 0);
            assert(memcmp(&expected, &actual, sizeof(real)) == 0);
            assert(calls == expected_calls);
            if (threads[t] > 1) assert((workers & (workers - 1)) != 0);
            calls = 0;
            #pragma omp parallel
            {
                #pragma omp single
                {
                    real nested = gauss_quad(probe, bounds[k][0], bounds[k][1], &model, &model, 0.25, 0);
                    assert(memcmp(&expected, &nested, sizeof(real)) == 0);
                }
            }
            assert(calls == expected_calls);
        }
    }
    /* Lazy models stay serial: no worker may initialize shared fields. */
    model.type = Cored;
    model.p0 = 0.0;
    workers = 0;
    gauss_quad(probe, 1, 10, &model, &model, 0.25, 0);
    assert(workers == 1);
    puts("PASS quadrature kernel: original bits/call counts, reversed/equal/zero/negative limits, counter exit, nested and lazy-model fallback; 1/4/12 threads");
    return 0;
}
