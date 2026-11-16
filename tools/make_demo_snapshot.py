#!/usr/bin/env python3
"""Convert upstream nbWriteBodies output (-o FILE) final Cartesian positions.

Both simple_output variants put type,id,x,y,z first (nbody_io.c).
Simulation time and step are supplied explicitly: upstream does not write them.
"""
import argparse
import math
import pathlib
import struct

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--time', type=float, default=0)
    parser.add_argument('--step', type=int, default=0)
    args = parser.parse_args()
    try:
        if not math.isfinite(args.time) or not 0 <= args.step < 2**64:
            raise ValueError('invalid simulation time or step')
        bodies = []
        header = False
        for line in args.input.read_text().splitlines():
            if line.lstrip().startswith('# type'):
                columns = line.lstrip('# ').split()
                if columns[:5] != ['type', 'id', 'x', 'y', 'z']:
                    raise ValueError('expected upstream Cartesian body columns')
                header = True
                continue
            if not header or not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = line.split(',')
            if len(fields) < 5:
                raise ValueError('incomplete body row')
            kind = int(fields[0]); int(fields[1])
            xyz = tuple(float(v) for v in fields[2:5])
            if not all(math.isfinite(v) for v in xyz):
                raise ValueError('nonfinite coordinate')
            bodies.append(struct.pack('<fffI', *xyz, 0 if kind < 0 else 1))
            if len(bodies) > 20000:
                raise ValueError('more than 20000 bodies')
        if not header:
            raise ValueError('missing upstream body header')
        payload = struct.pack('<6IdQd', 0x53434e4b, 1, 320048, len(bodies), 0, 0, args.time, args.step, 1.0)
        payload += b''.join(bodies) + bytes((20000-len(bodies))*16)
        args.output.write_bytes(payload)
        print('Wrote {} final-state bodies to {}'.format(len(bodies), args.output))
    except (ValueError, OSError, OverflowError, struct.error) as error:
        parser.exit(1, 'snapshot: {}\n'.format(error))
if __name__ == '__main__':
    main()
