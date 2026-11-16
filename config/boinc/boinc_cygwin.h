#ifndef KNC_BOINC_CYGWIN_WIN_COMPAT_H
#define KNC_BOINC_CYGWIN_WIN_COMPAT_H
// Included after Windows and CRT headers by the small upstream patch.
#include <cfenv>
#include <cstdint>
#define _T(s) s
#ifndef NT_SUCCESS
#define NT_SUCCESS(status) ((LONG)(status) >= 0)
#endif
// SYSTEM_INFORMATION_CLASS value used by NtQuerySystemInformation.
#define SystemProcessInformation 5
inline char* strdate(char* out) {
    time_t now = time(nullptr); struct tm value;
    localtime_r(&now, &value); strftime(out, 9, "%m/%d/%y", &value); return out;
}
inline char* strtime(char* out) {
    time_t now = time(nullptr); struct tm value;
    localtime_r(&now, &value); strftime(out, 9, "%H:%M:%S", &value); return out;
}
inline void _fpreset() { fesetenv(FE_DFL_ENV); }
// Cygwin initializes its runtime for Win32-created threads. The BOINC API
// itself also uses CreateThread; no MSVCRT thread-local CRT state is involved.
inline uintptr_t _beginthreadex(void* security, unsigned stack,
    unsigned (WINAPI *entry)(void*), void* arg, unsigned flags, unsigned* id) {
    HANDLE thread = CreateThread(static_cast<SECURITY_ATTRIBUTES*>(security),
        stack, entry, arg, flags, id);
    if (!thread) errno = EAGAIN;
    return reinterpret_cast<uintptr_t>(thread);
}
#endif
