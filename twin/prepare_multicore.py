"""Prepare explicitly partial one-body diagnostics, without inventing a slice loop.

The built function and S1-05 cut are unchanged. A successful diagnostic is not
an S1-06 128-body/context result. See evidence.json and docs/twin-multicore.md.
"""
import copy
import json
from pathlib import Path
root = Path('twin/multicore')
capture = json.loads((root/'capture.json').read_text())
kernel = json.loads(Path('twin/kernel.json').read_text())
layout = capture['capture_layout']
assert layout['bodies'] == 20000 and layout['chunk_bodies'] == 128
assert (root/'capture/expected.bin').stat().st_size == 4096*24
assert (root/'capture/ctx.bin').read_bytes()[0xbe] == 0
assert int.from_bytes((root/'capture/state.bin').read_bytes()[0xd4:0xd8], 'little') == 0
# Repack each offset block without changing any initialized byte or address.
# The model hashes an entire file on every load, so a large packed file per
# node repeats hundreds of GB of hashing. Small files keep that cost bounded.
blocks = root/'capture/blocks'
blocks.mkdir(exist_ok=True)
cache = {}
for index, block in enumerate(capture['init']['memory']):
    if 'file' not in block or 'offset' not in block:
        continue
    source = block['file']
    if source not in cache:
        cache[source] = (root/source).read_bytes()
    offset, length = block.pop('offset'), block.pop('length')
    data = cache[source][offset:offset+length]
    assert len(data) == length
    path = blocks/('%05d.bin' % index)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
    assert path.read_bytes() == cache[source][offset:offset+length]
    block['file'] = path.relative_to(root).as_posix()
print('Repacked %d nodes as byte-identical file blocks' % len(list(blocks.glob('*.bin'))))

body_addr = int(capture['init']['registers']['rcx'], 16)
records = kernel['streams'][0]['instructions']
# cut_gravity.py has already checked equality with full adapter records.
assert kernel['provenance']['region_cut']['retained_records_identical']
for scale, cores in [('core', 1), ('unit', 8), ('ring', 8)]:
    k = copy.deepcopy(kernel)
    k['name'] = 'large-first-force-one-body-diagnostic-'+scale
    k['init'] = copy.deepcopy(capture['init'])
    # Adapter-provided ELF constants remain part of the unchanged card region.
    k['init']['symbols'] = copy.deepcopy(kernel['init'].get('symbols', {}))
    k['init']['memory'] = [copy.deepcopy(b) for b in kernel['init']['memory'] if 'file' not in b] + k['init']['memory']
    k['numerical_policy'] = capture['numerical_policy']
    k['scenario'] = copy.deepcopy(capture['scenario'])
    k['expected'] = {'memory': []}
    k['streams'] = []
    for slot in range(cores*4):
        index = slot*128
        output = 0x60000000 + slot*4096
        k['streams'].append({'context':slot%4, 'core':slot//4,
            'init':{'registers':{'rcx':body_addr+index*layout['body_bytes'], 'rdi':output}},
            'instructions':records})
        k['expected']['memory'].append({'addr':hex(output), 'file':'capture/expected.bin',
                                       'offset':index*24, 'length':24})
    k['unit_of_work'] = {'description':'one body per context, first body of distinct 128-body chunks; diagnostic only',
                         'count':cores*4}
    k['provenance']['s1_06'] = {'slice_bodies':128, 'bodies_per_context_executed':1,
                               'captured_step':'first force step, seed 670828913, large 20000, x86 1 thread'}
    (root/(scale+'.json')).write_text(json.dumps(k, indent=2)+'\n')
evidence = {'slice_bodies':128, 'bodies_per_context_executed':1,
            'requested_experiment_complete':False,
            'reason':'nbGravity region computes one body; no captured body-loop driver in this region. Loop sampling supports exactly one context. compare rejects different scales/profile hashes/work counts.',
            'capture_layout':layout, 'streams':{'core':4, 'unit':32, 'ring':32},
            'body_indices':[128*i for i in range(32)]}
(root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('Prepared 4/32/32 one-body diagnostics; NOT the requested 128-body/context slices')
