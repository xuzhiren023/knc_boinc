# knc-boinc

Run a BOINC science app on an Intel Xeon Phi x100 (Knights Corner) card as **one BOINC task that uses all
240 hardware threads**, with a working screensaver on the host.

First target: MilkyWay@home N-body (`milkyway_nbody`), built for the card with GCC-KNC and OpenMP.

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

Independent of the GCC-KNC repository; it only uses its installed compiler. GPL-3.0-or-later, because it builds
and patches GPL code (MilkyWay@home client, BOINC LGPL libraries).
