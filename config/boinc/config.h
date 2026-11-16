#ifndef KNC_BOINC_CYGWIN_CONFIG_H
#define KNC_BOINC_CYGWIN_CONFIG_H
#define PACKAGE_VERSION "8.2.8"
#define HAVE_STD_MAX 1
#define HAVE_STD_MIN 1
#define HAVE_STD_TRANSFORM 1
#define HAVE_ALLOCA 1
#define HAVE_STRCASECMP 1
#define HAVE_SOCKLEN_T 1
#define HAVE_FCNTL_H 1
#define HAVE_SYS_RESOURCE_H 1
#define HAVE_UNISTD_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_DIRENT_H 1
#define HAVE_STRDUP 1
#define HAVE_SNPRINTF 1
#define HAVE_VSNPRINTF 1
#define HAVE_STDINT_H 1
#define HAVE_INTTYPES_H 1
// Cygwin CRT spellings for the Windows API source path.
#include <cerrno>
#include <ctime>
#include <cstdio>
#define _alloca __builtin_alloca
#define _msize malloc_usable_size
#define _MAX_PATH 260
#define _fileno fileno
#define _snprintf snprintf
inline int localtime_s(struct tm* result, const time_t* value) {
    return localtime_r(value, result) ? 0 : EINVAL;
}
#endif
