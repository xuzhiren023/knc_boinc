# Moving knc-boinc to the workstation (HP Z440, 2x E5-2690 v3)

Written 2026-11-17 by the laptop lead for the migration. Everything below that is not in git must be copied from the
laptop (Lenovo Y9000X) by USB stick or network share. Nothing here goes through GitHub except the repository itself.

## 1. Owner: install on the workstation (before the card moves)

| What | Why |
|---|---|
| Intel MPSS 3.x for Windows (the version the laptop runs) | card driver, `mic0`, SCIF/DMA. Install before the card goes in. |
| Git for Windows | clone, Git Bash (all repo scripts are bash) |
| Python 3.8+ on PATH | tools, tests, card_run |
| Windows OpenSSH client (built in) | `C:/Windows/System32/OpenSSH/ssh.exe`, used by the wrapper |
| BOINC 8.x, attached to MilkyWay@home | the target client |
| Claude Code (desktop app) and the Codex CLI | lead session and engineers (`tools/codex_run.sh`) |

## 2. Owner: copy from the laptop (about 3.6 GB)

Keep the same folder layout under `C:\Users\<you>\Documents\`. If the workstation user name is also `xuzhi`, every
script works unchanged; otherwise S11-05 (below) replaces the hardcoded paths with `config/local.env`.

| Laptop path | Size | Used for |
|---|---|---|
| `Documents\gcc_knc\.work\_shared\toolchain` | 2.5 GB | Cygwin host tools and k1om binutils |
| `Documents\gcc_knc\.work\_shared\gcc-knc-16.2.0` | 0.9 GB | the GCC-KNC cross compiler and card runtimes |
| `Documents\gcc_knc\.work\_shared\S10-02\host` | small | host `libknc_vmath.a` (DF_VECTOR8 check build) |
| `Documents\gcc_knc\tools\knc_lint`, `tools\card_run*`, `config\card.local.json` | small | lint and card_run helpers |
| `Documents\gcc_knc\.work\_state\card\known_hosts` | small | card host key |
| `Documents\card-coordination\` | small | shared card ledger (`jobs.jsonl`) |
| `.ssh\xeon_phi_rsa`, `.ssh\xeon_phi_rsa.pub`, the `phi3120` entry of `.ssh\config` | small | card login; **never put the key in git** |
| `.claude\skills\knc-twin`, `knc-optimize`, `agent-team-project` (and `Documents\knc-twin`) | small | twin and tuning skills |
| `Documents\knc-boinc\dist\knc-boinc-installer\` (optional) | 55 MB | ready-made installer, no build needed |

If GCC-KNC itself also moves, its lead migrates the whole `gcc_knc` checkout; knc-boinc needs only the rows above.

## 3. Clone and build

```bash
cd ~/Documents
git clone https://github.com/xuzhiren023/knc_boinc.git knc-boinc
cd knc-boinc
bash scripts/fetch.sh              # MilkyWay 1.96, BOINC, crlibm into third_party/ (not tracked) and applies patches/
bash packaging/make_package.sh     # release card binary (config/release.env), wrapper, graphics -> dist/milkyway_package
bash scripts/make-boinc-installer.sh dist/milkyway_package
```

Then double-click `dist\knc-boinc-installer\Install KNC BOINC.cmd` (docs/TRY-IT.md).

## 4. When the card is in

1. `ping 192.168.1.100` and `ssh phi3120 cat /proc/cpuinfo | grep -c processor` (expect 244 on a 7120).
2. Host side of TCP transfers is `192.168.1.99` (`tools/card_run --transfer auto|tcp`); allow it in the firewall
   once, as on the laptop (owner action).
3. One correctness job: `docs/benchmarks.md` core-small, then a real task through BOINC.

## 5. For the Claude lead on the workstation

Read `AGENTS.md`, `STATUS.md`, `docs/PLAN.md` first. Standing rules carried over from the laptop lead:

- Roles: the lead plans, writes tickets, reviews, merges, runs card jobs; Codex engineers implement
  (`MODEL=gpt-6.1-sol EFFORT=... bash tools/codex_run.sh <ticket>`, run in the background, never with `&`).
  After two engineer failures on a step the lead finishes it.
- Results stay bit-identical to stock x86 (`compare.py`, |diff| < 1e-10). Compiler-fixable gains go to GCC-KNC as
  findings; everything else is handwritten IMCI here. knc-boinc is independent of GCC-KNC's plans.
- Never write to `C:/ProgramData/BOINC`; never start or stop the owner's BOINC client; never write to the gcc_knc
  repository. Card jobs only inside our booked ledger turn, then clean up `/tmp/knc-boinc/claude-*`.
- No checksums on host-card transfers (length check only). Push only at the owner's request.
- After merging a patch, refetch `third_party` (`rm -rf third_party; bash scripts/fetch.sh`) before any build or
  dispatch; `codex_run.sh` copies main's `third_party`.
- Host load: the laptop capped engineers at 4 cores and pinned them to CPUs 0-9 (DMA helpers need free cores). The
  workstation has 24 cores / 48 threads: raise the cap in `AGENTS.md` and `tools/codex_run.sh` (suggest 8 cores per
  engineer, keep 2 cores free for the card DMA helpers) and run several engineers at once.

Open work at migration time (details in `work/tickets/`):

- **S11-03** (wrapper setup progress, checkpoint interval, automatic card booking): engineer run was still going on
  the laptop; its result arrives as branch `s11-03` if it finished, otherwise redispatch it here. Review it, merge,
  rebuild package and installer.
- **S11-05** (portability: `config/local.env`, doctor script, no hardcoded user paths): do it on the workstation, where
  the real paths are known.
- Owner end-to-end check: double-click install, one real task with progress during star setup.
- Close Sprint 11 (STATUS, PLAN). First real task 117676 was reported 2026-11-17; validation pending on MilkyWay.
- Later: S12-01 vector Milky Way potential; S12-02 exact vector log/atan (deferred).
