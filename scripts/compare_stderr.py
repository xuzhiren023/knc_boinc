#!/usr/bin/env python3
"""Diff every result tag's form, preserving tag order and value whitespace.

Numbers are compared separately with compare.py. Platform/architecture in the
upstream application banner describe the executing binary and may differ.
"""
import difflib
from pathlib import Path
import re
import sys


def forms(path):
    text = Path(path).read_text()
    result = []
    for match in re.finditer(r'<([A-Za-z_]\w*)>([^<>]*)</\1>', text):
        tag, value = match[1], match[2]
        if tag == 'search_application':
            value, count = re.subn(r'(milkyway_nbody 1\.96 )\S+ \S+( double)',
                                   r'\1PLATFORM ARCH\2', value)
            assert count == 1, 'unexpected application version/banner: ' + value
        elif tag.startswith('search_likelihood'):
            assert re.fullmatch(r'-?\d+\.\d{15}', value), 'unexpected numeric form: ' + value
            value = 'NUMBER'
        result.append('<' + tag + '>' + value + '</' + tag + '>\n')
    assert sum(line.startswith('<search_likelihood>') for line in result) == 1, 'expected one likelihood'
    assert sum(line.startswith('<search_application>') for line in result) == 1, 'expected one application tag'
    return result


def main():
    a, b = sys.argv[1:]
    before, after = forms(a), forms(b)
    diff = list(difflib.unified_diff(before, after, fromfile=a, tofile=b))
    sys.stdout.writelines(diff)
    if diff:
        print('FAIL result tag forms')
        return 1
    print('PASS all {} result tag forms and order; platform/arch and likelihood values normalized'.format(len(before)))
    print(''.join(before), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
