# Card snapshots to BOINC graphics

The standalone science app accepts `--snapshot-interval S` (wall seconds;
zero/default disables snapshots). At complete CPU simulation steps it selects
at most 4,096 evenly spaced body indices, preserving Cartesian positions and
dark/light type, simulation time, step and fraction done. The fixed S3-02
`knc_snapshot` includes zeroed padding/unused bodies. It writes `snapshot.tmp`,
closes it, then renames to `snapshot`; a final snapshot is also published.
No BOINC libraries, graphics calls, or extra simulation threads run on the card.
Snapshots are observational and never replace checkpoint/science output.

The wrapper prepends the configured `snapshot_interval` (default **5 seconds**)
to the app arguments. It probes snapshot availability with each status poll and
downloads at most once per snapshot interval, plus on completion, into the slot's
`knc_snapshot.tmp`. It checks the exact wire size, header, reserved words,
finite coordinates, type/count, and progress before retaining `knc_snapshot`.
Missing or invalid snapshots keep the last good frame. An unavailable graphics
mapping or malformed graphics file must not fail science.

After BOINC initialization the wrapper calls the upstream
`boinc_graphics_make_shmem(KNC_GRAPHICS_NAME, sizeof(knc_graphics))` identified
in S2-01. BOINC chooses `boinc_knc_nbody_<slot>`, separate from client IPC.
The single writer publishes odd sequence, full barrier, payload/status, full
barrier, then even sequence using atomic operations. Status is waiting before
contact and during connection failure, running after launch, suspended after
STOP, and finished on completion. Heartbeats advance at least once per second
even while the app is stopped. The last good snapshot survives status changes.

The graphics helper starts in the same slot, parses `init_data.xml`, and calls
`boinc_graphics_get_shmem("knc_nbody")`. It accepts only stable even sequences
and validated frames. Missing/stale mappings show an idle scene. The camera
uses the body centroid and 98th-percentile projected radius with time smoothing; point
size/brightness adapt to viewport and body count. A faint Galactic disc grid
and centre marker provide a spatial reference. Gold is light matter, blue dark.

Run the offline end-to-end acceptance in Git Bash:

```bash
bash tests/wrapper.sh graphics
bash tests/graphics.sh
```

The first runs the real x86 app through the fake-card transport, compares its
file bytes against the actual BOINC graphics mapping during suspension,
checks sequence heartbeats, resume and finish, and opens the real graphics
consumer to check its live status. Run `python tests/snapshot_cost.py` after the x86 build to measure snapshot
serialization cost at five seconds (asserted below 1% of elapsed runtime).
The second exercises reader/window contracts
and captures a full-duration medium final-state demo into
`docs/img/knc-nbody-graphics.png`. Visual readability requires lead review.

For the card, build `make -C mk card` with the documented toolchain and temporary
directory exports. The binary and GCC runtimes are left in `dist/card/`;
`scripts/card-launch.sh` accepts `--snapshot-interval 5` among its app
arguments. Use the wrapper's generated `knc_run.sh` to inspect exact task staging.
Only the lead has card access. Native timing, SSH transport, and real BOINC
service/session acceptance require lead execution.

The native smoke script is `scripts/card-snapshot-run.sh THREADS ARGS...`.
Stage it next to the packaged ELF/runtimes and input files, then for example
run `sh card-snapshot-run.sh 240 -f params.lua -h input.hist -z histogram.txt
--seed 670828913 --ignore-checkpoint --checkpoint-interval=-1 1024`.
It leaves `snapshot`, prints its four header words and the app's timing
diagnostic. The wrapper's normal SSH path retrieves the file itself.
