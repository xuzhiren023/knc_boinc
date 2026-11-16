"""Disambiguate duplicate ELF local symbol display names by their addresses.

The twin parser otherwise concatenates distinct functions called p_accu.
Only objdump annotations change; addresses, bytes and instructions are retained.
"""
from pathlib import Path
import collections, json, re
p = Path('twin/card.disassembly.txt')
text = p.read_text()
headers = []
for line in text.splitlines():
    if line.endswith('>:') and ' <' in line:
        addr, name = line[:-2].split(' <',1)
        try: headers.append((int(addr,16),name))
        except ValueError: pass
counts = collections.Counter(name for addr,name in headers)
seen = set()
ranges = []
for i,(addr,name) in enumerate(headers):
    if name in seen:
        end = headers[i+1][0] if i+1<len(headers) else 2**64
        ranges.append((addr,end,name,name+'__'+hex(addr)[2:]))
    seen.add(name)
def rename(m):
    addr = int(m.group(1),16)
    name = m.group(2)
    for start,end,old,new in ranges:
        if old == name and start <= addr < end:
            return m.group(1)+' <'+new+m.group(3)+'>'
    return m.group(0)
result = re.sub('([0-9a-f]+) <([^>+]+)([^>]*)>',rename,text)
# Prove the transformation changes annotations only.
def strip_annotations(s):
    return re.sub('<[^>]*>','<>',s)
assert strip_annotations(result) == strip_annotations(text)
Path('twin/card.symbols.disassembly.txt').write_text(result)
Path('twin/symbol-aliases.json').write_text(json.dumps(ranges,indent=2)+'\n')
print('Disambiguated duplicate local symbols:',len(ranges))
