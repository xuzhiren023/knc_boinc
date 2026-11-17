# KNC N-body graphics

Build in Git for Windows bash, using the supplied Cygwin toolchain:

```bash
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
make -C mk graphics
bash tests/graphics.sh
bash tests/packaging.sh
```

`tests/graphics.sh` builds host and card format checks, runs the full medium upstream workunit (1024 bodies, timeEvolve 3.945), converts its
`--output-file` final-state body rows, launches real OpenGL windows, and captures
the demo window's client area using OpenGL readback from its actual window framebuffer before presentation. It saves the PNG to
`docs/img/knc-nbody-graphics.png`. `--screenshot BMP` captures the first demo frame or first live running frame with bodies. No synthetic particle positions are used for
the screenshot. The converter needs only Python's standard library. Upstream
`nbody/src/nbody_io.c:74-105,155-190` writes Cartesian x,y,z first in both output
variants; its older texinfo's `--output-cartesian` switch no longer exists.

```bash
python tools/make_demo_snapshot.py build/graphics/final-state.txt build/graphics/demo.snapshot --time 3.945
build/graphics/knc_nbody_graphics.exe --demo build/graphics/demo.snapshot
build/graphics/knc_nbody_graphics.exe --fullscreen --demo build/graphics/demo.snapshot
```

The converter accepts 1.96's `# ignore id x y z ...` header and comma-delimited
body rows, maps ignore=1 to dark (0) and ignore=0 to light (1),
and rejects nonfinite coordinates and more than 20000 bodies. It reads actual
body output, not a histogram or checkpoint. `--time` and `--step` default to
zero because upstream's body file does not record those values. Fraction done
is 1 for a final-state demo. An empty body table is valid.

Without `--demo`, run the executable from the BOINC slot directory containing
`init_data.xml`. It parses BOINC init data and calls the actual upstream
`boinc_graphics_get_shmem("knc_nbody")`. The wrapper must create the matching
mapping using `boinc_graphics_make_shmem("knc_nbody", sizeof(knc_graphics))`.
BOINC derives the slot suffix and tries Global/session attachment as documented
in `boinc-api-on-cygwin.md`. The graphics helper retries missing mappings once
per second. It never calls `boinc_init` or owns science/BOINC IPC control.

## Wire format for the producer and wrapper

`src/knc_graphics_format.h` is a C header with no pointers, native longs or
packed/unaligned fields. All integers and IEEE754 floats are little endian.
Version 1 snapshot files are exactly 320048 bytes, including zeroed unused
bodies. The shared mapping is exactly 320080 bytes. All reserved words are zero.

| Snapshot offset | Field |
| ---: | --- |
| 0, 4, 8, 12 | uint32 magic KNCS, version 1, size, body_count <= 20000 |
| 16 | two reserved uint32 words |
| 24 | float64 simulation time |
| 32 | uint64 step |
| 40 | float64 fraction_done in [0, 1] |
| 48 | 20000 bodies: float32 x, y, z, uint32 type (16 bytes each) |

| Shared mapping offset | Field |
| ---: | --- |
| 0, 4, 8 | uint32 magic KNCG, version 1, size |
| 12 | aligned atomic uint32 sequence |
| 16 | uint32 status: running 0, suspended 1, finished 2, waiting 3 |
| 20 | three reserved uint32 words |
| 32 | snapshot above |

The wrapper is the sole writer. Publish an odd sequence before modifying any
payload, issue a full memory barrier, write the complete header/status/snapshot,
issue a full barrier, then atomically publish the next even sequence. Advance
sequence for heartbeat-only updates at least once per second, including while
suspended. Sequence wraps modulo 2^32. The renderer copies between equal even
sequence loads separated by full barriers and validates the copied header and
active body values. After 5 seconds without a new sequence it shows a stale idle
scene; waiting, invalid and missing data also show the calm idle
scene; suspended data retain the frozen body frame. A valid zero-body snapshot is safe. The producer and relay are documented in [graphics-shmem.md](graphics-shmem.md).

Windowed is the default. `--fullscreen` uses the screen dimensions and a borderless
window. Escape closes either mode; fullscreen also closes on keyboard, mouse
click, or pointer movement after a two-second startup grace period. Resize and
minimize keep the projection dimensions nonzero. Points use camera-facing soft
textured quads on legacy OpenGL 1.1 and additive blending, with slow rotation.

## Anonymous-platform discovery

The package includes `knc_nbody_graphics.exe` as executable with a `file_ref`,
`copy_file`, and the ticket-requested `graphics_app` marker. It also sets
`open_name` to `graphics_app`: pinned BOINC 8.2.8 `client/client_types.cpp:1121-1145`
does not parse a `graphics_app` boolean in FILE_REF, and
`client/client_state.cpp:1468` actually discovers graphics by that open name
(`lib/common_defs.h:408`). The checker allows this one intentional rename and
requires both tags. The package dependency scan starts from both executables.

No card access is required. The package retains the card science executable and
its runtime closure; existing `scripts/card-launch.sh` is the lead's card runner.
Real-client staging and service-session access still need lead integration testing.
The pinned 8.2.8 launch contract and source citations are in [boinc-graphics-launch.md](boinc-graphics-launch.md). Live fake-card producer updates and both BOINC launch modes are covered by `bash tests/wrapper.sh graphics graphics-launch`. The offline window test uses the real BOINC mapping
implementation, rather than a fake attach function.

The window uses BOINC's `BOINC_app` class. Screensaver minimization closes fullscreen; a terminal relay closes either live mode after two seconds. After 30 seconds without a sequence update, an attached orphan exits. Before any mapping exists it keeps waiting. Demo mode has no task lifetime dependency.
