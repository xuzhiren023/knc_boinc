#!/usr/bin/env bash
# Start one Codex engineer session on a ticket. Usage: tools/codex_run.sh S1-01 [extra instruction]
# Lead tool. Network access is on only for tickets whose header says "Network: yes".
set -euo pipefail
ID="$1"; shift || true
EXTRA="${*:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd -W 2>/dev/null || pwd)"
CODEX="$(ls -t "$LOCALAPPDATA"/OpenAI/Codex/bin/*/codex.exe | head -1)"
TICKET="work/tickets/$ID.md"
[ -f "$ROOT/$TICKET" ] || { echo "no ticket $TICKET" >&2; exit 2; }
NET=false; grep -q '^.*Network: yes' "$ROOT/$TICKET" && NET=true
mkdir -p "$ROOT/.codex-logs"
N=$(ls "$ROOT/.codex-logs" | grep -c "^$ID-" || true)
LOG="$ROOT/.codex-logs/$ID-$N.jsonl"; LAST="$ROOT/.codex-logs/$ID-$N-last.md"
PROMPT="You are an engineer on the knc-boinc project. Read AGENTS.md, then implement ticket $TICKET exactly as written.
Use bash. Before compiling, export TMPDIR, TMP and TEMP to \$PWD/build/tmp (create it). Work on branch ticket/$ID
(create it from main if missing; if it exists, continue it). Commit as you go. End by appending the Engineer report to
the ticket and committing. $EXTRA"
TRUST="projects.\"${ROOT//\//\\}\".trust_level=\"trusted\""
"$CODEX" exec --json -C "$ROOT" --sandbox workspace-write --dangerously-bypass-hook-trust \
  -c "$TRUST" -c 'approval_policy="never"' -c 'model_reasoning_effort="medium"' \
  -c "sandbox_workspace_write.network_access=$NET" \
  --output-last-message "$LAST" "$PROMPT" < /dev/null > "$LOG" 2>&1
echo "done: $LAST"
