/* Native per-operation oracle. Input/output are exact binary64 bit patterns.
 * Operands in this gravity trace are exactly representable binary64 values.
 * Volatile asm ensures each operation rounds once under control word 0x027f. */
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
int main(void) {
    char op[16]; uint64_t ua, ub, ur; double a,b,r;
    unsigned short cw=0x027f;
    __asm__ volatile("fldcw %0" : : "m"(cw));
    while(scanf("%15s %" SCNx64 " %" SCNx64,op,&ua,&ub)==3) {
        memcpy(&a,&ua,8); memcpy(&b,&ub,8);
        if(!strcmp(op,"add")) __asm__ volatile("fldl %1; faddl %2; fstpl %0":"=m"(r):"m"(a),"m"(b):"st");
        else if(!strcmp(op,"sub")) __asm__ volatile("fldl %1; fsubl %2; fstpl %0":"=m"(r):"m"(a),"m"(b):"st");
        else if(!strcmp(op,"mul")) __asm__ volatile("fldl %1; fmull %2; fstpl %0":"=m"(r):"m"(a),"m"(b):"st");
        else if(!strcmp(op,"div")) __asm__ volatile("fldl %1; fdivl %2; fstpl %0":"=m"(r):"m"(a),"m"(b):"st");
        else if(!strcmp(op,"sqrt")) __asm__ volatile("fldl %1; fsqrt; fstpl %0":"=m"(r):"m"(a):"st");
        else return 2;
        memcpy(&ur,&r,8); printf("%016" PRIx64 "\n",ur);
    }
    return 0;
}
