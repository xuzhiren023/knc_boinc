/* Performance only. Private to the mixed-dwarf generator. Default off.
 * Speculate values, never comparisons or committed dSFMT draws. */
#ifndef NBODY_DF_BATCH_H
#define NBODY_DF_BATCH_H
#define DFB_CAP 12
#define DFB_FIRST 4
#define DFB_TAIL 8
typedef struct {
    QuadInterval* nodes;
    size_t count;
    int reverse, ready;
    real energy;
} DfbJob;
static int dfb_ready(const Dwarf* a,const Dwarf* b)
{ return !df8_exact && !omp_in_parallel() && df_special_ready(a,b); }
static int dfb_plan(DfbJob* job,real lower,real upper)
{
    QuadInterval* nodes = malloc(128*sizeof(*nodes));
    if (!nodes) return 0;
    size_t count = 0, capacity = 128;
    real a = 0.0, b = 0.0;

    if(lower > upper)
    {
        a = upper;
        b = lower;
    }
    else
    {
        a = lower;
        b = upper;
    }

    real benchmark = 1.5 * a;
    real Ng = 100.0;//integral resolution
    real hg = (benchmark - a) / (Ng);
    real lowerg = a;
    real upperg = lowerg + hg;


    real coef2 = (lowerg + upperg) / 2.0;//initializes the first coeff to change the function limits
    real coef1 = (upperg - lowerg) / 2.0;//initializes the second coeff to change the function limits
    const real x1 = -0.77459666924;//-sqrt(3.0 / 5.0);
    const real x2 __attribute__((unused)) = 0.00000000000;
    const real x3 = 0.77459666924; //sqrt(3.0 / 5.0);
    real x1n = (coef1 * x1 + coef2);
    /*should be: x2n = (coef1 * x2 + coef2);*/
    real x2n = (coef2);
    real x3n = (coef1 * x3 + coef2);
    int counter = 0;
    while (1)
    {
                //gauss quad
        if (count == capacity)
        {
            size_t next_capacity = capacity * 2;
            QuadInterval* next = malloc(next_capacity * sizeof(*next));
            if (!next)
            {
                free(nodes);
                return 0;
            }
            memcpy(next, nodes, count * sizeof(*next));
            free(nodes);
            nodes = next;
            capacity = next_capacity;
        }
        nodes[count].x[0] = x1n;
        nodes[count].x[1] = x2n;
        nodes[count].x[2] = x3n;
        nodes[count].coef1 = coef1;
        count++;

        lowerg = upperg;
        upperg = upperg + hg;
        coef2 = (lowerg + upperg) / 2.0;//initializes the first coeff to change the function limits
        coef1 = (upperg - lowerg) / 2.0;

        x1n = ((coef1) * x1 + coef2);
        /*should be: x2n = (coef1 * x2 + coef2);*/
        x2n = (coef2);
        x3n = ((coef1) * x3 + coef2);

        if(lowerg > benchmark)
        {
            Ng = 10.0;//integral resolution
            hg = (b - benchmark) / (Ng);
        }

        if(upper > lower)
        {
            if(lowerg >= upper)//loop termination clause
            {
                break;
            }
        }
        else if(lower > upper)
        {
            if(lowerg >= lower)//loop termination clause
            {
                break;
            }
        }

        if(counter > 100000)
        {
            break;
        }
        else
        {
            counter++;
        }


    }

    job->nodes=nodes; job->count=count; job->reverse=lower>upper;
    return 1;
}
/* The window supplies compact sibling affinity. For a non-multiple-of-four
 * team retain complete coverage with per-integral contiguous block slices. */
static void dfb_range(int tid,int nt,int j,int n,size_t blocks,size_t* lo,size_t* hi)
{
    int worker,workers;
    *lo=*hi=0;
    if(nt<4 || nt%4) { worker=tid;workers=nt; }
    else {
        int cores=nt/4,core=tid/4,lane=tid%4;
        if(cores<n) {
            if(j%cores!=core)return;
            worker=lane;workers=4;
        } else {
            if(core%n!=j)return;
            worker=(core/n)*4+lane;
            workers=((cores-1-j)/n+1)*4;
        }
    }
    *lo=blocks*worker/workers; *hi=blocks*(worker+1)/workers;
}
static void dfb_evaluate(const real* v,int n,real r,const Dwarf* a,const Dwarf* b,mwbool dark,real* out)
{
    DfbJob job[DFB_CAP];
    /* One team, with parallel exact root preparation followed by the node
     * wave. No nested teams and no reduction of the original serial sum. */
    #pragma omp parallel
    {
        int tid=omp_get_thread_num(),nt=omp_get_num_threads();
        #pragma omp for schedule(static)
        for(int j=0;j<n;++j) {
            GenBounds bounds=gen_prepare(v[j],r,a,b);
            job[j].energy=bounds.energy;
            job[j].ready=dfb_plan(&job[j],bounds.lower,bounds.upper);
        }
        for(int j=0;j<n;++j) if(job[j].ready) {
            size_t lo,hi,count=job[j].count;
            dfb_range(tid,nt,j,n,(3*count+7)/8,&lo,&hi);
            for(size_t block=lo;block<hi;++block) {
                size_t begin=8*block,lanes=3*count-begin<8?3*count-begin:8;
                real x[8],f[8];
                for(size_t k=0;k<lanes;++k)x[k]=job[j].nodes[(begin+k)/3].x[(begin+k)%3];
                df8_nodes(x,lanes,a,b,job[j].energy,dark,f);
                for(size_t k=0;k<lanes;++k)job[j].nodes[(begin+k)/3].f[(begin+k)%3]=f[k];
            }
        }
    }
    for(int j=0;j<n;++j) {
        if(!job[j].ready) { out[j]=dist_fun(v[j],r,a,b,dark);continue; }
        real intv=0.0;
        const real c1=0.55555555555,c2=0.88888888888,c3=0.55555555555;
        for(size_t i=0;i<job[j].count;++i) {
            QuadInterval* node=&job[j].nodes[i]; real coef1=node->coef1;
            intv=intv+c1*node->f[0]*coef1+c2*node->f[1]*coef1+c3*node->f[2]*coef1;
        }
        if(job[j].reverse)intv *= -1.0;
        out[j]=v[j]*v[j]*0.03582244801567226*intv;
        free(job[j].nodes);
    }

}
static void dfb_draw(const dsfmt_t* rng,int n,real esc,real* v,real* u)
{
    dsfmt_t copy=*rng;
    for(int i=0;i<n;++i) {
        v[i]=(real)gp_random(&copy,0.0,1.0)*esc;
        u[i]=(real)gp_random(&copy,0.0,1.0);
    }
}
/* Cache belongs to one velocity call: radius, models and component cannot
 * change while live. Key matching is bitwise, preserving signed zero. */
static struct { real v[DFB_FIRST],u[DFB_FIRST],d[DFB_FIRST];int valid; } dfb_attempts;
static real dfb_esc;
static dsfmt_t* dfb_rng;
typedef struct {real v[8],d[8];int used[8],n;} DfbCache;
static void dfb_points(real x0,real x1,real x2,real x3,int depth,real* v,int* n)
{
    if(!depth)return;
    const real ratio=0.61803399,complement=1.0-ratio;
    real right=ratio*x2+complement*x3,left=ratio*x1+complement*x0;
    v[(*n)++]=right;v[(*n)++]=left;
    dfb_points(x1,x2,right,x3,depth-1,v,n);
    dfb_points(x0,left,x1,x2,depth-1,v,n);
}
static void dfb_fill(DfbCache* cache,real x0,real x1,real x2,real x3,int initial,
    real r,const Dwarf* a,const Dwarf* b,mwbool dark)
{
    real v[DFB_CAP],out[DFB_CAP];int n=0;
    if(initial){v[n++]=x1;v[n++]=x2;}
    dfb_points(x0,x1,x2,x3,2,v,&n);
    cache->n=n;
    int attempts=initial && dfb_rng ? DFB_FIRST:0;
    if(attempts) {
        dfb_draw(dfb_rng,attempts,dfb_esc,dfb_attempts.v,dfb_attempts.u);
        for(int i=0;i<attempts;++i)v[n+i]=dfb_attempts.v[i];
    }
    dfb_evaluate(v,n+attempts,r,a,b,dark,out);
    for(int i=0;i<n;++i){cache->v[i]=v[i];cache->d[i]=out[i];cache->used[i]=0;}
    if(attempts){for(int i=0;i<attempts;++i)dfb_attempts.d[i]=out[n+i];dfb_attempts.valid=1;}
}
static int dfb_get(DfbCache* cache,real v,real* d)
{
    for(int i=0;i<cache->n;++i)if(!cache->used[i] && !memcmp(&v,&cache->v[i],sizeof(v))) {
        cache->used[i]=1;*d=cache->d[i];return 1;
    }
    return 0;
}
static real dfb_max(real r,const Dwarf* a,const Dwarf* b,mwbool dark,
    real lower,real middle,real upper,int limit,real tolerance)
{
    const real ratio=0.61803399,complement=1.0-ratio;
    real x0=lower,x3=upper,x1,x2;
    if(mw_fabs(middle-upper)>mw_fabs(middle-lower)){x1=middle;x2=middle+complement*(upper-middle);}
    else {x2=middle;x1=middle-complement*(middle-lower);}
    DfbCache cache={0};real p1,p2;
    dfb_fill(&cache,x0,x1,x2,x3,1,r,a,b,dark);
    dfb_get(&cache,x1,&p1);dfb_get(&cache,x2,&p2);p1=-p1;p2=-p2;
    int counter=0;
    while(mw_fabs(x3-x0)>tolerance*(mw_fabs(x1)+mw_fabs(x2))) {
        ++counter;
        real v,d;
        /* Refill before changing the state. Both branch trees reproduce the
         * exact multiply/add grouping of the original golden-section steps. */
        int right=df8_less(p2,p1);
        v=right?ratio*x2+complement*x3:ratio*x1+complement*x0;
        if(!dfb_get(&cache,v,&d)) {
            dfb_fill(&cache,x0,x1,x2,x3,0,r,a,b,dark);
            dfb_get(&cache,v,&d);
        }
        if(right){x0=x1;x1=x2;x2=v;p1=p2;p2=-d;}
        else {x3=x2;x2=x1;x1=v;p2=p1;p1=-d;}
        if(counter>limit)break;
    }
    return df8_less(p1,p2)?-p1:-p2;
}
static real dfb_reject(real r,real esc,real maximum,const Dwarf* a,const Dwarf* b,mwbool dark,dsfmt_t* rng)
{
    int counter=0,initial=dfb_attempts.valid;
    real v=0;
    while(1) {
        real vv[DFB_TAIL],uu[DFB_TAIL],dd[DFB_TAIL];
        int n=initial?DFB_FIRST:DFB_TAIL;
        /* Do not evaluate attempts that the original limit cannot reach. */
        if(n>1002-counter)n=1002-counter;
        if(initial)for(int k=0;k<n;++k){vv[k]=dfb_attempts.v[k];uu[k]=dfb_attempts.u[k];dd[k]=dfb_attempts.d[k];}
        else {dfb_draw(rng,n,esc,vv,uu);dfb_evaluate(vv,n,r,a,b,dark,dd);}
        initial=0;dfb_attempts.valid=0;
        for(int k=0;k<n;++k) {
            /* Commit the original two draws, only when this attempt is used. */
            v=(real)gp_random(rng,0.0,1.0)*esc;
            real u=(real)gp_random(rng,0.0,1.0);

            if(df8_less(u,mw_fabs(dd[k]/maximum))) {return v;}
            if(counter>1000){return 0;}
            ++counter;
        }
    }
}
#endif
