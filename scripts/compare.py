#!/usr/bin/env python3
"""Compare run directories containing stdout.txt, stderr.txt, histogram.txt.

Likelihood: upstream nbody/tests/RunTestUnits.lua:137-139, strict abs < 1e-10.
Histogram: proposed extension of that absolute rule to every numeric field;
no upstream end-to-end histogram acceptance rule was found. Relative errors
are diagnostics only. This is a regression check, not a BOINC validator.
"""
import argparse
import math
import pathlib
import re
import sys

TOLERANCE = 1e-10


def load_run(directory):
    directory = pathlib.Path(directory)
    output = '\n'.join((directory / name).read_text() for name in
                       ('stdout.txt', 'stderr.txt') if (directory / name).exists())
    matches = re.findall(r'<search_likelihood>\s*([^<]+)\s*</search_likelihood>', output)
    if len(matches) != 1:
        raise ValueError('{}: expected exactly one search_likelihood'.format(directory))
    likelihood = float(matches[0])
    rows, metadata = [], {}
    for line in (directory / 'histogram.txt').read_text().splitlines():
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
    numbers = [likelihood] + [v for row in rows for v in row] + [v for row in metadata.values() for v in row]
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError('{}: non-finite result'.format(directory))
    return likelihood, rows, metadata


def differences(a, b):
    absolute = abs(a - b)
    scale = max(abs(a), abs(b))
    relative = absolute / scale if scale else 0.0
    return absolute, relative


def compare(a, b, tolerance):
    la, ra, ma = load_run(a)
    lb, rb, mb = load_run(b)
    if [len(row) for row in ra] != [len(row) for row in rb] or ma.keys() != mb.keys():
        raise ValueError('histogram shape/metadata mismatch')
    pairs = []
    for i, (row_a, row_b) in enumerate(zip(ra, rb)):
        # Bin mask and coordinates must match exactly: these define the schema.
        if row_a[:3] != row_b[:3]:
            raise ValueError('histogram bin identity mismatch at row {}'.format(i))
        pairs.extend(zip(row_a[3:], row_b[3:]))
    for key in ma:
        if len(ma[key]) != len(mb[key]):
            raise ValueError('histogram metadata shape mismatch: ' + key)
        pairs.extend(zip(ma[key], mb[key]))
    ld = differences(la, lb)
    hd = [differences(x, y) for x, y in pairs]
    print('likelihood: A={:.17g} B={:.17g} abs={:.17g} rel={:.17g}'.format(la, lb, *ld))
    print('histogram: rows={} max_abs={:.17g} max_rel={:.17g}'.format(len(ra), max(d[0] for d in hd), max(d[1] for d in hd)))
    passed = ld[0] < tolerance and all(d[0] < tolerance for d in hd)
    print('{} (strict absolute < {:g}; histogram tolerance is proposed)'.format('PASS' if passed else 'FAIL', tolerance))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('A', type=pathlib.Path)
    parser.add_argument('B', type=pathlib.Path)
    parser.add_argument('--tolerance', type=float, default=TOLERANCE)
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error('tolerance must be positive and finite')
    try:
        return compare(args.A, args.B, args.tolerance)
    except (OSError, ValueError) as error:
        print('FAIL: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
