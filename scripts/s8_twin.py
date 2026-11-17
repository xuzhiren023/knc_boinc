"""Rank the exact reduced tree octant helper with four contexts, fixed profile.

This is a helper experiment, not a model of insertion or the complete card.
Keep unsuccessful adapter/simulator statuses; never infer timing from partials.
"""
import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/s8-09'
TWIN = Path('C:/Users/xuzhi/.claude/skills/knc-twin/scripts')
SHARED = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
records = []
start = time.monotonic()


def command(cmd, result):
    command_start = time.monotonic()
    log_path = result.parent / (result.stem + '.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('w') as log:
        status = subprocess.run([str(x) for x in cmd], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
    # The binary adapter emits --report only for unsupported conversions.
    # On success its actual retained result is the normalized --out kernel.
    if status == 0 and not result.exists() and '--out' in cmd:
        actual = Path(cmd[cmd.index('--out') + 1])
        if actual.is_file():
            result = actual
    data = json.loads(result.read_text()) if result.exists() else {}
    records.append(dict(command=[str(x) for x in cmd], exit_code=status,
                        status=data.get('status', 'ok' if status == 0 else 'no_result'),
                        host_seconds=time.monotonic() - command_start, result=str(result.relative_to(ROOT))))
    return status


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = os.environ
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    command([sys.executable, TWIN / 'knc_twin.py', 'capabilities', '--out', OUT / 'twin-capabilities', '--force'],
            OUT / 'twin-capabilities/result.json')
    init = dict(init=dict(registers={}, memory=[
        dict(addr='0x20001000', hex=struct.pack('<3d', 1., -2., 0.).hex()),
        dict(addr='0x20002000', hex=struct.pack('<3d', 0., -1., 0.).hex())]),
        numerical_policy=dict(rounding='rn', ftz=False, daz=False, x87_control_word='0x027f'),
        scenario=dict(memory=dict(type='line_tracking', cold_level='memory'), branch=dict(type='all_predicted')),
        unit_of_work=dict(count=4, description='four exact octant classifications, one per context'))
    (OUT / 'subindex-init.json').write_text(json.dumps(init))
    for opt in ('O2', 'O3'):
        obj = OUT / ('subindex-' + opt + '.o')
        subprocess.run([str(SHARED / 'gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc'), '-' + opt,
                        '-march=knc', '-ffp-contract=off', '-fno-math-errno',
                        '-fopt-info-vec-missed=' + str(OUT / ('subindex-' + opt + '-missed.txt')),
                        '-c', str(ROOT / 'probes/s8_subindex.c'), '-o', str(obj)], check=True)
        kernel_path = OUT / ('subindex-' + opt + '.json')
        report = OUT / ('subindex-' + opt + '-adapter.json')
        if command([sys.executable, TWIN / 'from_binary.py', obj, '--function', 's8_subindex',
                    '--objdump', SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump',
                    '--init', OUT / 'subindex-init.json', '--out', kernel_path, '--report', report], report):
            continue
        kernel = json.loads(kernel_path.read_text())
        code = kernel['streams'][0]['instructions']
        kernel['streams'] = [dict(context=i, instructions=copy.deepcopy(code),
            init=dict(registers=dict(rdi=hex(0x20003000 + 64*i), rsi='0x20001000', rdx='0x20002000')))
            for i in range(4)]
        kernel['expected'] = dict(memory=[dict(addr=hex(0x20003000 + 64*i), hex=struct.pack('<i', 5).hex())
                                          for i in range(4)])
        kernel['provenance']['experiment'] = 'S8-09 nbSubIndex reduced helper, not whole insertion'
        kernel_path.write_text(json.dumps(kernel, indent=2))
        for action in ('validate', 'functional', 'simulate'):
            dest = OUT / ('subindex-' + opt + '-' + action)
            args = [sys.executable, TWIN / 'knc_twin.py', action, kernel_path,
                    '--out', dest, '--force']
            if action != 'functional':
                args += ['--profile', 'card-7120-measured']
            if action == 'simulate':
                args += ['--max-seconds', '60', '--no-issue-log']
            command(args, dest / 'result.json')
    compare_out = OUT / 'subindex-compare'
    command([sys.executable, TWIN / 'knc_twin.py', 'compare',
             OUT / 'subindex-O2-simulate/result.json', OUT / 'subindex-O3-simulate/result.json',
             '--out', compare_out, '--force'], compare_out / 'result.json')
    write = dict(commands=records, host_seconds=sum(row['host_seconds'] for row in records),
                 experiment_host_seconds=time.monotonic() - start,
                 model_table_used=True, scope='four-context exact nbSubIndex reduced helper only')
    (OUT / 'twin-evidence.json').write_text(json.dumps(write, indent=2) + '\n')
    print(json.dumps(write, indent=2))


if __name__ == '__main__':
    main()
