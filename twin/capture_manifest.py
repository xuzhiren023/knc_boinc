"""Check layout compatibility and fingerprint the independently captured bytes."""
import hashlib, json, struct
from pathlib import Path
root = Path('twin')
a = (root/'capture/layout-x86.bin').read_bytes()
b = (root/'capture/layout-card.bin').read_bytes()
# PE/COFF .data has trailing section alignment, not additional array elements.
assert a[:22*8] == b[:22*8] and len(b) >= 22*8
assert not any(a[22*8:]) and not any(b[22*8:])
k = json.loads((root/'capture.json').read_text())
cw = struct.unpack('<H',(root/'capture/host-fcw.bin').read_bytes())[0]
assert int(k['numerical_policy']['x87_control_word'],16) == cw
files = sorted((root/'capture').glob('*.bin'))
manifest = {'layout_values':list(struct.unpack('<22Q',b[:176])),
 'x87_control_word':hex(cw),'blocks':len(k['init']['memory']),
 'expected_acceleration':list(struct.unpack('<3d',(root/'capture/expected.bin').read_bytes())),
 'log_input':struct.unpack('<d',(root/'capture/log-input.bin').read_bytes())[0],
 'log_expected':struct.unpack('<d',(root/'capture/log-expected.bin').read_bytes())[0],
 'files':[{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,
           'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(root/'capture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Layout matched; captured files:',len(files))
