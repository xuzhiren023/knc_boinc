"""Attach independent real-source replay and exact midpoint evidence."""
from fractions import Fraction
import json
from pathlib import Path
import re
import struct
import os
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(os.environ.get("TWIN_HOME","C:/Users/xuzhi/.claude/skills/knc-twin"))/"scripts"))
from knc_model import fp
root=Path('twin/multicore')
evidence=json.loads((root/'isolation.json').read_text())
rows=re.findall(r'x87 body (\d+): ([0-9a-f]{16}) ([0-9a-f]{16}) ([0-9a-f]{16})',
                Path('build/s1-07-x87.log').read_text())
assert [int(row[0]) for row in rows]==evidence['body_indices']
expected=(root/'capture/expected.bin').read_bytes()
for body,*bits in rows:
    want=['%016x'%v for v in struct.unpack_from('<QQQ',expected,int(body)*24)]
    assert bits==want, (body,bits,want)
evidence['source_replay']={'flags':'same COMMON_CFLAGS plus -mfpmath=387',
    'control_word':'0x027f','matched_components':18,
    'body_results':{body:bits for body,*bits in rows}}
first=evidence['first_operation']
def rational(bits):
    return Fraction(struct.unpack('>d',bytes.fromhex(bits))[0])
a,b,got,want=[rational(first[key]) for key in ('a','b','twin','native')]
assert first['op']=='mul'
exact=a*b
assert abs(exact-want)<abs(exact-got)
rounded64=fp.round_exact(exact,fp.F80,fp.Policy('rn'))[0]
assert fp.classify(rounded64,fp.F80)[2] == (got+want)/2
evidence['rounding_proof']={'exact_product_minus_binary64_midpoint':str(exact-(got+want)/2),
    'native_result_is_closer':True,
    'F80_rounding_lands_on_binary64_midpoint':True,
    'cause':'_x87_binop rounds to F80 (64 bits) then converts to F80_P53; double rounding is not innocuous'}
(root/'isolation.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('Real-source -mfpmath=387 PC53 replay: all 18 components match SSE exactly')
print('First operation: '+json.dumps(first,sort_keys=True))
print('Exact product minus midpoint: '+evidence['rounding_proof']['exact_product_minus_binary64_midpoint'])
