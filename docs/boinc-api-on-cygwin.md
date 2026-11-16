# BOINC app API on Cygwin: S2-01

Source: BOINC release `client_release/8.2/8.2.8`, peeled commit
`0bb9686b9ea2cb26e342c715026d8059fa58b922` (see `SOURCES.md`).
All source citations below are relative to `third_party/boinc/`, at that commit;
line numbers refer to upstream, before our compatibility patch. The sources
are fetched for inspection, but only `lib/` and `api/` are compiled.

## Windows client protocol

The client chooses the first available `shm_boinc_N`, N=0..1023, creating
`sizeof(SHARED_MEM)` bytes. It passes `try_global` only when it has the sandbox
account service token (`client/app_start.cpp:133-149`). The actual object can
be `Global\shm_boinc_N`; a normal non-service client uses the session namespace.
`lib/shmem.cpp:71-201` builds an Everyone SID ACL granting FILE_MAP_ALL_ACCESS,
creates a pagefile mapping with `CreateFileMapping(INVALID_HANDLE_VALUE, ...,
PAGE_READWRITE, 0, size, name)`, retries without `Global\` on access denied,
rejects ERROR_ALREADY_EXISTS, and maps with `MapViewOfFile`.

The init file contains `<comm_obj_name>boinc_N</comm_obj_name>`, without `shm_`.
The client copies this into APP_INIT_DATA (`client/app_start.cpp:269-277`);
`lib/app_ipc.cpp:171-177,386` writes/parses it. The app prefixes SHM_PREFIX
(`shm_`) and calls attach_shmem (`api/boinc_api.cpp:319-326`). Attachment tries
`OpenFileMapping(FILE_MAP_ALL_ACCESS, FALSE, "Global\\" + name)` first, then
the session name, followed by `MapViewOfFile` (`lib/shmem.cpp:203-227`). Detach
unmaps and closes the mapping handle (`lib/shmem.cpp:229-234`). The fake
client retains its handle until the app exits; handle inheritance is unnecessary.
The client also passes its native Windows PID in init_data.xml; the API checks
it with OpenProcess (`api/boinc_api.cpp:492-518`).

`lib/app_ipc.h:38-98` defines SHARED_MEM as **8192 bytes**, alignment 1, eight
1024-byte MSG_CHANNELs, with no pointers, handles, longs or ABI-dependent fields:

| Offset | Channel | Direction / purpose |
| ---: | --- | --- |
| 0 | process_control_request | client ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ app: suspend/resume/quit/abort |
| 1024 | process_control_reply | app ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ client; unused |
| 2048 | graphics_request | client ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ app; legacy, currently unused |
| 3072 | graphics_reply | app ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ client; graphics/web/remote-desktop replies |
| 4096 | heartbeat | client ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ app: heartbeat and runtime information |
| 5120 | app_status | app ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ client: CPU, checkpoint CPU, fraction done |
| 6144 | trickle_up | app ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ client |
| 7168 | trickle_down | client ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ app |

Byte 0 is the pending flag. The remaining 1023 bytes hold a NUL-terminated
message (at most 1022 text bytes). send_msg refuses a full channel, copies text,
then sets the flag; get_msg copies text and clears it. reset_msgs zeros all
8192 bytes (`lib/app_ipc.cpp:429-450`). There is no named mutex or event in
this IPC handshake: each channel is a single-producer/single-consumer mailbox,
polled by the participants. The app has a private unnamed CreateMutex for its
worker/timer state (`api/boinc_api.cpp:352-368`). Windows diagnostics also has
its own thread/event machinery; those objects do not transport client control
or status messages.

The client enqueues `<quit/>` (`client/app_control.cpp:200-210`), `<suspend/>`
(:1333-1351), and `<resume/>` (:1354-1375) on process_control_request. The API's
0.1-second Windows CreateThread timer (`api/boinc_api.cpp:209-214,1503-1520,
1572-1609`) consumes them (`:1287-1369`). With direct_process_action enabled,
suspend calls SuspendThread (or enumerates threads/processes for multi-thread
or multi-process apps), resume calls ResumeThread, and quit exits without a
successful-finish marker (`:1163-1239,1345-1354,948-960`). A wrapper must set
`direct_process_action=0`: then boinc_get_status exposes suspended and
quit_request so the wrapper can control its remote worker. It must stop remote
work on suspend, restart on resume, and quit without boinc_finish(0) on quit.
This is the mode exercised here (`api/boinc_api.h:55-64`).

Status is XML text in app_status: `<current_cpu_time>`,
`<checkpoint_cpu_time>`, `<fraction_done>` (and optional fields).
The timer publishes it, and boinc_checkpoint_completed updates the saved
checkpoint CPU value and checkpoint interval; checkpoint reporting is a field
in status, not a separate channel (`api/boinc_api.cpp:418-467,1435-1471,
1666-1684`). While suspended, the API suppresses status reports (`api/boinc_api.cpp:1463-1470`);
the test checks the independent graphics work counter remains fixed.
The client reads/parses the same fields
(`client/app_control.cpp:1412-1479`).

## Graphics shared memory

This is a second mapping with an application-defined size and payload, not an
extension of SHARED_MEM. Both app and graphics helper call get_shmem_name:
`boinc_<prog_name>_<slot>` (`api/graphics2_util.cpp:49-54`). The slot comes from the cached APP_INIT_DATA via boinc_get_init_data
(`api/boinc_api.cpp:1153-1160`); a graphics process first parses init_data.xml. The science app creates it via
boinc_graphics_make_shmem, and the graphics app attaches via
boinc_graphics_get_shmem, both using the same Windows create_shmem/attach_shmem
calls (`:57-65,85-96`). Global-first creation/attachment and session fallback
apply here too. There is no mapping name sent over graphics_request and no
client-owned graphics payload layout. The graphics executable must run in the
correct slot directory with the same prog_name. The spike creates
`boinc_s201_731` and checks its payload from a separate process. It does not
build an OpenGL renderer.

## Build variant

Use **Cygwin x86-64 g++ with explicit `_WIN32`, `_WIN64`, `WIN32`,
`__CYGWIN32__`, and `HAVE_CONFIG_H`**, as recorded in `mk/boinc.mk`.
`__CYGWIN32__` selects BOINC's legacy Cygwin CRT/header guards (the compiler
only predefines `__CYGWIN__`). `_WIN64` selects the correct Windows diagnostics
structures on this 64-bit compiler. This remains a Cygwin executable using
cygwin1.dll; it calls Win32 through the installed w32api headers/import libs.
It is not a native MinGW build. Consumers must use the same flags and include
paths (including `-include config.h`), since APP_INIT_DATA and other non-wire classes have conditional members.

Plain POSIX Cygwin cannot match this client: SHMEM_SEG_NAME becomes int,
init data parses `<shm_key>` rather than `<comm_obj_name>`, setup_shared_mem
uses `boinc_mmap_file` or SysV keys, and graphics uses file mmap
(`lib/app_ipc.h:120-125`, `lib/app_ipc.cpp:171-177,386-390`,
`api/boinc_api.cpp:327-346`, `api/graphics2_util.cpp:66-82,97-113`). Merely sharing
SHARED_MEM's byte layout would not fix its object discovery or system calls.
The build does not require the obsolete `-mwin32` driver mode.

The checked-in config and `patches/boinc/cygwin-win32.patch` adapt CRT spellings,
thread creation in diagnostics, date/time and floating-point reset helpers,
MSVC-only includes, POSIX directory/delete/fopen paths, and three DWORD out
parameters. The archive contains upstream implementations, not test stubs.
The wire structures, mapping/security implementation, message operations,
control handling, init XML, status XML and graphics naming remain upstream.
Function/data sections plus linker garbage collection limit the app-side link;
no BOINC installation or configure/CMake invocation is needed.

## Reproduce and evidence

From this worktree, using Git for Windows bash:

```bash
export PATH="/c/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin:$PATH"
mkdir -p build/tmp
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
bash scripts/fetch.sh boinc
make -C mk boinc-api
bash tests/boinc-api.sh
```

The archive is `build/boinc/libboinc_api.a`; test executables are beside it.
The script creates fresh slot directories under `build/boinc/test.*` and retains
init data, diagnostic logs and control acknowledgments there. The fake client
copies only the mapping allocation loop and orchestration from the cited client
code, then links the actual upstream create_shmem, APP_INIT_DATA writer,
MSG_CHANNEL, and reset_msgs. It uses CreateProcessA with CREATE_NO_WINDOW and
a native executable path, and bounded waits with child cleanup on failure.
Static assertions fix the Windows channel size, mapping size and offsets.
The app links the real BOINC API and graphics helper. Both participants use
Windows mapping calls even though the fake client also uses Cygwin's CRT.

Validated with Cygwin g++ 14.4.0 on this Windows laptop (2026-11-16).
`make -C mk boinc-api` builds successfully; `bash tests/boinc-api.sh` exits 0:

```text
PASS local (namespace=session): layout=8192 progress=0.12 checkpoint=0.046875 suspend/resume/quit graphics
PASS global (namespace=session): layout=8192 progress=0.121 checkpoint=0.03125 suspend/resume/quit graphics
PASS standalone
```

The global **attempt fell back to the session namespace**, as upstream allows
on ERROR_ACCESS_DENIED. This account cannot prove a privileged Global mapping
or cross-session service access. The initial red test, before implementation,
failed with `No rule to make target 'boinc-api'`. During integration the first
protocol test incorrectly expected status while suspended; it failed with
`FAIL: no status while suspended (Win32 error 0)`. Reading upstream's explicit
suppression at `api/boinc_api.cpp:1463-1470` corrected that test expectation;
the final test checks a frozen work counter and no new status during the pause,
then requires work and status to advance on resume.

Evidence retained in `build/boinc-build.txt`, `build/boinc-test.txt`,
`build/boinc/test.Gzm50R/`, `build/boinc-runtime.txt`, and `build/boinc-dlls.txt`.
These generated files are ignored by Git. The source test and script are tracked
for repeatability. The library and both host executables remain in `build/boinc/`.

**Decision:** the explicit Windows source path under Cygwin is viable for the
wrapper's offline IPC boundary. Plain POSIX Cygwin is incompatible. This spike
does not establish real-client or service-account acceptance.

## Runtime DLLs

`objdump -p build/boinc/boinc_app.exe` shows direct non-system imports
`cygwin1.dll`, `cyggcc_s-seh-1.dll`, and `cygstdc++-6.dll`.
`cygcheck build/boinc/boinc_app.exe` also resolves the transitive
`cygiconv-2.dll` and `cygintl-8.dll` from the same toolchain's `bin/` directory.
Those **five DLLs** must be available to the app, e.g. beside the executable,
unless the matching Cygwin runtime is already on PATH. This build uses shared
Cygwin GCC/C++ runtimes. The fake client has the same non-system dependencies.
Windows supplies ADVAPI32, KERNEL32, SHELL32 and USER32 and their system
dependencies; do not package copies of those. No BOINC client installation,
GPU driver runtime or card runtime is required for this test.

## Remaining real-client risk

An offline fake client proves the app protocol boundary, not all behavior of an
installed Windows BOINC client. The lead should validate a real local task,
including service-account/session ACLs, sandbox directories and permissions,
client restarts and lost-client handling, abort, real checkpoint restart,
file staging and process priorities. The fake client's global attempt uses the
upstream access-denied fallback; a privileged service's cross-session access
requires a real service test. Automatic local thread suspension and Windows
crash diagnostics are not exercised by this wrapper-mode test. Cygwin CRT path
conventions and its internal threads need care when building the actual wrapper;
pass native paths to Windows-only calls. No card execution is involved or
claimed by this ticket, and no MinGW download is needed for this spike.
