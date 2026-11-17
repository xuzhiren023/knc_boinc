"""Reuse common objects within this build; recompile all option consumers.

Flags differ only in ORDER/HUGEPAGES/MEMORY_PROOF; those occur exclusively in
gravity, tree, types and checkpoint through their private helper headers.
"""
from pathlib import Path
import re
import shutil
import sys
B=Path('build/s10-memory'); source=B/sys.argv[1]; target=B/sys.argv[2]
assert not target.exists()
options=(source/'.build-options').read_text()
for key,value in zip(('WALK_ORDER','WALK_HUGEPAGES','WALK_MEMORY_PROOF'),sys.argv[3:]):
    options,n=re.subn(r'-DNBODY_'+key+r'=\d+', '-DNBODY_'+key+'='+value,options)
    assert n==1
for p in source.rglob('*'):
    if any(name in p.name for name in ('nbody_grav.c','nbody_tree.c','nbody_types.c','nbody_checkpoint.c')): continue
    if p.suffix not in ('.o','.d') and p.name not in ('.phase-options','.parallel-quad','.vector-gravity'): continue
    dest=target/p.relative_to(source); dest.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.d':
        dest.write_bytes(p.read_bytes().replace(source.as_posix().encode(),target.as_posix().encode()))
        shutil.copystat(p,dest)
    else: shutil.copy2(p,dest)
(target/'.build-options').write_bytes(options.encode()); shutil.copystat(source/'.build-options',target/'.build-options')
(target/'object-reuse.txt').write_text(__doc__+'\n'+options)
