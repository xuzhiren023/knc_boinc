"""Count actual source-level tree lines in matched target chunks before tuning.

The pinned S10-02 capture is a host counter input, not a simulated stand-in.
Lines cover fields nbGravity reads, excluding stack/caller/instructions.
"""
import bisect
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
B = ROOT/'build/s10-memory'
SOURCE = ROOT.parent/'S10-02/build/s10-walk'
sys.path.insert(0, str(ROOT/'scripts'))
from twin_s10_memory_common import load_tree, walk, spatial_order

def main():
    B.mkdir(exist_ok=True, parents=True)
    for suffix in ('.json', '.bin', '-provenance.json'):
        shutil.copyfile(SOURCE/('capture-base'+suffix), B/('model-capture'+suffix))
    shutil.copyfile(SOURCE/'layout-card-0.s', B/'model-layout.s')
    raw, data, layout, get = load_tree(B/'model-capture', B/'model-layout.s')
    chosen = set(range(0, raw['nbody'], max(1,raw['nbody']//1024)))
    orders = {'random':sorted(chosen), 'spatial':[i for i in spatial_order(raw,layout,get) if i in chosen]}
    rows = {}
    start = time.monotonic()
    sets = {}
    nodes = {}
    for i in chosen:
        _, count, lines = walk(raw,layout,get,i)
        sets[i] = lines
        nodes[i] = count
    for name, order in orders.items():
        chunks = [order[i:i+16] for i in range(0,len(order)-15,16)]
        chunks4 = [order[i:i+4] for i in range(0,len(order)-3,4)]
        union = lambda c:set().union(*(sets[i] for i in c))
        rows[name] = dict(targets=sorted(order),sequence=order,nbody=raw['nbody'],
            lines_per_body=sum(len(sets[i]) for i in order)/len(order),
            nodes_per_body=sum(nodes[i] for i in order)/len(order),
            lines_per_thread_chunk=sum(len(union(c)) for c in chunks4)/len(chunks4),
            lines_per_core_chunk=sum(len(union(c)) for c in chunks)/len(chunks),
            pages4k_per_core_chunk=sum(len({x//64 for x in union(c)}) for c in chunks)/len(chunks),
            pages2m_per_core_chunk=sum(len({x//32768 for x in union(c)}) for c in chunks)/len(chunks),
            core_chunk_bodies=16,thread_chunk_bodies=4,complete_core_chunks=len(chunks))
    value=dict(orders=rows,snapshot_sha256=hashlib.sha256(data).hexdigest(),
        source=str(SOURCE),counter_host_seconds=time.monotonic()-start,
        scope='Initial real large tree; matched evenly sampled generation indices, then DFS sorted. Source field lines, 64 B; no stack or code. Virtual addresses retain host allocation fragmentation.',
        scenario='4 contexts/core; four consecutive bodies/context, 16/core; chunks are independent cold sets, not an LRU timing model.')
    (B/'model.json').write_text(json.dumps(value,indent=2)+'\n')
    for name, row in rows.items():
        print(name,{k:v for k,v in row.items() if k not in ('targets','sequence')},flush=True)
if __name__ == '__main__': main()
