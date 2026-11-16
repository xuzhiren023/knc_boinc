"""Run S5-02's matrix; compare printed and saved histogram tokens exactly."""
import concurrent.futures
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


def science(directory):
    output = '\n'.join((directory / n).read_text() for n in ('stdout.txt', 'stderr.txt'))
    tokens = re.findall(r'<search_likelihood>\s*([^<]+?)\s*</search_likelihood>', output)
    def clean(text):
        return '\n'.join(line.strip() for line in text.splitlines()
                         if line.strip() and not line.lstrip().startswith('#'))
    return tokens, clean(compare.printed_histogram(output)), clean((directory / 'histogram.txt').read_text())


def run(spec):
    case, chunk, threads, binary = spec
    out = ROOT / 'runs/force-chunk' / ('%s-chunk%s-t%s' % (case, chunk, threads))
    out.mkdir(parents=True, exist_ok=True)
    for name in ('histogram.txt', 'exit.txt'):
        (out / name).unlink(missing_ok=True)
    command = [str(ROOT / binary), '-f', 'workunits/%s/params.lua' % case,
               '-h', 'workunits/%s/input.hist' % case, '-z', str(out / 'histogram.txt'),
               '-c', str(out / 'checkpoint'), '--seed', '670828913', '--nthreads', str(threads),
               '--print-histogram', '--ignore-checkpoint', '--checkpoint-interval=-1',
               str({'small': 64, 'medium': 1024, 'large': 20000}[case])]
    (out / 'command.txt').write_text(subprocess.list2cmdline(command) + '\n')
    start = time.monotonic()
    with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OMP_DYNAMIC='FALSE',
                                OMP_NUM_THREADS=str(threads)), stdout=stdout, stderr=stderr)
    (out / 'exit.txt').write_text(str(result.returncode) + '\n')
    (out / 'seconds.txt').write_text('%.3f\n' % (time.monotonic() - start))
    if result.returncode:
        raise RuntimeError('%s exited %s' % (out, result.returncode))
    compare.load_run(out)
    print('Completed %s' % out.name, flush=True)
    return (case, chunk, threads), out


def main():
    reference = sys.argv[1] if len(sys.argv) > 1 else 'build/x86/milkyway_nbody.exe'
    specs = [(case, 'default', 1 if case != 'large' else 12, reference)
             for case in ('small', 'medium', 'large')]
    specs += [(case, chunk, threads, 'build/x86-chunk-%d/milkyway_nbody.exe' % chunk)
              for case in ('small', 'medium') for chunk in (1, 4, 16, 128) for threads in (1, 4, 12)]
    specs += [('large', chunk, 12, 'build/x86-chunk-%d/milkyway_nbody.exe' % chunk) for chunk in (4, 128)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        runs = dict(pool.map(run, specs))
    for case, chunk, threads, _ in specs[3:]:
        ref = runs[case, 'default', 12 if case == 'large' else 1]
        out = runs[case, chunk, threads]
        print('%s chunk=%s threads=%s vs upstream default:' % (case, chunk, threads))
        if compare.compare(ref, out, compare.TOLERANCE):
            raise AssertionError('numeric comparison failed')
        if science(ref) != science(out):
            raise AssertionError('scientific tokens differ: ' + str(out))
        print('PASS bit-identical likelihood, printed histogram and saved histogram')
    print('PASS all 26 chunk/thread comparisons', flush=True)


if __name__ == '__main__':
    main()
