/* Compiler-first repro: the data-dependent successor is not a strided array.
 * No hand-coded arithmetic/vectorization; compare GCC's prefetch pass output. */
struct Node { double x, y, z, mass, rcrit; int type; struct Node *next, *more; };
double walk(const struct Node* p, double x, double y, double z)
{
    double sum=0;
    while(p) {
        double dx=p->x-x, dy=p->y-y, dz=p->z-z;
        double d=dz*dz+(dy*dy+dx*dx);
        if(p->type || d>=p->rcrit) { sum += p->mass/d; p=p->next; }
        else p=p->more;
    }
    return sum;
}
