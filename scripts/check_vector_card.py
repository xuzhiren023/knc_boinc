#!/usr/bin/env python3
"""Bit-exact printed likelihood/histogram check of both card variants vs x86."""
from pathlib import Path
import re
import compare
ROOT = Path(__file__).resolve().parents[1]


def scientific_tokens(path):
    if path.is_dir():
        text = '\n'.join((path/name).read_text() for name in ('stdout.txt','stderr.txt'))
    else:
        text = path.read_text()
    likelihood = re.findall(r'<search_likelihood>\s*([^<]+?)\s*</search_likelihood>', text)
    if len(likelihood) != 1:
        raise ValueError(f'{path}: expected one likelihood')
    histogram = compare.printed_histogram(text)
    if histogram is None:
        raise ValueError(f'{path}: missing printed histogram')
    # Compare textual scientific tokens exactly, including all emitted precision.
    rows = tuple(line.split() for line in histogram.splitlines()
                 if line.strip() and not line.lstrip().startswith('#'))
    return likelihood, rows


def main():
    for case in ('medium', 'large'):
        reference = ROOT/f'runs/force-chunk/{case}-chunk196-default-t12'
        want = scientific_tokens(reference)
        for variant in ('off', 'on'):
            actual = ROOT/f'runs/card/vector/{variant}-{case}.txt'
            compare.load_run(actual)  # reject malformed or non-finite output
            if scientific_tokens(actual) != want:
                raise AssertionError(f'{actual}: differs bit-for-bit in printed tokens from {reference}')
            print(f'PASS {variant}-{case}: exact printed likelihood and histogram vs x86')
    print('Scope: all printed scientific tokens; raw acceleration bytes require a captured card replay.')


if __name__ == '__main__':
    main()
