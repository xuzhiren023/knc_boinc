"""Check the actual supervisor argv and resolved outputs of each task contract."""
import os
import pathlib
import re
import shlex
import sys

def main():
    slot = pathlib.Path(sys.argv[1])
    lines = (slot / 'knc_run.sh').read_text().splitlines()
    argv = shlex.split(next(line for line in lines if line.startswith('./')))[1:-1]
    original = shlex.split(os.environ['KNC_TASK_ARGS'])
    task_argv = argv[-len(original):]
    real = sys.argv[2] == 'real-contract'
    if not real:
        assert (slot / 'bodies.data').stat().st_size > 0
        assert (slot / 'result.data').stat().st_size > 0
        assert (slot / 'bodies.out').read_text().startswith('<soft_link>')
        assert (slot / 'task.chk').read_text().startswith('<soft_link>')
    configured = re.search(r'(?m)^OMP_NUM_THREADS=(\d+)', (slot / 'knc_wrapper.cfg').read_text())[1]
    if sys.argv[2] == 'sample-contract':
        assert (slot / 'checkpoint.data').stat().st_size > 0
    # Values may change only where they name files. All options/numbers stay ordered.
    files = {'nbody_parameters.lua', 'histogram.txt', 'generated.hist', 'bodies.out',
             'task.chk', 'extra name.txt', 'params.lua', 'input.hist'}
    for i, (before, after) in enumerate(zip(original, task_argv)):
        prefix, sep, value = before.partition('=')
        if (value if sep else before) in files:
            remote = after.partition('=')[2] if sep else after
            assert remote.startswith('/') and '/task-' in remote, (before, after)
            if sep:
                assert after.startswith(prefix + '=')
        elif before.startswith('--nthreads='):
            assert after == '--nthreads=' + configured, (before, after)
        elif i and original[i-1] == '--nthreads':
            assert after == configured, (before, after)
        else:
            assert before == after, (before, after)
    assert len(argv) >= len(original)
    assert argv.count('--nthreads') + sum(a.startswith('--nthreads=') for a in argv) == 1
    assert argv.count('--checkpoint-interval=2') == (sys.argv[2] == 'sample-contract')
    assert sum(a == '--checkpoint' or a.startswith('--checkpoint=') for a in argv) == 1
    if real and sys.argv[3:] == ['--argv-only']:
        # A real 110k-body run may hit the ticket's two-hour cap. Preserve a
        # distinct argument verdict without claiming completed science output.
        assert configured == '240'
        for logical in ('nbody_parameters.lua', 'histogram.txt'):
            assert (slot / logical).read_text().startswith('<soft_link>')
        print('PASS wrapper real-contract argv: configured 240, exact seed/14 parameters/order, resolved real input names (completion not checked)')
        return
    assert 'search_likelihood' in (slot / 'nbody_stderr.txt').read_text()
    science = (slot / 'nbody_stderr.txt').read_text()
    returned = (slot / 'stderr.txt').read_text()
    tags = lambda text: re.findall(r'<(search_\w+)>\s*(.*?)\s*</\1>', text, re.S)
    assert tags(science), 'no science result tags'
    assert tags(science) == tags(returned), 'BOINC stderr lost or changed science tags'
    assert len(re.findall(r'<search_application>.*?</search_application>', returned)) == 1
    print('PASS wrapper', sys.argv[2], 'argv and resolved outputs')


if __name__ == "__main__":
    main()
