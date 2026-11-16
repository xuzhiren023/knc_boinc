#!/usr/bin/env bash
# Start one Codex engineer session on a ticket in its own worktree. Usage: tools/codex_run.sh S1-01 [extra instruction]
# Lead tool. The Codex sandbox cannot write .git: the engineer leaves changes uncommitted; the lead reviews and commits.
# Network access is on only for tickets whose header says "Network: yes".
set -euo pipefail
ID="$1"; shift || true
EXTRA="${*:-}"
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
TICKET="work/tickets/$ID.md"
[ -f "$MAIN/$TICKET" ] || { echo "no ticket $TICKET" >&2; exit 2; }
WT="$MAIN/.work/$ID"
if [ ! -d "$WT" ]; then
  if git -C "$MAIN" show-ref -q "refs/heads/ticket/$ID"; then git -C "$MAIN" worktree add -q "$WT" "ticket/$ID"
  else git -C "$MAIN" worktree add -q -b "ticket/$ID" "$WT" main; fi
fi
# Engineers have no network by default: give each worktree the lead-fetched pinned sources (scripts/fetch.sh in main).
[ -d "$MAIN/third_party" ] && [ ! -d "$WT/third_party" ] && cp -r "$MAIN/third_party" "$WT/"
ROOT="$(cd "$WT" && pwd -W 2>/dev/null || pwd)"
CODEX="$(ls -t "$LOCALAPPDATA"/OpenAI/Codex/bin/*/codex.exe | head -1)"
NET=false; grep -q 'Network: yes' "$WT/$TICKET" && NET=true
mkdir -p "$MAIN/.codex-logs"
N=$(ls "$MAIN/.codex-logs" | grep -c "^$ID-[0-9]*\.jsonl" || true)
LOG="$MAIN/.codex-logs/$ID-$N.jsonl"; LAST="$MAIN/.codex-logs/$ID-$N-last.md"
PROMPT="You are an engineer on the knc-boinc project. Read AGENTS.md, then implement ticket $TICKET exactly as written.
Use bash. Before compiling, export TMPDIR, TMP and TEMP to \$PWD/build/tmp (create it). Do not run git commands that
write (no commit, branch, add); the lead commits. End by appending the Engineer report to the ticket file. $EXTRA"
TRUST="projects.\"${ROOT//\//\\}\".trust_level=\"trusted\""
"$CODEX" exec --json -C "$ROOT" --sandbox workspace-write --dangerously-bypass-hook-trust \
  -c "$TRUST" -c 'approval_policy="never"' -c 'model_reasoning_effort="${EFFORT:-medium}"' \
  -c "sandbox_workspace_write.network_access=$NET" \
  --output-last-message "$LAST" "$PROMPT" < /dev/null > "$LOG" 2>&1
echo "done: $LAST"
