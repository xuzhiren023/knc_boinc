"""Read-only engine instrumentation: byte provenance and first fildl divergence.

No model files are modified. --trace envelopes are from the unchanged CLI.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.dont_write_bytecode=True
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
HOME=Path(os.environ.get('TWIN_HOME','C:/Users/xuzhi/.claude/skills/knc-twin'))
sys.path.insert(0,str(HOME/'scripts'))
from knc_model.kernel import load_kernel
from knc_model.functional import Interpreter, encode_values, load_input_file, run_functional
from knc_model.elf import Elf
from knc_model import fp

class Audit(Interpreter):
    def __init__(self,kernel,elf):
        super().__init__(kernel)
        self.reads=[]; self.origins={}; self.initial_ranges=[]; self.current='entry sentinel'; self.divergence=None
        self.snapshots=[]
        for idx,blk in enumerate(kernel.init.get('memory',[])):
            data=load_input_file(blk,kernel.dir,'audit')[0] if 'file' in blk else encode_values(blk,'audit')
            addr=int(str(blk['addr']),0)
            origin='init.memory[%d] %s'%(idx,blk.get('comment',blk.get('file','')))
            self.initial_ranges.append((addr,addr+len(data),origin))
        read,write=self.memory.read,self.memory.write
        def checked_read(addr,n,ctx=None):
            origins=[self.origins.get(a, next((o for lo,hi,o in reversed(self.initial_ranges) if lo<=a<hi),'UNINITIALIZED BYTE')) for a in range(addr,addr+n)]
            data=read(addr,n,ctx)
            section=elf.section_of_addr(addr)
            raw=elf.read_addr(addr,n) if section else None
            self.reads.append({'instruction':self.current,'addr':hex(addr),'bytes':n,'hex':data.hex(),
                'sources':list(dict.fromkeys(origins)), 'section':section.name if section else None,
                'matches_ELF':raw==data if raw is not None else None})
            if 'UNINITIALIZED BYTE' in origins: raise AssertionError(self.reads[-1])
            if section and section.name=='.rodata' and raw!=data: raise AssertionError(self.reads[-1])
            return data
        def checked_write(addr,data,ctx=None):
            write(addr,data,ctx)
            self.origins.update((addr+i,'store by '+self.current) for i in range(len(data)))
        self.memory.read=checked_read;self.memory.write=checked_write
    def execute(self,cx,insn,stream,trace,seq):
        self.current=insn.id
        before=cx.snapshot()
        start=len(self.reads)
        result=super().execute(cx,insn,stream,trace,seq)
        after=cx.snapshot()
        self.snapshots.append({'step':seq,'id':insn.id,'op':insn.op,'operands':str(insn.operands),'after':after})
        if insn.op=='fildl' and self.divergence is None:
            r=self.reads[start];low=int.from_bytes(bytes.fromhex(r['hex'])[:4],'little',signed=True)
            got=after['x87'][0]['f64']
            if float(got)!=low:
                self.divergence={'step':seq,'id':insn.id,'op':insn.op,'bytes_read':r,
                    'hand_expected_integer':low,'twin_value':got,'before':before,'after':after}
        return result

def main():
    source=json.loads(Path('twin/log-kernel.json').read_text())
    elf=Elf('build/card/milkyway_nbody.mic')
    rows=[line.split() for line in Path('runs/probe/x86.txt').read_text().splitlines()]
    selected=[r for r in rows if r[1]=='log_rn' and (r[0].startswith('fixed-') or r[0]=='captured' or r[0] in ['seed-%03d'%i for i in range(8)])]
    out=Path('twin/log-cases');out.mkdir(exist_ok=True)
    all_reads=[];cases=[];first=None
    for ident,fn,x,y,want in selected:
        k=copy.deepcopy(source)
        k['init']['registers']['zmm0']={'u64':['0x'+x]+[0]*7}
        k['expected']['registers']['0']['zmm0']={'u64':['0x'+want]}
        # File paths in these kernels are relative to log-cases.
        for blk in k['init']['memory']:
            if 'file' in blk: blk['file']='../'+blk['file']
        path=out/(ident+'.json');path.write_text(json.dumps(k)+'\n')
        result_dir=out/ident
        cmd=[sys.executable,str(HOME/'scripts/knc_twin.py'),'functional',str(path),'--trace','--out',str(result_dir),'--force']
        run=subprocess.run(cmd,capture_output=True,text=True)
        (result_dir/'command.log').write_text(run.stdout+run.stderr)
        result=json.loads((result_dir/'result.json').read_text())
        audit=Audit(load_kernel(str(path)),elf)
        try:
            audit.run()
            all_reads.extend(dict(case=ident,**r) for r in audit.reads)
        except Exception as exc:
            cases.append({'case':ident,'input_bits':x,'status':result['status'],'audit_error':str(exc)})
            raise
        if ident=='fixed-0':
            first=audit.divergence
            (out/'log-one-intermediates.json').write_text(json.dumps(audit.snapshots,indent=2)+'\n')
        cases.append({'case':ident,'input_bits':x,'expected_bits':want,'status':result['status'],
                      'functional_check':result.get('functional_check'),'dynamic_instructions':audit.steps})
        # Keep large auto-extracted kernels local; envelopes and trace are evidence.
        # Retain the generated kernel locally so each envelope input path is reviewable.
    minimal={key:copy.deepcopy(source[key]) for key in ('schema','entry','numerical_policy') if key in source}
    minimal.update({'name':'fildl reads 64 bits instead of 32','init':{'memory':[{'addr':'0x1000','hex':'000000000000f03f'}]},
        'expected':{'registers':{'0':{'zmm0':{'u64':['0x0']}}}},
        'streams':[{'context':0,'instructions':[
            {'id':'load','op':'fildl','ops':[{'base':'rax','disp':4096}]},
            {'id':'store','op':'fstpl','ops':[{'base':'rax','disp':8192}]},
            {'id':'return_value','op':'vbroadcastsd','ops':['zmm0',{'base':'rax','disp':8192}]},
            {'id':'return','op':'ret','ops':[]}]}]})
    p=Path('twin/fildl-repro.json');p.write_text(json.dumps(minimal,indent=2)+'\n')
    subprocess.run([sys.executable,str(HOME/'scripts/knc_twin.py'),'functional',str(p),'--trace','--out','twin/fildl-repro','--force'],check=False)
    assert json.loads(Path('twin/fildl-repro/result.json').read_text())['status']=='functional_mismatch'
    diagnostic=load_kernel('twin/log-kernel.json')
    for stream in diagnostic.streams:
        for insn in stream.insns:
            if insn.op=='fildl':
                insn.spec=dict(insn.spec)
                insn.spec['mem_size']=4
    interp,steps,check=run_functional(diagnostic)
    Path('twin/fildl-width-diagnostic.json').write_text(json.dumps({
        'kind':'local diagnostic only; copied per-instruction spec, no shared-engine edits; no timing claim',
        'change':'fildl mem_size 8 -> 4','functional_check':check,'steps':steps},indent=2)+chr(10))
    assert check['status']=='ok'
    evidence={'verdict':'Twin ISA defect: fildl reads 8 bytes, but opcode DB /0 loads a signed 32-bit integer. Tables are present and match ELF; no uninitialized read bytes on audited paths.',
        'binary_sha256':hashlib.sha256(Path('build/card/milkyway_nbody.mic').read_bytes()).hexdigest(),
        'engine_isa_sha256':hashlib.sha256((HOME/'scripts/knc_model/isa.py').read_bytes()).hexdigest(),
        'first_divergence':first,'cases':cases,'memory_reads':all_reads}
    Path('twin/log-diagnosis.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(evidence['verdict']);print(json.dumps(first,indent=2))
if __name__=='__main__':main()
