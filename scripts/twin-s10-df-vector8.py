"""Audit real compiled nodes and their callees, then execute supported kernels.

No unsupported call receives a fabricated functional model or timing cost.
The report retains failures as results rather than inventing a forecast.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
import struct
import subprocess
import time
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/df-vector8'
SKILL = Path('C:/Users/xuzhi/.claude/skills/knc-twin')
SHARED = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
MODE = sys.argv[1] if len(sys.argv)>1 else 'vector8'
assert MODE in ['vector8','scalar']
SUFFIX = '-scalar' if MODE=='scalar' else ''
OUT = B / ('twin-nodes'+SUFFIX)
OUT.mkdir(exist_ok=True)
commands = []

def save(p, data):
    p.write_text(json.dumps(data, indent=2) + '\n')

def run(args, label):
    t = time.monotonic()
    with (OUT / (label + '.txt')).open('w') as log:
        p = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
    commands.append(dict(command=args, exit_code=p.returncode, host_seconds=time.monotonic()-t))
    save(OUT / 'commands.json', commands)
    return p.returncode

def ordered(bits):
    return (~bits & ((1 << 64)-1)) if bits >> 63 else bits | (1 << 63)

capture_file=B/('twin-node-inputs'+SUFFIX+'.bin')
if not capture_file.exists():
    shutil.copyfile(ROOT/('runs/s10-df-vector8/core-small-'+MODE+'/node-inputs.bin'),capture_file)
raw = capture_file.read_bytes()
version, dwarf_size = struct.unpack_from('<II', raw)
assert version == 1 and dwarf_size == 240
width = 24 + 2*dwarf_size + 192
captures, lane_rows = [], []
for rec, off in enumerate(range(8, len(raw), width)):
    n = struct.unpack_from('<Q', raw, off)[0]
    a = raw[off+8:off+8+dwarf_size]
    b = raw[off+8+dwarf_size:off+8+2*dwarf_size]
    energy, dark = struct.unpack_from('<dQ', raw, off+8+2*dwarf_size)
    start = off+24+2*dwarf_size
    x, fast, exact = (raw[start+k*64:start+(k+1)*64] for k in range(3))
    captures.append(dict(n=n, a=a, b=b, energy=energy, dark=dark, x=x, fast=fast, exact=exact))
    for i in range(n):
        f, e = struct.unpack_from('<Q', fast, 8*i)[0], struct.unpack_from('<Q', exact, 8*i)[0]
        lane_rows.append(dict(record=rec, lane=i, dark=dark, fast_hex=hex(f), exact_hex=hex(e),
                              ulp_difference=abs(ordered(f)-ordered(e)), bitwise_equal=f == e))
save(B / ('captured-node-differences'+SUFFIX+'.json'), dict(records=len(captures), lanes=len(lane_rows),
     source_sha256=hashlib.sha256(raw).hexdigest(), source=capture_file.relative_to(ROOT).as_posix(), host_comparison=True,
     differing_lanes=sum(not r['bitwise_equal'] for r in lane_rows),
     max_ulp=max(r['ulp_difference'] for r in lane_rows), lanes_detail=lane_rows))

binary = B / ('card-'+MODE+'/twin-kernel.mic')
dis = OUT / 'diagnostic.dis'
with dis.open('w') as f:
    subprocess.run([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'), '-dr', str(binary)], stdout=f, check=True)
text = dis.read_text()
functions = {}
matches = list(re.finditer(r'^([0-9a-f]+) <([^>]+)>:\s*$', text, re.M))
for i, m in enumerate(matches):
    functions[m[2]] = text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]

def closure(name):
    todo, seen = [name], set()
    while todo:
        f = todo.pop()
        if f in seen or f not in functions or '@plt' in f: continue
        seen.add(f)
        for target in re.findall(r'\b(?:callq?|jmpq?)\s+[^\n]*<([^>]+)>', functions[f]):
            target = target.split('+')[0]
            if target != f: todo.append(target)
    return sorted(seen - {name})

# KNC Dwarf has the same field offsets as the host; GCC's maximum aggregate
# alignment may add tail padding. A diagnostic ELF object records its layout.
nm = subprocess.check_output([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-nm.exe'), '-S', str(binary)], text=True)
symbol = re.search(r'^([0-9a-f]+)\s+([0-9a-f]+)\s+\w\s+df8_twin_layout$', nm, re.M)
assert symbol
addr = int(symbol[1], 16)
sections = subprocess.check_output([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'), '-h', str(binary)], text=True)
elf = binary.read_bytes()
for m in re.finditer(r'^\s*\d+\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)', sections, re.M):
    size, vma, offset = (int(m[i], 16) for i in [1,2,3])
    if vma <= addr < vma+size:
        layout = struct.unpack_from('<4Q', elf, offset+addr-vma)
        break
else:
    raise AssertionError('layout section not found')
assert layout[1:] == (8, 16, 224), layout
card_dwarf_size = layout[0]
save(OUT / 'layout.json', dict(host_dwarf_size=dwarf_size, card_dwarf_size=card_dwarf_size,
                              offsets=list(layout[1:]), tail_padding_only=True))

def init_spec(indices, expected_kind):
    memory, expected, streams = [], [], []
    for context in range(4):
        calls = []
        for seq, index in enumerate(indices[context::4]):
            r = captures[index]
            base = 0x10000000 + context*0x100000 + seq*0x1000
            def block(offset, data):
                memory.append(dict(addr=hex(base+offset), hex=data.hex()))
            block(0, r['x'])
            block(128, r['a'] + bytes(card_dwarf_size-dwarf_size))
            block(512, r['b'] + bytes(card_dwarf_size-dwarf_size))
            block(896, struct.pack('<dQQ', r['energy'], r['n'], r['dark']))
            block(1024, bytes(64))
            expected.append(dict(addr=hex(base+1024), hex=r[expected_kind][:8*r['n']].hex()))
            calls.append(dict(registers=dict(rdi=hex(base), rsi=hex(base+128), rdx=hex(base+512),
                                            rcx=hex(base+896), r8=hex(base+1024))))
        streams.append(dict(context=context, calls_table=calls))
    return dict(init=dict(memory=memory), expected=dict(memory=expected), streams=streams,
                unit_of_work=dict(description='one quadrature node', count=sum(captures[i]['n'] for i in indices)),
                numerical_policy=dict(rounding='rn', ftz=False, daz=False, nan_compare='any_nan', x87_control_word='0x027f'),
                scenario=dict(memory=dict(type='fixed_level', level='l1'), branch=dict(type='all_predicted')))

summary = dict(mode=MODE,captured_records=len(captures), captured_lanes=len(lane_rows),
               host_fast_vs_exact_differing_lanes=sum(not r['bitwise_equal'] for r in lane_rows),
               host_fast_vs_exact_max_ulp=max(r['ulp_difference'] for r in lane_rows),
               model_table_used=False, entries={}, callees={})
selected = ([i for i,r in enumerate(captures) if not r['dark']][:2] +
            [i for i,r in enumerate(captures) if r['dark']][:2])
summary['selected_real_records'] = selected
summary['selected_lanes'] = sum(captures[i]['n'] for i in selected)
for variant, entry, expected_kind in [('scalar','df8_twin_scalar','exact'), ('vector8','df8_twin_vector','fast')]:
    folder = OUT / variant
    folder.mkdir(exist_ok=True)
    spec = init_spec(selected, expected_kind)
    save(folder/'init.json', spec)
    args = ['python', str(SKILL/'scripts/from_binary.py'), str(binary), '--function', entry,
            '--disassembly', str(dis), '--init', str(folder/'init.json'),
            '--out', str(folder/'kernel.json'), '--report', str(folder/'adapter.json')]
    for callee in closure(entry): args += ['--with-callee', callee]
    code = run(args, variant+'-adapter')
    adapter = json.loads((folder/'adapter.json').read_text())
    summary['entries'][variant] = dict(adapter_exit=code, adapter_status='ok' if code==0 else 'unsupported',
                                      unsupported=adapter.get('unsupported', []), callees=closure(entry))
    if code == 0:
        # Adapter merges instruction records with the explicit four-context
        # argument tables. Preserve its binary/data provenance and layout.
        kernel = json.loads((folder/'kernel.json').read_text())
        kernel.pop('memory_default', None)
        kernel['init']['registers']={'fcw':'0x027f'}
        original = kernel['streams'][0]['instructions']
        kernel['streams'] = [dict(s, instructions=copy.deepcopy(original)) for s in spec['streams']]
        for k in ['unit_of_work','numerical_policy','scenario','expected']:
            kernel[k] = spec[k]
        save(folder/'kernel.json', kernel)
        for command in ['functional','simulate']:
            extra = ['--profile','card-7120-measured','--contexts','0,1,2,3','--no-issue-log'] if command=='simulate' else []
            run(['python',str(SKILL/'scripts/knc_twin.py'),command,str(folder/'kernel.json'),
                 '--out',str(folder/command),'--force','--max-steps','2000000','--max-seconds','55']+extra, variant+'-'+command)
            result=json.loads((folder/command/'result.json').read_text())
            summary['entries'][variant][command]={k:result.get(k) for k in
                ['status','result_class','assumptions','unsupported','limiting_constraints','calibration_status',
                 'parameters_used','prediction','message','functional_check']}
    else:
        # Cut unsupported callees at their real entry boundaries and audit each
        # target independently; never substitute invented call-cycle costs.
        for callee in closure(entry):
            if callee in summary['callees']: continue
            slug=re.sub(r'[^a-zA-Z0-9_-]', '_', callee)
            target=OUT/('callee-'+slug); target.mkdir(exist_ok=True)
            code=run(['python',str(SKILL/'scripts/from_binary.py'),str(binary),'--function',callee,
                '--disassembly',str(dis),'--out',str(target/'kernel.json'),'--report',str(target/'adapter.json')], 'callee-'+slug)
            report=json.loads((target/'adapter.json').read_text())
            summary['callees'][callee]=dict(adapter_exit=code, status=report.get('status'), unsupported=report.get('unsupported',[]))
        # Retry the real vector entry, cutting at unsupported call targets as
        # requested by the lead. Unknown targets remain undeclared, so the
        # interpreter stops if it reaches one; no default cost or result.
        if variant == 'vector8':
            cut=folder/'cut'; cut.mkdir(exist_ok=True)
            args=['python',str(SKILL/'scripts/from_binary.py'),str(binary),'--function',entry,
                  '--disassembly',str(dis),'--init',str(folder/'init.json'),
                  '--out',str(cut/'kernel.json'),'--report',str(cut/'adapter.json')]
            for callee in closure(entry):
                if summary['callees'][callee]['adapter_exit']==0:
                    args += ['--with-callee',callee]
            cut_code=run(args,variant+'-cut-adapter')
            summary['entries'][variant]['cut_adapter_exit']=cut_code
            if cut_code==0:
                kernel=json.loads((cut/'kernel.json').read_text())
                kernel.pop('memory_default',None)
                kernel['init']['registers']={'fcw':'0x027f'}
                original=kernel['streams'][0]['instructions']
                kernel['streams']=[dict(s,instructions=copy.deepcopy(original)) for s in spec['streams']]
                for k in ['unit_of_work','numerical_policy','scenario','expected']:kernel[k]=spec[k]
                save(cut/'kernel.json',kernel)
                for command in ['functional','simulate']:
                    extra=['--profile','card-7120-measured','--contexts','0,1,2,3','--no-issue-log'] if command=='simulate' else []
                    run(['python',str(SKILL/'scripts/knc_twin.py'),command,str(cut/'kernel.json'),
                         '--out',str(cut/command),'--force','--max-steps','2000000','--max-seconds','55']+extra,variant+'-cut-'+command)
                    result=json.loads((cut/command/'result.json').read_text())
                    summary['entries'][variant]['cut_'+command]={k:result.get(k) for k in
                        ['status','result_class','assumptions','unsupported','limiting_constraints','calibration_status',
                         'parameters_used','prediction','message','functional_check']}
summary['commands']=commands
summary['host_seconds']=sum(c['host_seconds'] for c in commands)
summary['cycles_per_node']={v:None for v in ['scalar','vector8']}
for variant, entry in summary['entries'].items():
    result=entry.get('simulate', {})
    if result.get('status') == 'ok':
        # Keep the model's own per-unit fields alongside the complete raw result.
        summary['cycles_per_node'][variant]=result.get('prediction')
summary['predicted_ratio']=None
save(B/('twin-node-results'+SUFFIX+'.json'),summary)
print(json.dumps({k:v for k,v in summary.items() if k not in ['commands','callees','entries']},indent=2))
