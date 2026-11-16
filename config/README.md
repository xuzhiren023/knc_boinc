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
