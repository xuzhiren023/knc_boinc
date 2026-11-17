/* Instrumentation, test TU only. Exact RNG-state trace, one record per body.
 * dsfmt's state words and idx are initialized; avoid struct padding bytes. */
#include "quad_capture.h"
#include <stdint.h>
static FILE* s10_rng_file;
static void s10_rng_open(void)
{
    const char* name = getenv("S10_RNG_TRACE");
    if (!name || !(s10_rng_file = fopen(name, "wb"))) abort();
}
static void s10_rng_body(const dsfmt_t* state)
{
    if (fwrite(state->status, sizeof(state->status), 1, s10_rng_file) != 1 ||
        fwrite(&state->idx, sizeof(state->idx), 1, s10_rng_file) != 1) abort();
}
static void s10_rng_close(void)
{
    if (fclose(s10_rng_file)) abort();
    fprintf(stderr, "S10_RNG_RECORD_BYTES=%lu\n",
        (unsigned long)(sizeof(((dsfmt_t*)0)->status) + sizeof(((dsfmt_t*)0)->idx)));
}
