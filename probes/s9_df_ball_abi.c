/* Reduced from the rejected certified integrand: a ball is two KNC vectors.
 * Compiler item: by-value pair-vector helpers are rejected before useful SIMD.
 * k1om-mpss-linux-gcc -O2 -march=knc -fno-math-errno \
 *   -mveclibabi=knc -fopt-info-vec-missed -S probes/s9_df_ball_abi.c
 */
typedef double lanes8 __attribute__((vector_size(64)));
typedef struct { lanes8 value, error; } ball8;
ball8 s9_ball_add(ball8 a, ball8 b)
{
    return (ball8){a.value+b.value, a.error+b.error};
}
