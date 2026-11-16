/* Independent x86 execution of the exact DB /0 instruction in the repro. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    uint64_t input=UINT64_C(0x3ff0000000000000), output;
    double y;
    __asm__ volatile("fildl %1; fstpl %0" : "=m"(y) : "m"(input) : "st");
    memcpy(&output,&y,8);
    printf("fildl input=%016llx output=%016llx\n",(unsigned long long)input,(unsigned long long)output);
    return output!=0;
}
