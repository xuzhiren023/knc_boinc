"""Bind the scalar ABI register to bytes captured from the real small run."""
import json, struct
from pathlib import Path
root = Path('twin')
x = struct.unpack('<Q',(root/'capture/log-input.bin').read_bytes())[0]
y = struct.unpack('<Q',(root/'capture/log-expected.bin').read_bytes())[0]
cw = struct.unpack('<H',(root/'capture/host-fcw.bin').read_bytes())[0]
# Scalar K1OM floating-point ABI: low f64 of zmm0; other lanes are inactive.
overlay = {
 'init': {'registers': {'zmm0': {'u64': [hex(x)]+[0]*7}},
          'memory': [{'addr':'0x60000000','file':'capture/log-input.bin'}]},
 'expected': {'registers': {'0': {'zmm0': {'u64':[hex(y)]}}}},
 'unit_of_work': {'description':'one log_rn call, first real small input','count':1},
 'numerical_policy': {'rounding':'rn','ftz':False,'daz':False,'x87_control_word':hex(cw)},
 'scenario': {'memory': {'type':'line_tracking','cold_level':'memory'},'branch':{'type':'all_predicted'}}
}
(root/'log-capture.json').write_text(json.dumps(overlay,indent=2)+'\n')
print('Captured host x87 control word:',hex(cw))
