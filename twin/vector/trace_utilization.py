"""Count the compiled q!=NULL branch eight times per walk iteration."""
import json
from pathlib import Path
root=Path('twin/vector')
k=json.loads((root/'vector-0.json').read_text())
r=k['streams'][0]['instructions']
# Unique compiler idiom for active |= q[l] != NULL, then q[l] branch.
indices=[i for i in range(len(r)-3) if [x['op'] for x in r[i:i+4]]==['setne','or','test','jne']]
assert len(indices)==1
branch=r[indices[0]+3]['id']
result={}
for first in (0,1024,2048,4088):
    path=root/('vector-%d-functional/trace.json'%first)
    if not path.exists(): continue
    trace=json.loads(path.read_text())['0']
    flags=[row['taken'] for row in trace if row['id']==branch]
    assert len(flags)%8==0
    counts=[sum(flags[i:i+8]) for i in range(0,len(flags),8)]
    assert counts[-1]==0 and all(0<x<=8 for x in counts[:-1])
    counts.pop() # terminating empty iteration performs no arithmetic
    ranges=json.loads((root/'range.json').read_text())
    assert sum(counts)==sum(ranges['group_visits'][str(first)])
    result[str(first)]={'branch_id':branch,'iterations':len(counts),
        'active_lanes_per_iteration':counts,'mean_active_lanes':sum(counts)/len(counts),
        'lane_utilization':sum(counts)/(8*len(counts)),
        'functional_status':json.loads((path.parent/'result.json').read_text())['status'],
        'scope':'observed q!=NULL lane occupancy from functional trace; this is not a timing measurement'}
(root/'lane-utilization.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if x!='active_lanes_per_iteration'} for k,v in result.items()},indent=2))
