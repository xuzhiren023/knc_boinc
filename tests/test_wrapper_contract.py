"""Check the actual supervisor argv and resolved outputs of each task contract."""
import os
import pathlib
import shlex
import sys

slot = pathlib.Path(sys.argv[1])
lines = (slot / 'knc_run.sh').read_text().splitlines()
argv = shlex.split(next(line for line in lines if line.startswith('./')))[1:-1]
original = shlex.split(os.environ['KNC_TASK_ARGS'])
task_argv = argv[-len(original):]
assert (slot / 'bodies.data').stat().st_size > 0
assert (slot / 'result.data').stat().st_size > 0
assert (slot / 'bodies.out').read_text().startswith('<soft_link>')
assert (slot / 'task.chk').read_text().startswith('<soft_link>')
if sys.argv[2] == 'sample-contract':
    assert (slot / 'checkpoint.data').stat().st_size > 0
# Values may change only where they name files. All options/numbers stay ordered.
files = {'nbody_parameters.lua', 'histogram.txt', 'generated.hist', 'bodies.out',
         'task.chk', 'extra name.txt', 'params.lua', 'input.hist'}
for before, after in zip(original, task_argv):
    prefix, sep, value = before.partition('=')
    if (value if sep else before) in files:
        remote = after.partition('=')[2] if sep else after
        assert remote.startswith('/') and '/task-' in remote, (before, after)
        if sep:
            assert after.startswith(prefix + '=')
    else:
        assert before == after, (before, after)
assert len(argv) >= len(original)
assert argv.count('--nthreads') + sum(a.startswith('--nthreads=') for a in argv) == 1
assert argv.count('--checkpoint-interval=2') == (sys.argv[2] == 'sample-contract')
assert sum(a == '--checkpoint' or a.startswith('--checkpoint=') for a in argv) == 1
assert 'search_likelihood' in (slot / 'nbody_stderr.txt').read_text()
print('PASS wrapper', sys.argv[2], 'argv and resolved outputs')
