# knc-boinc

Run a BOINC science app on an Intel Xeon Phi x100 (Knights Corner) card as **one BOINC task that uses all
240 hardware threads**, with a working screensaver on the host.

First target: standard MilkyWay@home N-body **1.96** (`milkyway_nbody`, tag `nbody_1.96`,
commit `1e640779`), built for the card with GCC-KNC and OpenMP. Package version 196
uses host platform `windows_x86_64`. See [SOURCES.md](SOURCES.md) for pins and
[the 1.96 regression](tests/nbody_196_matrix.py) for references and vector/chunk checks.

```
BOINC client (laptop, Windows)
  └─ knc_wrapper.exe        one task, 1 host CPU, BOINC API (progress, suspend, quit, checkpoint)
       ├─ ssh/scp ──► card: milkyway_nbody (k1om, OpenMP, 240 threads)
       └─ graphics shared memory ◄── particle snapshots from the card
  └─ knc_nbody_graphics.exe  screensaver / "Show graphics" window
```

- Plan, decisions and sprints: [docs/PLAN.md](docs/PLAN.md)
- Current state: [STATUS.md](STATUS.md)
- Try it yourself: [docs/TRY-IT.md](docs/TRY-IT.md) (written in Sprint 4)
- Engineer rules: [AGENTS.md](AGENTS.md)

Independent of the GCC-KNC repository; it only uses its installed compiler. New setup on another machine:
[WORKSTATION-SETUP.md](WORKSTATION-SETUP.md).

Licence: our own code is Apache-2.0 ([LICENSE](LICENSE)). The files in `patches/` modify GPL-3.0 MilkyWay@home and
LGPL BOINC sources and stay under those licences; the built card application combines with that code and is
distributed under GPL-3.0-or-later. Third-party pins and notices: [SOURCES.md](SOURCES.md).
