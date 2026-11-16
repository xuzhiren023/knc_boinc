# Checked-in standalone configuration

These headers are expanded from the pinned source's `.h.in` templates without
running CMake. They retain the upstream notices and macro bodies. The target
is Cygwin x86-64: BOINC/OpenCL/crlibm/curses/graphics/debug off, double on,
OpenMP from `-fopenmp`. POSIX headers, allocation and time functions are enabled;
Windows/Mach and unavailable functions are disabled. Lua uses its upstream
POSIX settings and standard 60-byte source ID / 512-byte CLI input settings;
no readline, dynamic module loading or external modules are needed.
Popt translations/iconv are disabled as upstream does. Its configuration file
search is unused by the recorded workunit command lines.

`mk/sources.mk` contains the shared sources and flags. C files are compiled as
GNU C99 with Cygwin gcc, the one `.cc` file as C++11, and linked with Cygwin g++.
Scalar dSFMT avoids an x86-only dependency in the future card source list.
`-fno-strict-aliasing` follows upstream dSFMT requirements; `-ffp-contract=off`
avoids accidental contraction outside upstream's explicit fused operations.
S1-02 must supply/check target platform feature values and architecture logic
when adding the KNC target; these are not claimed to be a tested card config.
