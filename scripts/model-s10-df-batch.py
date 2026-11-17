"""Explicit working-set/occupancy calculation, not a twin cycle prediction."""
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10/df-batch'
def ceildiv(a,b):return (a+b-1)//b
rows=[]
for integrals in [6,8,12]:
    blocks=42
    minimum_cores=60//integrals
    blocks_per_core=ceildiv(blocks,minimum_cores)
    # One extra interval at each end of a vector-block shard, cache-line rounded.
    node_bytes=ceildiv((ceildiv(blocks_per_core*8,3)+2)*56,64)*64
    rows.append(dict(integrals=integrals,vector_blocks_per_integral=blocks,logical_vectors=blocks*integrals,
        minimum_cores_per_integral=minimum_cores,max_vector_blocks_per_core=blocks_per_core,
        node_bytes_per_core=node_bytes,active_contexts_upper_bound=min(240,blocks*integrals)))
# Read actual KNC frames for the node worker and its local arithmetic helpers.
# The model budgets one hot arithmetic chain per context; it is not a bound
# on linked crlibm/vmath callee stacks or the root-preparation working set.
frames={}
p=B/'card-batch/generator.su'
if p.exists():
    for line in p.read_text().splitlines():
        cols=line.split('\t')
        if len(cols)>=2:frames[cols[0].split(':')[-1]]=int(cols[1])
node_stack=frames.get('df8_nodes',0)
helpers=sum(value for name,value in frames.items() if name.startswith('d8_'))
worker=max([value for name,value in frames.items() if name.startswith('dfb_evaluate._omp_fn')]+[0])
stack_budget=4*(node_stack+helpers+worker+256)
model=dict(classification='working-set arithmetic; conditional L1 residency, no timing forecast',
    assumptions=['~330 nodes / 42 vector blocks per integral, 60 cores, four compact siblings per core',
        '56-byte QuadInterval; cache-line-rounded contiguous node shards',
        'Two read-only Dwarf models budgeted as 512 bytes; 512 bytes shared batch metadata',
        'Local node/helper stack frames from GCC -fstack-usage plus 256 bytes scratch per context',
        'Linked crlibm/vmath stacks, root preparation, code footprint and conflict misses are excluded; no guaranteed L1 residency'],
    rows=rows,node_bytes_per_core=max(r['node_bytes_per_core'] for r in rows),
    local_node_stack_bytes=node_stack,local_helper_stack_budget_bytes=helpers,local_worker_stack_bytes=worker,
    measured_local_frames=frames,local_stack_bytes_per_core=stack_budget,
    total_budget_bytes_per_core=max(r['node_bytes_per_core'] for r in rows)+512+512+stack_budget,
    per_core_l1_bytes=32768,per_core_l2_bytes=524288,
    total_node_allocation_bytes=12*128*56,
    attempt_choice=dict(first=4,tail=8,mean_attempts=2.56,
        geometric_survival_after_four=(1-1/2.56)**4,
        note='Mean alone does not determine the distribution; this is a geometric planning prior, actual counts in proof.json'),
    occupancy='6/8/12 integrals expose 252/336/504 vector blocks. 4 sibling contexts per core execute separate df8_nodes chains. This is potential work, not proof of simultaneous vector issue.')
(B/'working-set.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps({k:model[k] for k in ['node_bytes_per_core','local_stack_bytes_per_core','total_budget_bytes_per_core']},indent=2))
