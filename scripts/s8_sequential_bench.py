"""Compare existing exact host binaries sequentially after validation jobs.

No compiler or card access. Ambient laptop activity is not controlled.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s8', ROOT / 'scripts/s8_integration.py')
s8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s8)

variants = [
    ('portable-scalar', s8.BUILD / 'x86-final/milkyway_nbody.exe'),
    ('native-sse-scalar', s8.BUILD / 'x86-native/milkyway_nbody.exe'),
    ('native-sse-vector', s8.BUILD / 'x86-native/vector-bench.exe'),
    ('portable-vector', s8.BUILD / 'x86-final/vector-bench.exe'),
    ('stock-196', s8.BUILD / 'stock-196.exe'),
]
records = {}
for label, binary in variants:
    record = dict(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), cases={})
    for case in ('large', 'core-small'):
        output = s8.run(binary, case, 12, 'bench-' + label + '-' + case)
        reference = s8.copy_reference(case)
        assert s8.compare.compare(reference, output, s8.compare.TOLERANCE) == 0
        assert s8.compare.load_run(reference)[0].hex() == s8.compare.load_run(output)[0].hex()
        if label != 'stock-196':
            assert s8.compare.load_run(reference) == s8.compare.load_run(output)
        record['cases'][case] = dict(seconds=float((output / 'seconds.txt').read_text()),
                                     run=str(output.relative_to(ROOT)), bit_identical=True)
    records[label] = record
(s8.BUILD / 'sequential-benchmarks.json').write_text(json.dumps(records, indent=2) + '\n')
