/* Reduced compiler item from nbody_tree.c:nbSubIndex.
 * Preserve the exact <= octant decisions, including ties. */
void s8_subindex(int *out, const double *p, const double *q)
{
    int ind = 0;
    if (q[0] <= p[0]) ind += 4;
    if (q[1] <= p[1]) ind += 2;
    if (q[2] <= p[2]) ind += 1;
    *out = ind;
}
