# Sprint 2 review: one task from the host

Closed 2026-11-16 (EST). Goal met offline; real BOINC client and real card are Sprint 4.

## Delivered
- S2-01: BOINC 8.2.8 app API built with Cygwin g++ on its Win32 paths; offline fake-client protocol test (mapping
  names, 8192-byte layout, progress, checkpoint, suspend/resume/quit, graphics shmem, standalone).
- S2-02: `knc_wrapper.exe`: card staging over ssh/scp, detached card process with PID file, progress relay,
  STOP/CONT, checkpoint on quit and restore on restart (worked around an upstream restore defect), abort, bounded
  retries then temporary exit. Five flows tested through real BOINC IPC with a fake card running the x86 app.
- S2-03: project-directory package and `app_info.xml` (one app version, 1 host CPU, wrapper as main program), checker.
- S2-04: task contract passed through: argv order kept, file operands per upstream's option table staged and mapped back.

## Not proven
- The real Windows BOINC client (service/sandbox ACLs) with the Cygwin-built API.
- Windows OpenSSH against the card; real card execution and checkpoints.
- Current production task definition (logs/outputs declarations).

## Retro
- Codex's sandbox cannot write any `.git` path: engineers leave changes, the lead commits. Works well.
- Two sessions were lost to setup (no network for fetch; editing the dispatch script while bash ran it). Fixed: the
  lead fetches pinned sources once and the dispatcher copies them; never edit a running script.
- Keep worktrees until their gitignored artifacts (dist/, runs/) are used.
