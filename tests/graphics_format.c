#include "knc_graphics_format.h"
#include <stddef.h>
#define CHECK(c) _Static_assert(c, #c)
CHECK(sizeof(float)==4);
CHECK(sizeof(knc_body)==16);
CHECK(offsetof(knc_body,type)==12);
CHECK(sizeof(knc_snapshot)==320048);
CHECK(offsetof(knc_snapshot,sim_time)==24);
CHECK(offsetof(knc_snapshot,step)==32);
CHECK(offsetof(knc_snapshot,fraction_done)==40);
CHECK(offsetof(knc_snapshot,bodies)==48);
CHECK(sizeof(knc_graphics)==320080);
CHECK(offsetof(knc_graphics,sequence)==12);
CHECK(offsetof(knc_graphics,status)==16);
CHECK(offsetof(knc_graphics,snapshot)==32);
int main(void) {return 0;}
CHECK(sizeof(double)==8);
CHECK(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__);
CHECK(offsetof(knc_body,x)==0);
CHECK(offsetof(knc_body,y)==4);
CHECK(offsetof(knc_body,z)==8);
CHECK(offsetof(knc_snapshot,magic)==0);
CHECK(offsetof(knc_snapshot,version)==4);
CHECK(offsetof(knc_snapshot,size)==8);
CHECK(offsetof(knc_snapshot,body_count)==12);
CHECK(offsetof(knc_snapshot,reserved)==16);
CHECK(offsetof(knc_graphics,magic)==0);
CHECK(offsetof(knc_graphics,version)==4);
CHECK(offsetof(knc_graphics,size)==8);
CHECK(offsetof(knc_graphics,reserved)==20);
