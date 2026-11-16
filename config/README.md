# Checked-in standalone configuration

These headers expand the pinned upstream templates without CMake. Both builds
use BOINC/OpenCL/curses/graphics/debug off, double precision and bundled crlibm
on, OpenMP via `-fopenmp`. POSIX allocation/time/filesystem features are enabled;
Windows/Mach APIs are disabled. Lua uses POSIX with no readline or module loader.
Popt translations/iconv are disabled. Scalar dSFMT is used in both targets.

`mk/sources.mk` contains the shared explicit source list (including exactly the
crlibm sources in its CMakeLists.txt) and IEEE flags. C is GNU99; C++ is GNU++11.
The card additionally uses `-march=knc`. `-ffp-contract=off` prevents unintended
FMA contraction. There is no fast-math or static libc link.

As upstream documents in `milkyway/CMakeLists.txt:108-110`, crlibm selection is
per application: N-body sources include nbody_config.h and use crlibm, while
the shared MilkyWay utility/Lua objects retain upstream's system-math setting.

`crlibm_config.h` defines CRLIBM_TYPECPU_AMD64 for the little-endian, 64-bit
K1OM ABI as well as x86. It explicitly enables CRLIBM_HAS_FPU_CONTROL, which
upstream's bundled CMake does not define: otherwise crlibm_init is a no-op.
Card builds use the sysroot fpu_control.h; Cygwin uses crlibm's own inline
GETCW/SETCW with matching x87 constants. Both select portable double-double
crlibm sources rather than the optional extended-precision variants.

`main.c:nbSpecialSetup` calls crlibm_init before OpenMP worker creation. Card
objdump shows fnstcw, immediate 0x027f, fldcw: precision control 53 bits and
round-to-nearest. New workers inherit that floating-point environment. This
is static build evidence, not a native card execution claim; dynamic behavior
and x86/card agreement remain for the lead. See the ticket report for evidence.

S5-02 sets `NBODY_FORCE_CHUNK=4` only for the card through `mk/Makefile`.
At 1,024 bodies this provides 256 dynamic chunks, enough to offer work to all
240 workers instead of only eight. At 20,000 bodies there are 5,000 chunks
(about 21 per worker), amortizing dispatch over four expensive body walks
rather than using one-body chunks. This is a reasoned initial setting, not a
measured KNC optimum. At 64 bodies even chunk 4 only offers 16 chunks; the
chosen target is medium and large. The guided shared-memory loop uses 4 as a
minimum chunk, so its initial chunks still depend on the OpenMP runtime.

For controlled experiments, `FORCE_CHUNK=N` overrides either target. Use a
separate output directory for every setting, as make does not track command
line flag changes, for example:

```bash
make -C mk -j6 TARGET=card OUT=../build/card-chunk-128 FORCE_CHUNK=128 program
make -C mk -j6 TARGET=x86 OUT=../build/x86-chunk-4 FORCE_CHUNK=4 program
```

`bash tests/force-chunk.sh` builds separate x86 variants and checks all 26
small/medium/large combinations against the x86 upstream-default build. An
optional argument names an archived pre-patch default binary; the S5-02 report
uses that stronger independent reference. Captures are in `runs/force-chunk/`,
with exact scientific-token checks in addition to `scripts/compare.py`.
Compiler scratch is always in `build/tmp`.

The twin can inspect generated per-body arithmetic/ISA and estimate isolated
kernel costs under its assumptions. It does not model the OpenMP runtime,
dynamic/guided dispatch, worker contention, OpenMP barriers or scheduling overhead;
it cannot predict the chunk-size speedup or choose the optimum. Run medium
and large at 240 threads on the card before and after, with identical inputs,
seed, compiler flags, runtimes and affinity. Compare science with
`scripts/compare.py`, check receipt exit status, and compare wall time on
repeated exclusive runs. Use `bash scripts/card-check.sh` to print the commands
without accessing the card, and retain separate captures/receipts for each
binary. The bounded large workunit is not a full production-duration proof.
