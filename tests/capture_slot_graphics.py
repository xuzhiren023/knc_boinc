"""Validate and losslessly convert the two live-slot framebuffer captures."""
import pathlib
import struct
import sys
import zlib

slot = pathlib.Path(sys.argv[1])
out = pathlib.Path(__file__).resolve().parents[1] / 'docs/img'
out.mkdir(exist_ok=True)

def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)

for mode in ('manager', 'screensaver'):
    bmp = (slot / (mode + '.bmp')).read_bytes()
    assert bmp[:2] == b'BM', 'expected real framebuffer BMP'
    offset = struct.unpack_from('<I', bmp, 10)[0]
    w, h, planes, bits, compression = struct.unpack_from('<iiHHI', bmp, 18)
    assert w >= 640 and h >= 400 and planes == 1 and bits == 24 and compression == 0
    stride = (w * 3 + 3) & ~3
    assert len(bmp) == offset + stride * h, 'truncated framebuffer'
    assert len(set(bmp[offset:])) > 32, 'blank framebuffer'
    rows = []
    for y in reversed(range(h)):
        row = bmp[offset+y*stride:offset+y*stride+w*3]
        rgb = bytearray(row)
        rgb[0::3], rgb[2::3] = row[2::3], row[0::3]
        rows.append(b'\0' + rgb)
    assert sum(row.count(bytes([4, 6, 15])) for row in rows) > w*h//2, 'missing OpenGL background'
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')
    dest = out / ('s11-' + mode + '-graphics.png')
    dest.write_bytes(png)
    print('PASS live-slot capture: %s %dx%d -> %s' % (mode, w, h, dest.relative_to(out.parent.parent)))
