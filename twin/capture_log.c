/* Link-time wrapping captures the actual hottest function without editing it. */
#include <stdio.h>
#include <stdlib.h>
extern double __real_log_rn(double);
double __wrap_log_rn(double x) {
    static int done;
    if (!done++) {
        FILE *f = fopen("twin/capture/log-input.bin", "wb");
        double y;
        unsigned short cw;
        __asm__ volatile("fnstcw %0" : "=m"(cw));
        { FILE *c=fopen("twin/capture/host-fcw.bin","wb"); if(!c || fwrite(&cw,2,1,c)!=1) abort(); fclose(c); }
        if (!f || fwrite(&x, sizeof(x), 1, f) != 1) abort(); fclose(f);
        y = __real_log_rn(x);
        f = fopen("twin/capture/log-expected.bin", "wb");
        if (!f || fwrite(&y, sizeof(y), 1, f) != 1) abort(); fclose(f);
        return y;
    }
    return __real_log_rn(x);
}
