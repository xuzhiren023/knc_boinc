"""Compare exact result bits, reporting the first differences; exits nonzero."""
import argparse
import json
from pathlib import Path

def read(path):
    rows = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip(): continue
        if line.startswith('{'):
            receipt=json.loads(line)
            if receipt.get('exit_code') != 0: raise ValueError('card runner did not exit successfully')
            continue
        fields = line.split()
        if len(fields) != 5: raise ValueError('invalid probe row: '+line)
        key = tuple(fields[:4])
        if key in rows: raise ValueError('duplicate probe row: '+line)
        int(fields[4],16)
        rows[key] = fields[4].lower()
    if not rows: raise ValueError('empty probe output')
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate');args=p.parse_args()
    a,b=read(args.reference),read(args.candidate)
    bad=[(k,a.get(k,'MISSING'),b.get(k,'MISSING')) for k in dict.fromkeys(list(a)+list(b)) if a.get(k)!=b.get(k)]
    for k,x,y in bad[:20]: print(' '.join(k)+': host='+x+' card='+y)
    print(f'{len(bad)} differences; host rows={len(a)}, candidate rows={len(b)}')
    return bool(bad)
if __name__=='__main__': raise SystemExit(main())
