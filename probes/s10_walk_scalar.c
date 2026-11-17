/* Compiler-only reduced scalar dependence/stack-pressure reproducer.
 * Same distance, monopole and quadrupole grouping as nbody_1.96 nbGravity.
 * No application optimization; inspect -O2 -march=knc and vec-missed output. */
#include <math.h>
typedef struct { double x,y,z,w; } Vec;
typedef struct Node { Vec pos; struct Node *next, *more; double mass,rcrit;
    short type; double xx,xy,xz,yy,yz,zz; } Node;
Vec s10_walk(const Node* q, const Node* p, const double eps[3], int quad)
{
    Vec a={0,0,0,0};
    while(q) {
        double x=q->pos.x-p->pos.x, y=q->pos.y-p->pos.y, z=q->pos.z-p->pos.z;
        double d=z*z+(y*y+x*x);
        if(q->type || d>=q->rcrit) {
            if(q!=p) {
                int t=q->type+p->type;
                double local_eps[3]={0.,0.,0.};
                local_eps[0]=eps[0];local_eps[1]=eps[1];local_eps[2]=eps[2];
                d+=local_eps[t==-2?2:t==2?0:1];
                double r=sqrt(d), phi=q->mass/r, m=phi/d;
                a.x+=m*x; a.y+=m*y; a.z+=m*z;
                if(quad && !q->type) {
                    double qx=(q->xx*x+q->xy*y)+q->xz*z;
                    double qy=(q->xy*x+q->yy*y)+q->yz*z;
                    double qz=(q->xz*x+q->yz*y)+q->zz*z;
                    double dot=(qx*x+qy*y)+qz*z;
                    double inv=1.0/((d*d)*r), pq=(2.5*(inv*dot))/d;
                    a.x+=pq*x; a.y+=pq*y; a.z+=pq*z;
                    a.x-=inv*qx; a.y-=inv*qy; a.z-=inv*qz;
                }
            }
            q=q->next;
        } else q=q->more;
    }
    return a;
}
