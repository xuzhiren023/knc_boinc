/* Compile on both targets and compare .data; raw captures require these layouts. */
#include "nbody_priv.h"
#include <stddef.h>
#define O(T,x) offsetof(T,x)
unsigned long long capture_layout[] = {
 sizeof(void*),sizeof(real),sizeof(mwvector),sizeof(NBodyCtx),sizeof(NBodyState),sizeof(NBodyNode),sizeof(Body),sizeof(NBodyCell),
 O(NBodyCtx,eps2),O(NBodyCtx,eps2_size),O(NBodyCtx,eps2_min),O(NBodyCtx,useQuad),
 O(NBodyState,tree),O(NBodyState,treeIncest),
 O(NBodyNode,pos),O(NBodyNode,next),O(NBodyNode,mass),O(NBodyNode,type),
 O(Body,eps2Index),O(NBodyCell,rcrit2),O(NBodyCell,more),O(NBodyCell,stuff)
};
