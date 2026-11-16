"""S5-01: whole-binary gravity extraction, fixed-input checks and frozen batches.

Run from repo root after run_flags.sh builds the four linked variants. Never
changes the toolchain/model or selects inputs based on numerical outcomes.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
HOME = Path(os.environ.get('TWIN_HOME', 'C:/Users/xuzhi/.claude/skills/knc-twin'))
DUMP = os.environ.get('KNC_OBJDUMP', 'C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cross/bin/k1om-mpss-linux-objdump.exe')
ROOT = Path('twin/flags')
INPUTS = ['small', 'large-0', 'large-128', 'large-256', 'large-384']
FLAGS = {'V0':'-O2', 'V1':'-O3', 'V2':'-mphinix -ffp-contract=off', 'V3':'-O2 -funroll-loops'}
PROFILE = 'card-7120-measured'

def read(path):
    return json.loads(Path(path).read_text())

def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2)+'\n')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def command(args):
    print('$ '+' '.join(map(str,args)), flush=True)
    p = subprocess.run(list(map(str,args)))
    return p.returncode

def twin(cmd, kernel, out, *options):
    profile = [] if cmd == 'functional' else ['--profile', PROFILE]
    command([sys.executable, HOME/'scripts/knc_twin.py', cmd, kernel,
             *profile, '--out', out, '--force', *options])
    return read(out/'result.json')

def absolute_files(obj, parent):
    obj = copy.deepcopy(obj)
    for part in ('init', 'expected'):
        for block in obj.get(part, {}).get('memory', []):
            if 'file' in block:
                block['file'] = str((parent/block['file']).resolve())
    return obj

def summarize(result):
    keys = ['status','message','engine_version','profile','functional_check',
            'prediction','result_class','limiting_constraints','assumptions',
            'unsupported','calibration_status']
    out = {key:copy.deepcopy(result[key]) for key in keys if key in result}
    if out.get('prediction'):
        out['prediction'].pop('input_files', None)
    if out.get('profile'):
        out['profile'] = {key:out['profile'][key] for key in ['id','hash','version']}
    return out

def main():
    ROOT.mkdir(exist_ok=True)
    evidence = {'inputs': INPUTS, 'variants': [], 'batches': {}, 'native': [], 'model_metadata': {}}
    small = absolute_files(read('twin/capture.json'), Path('twin'))
    large = absolute_files(read('twin/multicore/capture.json'), Path('twin/multicore'))
    # Coalesce adjacent/overlapping captured bytes, checking overlap equality.
    # This changes only file packaging, preserving every address and byte.
    # Bounded blocks avoid rehashing a 4 MB tree for each individual node.
    cache, spans = {}, []
    for block in large['init']['memory']:
        if 'file' not in block:
            assert block.get('hex', '') == ''
            continue
        source = block['file']
        if source not in cache:
            cache[source] = Path(source).read_bytes()
        offset = block.get('offset', 0)
        data = cache[source][offset:offset+block.get('length', len(cache[source]))]
        spans.append((int(block['addr'], 16), data))
    merged = []
    for addr, data in sorted(spans, key=lambda x:x[0]):
        if merged and addr <= merged[-1][0]+len(merged[-1][1]):
            base, current = merged[-1]
            overlap = min(len(data), base+len(current)-addr)
            assert current[addr-base:addr-base+overlap] == data[:overlap]
            current.extend(data[overlap:])
        else:
            merged.append((addr, bytearray(data)))
    blocks = ROOT/'coalesced-inputs'
    blocks.mkdir(exist_ok=True)
    large['init']['memory'] = []
    for base, data in merged:
        for offset in range(0, len(data), 65536):
            target = blocks/('%x.bin'%(base+offset))
            target.write_bytes(data[offset:offset+65536])
            large['init']['memory'].append({'addr':hex(base+offset), 'file':str(target.resolve())})
    print('Large capture: %d records coalesced to %d byte-identical bounded file blocks' %
          (len(spans), len(large['init']['memory'])), flush=True)
    overlays = {'small':small}
    for index in [0,128,256,384]:
        c = copy.deepcopy(large)
        c.pop('capture_layout', None)
        c['init']['registers']['rcx'] = hex(int(large['init']['registers']['rcx'],16) + index*128)
        c['expected']['memory'][0].update(offset=index*24, length=24)
        overlays['large-%d'%index] = c
    for name, c in overlays.items():
        c['unit_of_work'] = {'description':'one nbGravity call (one body), one context', 'count':1}
        write(ROOT/(name+'-init.json'), c)
    objects = sorted(Path('build/card').rglob('*.o'))
    rest = {p.as_posix():sha(p) for p in objects if p.as_posix() != 'build/card/nbody/src/nbody_grav.c.o'}
    manifest = {'common_flags':'-g -fopenmp -fno-strict-aliasing -ffp-contract=off -fno-math-errno -march=knc -std=gnu99',
                'unchanged_objects':rest, 'variants':{}, 'inputs':{},
                'gravity_source_sha256':sha('third_party/milkywayathome_client/nbody/src/nbody_grav.c'),
                'upstream_revision':subprocess.check_output(['git','-C','third_party/milkywayathome_client','rev-parse','HEAD'], text=True).strip()}
    for name, original in [('small',Path('twin/capture.json')),('large',Path('twin/multicore/capture.json'))]:
        raw = read(original)
        paths = {original.parent/b['file'] for part in ['init','expected'] for b in raw[part]['memory'] if 'file' in b}
        manifest['inputs'][name] = {str(p):sha(p) for p in sorted(paths)}
    profile_hash = None
    passing = []
    for v, flags in FLAGS.items():
        out = ROOT/v
        out.mkdir(exist_ok=True)
        binary = Path('build/flags')/v/'milkyway_nbody.mic'
        manifest['variants'][v] = {'flags':flags,'binary_sha256':sha(binary),
                                  'gravity_object_sha256':sha(binary.parent/'nbody_grav.o')}
        dis = out/'app.disassembly.txt'
        with dis.open('w') as f:
            subprocess.run([DUMP, '-dr', str(binary)], stdout=f, check=True)
        if v == 'V0':
            closure = out/'closure-report.json'
            rc = command([sys.executable, HOME/'scripts/from_binary.py', binary,
                '--function','nbGravity','--with-callee','nbReportTreeIncest',
                '--with-callee','fprintf@plt','--disassembly',dis,
                '--init',ROOT/'small-init.json','--out',out/'closure.json','--report',closure])
            cr = read(closure)
            evidence['closure_attempt'] = {'exit':rc, 'summary':cr['summary'], 'unsupported':cr['unsupported']}
        row = {'name':v, 'flags':flags, 'whole_function':False, 'cases':{}}
        for case in INPUTS:
            path = out/(case+'.json')
            rc = command([sys.executable, HOME/'scripts/from_binary.py', binary, '--function','nbGravity',
                          '--disassembly',dis,'--init',ROOT/(case+'-init.json'),'--out',path,
                          '--report',out/(case+'-conversion.json')])
            if rc != 0:
                assert '<nbGravity>:' not in dis.read_text(), 'adapter failed on an existing function'
                row['cases'][case] = {
                    'extraction':{'status':'invalid_input', 'exit':rc, 'message':"function 'nbGravity' not in the disassembly"},
                    'functional':{'status':'not_run', 'message':'nbGravity has no standalone symbol at these flags; no comparable isolated call kernel'},
                    'simulate':{'status':'not_run', 'message':'no extracted kernel; no timing prediction'},
                    'instruction_count':None}
                write(ROOT/'evidence.json',dict(evidence, variants=evidence['variants']+[row]))
                continue
            k = read(path)
            k.pop('memory_default', None)  # missing input memory must be an error
            assert 'region_cut' not in k['provenance']
            write(out/(case+'-full.json'),k)
            full = twin('simulate',out/(case+'-full.json'),out/(case+'-full-simulate'),
                        '--no-issue-log','--max-seconds','240')
            if full['status'] == 'unsupported':
                records = k['streams'][0]['instructions']
                calls = [i for i,r in enumerate(records) if r['op'] == 'call' and r['ops'] == ['nbReportTreeIncest']]
                assert len(calls) == 1
                cut = calls[0]-2
                assert [r['op'] for r in records[cut:calls[0]]] == ['mov','mov']
                label = records[cut]['label']
                kept = copy.deepcopy(records[:cut])
                assert any(r['op'] == 'ret' for r in kept)
                assert any(r.get('ops') == [label] for r in kept)
                kept.append({'id':'cold_error_exit','op':'nop','ops':[],'label':label})
                k['streams'][0]['instructions'] = kept
                k['provenance']['region_cut'] = {'exit_label':label, 'unchanged_records':cut,
                    'retained_records_identical':kept[:-1] == records[:cut],
                    'reason':full['message']}
                k['provenance']['undeclared_callees'] = []
            else:
                assert full['status'] == 'ok', full['message']
                row['whole_function'] = True
            write(path,k)
            f = twin('functional',path,out/(case+'-functional'),'--trace')
            if f['status'] == 'ok':
                trace = read(out/(case+'-functional')/'trace.json')['0']
                assert not any(r['id'] == 'cold_error_exit' for r in trace)
                assert any(r['op'] == 'ret' for r in trace)
            f_summary = summarize(f)
            f_summary['cold_exit_executed'] = False if f['status'] == 'ok' else None
            f_summary['region_cut'] = k['provenance'].get('region_cut')
            f_summary['full_function_attempt'] = summarize(full)
            s = twin('simulate',path,out/(case+'-simulate'),'--no-issue-log','--max-seconds','240')
            row['cases'][case] = {'functional':f_summary,'simulate':summarize(s),
                                  'instruction_count':len(k['streams'][0]['instructions'])}
            evidence['model_metadata'].update({key:value for key,value in s.get('parameters_used', {}).items() if value['status'] in ['assumed','derived']})
            if s['status'] == 'ok':
                h = s['profile']['hash']
                assert profile_hash is None or profile_hash == h
                profile_hash = h
            write(ROOT/'evidence.json',dict(evidence, variants=evidence['variants']+[row]))
        if all(c['functional']['status'] == 'ok' and c['simulate']['status'] == 'ok' for c in row['cases'].values()):
            passing.append(v)
        evidence['variants'].append(row)
    assert {p:sha(p) for p in map(Path,rest)} == {Path(p):h for p,h in rest.items()}, 'baseline objects changed'
    write(ROOT/'build-manifest.json',manifest)
    for case in INPUTS:
        batch = {'schema':'knc-twin.batch/1','name':'S5-01 '+case,'profile':PROFILE,
                 'frozen_profile_hash':profile_hash,'baseline':'V0','too_close_fraction':0.30,
                 'queue_uncertain':False,
                 'candidates':[{'name':v,'kernel':v+'/'+case+'.json'} for v in passing]}
        path = ROOT/('batch-'+case+'.json')
        write(path,batch)
        evidence['batches'][case] = twin('batch',path,ROOT/('batch-'+case),'--max-seconds','240')
    # Retain the whole function; select its tree-walk loop by its actual
    # backward branch. Interior control flow is left for schedule to assess.
    k = read(ROOT/'V0/small.json')
    recs = k['streams'][0]['instructions']
    labels = {r['label']:i for i,r in enumerate(recs) if r.get('label')}
    backs = [(labels[r['ops'][0]],i) for i,r in enumerate(recs)
             if r['op'].startswith('j') and r['op'] != 'jmp' and r.get('ops') and isinstance(r['ops'][0],str)
             and r['ops'][0] in labels and labels[r['ops'][0]] < i]
    head, back = max(backs,key=lambda x:x[1]-x[0])
    k['loop'] = {'label':recs[head]['label'],'back_branch':recs[back]['id']}
    evidence['schedule_selection'] = dict(k['loop'])
    write(ROOT/'schedule-input.json',k)
    evidence['schedule'] = twin('schedule',ROOT/'schedule-input.json',ROOT/'schedule','--method','list','--max-states','4096')
    # The top nonbaseline candidate is chosen by batch output, not hand ranking.
    ranking = evidence['batches']['small']['prediction']['ranking']
    top = next(v for v in ranking if v != 'V0')
    evidence['top_candidate'] = top
    for v in ['V0',top]:
        evidence['native'].append(twin('prepare-native', ROOT/v/'small.json', ROOT/('native-'+v),
                                      '--prediction', ROOT/v/'small-simulate/result.json'))
    write(ROOT/'evidence.json', evidence)
    print('Fixed inputs: '+', '.join(INPUTS))
    print('All-input passing variants: '+', '.join(passing))
    print('Batch top nonbaseline candidate for native A/B: '+top)

if __name__ == '__main__':
    main()
