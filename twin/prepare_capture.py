"""Generate an instrumented copy without changing the pinned upstream tree."""
from pathlib import Path
import sys
multicore = sys.argv[1:] == ["--multicore"]
if sys.argv[1:] and not multicore:
    raise SystemExit("usage: prepare_capture.py [--multicore]")
src = Path('third_party/milkywayathome_client/nbody/src/nbody_grav.c').read_text()
needle = 'static inline mwvector nbGravity(const NBodyCtx* ctx, NBodyState* st, const Body* p)\n{'
assert src.count(needle) == 1
helper = 'capture_multicore.h' if multicore else 'capture_helper.h'
src = src.replace(needle, '#include "capture_helper.h"\n' + needle + '\n    int capturing = capture_begin(ctx, st, p);')
src = src.replace('    return acc0;', '    if (capturing) capture_end(acc0);\n    return acc0;', 1)
src = src.replace('capture_helper.h', helper)
Path('build/capture_grav.c').write_text(src)
