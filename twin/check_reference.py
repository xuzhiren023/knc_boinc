"""Retain evidence that the excluded printing path is absent on the reference."""
import hashlib
import json
from pathlib import Path
root = Path('runs/x86/small-1')
assert (root/'exit.txt').read_text().strip() == '0'
streams = {}
for name in ('stdout.txt', 'stderr.txt'):
    data = (root/name).read_bytes()
    count = data.lower().count(b'tree-incest')
    assert count == 0, 'reference reached cold error path: '+name
    streams[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                     'tree_incest_diagnostics': count}
ctx = Path('twin/capture/block-0.bin').read_bytes()
st = Path('twin/capture/block-1.bin').read_bytes()
# Offsets from the actual card disassembly of nbReportTreeIncest, also covered
# by the existing cross-target layout capture. Neither warning gate suppresses
# the first error in this capture.
assert ctx[0xbe] == 0
assert int.from_bytes(st[0xd4:0xd8], 'little') == 0
result = {'command': (root/'command.txt').read_text().strip(), 'exit': 0,
          'capture_quietErrors': 0, 'capture_treeIncest': 0, 'streams': streams,
          'histogram_sha256': hashlib.sha256((root/'histogram.txt').read_bytes()).hexdigest()}
Path('twin/gravity-reference.json').write_text(json.dumps(result, indent=2)+'\n')
print('Reference small-1: exit=0; stdout/stderr tree-incest diagnostics=0/0')
print('Capture warning gates: quietErrors=0, treeIncest=0 (first error would print)')
