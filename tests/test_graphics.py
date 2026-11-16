"""Snapshot converter contract and captured real window PNG (stdlib only)."""
import pathlib
import struct
import subprocess
import sys
import zlib
root = pathlib.Path(__file__).resolve().parents[1]
scratch = root / 'build/graphics'
source = scratch / 'converter-input.txt'
source.write_text('simple_output = 1\n# ignore id x y z v_x v_y v_z mass\n1, 1, 1.25, -2, 3, 0, 0, 0, 1\n0, 2, -4, 5, 6, 0, 0, 0, 1\n')
def convert(ok):
    r = subprocess.run([sys.executable, str(root/'tools/make_demo_snapshot.py'), str(source), str(scratch/'converted.snapshot'), '--time', '2.5', '--step', '42'], capture_output=True, text=True)
    assert (r.returncode == 0) == ok, r.stdout+r.stderr
convert(True)
b = (scratch/'converted.snapshot').read_bytes()
assert len(b) == 320048
assert struct.unpack_from('<4I', b) == (0x53434e4b, 1, 320048, 2)
assert struct.unpack_from('<dQd', b, 24) == (2.5, 42, 1.0)
assert struct.unpack_from('<fffI', b, 48) == (1.25, -2, 3, 0)
assert struct.unpack_from('<fffI', b, 64) == (-4, 5, 6, 1)
for bad in ['# ignore id x y z\n1, 1, nan, 0, 0\n', '# ignore id x y z\n'+ '1,1,0,0,0\n'*20001, 'not an upstream output']:
    source.write_text(bad)
    convert(False)
# OpenGL framebuffer capture from the real window, converted losslessly to PNG.
b = (scratch/'window.bmp').read_bytes()
offset = struct.unpack_from('<I', b, 10)[0]
w, h = struct.unpack_from('<ii', b, 18)
stride = (w*3+3)&~3
rows=[]
for y in reversed(range(h)):
    row=b[offset+y*stride:offset+y*stride+w*3]
    rgb=bytearray(row)
    rgb[0::3],rgb[2::3]=row[2::3],row[0::3]
    rows.append(b'\0'+rgb)
assert len(set(b[offset:])) > 32, 'blank window capture'
assert sum(row.count(bytes([4,6,15])) for row in rows) > w*h//2, 'capture must contain the OpenGL window background'
def chunk(kind, data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
(root/'docs/img').mkdir(exist_ok=True)
(root/'docs/img/knc-nbody-graphics.png').write_bytes(png)
print('PASS converter: upstream positions/type, fixed LE format, invalid/oversize rejection; window PNG')
