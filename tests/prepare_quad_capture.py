"""Add identical observation hooks to pristine 1.96 and patched generators."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
upstream = root/'third_party/milkywayathome_client_196'
original = subprocess.check_output(
    ['git', '--no-optional-locks', '-C', str(upstream), 'show',
     '1e640779f1cabf88aaa49e4db569cfe7e09016c4:nbody/src/nbody_mixeddwarf.c'],
    text=True)
patched = (upstream/'nbody/src/nbody_mixeddwarf.c').read_text()
for variant, text in [('off', original), ('on', patched)]:
    text = text.replace('#include "nbody_king_model.h"',
                        '#include "nbody_king_model.h"\n#include "quad_capture.h"')
    marker = '        unsigned int i = 0;'
    assert text.count(marker) == 1
    text = text.replace(marker, '        double s8_start = s8_capture_start();\n' + marker)
    marker = '        /* pushing the bodies */'
    assert text.count(marker) == 1
    text = text.replace(marker,
        '        s8_capture_end(s8_start, nbody, x, y, z, vx, vy, vz, masses);\n' + marker)
    (root/f'build/s8/mixeddwarf-{variant}.c').write_text(text)
