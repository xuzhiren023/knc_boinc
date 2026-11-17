"""Reuse same-HOT objects unaffected by gravity-only switches, within this build.

No imported binaries: sources/common compile flags and HOT are identical. The
only changed defines occur exclusively in nbody_grav.c's private helper headers.
Always recompile that translation unit. Preserve make's dependency tracking.
"""
from pathlib import Path
import shutil
import sys
B=Path('build/s10-walk')
source=B/sys.argv[1]
target=B/sys.argv[2]
assert (source/'milkyway_nbody.exe').exists() or (source/'milkyway_nbody.mic').exists()
assert not target.exists(), 'seed only an absent directory'
options=(source/'.build-options').read_text(encoding='utf-8')
for setting in sys.argv[3:]:
    key,value=setting.split('=')
    assert key in ('WALK_PROFILE','WALK_PREFETCH','WALK_SCHEDULE','WALK_PROOF')
    import re
    options,n=re.subn(r'-DNBODY_'+key+r'=\d+', '-DNBODY_'+key+'='+value,options)
    assert n==1
for p in source.rglob('*'):
    rel=p.relative_to(source)
    if 'nbody_grav.c' in p.name: continue
    if p.suffix not in ('.o','.d') and p.name not in ('.phase-options','.parallel-quad','.vector-gravity'): continue
    dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.d':
        dest.write_bytes(p.read_bytes().replace(source.as_posix().encode(),target.as_posix().encode()))
        shutil.copystat(p,dest)
    else: shutil.copy2(p,dest)
shutil.copy2(source/'.build-options',target/'.build-options')
(target/'.build-options').write_bytes(options.encode())
shutil.copystat(source/'.build-options',target/'.build-options')
(target/'object-reuse.txt').write_text('Reused same-HOT common objects from '+str(source)+'; recompiled gravity.\n'+options)
print('Seeded '+str(target),flush=True)
