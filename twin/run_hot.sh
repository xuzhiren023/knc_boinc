#!/usr/bin/env bash
# The measured overall hotspot, in addition to the ticket's gravity kernel.
set -euo pipefail
cd "$(dirname "$0")/.."
TWIN_HOME=${TWIN_HOME:-C:/Users/xuzhi/.claude/skills/knc-twin}
python twin/log_overlay.py
python twin/disambiguate.py
python "$TWIN_HOME/scripts/from_binary.py" build/card/milkyway_nbody.mic \
 --function log_rn --with-callee p_accu --disassembly twin/card.symbols.disassembly.txt \
 --init twin/log-capture.json --out twin/log-kernel.json --report twin/log-conversion.json
python - <<'PY'
import json
from pathlib import Path
p=Path('twin/log-kernel.json');k=json.loads(p.read_text());k.pop('memory_default',None);p.write_text(json.dumps(k,indent=2)+'\n')
PY
failed=0
for command in validate functional simulate bounds; do
 options=(); [[ "$command" == functional ]] || options+=(--profile card-7120-measured)
 python "$TWIN_HOME/scripts/knc_twin.py" "$command" twin/log-kernel.json \
  "${options[@]}" --out "twin/hot/$command" --force || failed=1
done
exit "$failed"
