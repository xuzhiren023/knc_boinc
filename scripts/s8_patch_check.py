"""Replay all patches on pinned blobs, without downloads or Git writes."""
from pathlib import Path
import argparse
import re
import subprocess

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--correctness-only', action='store_true')
args = parser.parse_args()
upstream = root / 'third_party/milkywayathome_client_196'
prefix = 'patch-replay-correctness' if args.correctness_only else 'patch-replay'
out = root / 'build/s8-09' / prefix
number = 1
while out.exists():
    number += 1
    out = root / ('build/s8-09/' + prefix + '-%d' % number)
out.mkdir(parents=True, exist_ok=False)
patches = sorted((root / 'patches').glob('*.patch'))
all_patches = patches
if args.correctness_only:
    readme = (root / 'patches/README.md').read_text()
    names = re.findall(r'^\| `([^`]+)` \| Correctness/portability \|', readme, re.M)
    patches = [p for p in patches if p.name in names]
paths = set()
for patch in all_patches:
    paths.update(re.findall(r'^\+\+\+ b/(\S+)', patch.read_text(), re.M))
for name in sorted(paths):
    blob = subprocess.run(['git', '--no-optional-locks', '-C', str(upstream), 'show',
                           '1e640779f1cabf88aaa49e4db569cfe7e09016c4:' + name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if blob.returncode:
        assert ('--- /dev/null\n+++ b/' + name) in ''.join(p.read_text() for p in all_patches), name
        continue
    destination = out / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob.stdout)
for patch in patches:
    options = ['--binary'] if patch.name == 'zz-nbody-phase-timers.patch' else []
    with patch.open('rb') as source:
        subprocess.run(['patch'] + options + ['--batch', '-p1', '-d', str(out)], stdin=source, check=True)
if args.correctness_only:
    forbidden = ('NBODY_TREE_VARIANT', 'treePool', 'NBODY_PARALLEL_QUAD', 'NBODY_VECTOR_GRAVITY',
                 'NBODY_STATIC_INTEGRATE', 'nbody_walk_layout.h', 'NB_PHASE')
    for name in paths:
        if (out / name).exists():
            text = (out / name).read_text()
            assert not any(token in text for token in forbidden), 'optimization/instrumentation leaked: ' + name
    assert not (out / 'nbody/include/nbody_phase_timers.h').exists()
    print('PASS correctness-only baseline excludes performance and instrumentation: ' + str(out))
else:
    for name in sorted(paths):
        assert (out / name).read_text() == (upstream / name).read_text(), 'patch state differs: ' + name
    print('PASS all patches replay from pinned 1.96 blobs; complete affected source files match: ' + str(out))
