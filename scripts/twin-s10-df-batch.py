"""Faithful vector worker audit and four-context runs, with unsupported calls cut.

The 1/2/4-integral experiments share the same compiled worker and model. A
blocked call never receives invented output or cost. No partial cycle result
is promoted to a prediction.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10/df-batch'
OUT=B/'twin';OUT.mkdir(parents=True,exist_ok=True)
SKILL=Path('C:/Users/xuzhi/.claude/skills/knc-twin')
SHARED=Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
commands=[]
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(args,label):
    t=time.monotonic()
    with (OUT/(label+'.txt')).open('w') as f:
        p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    commands.append(dict(command=[str(a) for a in args],exit_code=p.returncode,host_seconds=time.monotonic()-t))
    save(OUT/'commands.json',commands)
    return p.returncode
run(['python',str(SKILL/'scripts/knc_twin.py'),'capabilities','--out',str(OUT/'capabilities'),'--force'],'capabilities')
capabilities=json.loads((OUT/'capabilities/capabilities.json').read_text())
assert 'simulate' in capabilities['commands'] and 'functional' in capabilities['commands']
print('Inspected knc-twin capabilities, engine '+capabilities['engine_version'],flush=True)
# These are real nodes of the identical pinned workunit/model/seed, captured
# before this ticket. Retain their original provenance, not generated inputs.
source=ROOT.parent/'S10-09/runs/s10-df-vector8/core-small-scalar/node-inputs.bin'
shutil.copyfile(source,OUT/'node-inputs.bin')
raw=(OUT/'node-inputs.bin').read_bytes();version,size=struct.unpack_from('<II',raw);assert (version,size)==(1,240)
width=24+2*size+192
captures=[]
for off in range(8,len(raw),width):
    n=struct.unpack_from('<Q',raw,off)[0];e,dark=struct.unpack_from('<dQ',raw,off+8+2*size)
    start=off+24+2*size
    captures.append(dict(n=n,a=raw[off+8:off+8+size],b=raw[off+8+size:off+8+2*size],energy=e,dark=dark,x=raw[start:start+64],out=raw[start+64:start+128]))
binary=B/'card-batch/twin-kernel.mic';dis=OUT/'worker.dis'
with dis.open('w') as f:subprocess.run([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'),'-dr',str(binary)],stdout=f,check=True)
text=dis.read_text();functions={};matches=list(re.finditer(r'^([0-9a-f]+) <([^>]+)>:\s*$',text,re.M))
for i,m in enumerate(matches):functions[m[2]]=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
def closure(entry):
    todo=[entry];seen=set()
    while todo:
        f=todo.pop()
        if f in seen or f not in functions or '@plt' in f:continue
        seen.add(f)
        todo.extend(t.split('+')[0] for t in re.findall(r'\b(?:callq?|jmpq?)\s+[^\n]*<([^>]+)>',functions[f]))
    return sorted(seen-{entry})
entry='df8_twin_vector';callees=closure(entry)
# Verify actual KNC Dwarf layout before padding the host captures.
nm=subprocess.check_output([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-nm.exe'),'-S',str(binary)],text=True)
symbol=re.search(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+\w\s+df8_twin_layout$',nm,re.M);addr=int(symbol[1],16)
sections=subprocess.check_output([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'),'-h',str(binary)],text=True)
elf=binary.read_bytes()
for m in re.finditer(r'^\s*\d+\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)',sections,re.M):
    count,vma,offset=[int(m[i],16) for i in [1,2,3]]
    if vma<=addr<vma+count:layout=struct.unpack_from('<4Q',elf,offset+addr-vma);break
assert layout[1:]==(8,16,224)
# The requested cut is at real vmath/crlibm calls. Audit the caller and every
# local d8 helper separately, retaining the actual unsupported mnemonic.
local=[f for f in callees if f.startswith(('d8_','df8_nodes'))]
full=OUT/'full';full.mkdir(exist_ok=True)
base=['python',str(SKILL/'scripts/from_binary.py'),str(binary),'--function',entry,'--disassembly',str(dis)]
run(base+sum((['--with-callee',c] for c in callees),[])+['--out',str(full/'kernel.json'),'--report',str(full/'adapter.json')],'full-adapter')
cut=OUT/'cut';cut.mkdir(exist_ok=True)
code=run(base+sum((['--with-callee',c] for c in local),[])+['--out',str(cut/'kernel.json'),'--report',str(cut/'adapter.json')],'cut-adapter')
summary=dict(profile='card-7120-measured',contexts=4,model_table_used=False,
    engine_version=capabilities['engine_version'],
    source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),binary_sha256=hashlib.sha256(elf).hexdigest(),
    card_dwarf_layout=list(layout),full_adapter=json.loads((full/'adapter.json').read_text()),
    cut_adapter=json.loads((cut/'adapter.json').read_text()),independent_integrals={})
for integrals in [1,2,4]:
    folder=OUT/('integrals-'+str(integrals));folder.mkdir(exist_ok=True)
    row=dict(status='blocked',cycles_per_node=None,issue_occupancy_constraint=None)
    if code==0:
        kernel=json.loads((cut/'kernel.json').read_text());instructions=kernel['streams'][0]['instructions']
        memory=[];expected=[];streams=[];nodes=0
        # Four actual contexts. One integral is shared by four contexts,
        # two integrals by pairs, four by single contexts. Each retained block
        # is a real capture; no new floating inputs or call outputs are invented.
        for context in range(4):
            group=context//(4//integrals);calls=[]
            for seq in range(2*integrals):
                rec=captures[(group*8+seq*4+context)%len(captures)]
                origin=0x10000000+context*0x100000+seq*0x1000
                def block(offset,data):memory.append(dict(addr=hex(origin+offset),hex=data.hex()))
                block(0,rec['x']);block(128,rec['a']+bytes(layout[0]-size));block(512,rec['b']+bytes(layout[0]-size))
                block(896,struct.pack('<dQQ',rec['energy'],rec['n'],rec['dark']));block(1024,bytes(64))
                expected.append(dict(addr=hex(origin+1024),hex=rec['out'][:8*rec['n']].hex()));nodes+=rec['n']
                calls.append(dict(registers=dict(rdi=hex(origin),rsi=hex(origin+128),rdx=hex(origin+512),rcx=hex(origin+896),r8=hex(origin+1024))))
            streams.append(dict(context=context,calls_table=calls,instructions=copy.deepcopy(instructions)))
        kernel.pop('memory_default',None)
        # Keep the adapter's ELF .rodata/.data and register initialization.
        # Captured arguments supplement those sections; they do not replace them.
        kernel['init'].setdefault('memory',[]).extend(memory)
        # Function argument registers come from calls_table. The adapter's
        # placeholder integer zeros for vector registers are not engine inputs.
        kernel['init']['registers']=dict(fcw='0x027f')
        kernel['expected']=dict(memory=expected);kernel['streams']=streams
        kernel['unit_of_work']=dict(description='one quadrature node',count=nodes)
        kernel['numerical_policy']=dict(rounding='rn',ftz=False,daz=False,nan_compare='any_nan',x87_control_word='0x027f')
        kernel['scenario']=dict(memory=dict(type='fixed_level',level='l1'),branch=dict(type='all_predicted'))
        save(folder/'kernel.json',kernel)
        for command in ['functional','simulate']:
            extra=['--profile','card-7120-measured','--contexts','0,1,2,3','--no-issue-log'] if command=='simulate' else []
            run(['python',str(SKILL/'scripts/knc_twin.py'),command,str(folder/'kernel.json'),'--out',str(folder/command),'--force','--max-steps','2000000','--max-seconds','45']+extra,'integrals-'+str(integrals)+'-'+command)
            result=json.loads((folder/command/'result.json').read_text())
            row[command]={k:result.get(k) for k in ['status','result_class','assumptions','unsupported','limiting_constraints','calibration_status','parameters_used','prediction','message']}
        row['status']=row['simulate']['status']
        row['issue_occupancy_constraint']=row['simulate']['limiting_constraints']
        if row['status']=='ok':row['cycles_per_node']=row['simulate']['prediction']
    else:row['unsupported']=summary['cut_adapter'].get('unsupported')
    summary['independent_integrals'][str(integrals)]=row
previous=B/'twin-invalid-input.json'
prior=json.loads(previous.read_text())['commands'] if previous.exists() else []
summary['commands']=prior+commands
summary['initial_input_retry']=str(previous) if previous.exists() else None
summary['host_seconds']=sum(c['host_seconds'] for c in summary['commands'])
save(B/'twin-results.json',summary)
print(json.dumps(dict(host_seconds=summary['host_seconds'],model_table_used=False,
    independent_integrals={k:dict(status=v['status'],cycles_per_node=v['cycles_per_node'],
        message=v.get('simulate',{}).get('message')) for k,v in summary['independent_integrals'].items()}),indent=2))
