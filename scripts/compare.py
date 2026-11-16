#!/usr/bin/env python3
"""Compare run directories or stdout/stderr captures.

Likelihood verdict: upstream nbody/tests/RunTestUnits.lua:137-139, abs < 1e-10.
Histograms are diagnostics only. Captures use upstream --print-histogram.
"""
import argparse
import math
import pathlib
import re
import sys

TOLERANCE = 1e-10


def printed_histogram(output):
    blocks = re.findall(r'<histogram>\s*(.*?)</histogram>', output, re.S)
    if len(blocks) > 1:
        raise ValueError('ambiguous histogram capture')
    if blocks:
        return blocks[0]
    # Standalone nbPrintHistogram suppresses the BOINC-only XML wrappers.
    starts = list(re.finditer(r'(?m)^n\s*=\s*\d+\s*$', output))
    if not starts:
        return None
    if len(starts) != 1:
        raise ValueError('ambiguous standalone histogram capture')
    tail = output[starts[0].start():]
    dimensions = [re.search(r'(?m)^' + name + r'\s*=\s*(\d+)\s*$', tail)
                  for name in ('lambdaBins', 'betaBins')]
    if not all(dimensions):
        raise ValueError('missing histogram dimensions')
    expected = int(dimensions[0][1]) * int(dimensions[1][1])
    lines, count = [], 0
    for line in tail.splitlines():
        lines.append(line)
        if re.match(r'^[01]\s+', line):
            count += 1
            if count == expected:
                return '\n'.join(lines)
    raise ValueError('incomplete standalone histogram capture')


def captured_output(directory):
    directory = pathlib.Path(directory)
    return (directory.read_text() if directory.is_file() else '\n'.join(
        (directory / name).read_text() for name in ('stdout.txt', 'stderr.txt')
        if (directory / name).exists()))


def likelihood(output, directory):
    matches = re.findall(r'<search_likelihood>\s*([^<]+)\s*</search_likelihood>', output)
    if len(matches) != 1:
        raise ValueError('{}: expected exactly one search_likelihood'.format(directory))
    value = float(matches[0])
    if not math.isfinite(value):
        raise ValueError('{}: non-finite result'.format(directory))
    return value


def load_run(directory):
    directory = pathlib.Path(directory)
    output = captured_output(directory)
    result_likelihood = likelihood(output, directory)
    rows, metadata = [], {}
    histogram = printed_histogram(output)
    if histogram is None:
        histogram = (directory / 'histogram.txt').read_text()
    for line in histogram.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', '<')) or line == '!':
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            if key in metadata:
                raise ValueError('duplicate histogram metadata: ' + key)
            metadata[key] = tuple(float(x) for x in value.strip(' {}').split(','))
        else:
            row = tuple(float(x) for x in line.split())
            if len(row) < 5 or row[0] not in (0, 1):
                raise ValueError('invalid histogram row: ' + line)
            rows.append(row)
    if not rows:
        raise ValueError('{}: empty histogram'.format(directory))
    numbers = [result_likelihood] + [v for row in rows for v in row] + [v for row in metadata.values() for v in row]
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError('{}: non-finite result'.format(directory))
    return result_likelihood, rows, metadata


def differences(a, b):
    absolute = abs(a - b)
    scale = max(abs(a), abs(b))
    relative = absolute / scale if scale else 0.0
    return absolute, relative


def compare(a, b, tolerance, likelihood_only=False):
    if likelihood_only:
        la, lb = (likelihood(captured_output(p), p) for p in (a, b))
        ld = differences(la, lb)
        print('likelihood: A={:.17g} B={:.17g} abs={:.17g} rel={:.17g}'.format(la, lb, *ld))
        print('histogram: not requested (stderr-only task contract)')
        print('{} (strict absolute < {:g}; likelihood verdict)'.format(
            'PASS' if ld[0] < tolerance else 'FAIL', tolerance))
        return 0 if ld[0] < tolerance else 1
    la, ra, ma = load_run(a)
    lb, rb, mb = load_run(b)
    schema_matches = ([len(row) for row in ra] == [len(row) for row in rb]
                      and ma.keys() == mb.keys())
    pairs = []
    for i, (row_a, row_b) in enumerate(zip(ra, rb)):
        # Bin identities are diagnostics as well; likelihood alone is the verdict.
        if row_a[:3] != row_b[:3]:
            schema_matches = False
            continue
        pairs.extend(zip(row_a[3:], row_b[3:]))
    for key in ma.keys() & mb.keys():
        if len(ma[key]) != len(mb[key]):
            schema_matches = False
        pairs.extend(zip(ma[key], mb[key]))
    ld = differences(la, lb)
    hd = [differences(x, y) for x, y in pairs]
    print('likelihood: A={:.17g} B={:.17g} abs={:.17g} rel={:.17g}'.format(la, lb, *ld))
    print('histogram: rows={}/{} schema_matches={} max_abs={:.17g} max_rel={:.17g}'.format(
        len(ra), len(rb), schema_matches, max((d[0] for d in hd), default=0.0),
        max((d[1] for d in hd), default=0.0)))
    passed = ld[0] < tolerance
    print('{} (strict absolute < {:g}; likelihood verdict; histogram diagnostic only)'.format('PASS' if passed else 'FAIL', tolerance))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('A', type=pathlib.Path)
    parser.add_argument('B', type=pathlib.Path)
    parser.add_argument('--tolerance', type=float, default=TOLERANCE)
    parser.add_argument('--likelihood-only', action='store_true',
                        help='compare stderr-only tasks that request no histogram output')
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error('tolerance must be positive and finite')
    try:
        return compare(args.A, args.B, args.tolerance, args.likelihood_only)
    except (OSError, ValueError) as error:
        print('FAIL: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
