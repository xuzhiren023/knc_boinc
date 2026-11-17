from pathlib import Path
import re
import json
root=Path('build/s11/science')
a,b=[(root/m/'stderr.txt').read_text() for m in ('off','on')]
value=lambda s: re.search(r'<search_likelihood>\s*(.*?)\s*</search_likelihood>',s)[1]
assert value(a)==value(b), (value(a),value(b))
assert value(b)==json.loads(Path('workunits/core-small/reference.json').read_text())['likelihood_text']
histogram=lambda mode: b''.join(line for line in (root/mode/'histogram.txt').read_bytes().splitlines(True)
                                if not line.startswith(b'# Generated '))
assert histogram('off')==histogram('on')
assert not (root/'off/generation').exists()
assert (root/'on/generation').read_text().split()==['4000','4000']
print('PASS core-small instrumentation off/on: bit-identical likelihood '+value(b)+', histogram bytes except generated-at comment; generation=4000/4000 (OMP_NUM_THREADS=4)')
