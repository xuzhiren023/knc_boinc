#ifndef KNC_GRAPHICS_FORMAT_H
#define KNC_GRAPHICS_FORMAT_H
#include <stdint.h>
/* Wire ABI v1: little endian, IEEE754 float/double, fixed sizes, no pointers.
 * Reserved fields and unused bodies must be zero. A snapshot file is exactly
 * sizeof(knc_snapshot), including unused bodies. Coordinates are Cartesian.
 * Type 0 = dark (upstream negative); type 1 = light (upstream nonnegative).
 * Reject unknown magic/version/size, >20000 bodies or nonfinite active values.
 */
#define KNC_SNAPSHOT_MAGIC UINT32_C(0x53434e4b) /* KNCS */
#define KNC_GRAPHICS_MAGIC UINT32_C(0x47434e4b) /* KNCG */
#define KNC_GRAPHICS_VERSION 1
#define KNC_MAX_BODIES 20000
#define KNC_GRAPHICS_NAME "knc_nbody"
#define KNC_DARK 0
#define KNC_LIGHT 1
#define KNC_RUNNING 0
#define KNC_SUSPENDED 1
#define KNC_FINISHED 2
#define KNC_WAITING 3
/* Explicit padding keeps this ABI identical on host and K1OM. */
typedef struct { float x,y,z; uint32_t type; } knc_body;
typedef struct {
    uint32_t magic,version,size,body_count;
    uint32_t reserved[2];
    double sim_time;
    uint64_t step;
    double fraction_done;
    knc_body bodies[KNC_MAX_BODIES];
} knc_snapshot;
typedef struct {
    uint32_t magic,version,size,sequence;
    uint32_t status,reserved[3];
    knc_snapshot snapshot;
} knc_graphics;
/* Single wrapper writer: aligned atomic sequence becomes odd before any write,
 * full memory barrier, write payload/header, full barrier, publish next even
 * sequence. Increment even for heartbeat-only updates (at least once/second).
 * Reader copies only between equal even sequence loads with full barriers.
 * Sequence wraps mod 2^32. No change for 5 seconds => stale, idle scene.
 * Mapping name is BOINC boinc_knc_nbody_<slot>, NOT the client IPC mapping.
 */
#endif
