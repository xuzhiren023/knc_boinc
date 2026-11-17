"""Capture each real initial large tree; stop our host process after snapshot.

The full exactness runs are separate. This is a capture, never a completed run
or a timing sample. No binary, inputs, tree fields or FP operations are modified.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import s8_integration as harness
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'build/s10-memory'
for variant in ('base',):
    exe=B/('x86-'+variant+'/milkyway_nbody.exe')
    prefix=B/('capture-'+variant)
    provenance=B/('capture-'+variant+'-provenance.json')
    binary_sha=sha256(exe.read_bytes()).hexdigest()
    if provenance.exists():
        old=json.loads(provenance.read_text(encoding='utf-8'))
        if (old['binary_sha256']==binary_sha and all(Path(str(prefix)+x).exists() for x in ('.json','.bin')) and
            old['snapshot_sha256']==sha256(Path(str(prefix)+'.bin').read_bytes()).hexdigest() and
            old['metadata_sha256']==sha256(Path(str(prefix)+'.json').read_bytes()).hexdigest()):
            print('Retained complete tree capture '+variant,flush=True);continue
    out=B/('capture-run-'+variant);out.mkdir(exist_ok=True)
    args=harness.arguments('large',1)
    for flag in ('-f','-h'):
        i=args.index(flag)+1;args[i]=str(ROOT/args[i])
    command=[str(exe),'-z',str(out/'histogram.txt'),'-c',str(out/'checkpoint')]+args
    env=dict(os.environ,OMP_NUM_THREADS='1',OMP_DYNAMIC='FALSE',OMP_WAIT_POLICY='PASSIVE',GOMP_SPINCOUNT='0',NBODY_WALK_CAPTURE=str(prefix))
    env['PATH']='C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin'+os.pathsep+env['PATH']
    env.pop('NBODY_WALK_FORCE_DUMP',None)
    for suffix in ('.json','.bin'):
        Path(str(prefix)+suffix).unlink(missing_ok=True)
    start=time.monotonic()
    with (out/'stdout.txt').open('w') as stdout,(out/'stderr.txt').open('w') as stderr:
        process=subprocess.Popen(command,cwd=out,env=env,stdout=stdout,stderr=stderr)
        try:
            while True:
                try:
                    raw=json.loads(Path(str(prefix)+'.json').read_text(encoding='utf-8'))
                    data=Path(str(prefix)+'.bin').read_bytes()
                    end=max(b['offset']+b['length'] for b in raw['blocks'] if b)
                    if len(data)==end:break
                except (OSError,ValueError):pass
                if process.poll() is not None:raise RuntimeError('capture process exited before a complete snapshot')
                if time.monotonic()-start>120:raise RuntimeError('tree capture deadline')
                time.sleep(0.2)
        finally:
            if process.poll() is None:process.terminate()
            process.wait()
    record=dict(binary_sha256=binary_sha,command=command,host_seconds=time.monotonic()-start,
        snapshot_sha256=sha256(data).hexdigest(),metadata_sha256=sha256(Path(str(prefix)+'.json').read_bytes()).hexdigest(),
        status='complete_initial_tree_capture; process stopped by driver after snapshot closed',nbody=raw['nbody'],step=raw['step'])
    provenance.write_text(json.dumps(record,indent=2)+'\n')
    print('Captured '+variant+' (%d bodies; %.3f s host)'%(raw['nbody'],record['host_seconds']),flush=True)
